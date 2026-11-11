"""Classification ladder: (a) exchange label → (b) keyword rules → (c) cheap model, leftovers only.

classify(filing) returns a Classification and records which tier decided it, so every run can report the
split (CLAUDE.md rule 5: rules before models). When the model is unavailable (no key, quota exhausted,
error) the filing is honestly 'unclassified' with tier 'failed' — never a guess.
"""

from __future__ import annotations

import io
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

from finn.classification import exchange_map, rules
from finn.llm import LLMRequest, LLMUnavailable, Router
from finn.models import Category, EventStage, Filing
from finn.sources.nse import subject_core

log = logging.getLogger("finn.classify")

Tier = Literal["exchange", "rule", "model", "failed"]

# Exchange-label routine groups that are containers for other content (an ad can carry results or an IPO).
WEAK_ROUTINE_REASONS = {"Newspaper ad"}
# Ad subjects that say nothing about the ad's content: the PDF is the only way to know.
CONTENT_FREE_AD = re.compile(
    r"^(?:submission of )?(?:the )?(?:copy|copies) of (?:the )?news ?paper (?:publications?|advertisements?|ads?)\.?$"
    r"|^news ?paper (?:publications?|advertisements?|ads?|clippings?)\.?$|captioned subject",
    re.I,
)


@dataclass
class Classification:
    category: Category
    tier: Tier
    stage: EventStage | None = None
    hidden_reason: str | None = None
    confidence: float | None = None
    model: str | None = None
    note: str | None = None

    def apply(self, f: Filing) -> Filing:
        f.category = self.category
        f.category_source = None if self.tier == "failed" else self.tier
        f.category_model = self.model
        f.category_confidence = self.confidence
        f.stage = self.stage
        f.hidden_reason = self.hidden_reason
        return f


@dataclass
class TierStats:
    counts: Counter = field(default_factory=Counter)
    by_category: Counter = field(default_factory=Counter)
    failures: list[str] = field(default_factory=list)

    def add(self, f: Filing, c: Classification) -> None:
        self.counts[c.tier] += 1
        self.by_category[str(c.category)] += 1
        if c.tier == "failed":
            self.failures.append(f"{f.id} {f.symbol}: {c.note}")

    def as_dict(self) -> dict:
        total = sum(self.counts.values())
        return {
            "total": total,
            "tiers": dict(self.counts),
            "tier_pct": {k: round(100 * v / total, 1) for k, v in self.counts.items()} if total else {},
            "categories": dict(self.by_category),
        }


# Subjects that say nothing about content: send the PDF's first pages to the model.
_UNINFORMATIVE = re.compile(
    r"^(general updates?|updates?|disclosure under regulation 30\b.*|action\(s\) taken or orders passed|"
    r"announcement under regulation 30.*|outcome of board meeting|board meeting held on .*|"
    r"corrigendum|disclosure of material issue|press release|change in management)\.?$",
    re.I,
)


def is_uninformative(subject: str) -> bool:
    core = subject_core(subject)
    return len(core) < 12 or bool(_UNINFORMATIVE.match(core.strip()))


CATEGORY_GUIDE = """\
results: quarterly/annual financial results, board meetings to approve results, results press releases/decks
mna: acquisitions, mergers, demergers, JVs, stake sales/purchases (incl. a subsidiary's IPO), schemes of
     arrangement, divestments
management_change: appointment/resignation/retirement of directors, CEO/CFO/KMP, auditors
litigation: court/tribunal/regulator orders, tax demands, penalties, insolvency, FDA/regulatory inspections
credit_rating: credit rating assigned/reaffirmed/upgraded/downgraded
pledging: creation/release of pledge or encumbrance on promoter shares
capex: capacity additions, new plants, commissioning, capital expenditure plans
press_release: order wins, contracts, product launches, partnerships, monthly business/sales updates
insider_trading: SAST / PIT disclosures of promoter or insider share transactions
fund_raise: QIP, preferential issue, rights issue, equity/convertible fund raising, NCD/debenture/CP
            allotments (debt raises), buyback
dividend: dividend declaration or record date
bonus_split: bonus issue, stock split
earnings_call: earnings/analyst call schedules, audio recordings, transcripts
agm_egm: AGM/EGM notices, proceedings, voting results, annual report
postal_ballot: postal ballot notices and results
investor_meetings: analyst/investor meetings or conference participation (not results calls)
routine: compliance certificates, trading-window notices, newspaper ads with no material content, ESOP
         allotments, KYC letters, policy documents, clarifications with no new business information
unclassified: genuinely impossible to tell from the text"""

