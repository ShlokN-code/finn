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
    "You add to an executive's professional background from web search snippets. Use ONLY the snippets. "
    "Extract only what the filing does NOT already say (listed under 'Already known'): earlier roles, the years "
    "of a role the filing names without dates, qualifications, notable achievements (awards, turnarounds, "
    "launches, boards). Skip snippets that merely report this appointment or restate the filing. Prefer, in "
    "order: professional profiles, company leadership/bio pages, prior employers' pages, then news. Each item "
    "cites its snippet number and a verbatim quote from that snippet (≤ 30 words). If you give a role's "
    "period, the quote must include those years exactly as printed; do not calculate. Ignore snippets about a "
    "different person with the same name. Return nothing you cannot quote."
)
WEB_SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {"type": "object", "properties": {
        "kind": {"type": "string", "enum": ["role", "qualification", "achievement"]},
        "company": {"type": "string"}, "role": {"type": "string"},
        "period": {"type": "string", "description": "As printed, e.g. '2012–2018'"},
        "text": {"type": "string", "description": "qualification or achievement, short"},
        "snippet": {"type": "integer"}, "quote": {"type": "string"}}, "required": ["kind", "snippet", "quote"]}}},
    "required": ["items"],
}  # fmt: skip

# Web source kinds, in order of preference (the product owner's ranking). Decided in code from the URL.
KIND_LABEL = {"exchange_filing": "Exchange filing", "profile": "Professional profile", "bio": "Leadership/bio page",
              "prior_employer": "Prior employer", "news": "News"}  # fmt: skip
EXCHANGE_HOSTS = ("nseindia.com", "bseindia.com")
PROFILE_HOSTS = ("linkedin.com", "theorg.com", "crunchbase.com")
NEWS_HOSTS = ("economictimes", "moneycontrol", "livemint", "thehindubusinessline", "thehindu", "business-standard",
              "financialexpress", "ndtv", "reuters", "bloomberg", "cnbc", "zeebiz", "indianexpress",
              "hindustantimes", "businesstoday", "timesofindia", "forbesindia", "fortuneindia", "telecomtalk",
              "medianama", "inc42", "yourstory", "news")  # fmt: skip
_BIO_PATH = re.compile(r"/(leadership|board|management|team|people|our-team|directors?|about|bio|profile|"
                       r"executives?|governance)\b", re.I)  # fmt: skip


_GENERIC = {
    "electric",
    "power",
    "steel",
    "motors",
    "finance",
    "financial",
    "energy",
    "industries",
    "holdings",
    "capital",
    "services",
    "technologies",
    "systems",
    "global",
    "group",
    "international",
    "solutions",
    "foods",
    "pharma",
    "pharmaceuticals",
    "chemicals",
    "cement",
    "electronics",
    "engineering",
    "consumer",
    "products",
    "retail",
    "networks",
    "communications",
    "telecom",
    "infra",
    "infrastructure",
    "bank",
}


def _owns(host: str, name: str) -> bool:
    """Does this host look like `name`'s own website? (joined name, or a distinctive word ≥ 5 letters — so
    'airtel.in' is Bharti Airtel's, but 'jswsteel.in' isn't Tata Steel's)"""
    key = company_key(name)
    if not key:
        return False
    h = re.sub(r"[^a-z0-9]", "", host.rsplit(".", 1)[0])
    return key.replace(" ", "") in h or any(len(w) >= 5 and w not in _GENERIC and w in h for w in key.split())


def source_kind(url: str, company: str, prior_companies: list[str]) -> str:
    from urllib.parse import urlparse

    u = urlparse(url)
    host, path = u.netloc.lower().removeprefix("www."), u.path.lower()
    if any(host == d or host.endswith("." + d) for d in EXCHANGE_HOSTS):
        return "exchange_filing"  # another filing (e.g. a postal-ballot notice with the director's profile)
    if any(host == d or host.endswith("." + d) for d in PROFILE_HOSTS):
        return "profile"
    if any(n in host for n in NEWS_HOSTS):
        return "news"
    if _owns(host, company) and _BIO_PATH.search(path):
        return "bio"
    if any(_owns(host, c) for c in prior_companies):
        return "prior_employer"
    return "bio" if _BIO_PATH.search(path) else "news"


_SUFFIX = re.compile(r"\b(limited|ltd|private|pvt|india|the|co|company|corporation|corp|inc|plc)\b\.?", re.I)


def company_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _SUFFIX.sub(" ", name.lower())).strip()


