"""Ask (Phase 5): a question about one company, answered from its dossier's facts and its own documents.

Retrieval is code: the dossier's numbered facts (computed figures, ledger verdicts, analyst themes — the same list
REDUCE writes from) plus the best BM25 passages from the company's transcripts and decks already stored in
`research_doc_text`. One Flash-Lite call (Groq fallback; never the strong tier) reads them and answers in ≤ 2
sentences, citing fact ids and verbatim passage quotes. Code then:

- keeps only cited facts that exist and passage quotes found in that passage's text;
- refuses any number in the answer that isn't printed in a cited fact or quote (the model reads, code calculates);
- without a surviving citation, answers "Not found in sources".

Cost guards: answers are cached per (symbol, normalised question, dossier version); a visitor (salted daily hash of
the client IP) gets ASK_VISITOR_DAILY new answers per IST day (cache hits are free); the router's `research.ask`
lane caps all visitors together (RESEARCH_ASK_RPD).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta

from finn.calendar import IST, ist_today, next_quota_reset, now_utc
from finn.citations import quote_in_text
from finn.llm import LLMRequest, LLMUnavailable, PostgresLLMLog, Router
from finn.models import Citation, Claim
from finn.models.research import AskAnswer, Dossier
from finn.research import store as rstore
from finn.research.bm25 import BM25, Passage, passages
from finn.research.checker import numbers_in
from finn.research.reduce import Fact, facts

log = logging.getLogger("finn.research.ask")

PROMPT_VERSION = "v1"
PURPOSE = f"research.ask.{PROMPT_VERSION}"
N_PASSAGES = 6
MAX_FACTS = 70
MAX_DOCS = 12

SYSTEM = """You answer one question about an Indian listed company for a professional investor, using ONLY the
numbered facts (computed in code from the company's filings and screener's standardised tables) and the passages
(verbatim excerpts from the company's own earnings-call transcripts and investor presentations) given below.
Never use outside knowledge, news, broker views, or anything you know about the company.
Never calculate: no sums, differences, ratios, growth rates or comparisons of your own. Copy numbers exactly as a
fact or passage prints them. If answering would need a calculation or a figure that isn't given, set found=false.
If the facts and passages don't answer the question, set found=false — saying so is the right answer.
Otherwise answer in at most 2 short sentences (under 45 words), plain and neutral, no advice.
Cite every fact id you used, and for each passage you used give its id and a quote of 8-40 words copied exactly."""

SCHEMA = {
    "type": "object",
    "properties": {
        "found": {"type": "boolean"},
        "answer": {"type": "string"},
        "fact_ids": {"type": "array", "items": {"type": "string"}},
        "passages": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "quote": {"type": "string"}}, "required": ["id", "quote"]}},
    },
    "required": ["found", "answer"],
}  # fmt: skip

_WORDS = re.compile(r"[a-z0-9%]+")
_PERIODS = re.compile(r"\b(?:Q[1-4]\s*)?FY\s?'?\d{2,4}\b|\b[HQ][1-4]\b|\b(?:19|20)\d{2}\b", re.I)


def visitor_cap() -> int:
    return int(os.environ.get("ASK_VISITOR_DAILY", "8"))


def normalise_question(q: str) -> str:
    return " ".join(_WORDS.findall(q.lower()))[:300]


def visitor_id(client_ip: str | None, today=None) -> str:
    salt = os.environ.get("ASK_SALT", "finn-ask")
    raw = f"{salt}|{client_ip or 'unknown'}|{today or ist_today()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def _next_ist_midnight(now: datetime | None = None) -> datetime:
    local = (now or now_utc()).astimezone(IST)
    return datetime.combine(local.date() + timedelta(days=1), time(0, 0), tzinfo=IST).astimezone(UTC)


# --- retrieval -------------------------------------------------------------------------------------------------


@dataclass
class Source:
    pid: str
    passage: Passage
    citation_base: dict  # source_type, url, title, retrieved_at


def load_sources(conn, symbol: str) -> list[tuple[Passage, dict]]:
    """Every passage of the company's read transcripts and decks (newest first, at most MAX_DOCS documents)."""
    rows = conn.execute(
        "select url, kind, title, period_label, call_date, sha256, fetched_at from public.research_documents "
        "where symbol = %s and status = 'read' and sha256 is not null and kind in ('transcript', "
        "'investor_presentation') order by call_date desc nulls last, fetched_at desc limit %s",
        (symbol, MAX_DOCS),
    ).fetchall()
    out = []
    for r in rows:
        pages = rstore.load_text(conn, r["sha256"])
        if not pages:
            continue
        label = r["period_label"] or (r["title"] or "").strip()
        is_deck = r["kind"] == "investor_presentation"
        meta = {
            "source_type": "investor_presentation" if is_deck else "concall_transcript",
            "url": r["url"],
            "title": f"{label} {'investor presentation' if is_deck else 'earnings call transcript'}".strip(),
            "retrieved_at": r["fetched_at"] or now_utc(),
        }
        out += [(p, meta) for p in passages(r["url"], pages)]
    return out


def retrieve(question: str, sources: list[tuple[Passage, dict]], k: int = N_PASSAGES) -> list[Source]:
    if not sources:
        return []
    meta = {id(p): m for p, m in sources}
    hits = BM25([p for p, _ in sources]).search(question, k=k)
    return [Source(f"P{i}", p, meta[id(p)]) for i, (_, p) in enumerate(hits, 1)]


def build_request(d: Dossier, question: str, fs: list[Fact], srcs: list[Source]) -> LLMRequest:
    head = f"Company: {d.name} ({d.symbol}); figures are {d.basis or 'reported'}.\n\nFacts:\n"
    fact_lines = "\n".join(f.line for f in fs[:MAX_FACTS]) or "(none)"
    pas = "\n\n".join(f"{s.pid} [{s.citation_base['title']}, page {s.passage.page}]: {s.passage.text}" for s in srcs)
    prompt = f"{head}{fact_lines}\n\nPassages:\n{pas or '(none)'}\n\nQuestion: {question.strip()}"
    return LLMRequest(purpose=PURPOSE, system=SYSTEM, prompt=prompt, schema=SCHEMA, max_output_tokens=1024,
                      timeout_s=45, tags={"symbol": d.symbol, "kind": "ask"})  # fmt: skip


# --- checking the model's answer ---------------------------------------------------------------------------------


def _numbers(text: str) -> list[float]:
    return numbers_in(_PERIODS.sub(" ", text))


def check(data: dict, question: str, fs: list[Fact], srcs: list[Source]) -> tuple[Claim | None, list, str | None]:
    """(claim, figures, reason). claim None → not found (reason says why when it isn't plain absence)."""
    if not data.get("found") or not (data.get("answer") or "").strip():
        return None, [], None
    by_id = {f.id: f for f in fs}
    by_pid = {s.pid: s for s in srcs}
    cited = [by_id[i.strip()] for i in data.get("fact_ids") or [] if i and i.strip() in by_id]
    cites: list[Citation] = [c for f in cited for c in f.citations[:2]]
    quotes: list[str] = []
    for p in data.get("passages") or []:
        s = by_pid.get((p.get("id") or "").strip())
        q = " ".join((p.get("quote") or "").split())
        if s and quote_in_text(q, s.passage.text):
            quotes.append(q)
            cites.append(Citation(page=s.passage.page, quote=q, **s.citation_base))
    if not cites:
        return None, [], None
    text = " ".join(data["answer"].split())
    support = " ".join([f.line for f in cited] + [f.display or "" for f in cited] + quotes + [question])
    have = _numbers(support)
    for n in _numbers(text):
        if not any(abs(n - h) <= max(1e-9, abs(h) * 1e-6) for h in have):
            log.info("ask: number %s not in cited sources — refused", n)
            return None, [], "unsupported_number"
    seen, uniq = set(), []
    for c in cites:
        key = (c.url, c.page, c.quote, c.locator)
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    figures = [f.figure for f in cited if f.figure is not None][:4]
    return Claim(text=text, status="verified", citations=uniq[:6]), figures, None


# --- cache and caps ----------------------------------------------------------------------------------------------


def _cached(conn, symbol: str, qn: str, version: int) -> AskAnswer | None:
    row = conn.execute(
        "update public.ask_answers set hits = hits + 1 where symbol = %s and qnorm = %s and dossier_version = %s "
        "returning payload",
        (symbol, qn, version),
    ).fetchone()
    if not row:
        return None
    payload = row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"])
    return AskAnswer.model_validate({**payload, "cached": True})


def _store(conn, symbol: str, qn: str, version: int, a: AskAnswer) -> None:
    conn.execute(
        "insert into public.ask_answers (symbol, qnorm, dossier_version, payload, model) values (%s, %s, %s, %s, %s) "
        "on conflict (symbol, qnorm, dossier_version) do update set payload = excluded.payload, "
        "model = excluded.model, created_at = now()",
        (symbol, qn, version, json.dumps(a.model_dump(mode="json", exclude={"remaining_today", "cached"})), a.model),
    )


def used_today(conn, visitor: str) -> int:
    row = conn.execute(
        "select n from public.ask_usage where visitor = %s and ist_date = %s", (visitor, ist_today())
    ).fetchone()
    return row["n"] if row else 0


def _count(conn, visitor: str) -> int:
    row = conn.execute(
        "insert into public.ask_usage (visitor, ist_date, n) values (%s, %s, 1) on conflict (visitor, ist_date) "
        "do update set n = ask_usage.n + 1 returning n",
        (visitor, ist_today()),
    ).fetchone()
    return row["n"]


# --- entry point -------------------------------------------------------------------------------------------------


def answer(conn, symbol: str, question: str, client_ip: str | None = None, router: Router | None = None) -> AskAnswer:
    question = " ".join(question.split())
    row = rstore.get_dossier_row(conn, symbol)
    d = rstore.load_dossier(row)
    if d is None:
        return AskAnswer(status="unavailable", question=question, reason="no_dossier")
    version = int(row.get("version") or 1)
    qn = normalise_question(question)
    hit = _cached(conn, symbol, qn, version)
    visitor = visitor_id(client_ip)
    left = max(0, visitor_cap() - used_today(conn, visitor))
    if hit:
        conn.commit()
        return hit.model_copy(update={"remaining_today": left})
    if left <= 0:
        return AskAnswer(status="unavailable", question=question, reason="visitor_cap",
                         resume_after=_next_ist_midnight(), remaining_today=0)  # fmt: skip

    fs = facts(d, [])
    srcs = retrieve(question, load_sources(conn, symbol))
    if not fs and not srcs:
        return AskAnswer(status="not_found", question=question, reason="no_sources", remaining_today=left)
    req = build_request(d, question, fs, srcs)
    router = router or Router.default(PostgresLLMLog(conn))
    try:
        res = router.run("cheap", req)
    except LLMUnavailable as e:
        return AskAnswer(status="unavailable", question=question,
                         reason="quota" if e.kind == "quota" else "model_unavailable",
                         resume_after=e.retry_after or next_quota_reset(),
                         remaining_today=left)  # fmt: skip
    if not res.cached:
        left = max(0, visitor_cap() - _count(conn, visitor))
    claim, figures, reason = check(res.data, question, fs, srcs)
    a = AskAnswer(status="answered" if claim else "not_found", question=question, answer=claim, figures=figures,
                  model=res.model, reason=reason, remaining_today=left)  # fmt: skip
    _store(conn, symbol, qn, version, a)
    conn.commit()
    return a