SYSTEM = (
    "You classify Indian stock-exchange (NSE) corporate filings for an investor. Use ONLY the filing text or "
    "document provided — never outside knowledge about the company. Pick exactly one category from the list. "
    "Choose 'routine' for compliance boilerplate. If the text does not allow a decision, choose 'unclassified' "
    "with low confidence. 'stage' applies only to results/earnings-call filings (intimation, outcome, "
    "presentation, call, transcript) or newspaper ads; otherwise use 'other'. For 'routine', set hidden_reason "
    "to the closest group. If a filing could be either 'routine' or a material category, choose the material "
    "category: wrongly hiding a material filing is worse than showing a routine one. Categories:\n" + CATEGORY_GUIDE
)

# Hidden-drawer groups (PRODUCT.md §4). The model must pick one of these, never write its own.
HIDDEN_GROUPS = [
    "Newspaper ad", "Trading-window notice", "ESOP allotment / grant", "Compliance certificate",
    "Compliance report", "Shareholder administration", "Policy document",
    "ESG rating", "Administrative change", "Guarantee / intra-group support", "Other routine filing",
]  # fmt: skip

SCHEMA = {
    "type": "object",
    "properties": {
        # price_volume is synthetic (never a filing); excluding it also keeps cached classification calls valid.
        "category": {"type": "string", "enum": [c.value for c in Category if c != Category.price_volume]},
        "stage": {"type": "string", "enum": [s.value for s in EventStage]},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
        "hidden_reason": {"type": "string", "enum": HIDDEN_GROUPS},
    },
    "required": ["category", "stage", "confidence", "reason"],
}


def first_pages(pdf: bytes, n: int = 2) -> bytes | None:
    """Cut the first n pages (keeps the model call small). None if the bytes aren't a readable PDF."""
    try:
        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(io.BytesIO(pdf))
        w = PdfWriter()
        for page in reader.pages[:n]:
            w.add_page(page)
        out = io.BytesIO()
        w.write(out)
        return out.getvalue()
    except Exception as e:  # malformed/encrypted PDFs are common on exchanges
        log.warning("could not cut PDF: %s", e)
        return None