def same_company(a: str, b: str) -> bool:
    ka, kb = company_key(a), company_key(b)
    return bool(ka and kb) and (ka in kb or kb in ka)


_QWORDS = re.compile(r"[a-z]{3,}")
_QSTOP = {"from", "the", "and", "degree", "holds", "bachelor", "master", "university", "institute", "college",
          "with", "his", "her", "has", "also", "school", "management", "business", "administration"}  # fmt: skip


def _words(x: str) -> set[str]:
    return set(_QWORDS.findall(x.lower())) - _QSTOP


def restates(fact: str, known: str) -> bool:
    """Every distinctive word of `fact` is already in `known` — it adds nothing."""
    w = _words(fact)
    return bool(w) and w <= _words(known)


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
        person = PersonProfile(name=p["name"][:120], role=(p.get("role") or "—")[:120],
                               change=p.get("change") or "other", prior_roles=roles, qualifications=quals,
                               insider=ins, insider_reason=why, tenure_years=ten, profile=profile)  # fmt: skip
        if substantive(person):
            people.append(person)
    return ManagementDetail(people=people, web_enrichment="not_run")


def substantive(p: PersonProfile) -> bool:
    """Not a passing mention (e.g. the company secretary who signed the letter): a real change, or something
    the filing says about them."""
    return p.change != "other" or bool(p.profile or p.prior_roles or p.qualifications or p.tenure_years)


_HONORIFIC = re.compile(r"^(mr|mrs|ms|dr|shri|smt|prof)\.?\s+", re.I)


def surname(name: str) -> str:
    parts = _HONORIFIC.sub("", name.strip()).split()
    return parts[-1].lower().strip(".,") if parts else ""


def _around(content: str, quote: str, width: int = 250) -> str:
    """The snippet text around where the quote sits (whole snippet if it can't be located exactly)."""
    low, q = content.lower(), (quote or "").lower().strip()
    i = low.find(q[:40]) if q else -1
    return content if i < 0 else content[max(0, i - width) : i + len(q) + width]


def about_person(name: str, sn: dict, quote: str) -> bool:
    """The fact is tied to this person: their surname is in the snippet's title (a profile page) or near the
    quote (a board page listing several directors must name them next to the role)."""
    sur = surname(name)
    if len(sur) < 2:
        return False
    pat = re.compile(rf"\b{re.escape(sur)}\b", re.I)
    return bool(pat.search(sn.get("title") or "") or pat.search(_around(sn["content"], quote)))


def _snippets(p: PersonProfile, company: str) -> list[dict]:
    """General search + a LinkedIn-scoped one (snippets only), merged by URL, best source kind first."""
    general = tavily.search(f'"{p.name}" {company} {p.role}', max_results=5)
    profiles = tavily.search(f'"{p.name}" {company_key(company)}', max_results=3, include_domains=["linkedin.com"])
    seen, out = set(), []
    prior = [r.company for r in p.prior_roles]
    for sn in profiles + general:
        if sn["url"] in seen or not sn.get("content"):
            continue
        seen.add(sn["url"])
        out.append({**sn, "kind": source_kind(sn["url"], company, prior)})
    order = list(KIND_LABEL)
    return sorted(out, key=lambda x: order.index(x["kind"]))[:7]


def enrich(router: Router, detail: ManagementDetail, company: str) -> ManagementDetail:
    """Add web background for appointees — only what the filing doesn't already say, each fact labelled
    'web · unverified' with its snippet URL. Never fails the card: any problem → 'unavailable'."""
    if not tavily.available():
        return detail.model_copy(update={"web_enrichment": "unavailable", "web_note": "TAVILY_API_KEY not set"})
    people, kinds = [], {}
    try:
        for p in [x for x in detail.people if substantive(x)]:
            if p.change not in ("appointed", "re_designated"):
                people.append(p)
                continue
            snippets = _snippets(p, company)
            if not snippets:
                people.append(p)
                continue
            body = "\n\n".join(f"[{i}] ({KIND_LABEL[s['kind']]}) {s['title']} — {s['url']}\n{s['content'][:1200]}"
                                for i, s in enumerate(snippets))  # fmt: skip
            known = [f"role: {r.role or ''} at {r.company}" + (f" ({r.start_year}–{r.end_year or ''})"
                                                                 if r.start_year else " (no dates)")
                     for r in p.prior_roles] + [f"qualification: {q.text}" for q in p.qualifications]  # fmt: skip
            if p.profile:
                known.append(f"profile: {p.profile.text}")
            prompt = (f"Person: {p.name}, {p.role} at {company}\n\nAlready known (from the filing):\n"
                      + ("\n".join(known) or "(nothing)") + f"\n\nSnippets:\n{body}")  # fmt: skip
            req = LLMRequest(purpose="management_web", system=WEB_SYSTEM, prompt=prompt, schema=WEB_SCHEMA,
                             max_output_tokens=900)  # fmt: skip
            items = router.run("cheap", req).data.get("items") or []
            p2, added = _apply_web(p, items, snippets)
            for k in added:
                kinds[k] = kinds.get(k, 0) + 1
            people.append(p2)
    except (tavily.TavilyUnavailable, LLMUnavailable) as e:
        return detail.model_copy(update={"web_enrichment": "unavailable", "web_note": str(e)[:200]})
    found = sum(kinds.values())
    note = ", ".join(f"{n} from {KIND_LABEL[k].lower()}" for k, n in kinds.items())
    web_note = (
        (f"{found} web item(s), unverified" + (f": {note}" if note else ""))
        if found
        else ("Web search found nothing the filing doesn't already say")
    )
    return detail.model_copy(update={"people": people, "web_enrichment": "done" if found else "nothing_found",
                                     "web_note": web_note})  # fmt: skip


