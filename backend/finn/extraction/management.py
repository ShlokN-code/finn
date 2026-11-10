"""Management-change card: the incoming person's mini-CV.

Source order (PRODUCT §4): the profile in the filing itself (SEBI LODR requires a brief profile for
appointments) → web-search snippets (Tavily; no LinkedIn). The card is complete from the filing alone; when
Tavily is missing, out of quota or fails, `web_enrichment = "unavailable"` and a later run retries.

The model only copies what is printed (names, roles, periods, quotes). Code parses years, decides insider vs
outside hire, computes tenure and checks every quote against the source text.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, date, datetime

from finn.citations import page_of, quote_in_text
from finn.llm import LLMRequest, LLMUnavailable, Router
from finn.models import Citation, Claim, Figure, ManagementDetail, PersonProfile, PriorRole
from finn.sources import tavily

log = logging.getLogger("finn.management")

SYSTEM = (
    "You extract facts about people from one Indian stock-exchange filing about a management or board change. "
    "Use ONLY the filing text — never your own knowledge. Copy names, roles, companies, periods and "
    "qualifications exactly as printed. Every quote must be verbatim from the filing (≤ 40 words). Do not "
    "calculate tenures or compare dates. Skip people who are only mentioned in passing."
)
PERSON = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "role": {"type": "string", "description": "Position, as printed"},
        "change": {"type": "string", "enum": ["appointed", "resigned", "re_designated", "retired", "other"]},
        "effective_date": {"type": "string", "description": "As printed"},
        "profile_quote": {"type": "string", "description": "Verbatim sentence(s) of the brief profile"},
        "prior_roles": {"type": "array", "items": {"type": "object", "properties": {
            "company": {"type": "string"}, "role": {"type": "string"},
            "period": {"type": "string", "description": "As printed, e.g. '2015–2020', 'since 2019'"},
            "quote": {"type": "string"}}, "required": ["company", "quote"]}},
        "qualifications": {"type": "array", "items": {"type": "object", "properties": {
            "text": {"type": "string"}, "quote": {"type": "string"}}, "required": ["text", "quote"]}},
        "joined_company": {"type": "string", "description": "When this person joined / was first appointed at "
                           "THIS company, as printed (for resignations/retirements)"},
        "joined_quote": {"type": "string"},
    },
    "required": ["name", "role", "change"],
}  # fmt: skip
SCHEMA = {"type": "object", "properties": {"people": {"type": "array", "items": PERSON}}, "required": ["people"]}

WEB_SYSTEM = (
    "You extract a person's prior roles and qualifications from web search snippets. Use ONLY the snippets. "
    "Each item must cite the snippet number it came from and a verbatim quote from that snippet (≤ 30 words). "
    "Ignore snippets about a different person with the same name. Return nothing you cannot quote. Skip "
    "anything the filing already states (listed under 'Already known'): only new roles or qualifications."
)
WEB_SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {"type": "object", "properties": {
        "kind": {"type": "string", "enum": ["role", "qualification"]}, "company": {"type": "string"},
        "role": {"type": "string"}, "period": {"type": "string"}, "text": {"type": "string"},
        "snippet": {"type": "integer"}, "quote": {"type": "string"}}, "required": ["kind", "snippet", "quote"]}}},
    "required": ["items"],
}  # fmt: skip

_SUFFIX = re.compile(r"\b(limited|ltd|private|pvt|india|the|co|company|corporation|corp|inc|plc)\b\.?", re.I)


def company_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _SUFFIX.sub(" ", name.lower())).strip()


def same_company(a: str, b: str) -> bool:
    ka, kb = company_key(a), company_key(b)
    return bool(ka and kb) and (ka in kb or kb in ka)


_QWORDS = re.compile(r"[a-z]{3,}")
_QSTOP = {"from", "the", "and", "degree", "holds", "bachelor", "master", "university", "institute", "college",
          "with", "his", "her", "has", "also", "school", "management", "business", "administration"}  # fmt: skip


def same_qualification(a: str, b: str) -> bool:
    """Same qualification restated (e.g. 'MBA from SIBM Pune' vs 'MBA from Symbiosis … (SIBM), Pune'): the
    distinctive words of the shorter one (institution, place) all appear in the longer one."""
    wa, wb = (set(_QWORDS.findall(x.lower())) - _QSTOP for x in (a, b))
    short, long_ = (wa, wb) if len(wa) <= len(wb) else (wb, wa)
    return bool(short) and short <= long_


def years(period: str | None) -> tuple[int | None, int | None]:
    ys = [int(y) for y in re.findall(r"\b(19[5-9]\d|20[0-4]\d)\b", period or "")]
    if not ys:
        return None, None
    if len(ys) == 1:
        return (
            (ys[0], None) if re.search(r"since|from|onwards|till date|present", period or "", re.I) else (ys[0], ys[0])
        )
    return min(ys), max(ys)


def insider(company: str, roles: list[PriorRole], profile: str | None) -> tuple[bool | None, str | None]:
    for r in roles:
        if same_company(r.company, company):
            return True, f"Previously {r.role or 'worked'} at {r.company}"
    if profile and re.search(r"(associated|been) with the company (since|for)|joined the company in", profile, re.I):
        return True, "Profile says they were already with the company"
    if roles:
        return False, "No earlier role at this company in the filing"
    return None, None


def tenure_years(joined: str | None, until: date) -> float | None:
    s, _ = years(joined)
    if s is None:
        return None
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?[\s\-/]+([A-Za-z]{3,9})[\s\-/,]+(\d{4})", joined or "")
    if m:
        try:
            d = datetime.strptime(f"{m.group(1)} {m.group(2)[:3]} {m.group(3)}", "%d %b %Y").date()
            return (until - d).days / 365.25
        except ValueError:
            pass
    return float(until.year - s)


def extract(router: Router, event: dict, filing: dict, text: str, pages: list[str], pdf: bytes | None,
            company: str) -> ManagementDetail | None:  # fmt: skip
    """Filing → ManagementDetail (no web yet). None when the model is unavailable (retried next run)."""
    prompt = (f"Company: {company} (NSE: {event['symbol']})\nSubject: {filing['subject']}\n"
              f"Filed: {filing['filed_at']:%Y-%m-%d}\n")  # fmt: skip
    prompt += ("\nFiling text:\n" + text[:20000]) if text else "\n(Filing attached as PDF.)"
    req = LLMRequest(purpose="management_profile", system=SYSTEM, prompt=prompt, schema=SCHEMA,
                     pdf=None if text else pdf, pdf_required=not text and bool(pdf),
                     max_output_tokens=1500)  # fmt: skip
    try:
        d = router.run("cheap", req).data
    except LLMUnavailable as e:
        log.info("management extraction unavailable: %s", e)
        return None
    return build_detail(d, event, filing, text or filing["subject"], pages, company)


def build_detail(d: dict, event: dict, filing: dict, source: str, pages: list[str], company: str) -> ManagementDetail:
    now = datetime.now(UTC)
    url = filing.get("attachment_url") or ""

    def cite(quote: str | None) -> Citation | None:
        if not url:
            return None
        ok = bool(quote) and quote_in_text(quote, source)
        return Citation(source_type="exchange_filing", url=url, title=filing["subject"][:120], exchange="NSE",
                        page=page_of(quote, pages) if ok and pages else None, quote=quote[:300] if ok else None,
                        published_at=filing["filed_at"], retrieved_at=now)  # fmt: skip

    people: list[PersonProfile] = []
    for p in d.get("people") or []:
        if not p.get("name"):
            continue
        roles = []
        for r in p.get("prior_roles") or []:
            if not r.get("company") or not quote_in_text(r.get("quote"), source) or not (c := cite(r.get("quote"))):
                continue  # unquotable role → dropped (citation checker)
            s, e = years(r.get("period"))
            roles.append(PriorRole(company=r["company"][:120], role=(r.get("role") or None), start_year=s,
                                   end_year=e, source="filing", citation=c))  # fmt: skip
        quals = [Claim(text=q["text"][:160], status="verified", citations=[c])
                 for q in p.get("qualifications") or []
                 if q.get("text") and quote_in_text(q.get("quote"), source)
                 and (c := cite(q.get("quote")))]  # fmt: skip
        prof = p.get("profile_quote")
        profile = (Claim(text=prof[:600], status="verified", citations=[c])
                   if prof and quote_in_text(prof, source) and (c := cite(prof)) else None)  # fmt: skip
        ins, why = insider(company, roles, prof)
        ten = None
        if p.get("change") in ("resigned", "retired") and (y := tenure_years(p.get("joined_company"),
                                                                             filing["filed_at"].date())):  # fmt: skip
            jc = cite(p.get("joined_quote") or p.get("joined_company"))
            if jc:
                ten = Figure(label="Tenure", value=round(y, 1), unit="YEARS",
                             status="verified" if jc.quote else "unverified", citation=jc,
                             raw=p.get("joined_company"))  # fmt: skip
        people.append(PersonProfile(name=p["name"][:120], role=(p.get("role") or "—")[:120],
                                    change=p.get("change") or "other", prior_roles=roles, qualifications=quals,
                                    insider=ins, insider_reason=why, tenure_years=ten, profile=profile))  # fmt: skip
    return ManagementDetail(people=people, web_enrichment="not_run")


def enrich(router: Router, detail: ManagementDetail, company: str) -> ManagementDetail:
    """Add web-snippet roles/qualifications for appointees. Never fails the card: any problem → 'unavailable'."""
    if not tavily.available():
        return detail.model_copy(update={"web_enrichment": "unavailable", "web_note": "TAVILY_API_KEY not set"})
    people, found = [], 0
    try:
        for p in detail.people:
            if p.change not in ("appointed", "re_designated"):
                people.append(p)
                continue
            snippets = tavily.search(f'"{p.name}" {company} {p.role}', max_results=5)
            if not snippets:
                people.append(p)
                continue
            body = "\n\n".join(
                f"[{i}] {s['title']} — {s['url']}\n{s['content'][:1200]}" for i, s in enumerate(snippets)
            )
            known = [f"role: {r.role or ''} at {r.company}" for r in p.prior_roles] + [
                f"qualification: {q.text}" for q in p.qualifications
            ]
            prompt = (f"Person: {p.name}, {p.role} at {company}\n\nAlready known (from the filing):\n"
                      + ("\n".join(known) or "(nothing)") + f"\n\nSnippets:\n{body}")  # fmt: skip
            req = LLMRequest(purpose="management_web", system=WEB_SYSTEM, prompt=prompt,
                             schema=WEB_SCHEMA, max_output_tokens=800)  # fmt: skip
            items = router.run("cheap", req).data.get("items") or []
            roles, quals = list(p.prior_roles), list(p.qualifications)
            for it in items:
                i = it.get("snippet")
                if not isinstance(i, int) or not 0 <= i < len(snippets):
                    continue
                sn = snippets[i]
                if not quote_in_text(it.get("quote"), sn["content"]):
                    continue
                c = Citation(source_type="web_profile", url=sn["url"], title=sn["title"][:120],
                             quote=it["quote"][:300], retrieved_at=datetime.now(UTC))  # fmt: skip
                if it["kind"] == "role" and it.get("company"):
                    if any(same_company(r.company, it["company"]) for r in roles):
                        continue  # the filing already says it
                    s, e = years(it.get("period"))
                    roles.append(PriorRole(company=it["company"][:120], role=it.get("role") or None, start_year=s,
                                           end_year=e, source="web", citation=c))  # fmt: skip
                    found += 1
                elif it["kind"] == "qualification" and it.get("text"):
                    if any(same_qualification(q.text, it["text"]) for q in quals):
                        continue  # the filing already says it
                    quals.append(Claim(text=it["text"][:160], status="unverified", citations=[c]))
                    found += 1
            ins, why = insider(
                company, [r for r in roles if r.source == "filing"], p.profile.text if p.profile else None
            )
            people.append(p.model_copy(update={"prior_roles": roles, "qualifications": quals}))
    except (tavily.TavilyUnavailable, LLMUnavailable) as e:
        return detail.model_copy(update={"web_enrichment": "unavailable", "web_note": str(e)[:200]})
    return detail.model_copy(update={"people": people, "web_enrichment": "done" if found else "nothing_found",
                                     "web_note": f"{found} item(s) from web snippets (unverified)"})  # fmt: skip


def so_what(detail: ManagementDetail) -> str | None:
    p = next((x for x in detail.people if x.change == "appointed"), None) or (detail.people[0] if detail.people
                                                                               else None)  # fmt: skip
    if p is None:
        return None
    if p.change == "appointed":
        who = "insider" if p.insider else "outside hire" if p.insider is False else "new"
        return f"New {p.role.split(',')[0][:40]}: {who}"[:80]
    return f"{p.role.split(',')[0][:40]} {p.change.replace('_', '-')}"