class Classifier:
    def __init__(self, router: Router | None, pdf_fetcher=None, company_names: dict[str, str] | None = None):
        """router: None disables tier (c). pdf_fetcher(url) -> bytes | None, used for uninformative subjects."""
        self.router = router
        self.pdf_fetcher = pdf_fetcher
        self.names = company_names or {}
        self.stats = TierStats()

    def classify(self, f: Filing) -> Classification:
        c = self._classify(f)
        self.stats.add(f, c)
        return c

    def _classify(self, f: Filing) -> Classification:
        core = subject_core(f.subject)
        label_a = exchange_map.lookup(f.exchange_category)
        if label_a:
            # A weak routine label (e.g. "Copy of Newspaper Publication") yields to a material subject rule.
            if label_a.category == Category.routine and label_a.hidden_reason in WEAK_ROUTINE_REASONS:
                if better := rules.prefer_material(core, label_a):
                    rule, lab = better
                    note = f"rule={rule.name} (material over desc={f.exchange_category})"
                    return Classification(lab.category, "rule", lab.stage, None, note=note)
            c = Classification(label_a.category, "exchange", label_a.stage, label_a.hidden_reason,
                               note=f"desc={f.exchange_category}")  # fmt: skip
            return self._read_ad_if_blind(f, core, c)
        if rules.CLARIFICATION.search(core) or rules.CLARIFICATION.search(f.exchange_category):
            c = self._model(f, core)
            c.stage = EventStage.clarification
            return c
        hit = rules.match(f.exchange_category, core)
        if hit:
            rule, lab = hit
            c = Classification(lab.category, "rule", lab.stage, lab.hidden_reason, note=f"rule={rule.name}")
            return self._read_ad_if_blind(f, core, c)
        return self._model(f, core)

    def _read_ad_if_blind(self, f: Filing, core: str, routine_ad: Classification) -> Classification:
        """A newspaper ad whose subject names nothing ('Copy of Newspaper Publication') can carry results or an
        IPO notice: read its first PDF pages with the model (material over routine). Keeps the routine label
        when there's no model or no readable PDF; if the model is unavailable the filing is marked for retry."""
        if not (routine_ad.category == Category.routine and routine_ad.stage == EventStage.newspaper_ad):
            return routine_ad
        if not CONTENT_FREE_AD.search(core) or self.router is None or not (f.attachment_url and self.pdf_fetcher):
            return routine_ad
        raw = self.pdf_fetcher(f.attachment_url)
        pdf = first_pages(raw) if raw else None
        if not pdf:
            return routine_ad
        c = self._model(f, core, pdf=pdf, hint="This is a newspaper advertisement whose subject names nothing. "
                        "Classify by what the advertisement is about (e.g. financial results, an AGM notice, a "
                        "subsidiary's IPO); choose 'routine' only if it carries no material information.")  # fmt: skip
        if c.tier == "failed":
            # Hidden for now, but recorded as a model failure so the next run retries it.
            return Classification(Category.routine, "failed", EventStage.newspaper_ad, routine_ad.hidden_reason,
                                  note=c.note)  # fmt: skip
        c.stage = EventStage.newspaper_ad
        if c.category == Category.routine:
            c.hidden_reason = routine_ad.hidden_reason
        return c

    def _model(self, f: Filing, core: str, pdf: bytes | None = None, hint: str | None = None) -> Classification:
        if self.router is None:
            return Classification(Category.unclassified, "failed", note="model tier disabled")
        name = self.names.get(f.symbol, f.symbol)
        prompt = (
            f"Company: {name} (NSE: {f.symbol})\nExchange category: {f.exchange_category}\n"
            f"Subject: {f.subject}\nFiled: {f.filed_at.date().isoformat()}"
        )
        pdf_required = pdf is not None
        if pdf is None and is_uninformative(f.subject) and f.attachment_url and self.pdf_fetcher:
            raw = self.pdf_fetcher(f.attachment_url)
            pdf = first_pages(raw) if raw else None
            if pdf:
                prompt += "\nThe subject is uninformative: classify from the attached first pages of the filing."
        if hint:
            prompt += "\n" + hint
        req = LLMRequest(purpose="classify_filing", system=SYSTEM, prompt=prompt, schema=SCHEMA, pdf=pdf,
                         pdf_required=pdf_required)  # fmt: skip
        try:
            res = self.router.run("cheap", req)
        except LLMUnavailable as e:
            if "refused" in str(e):  # a content refusal is permanent; only 'llm unavailable…' failures are retried
                return Classification(Category.unclassified, "failed", note=f"model refused: {e}"[:300])
            return Classification(Category.unclassified, "failed", note=f"llm unavailable: {e}"[:300])
        d = res.data
        try:
            cat = Category(d.get("category", "unclassified"))
        except ValueError:
            return Classification(Category.unclassified, "failed", note=f"model gave unknown category {d}"[:300])
        try:
            stage = EventStage(d["stage"]) if d.get("stage") else None
        except ValueError:
            stage = None
        # Thread stages only mean something inside a results thread (plus newspaper ads / clarifications).
        if stage == EventStage.other or (
            cat not in (Category.results, Category.earnings_call)
            and stage not in (EventStage.newspaper_ad, EventStage.clarification)
        ):
            stage = None
        conf = d.get("confidence")
        conf = max(0.0, min(1.0, float(conf))) if isinstance(conf, int | float) else None
        hidden = None
        if cat == Category.routine:
            hidden = d.get("hidden_reason") if d.get("hidden_reason") in HIDDEN_GROUPS else "Other routine filing"
        return Classification(cat, "model", stage, hidden, conf, res.model,
                              note=(d.get("reason") or "")[:300] + (" [pdf]" if pdf else ""))  # fmt: skip