def _apply_web(p: PersonProfile, items: list[dict], snippets: list[dict]) -> tuple[PersonProfile, list[str]]:
    """Code-side checks on the model's web items: quote must be in its snippet; drop anything the filing (or an
    earlier web item) already says; dates for a filing role only fill a gap."""
    roles, quals, achievements = list(p.prior_roles), list(p.qualifications), list(p.achievements)
    profile_text = p.profile.text if p.profile else ""
    added: list[str] = []
    for it in items:
        i = it.get("snippet")
        if not isinstance(i, int) or not 0 <= i < len(snippets):
            continue
        sn = snippets[i]
        if not quote_in_text(it.get("quote"), sn["content"]):
            continue  # citation checker: unquotable → dropped
        if not about_person(p.name, sn, it["quote"]):
            continue  # e.g. a generic 'Independent Director' line from a page listing several people
        c = Citation(source_type="web_profile", url=sn["url"], title=f"{KIND_LABEL[sn['kind']]} · {sn['title']}"[:120],
                     quote=it["quote"][:300], retrieved_at=datetime.now(UTC))  # fmt: skip
        kind = it.get("kind")
        if kind == "role" and it.get("company"):
            s, e = years(it.get("period"))
            if any(y is not None and str(y) not in it["quote"] for y in (s, e)):
                s = e = None  # dates must be in the quoted text itself: list-like snippets (LinkedIn) put a
                # neighbouring role's years close by, so "nearby" isn't proof — no quoted date, no date
            hit = next((k for k, r in enumerate(roles) if same_company(r.company, it["company"])), None)
            if hit is not None:
                r = roles[hit]
                if r.start_year is None and s is not None:  # the web supplies the tenure the filing omits
                    roles[hit] = r.model_copy(update={"start_year": s, "end_year": e, "period_citation": c})
                    added.append(sn["kind"])
                continue
            roles.append(PriorRole(company=it["company"][:120], role=it.get("role") or None, start_year=s,
                                   end_year=e, source="web", citation=c))  # fmt: skip
            added.append(sn["kind"])
        elif kind == "qualification" and it.get("text"):
            if any(same_qualification(q.text, it["text"]) for q in quals) or restates(it["text"], profile_text):
                continue
            quals.append(Claim(text=it["text"][:160], status="unverified", citations=[c]))
            added.append(sn["kind"])
        elif kind == "achievement" and it.get("text"):
            if restates(it["text"], profile_text) or any(restates(it["text"], a.text) for a in achievements):
                continue
            achievements.append(Claim(text=it["text"][:200], status="unverified", citations=[c]))
            added.append(sn["kind"])
    return p.model_copy(update={"prior_roles": roles, "qualifications": quals, "achievements": achievements}), added


def so_what(detail: ManagementDetail) -> str | None:
    p = next((x for x in detail.people if x.change == "appointed"), None) or (detail.people[0] if detail.people
                                                                               else None)  # fmt: skip
    if p is None:
        return None
    if p.change == "appointed":
        who = "insider" if p.insider else "outside hire" if p.insider is False else "new"
        return f"New {p.role.split(',')[0][:40]}: {who}"[:80]
    return f"{p.role.split(',')[0][:40]} {p.change.replace('_', '-')}"
