"""Tier (a): NSE's own category label (`desc`) → FINN category, only where the label alone is unambiguous.

Coarse labels ("Updates", "General Updates", "Analysts/Institutional Investor Meet/Con. Call Updates",
"Outcome of Board Meeting", "Press Release", "Shareholders meeting", ...) are deliberately absent: they need
the subject text (tier b) or the model (tier c).
"""

from __future__ import annotations

from dataclasses import dataclass

from finn.models import Category, EventStage


@dataclass(frozen=True)
class Label:
    category: Category
    stage: EventStage | None = None
    hidden_reason: str | None = None


C, S = Category, EventStage

EXCHANGE_MAP: dict[str, Label] = {
    # management
    "change in management": Label(C.management_change),
    "appointment": Label(C.management_change),
    "resignation of director/kmp/smp": Label(C.management_change),
    "change in director(s)": Label(C.management_change),
    "cessation": Label(C.management_change),
    "resignation": Label(C.management_change),
    "retirement": Label(C.management_change),
    "demise": Label(C.management_change),
    # ratings
    "credit rating": Label(C.credit_rating),
    "credit rating- new": Label(C.credit_rating),
    "credit rating - new": Label(C.credit_rating),
    "credit rating- revision": Label(C.credit_rating),
    # M&A / restructuring
    "acquisition": Label(C.mna),
    "amalgamation/merger": Label(C.mna),
    "scheme of arrangement": Label(C.mna),
    "diversification/disinvestment": Label(C.mna),
    "sale or disposal": Label(C.mna),
    "other restructuring": Label(C.mna),
    # legal
    "pendency of litigation(s)/dispute(s) or the outcome impacting the company": Label(C.litigation),
    "action(s) initiated or orders passed": Label(C.litigation),
    "action(s) taken or orders passed": Label(C.litigation),
    "corporate insolvency resolution process": Label(C.litigation),
    "initiation of forensic audit": Label(C.litigation),
    # capital
    "qualified institutional placement": Label(C.fund_raise),
    "preferential issue": Label(C.fund_raise),
    "issue of securities": Label(C.fund_raise),
    "rights issue": Label(C.fund_raise),
    "buy back": Label(C.fund_raise),
    # business
    "bagging/receiving of orders/contracts": Label(C.press_release),
    "commencement of commercial production/operations": Label(C.capex),
    "monthly business updates": Label(C.press_release),
    "arrangements for strategic, technical, manufacturing, or marketing tie up": Label(C.press_release),
    # pledges / insider
    "pledge": Label(C.pledging),
    "disclosure of encumbrance": Label(C.pledging),
    "insider trading": Label(C.insider_trading),
    # board-meeting intimations (from the board-meetings feed)
    "board meeting: financial results": Label(C.results, S.intimation),
    "board meeting: financial results/dividend": Label(C.results, S.intimation),
    "board meeting: fund raising": Label(C.fund_raise, S.intimation),
    # routine (hidden drawer)
    "copy of newspaper publication": Label(C.routine, S.newspaper_ad, "Newspaper ad"),
    "trading window": Label(C.routine, None, "Trading-window notice"),
    "certificate under sebi (depositories and participants) regulations, 2018": Label(
        C.routine, None, "Compliance certificate"
    ),
    "esop/esos/esps": Label(C.routine, None, "ESOP allotment / grant"),
    "address change": Label(C.routine, None, "Administrative change"),
    "amendment to aoa/moa": Label(C.routine, None, "Administrative change"),
    "monitoring agency report": Label(C.routine, None, "Compliance report"),
    "statement of deviation(s) or variation(s) under reg. 32": Label(C.routine, None, "Compliance report"),
}


def lookup(exchange_category: str) -> Label | None:
    return EXCHANGE_MAP.get(" ".join(exchange_category.lower().split()))
