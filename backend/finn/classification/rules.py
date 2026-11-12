"""Tier (b): keyword/regex rules on the subject text (and, as weak fallbacks, the exchange label).

Rules are ordered: the first match wins. Built from ~800 real NSE subjects for the demo portfolio
(Aug–Nov 2026). Each rule has a name, logged as the classification note so wrong rules are easy to find.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from finn.classification.exchange_map import Label
from finn.models import Category, EventStage

C, S = Category, EventStage


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern
    label: Label
    on: str = "subject"  # subject | desc


def r(name: str, pattern: str, label: Label, on: str = "subject") -> Rule:
    return Rule(name, re.compile(pattern, re.I), label, on)


RESULTS_WORDS = r"(financial results?|unaudited|audited|results for the (?:quarter|period|half)|earnings)"

RULES: list[Rule] = [
    # --- results thread (order matters: transcript/audio before generic call/meet rules) ---
    r("transcript", r"\btranscript", Label(C.earnings_call, S.transcript)),
    r(
        "call_recording",
        r"audio(?![ -]?visual)|recording|video of the (?:call|meet)|webcast",
        Label(C.earnings_call, S.call),
    ),
    r(
        "results_call_schedule",
        r"(earnings?|conference|analyst|investor)[^.]{0,40}call|call[^.]{0,80}(quarter|results|earnings)",
        Label(C.earnings_call, S.call),
    ),  # fmt: skip
    r(
        "board_meeting_intimation",
        r"(intimation|notice|scheduled?|to be held|prior intimation)[^.]{0,120}board[^.]{0,80}(results?|financial)"
        r"|board.{0,80}?(scheduled|to be held|will be held|to consider).{0,220}?(results?|financial statements)",
        Label(C.results, S.intimation),
    ),  # fmt: skip
    r("results_press_release", r"press release[^.]{0,40}" + RESULTS_WORDS, Label(C.results, S.presentation)),
    # A results press release titled with the numbers instead of the word "results"
    # ("Persistent Achieves $452.4M Revenue in Q1 FY27 with 16.1% YoY Growth", "Tata Steel reports Consolidated
    # EBITDA of Rs 10,665 crores for the quarter … ended September 30"): a period plus a P&L word in a
    # press-release subject.
    r(
        "results_press_release_titled",
        r"^(?=.*press release)(?=.*(?:\b(?:Q[1-4]|H[12]|[1-4]Q)\s*'?FY\s*'?\d{2,4}\b|\b(?:quarter|half[- ]year)\b"
        r"[^.]{0,80}\bended\b))"
        r"(?=.*\b(?:revenues?|profit|pat|ebitda|margins?|net income|earnings)\b)",
        Label(C.results, S.presentation),
    ),  # fmt: skip
    r(
        "results_presentation",
        r"(investor|earnings) presentation[^.]{0,80}(quarter|results)",
        Label(C.results, S.presentation),
    ),  # fmt: skip
    r(
        "results_outcome",
        r"submitted to the exchange,? (?:the )?financial results|"
        + RESULTS_WORDS
        + r"[^.]{0,80}(quarter|period|half year|year) ended|outcome of (?:the )?board meeting[^.]{0,80}results",
        Label(C.results, S.outcome),
    ),  # fmt: skip
    r(
        "auditor_report_on_results",
        r"report of auditors? on (?:the )?financial statements",
        Label(C.results, S.outcome),
    ),
    r(
        "quarterly_report",
        r"quarterly (?:report|update) for the (?:first|second|third|fourth) quarter",
        Label(C.results, S.presentation),
    ),  # fmt: skip
    r("results_newspaper", r"regulations? 33 (?:and|&) 47|regulation 47\b", Label(C.results, S.newspaper_ad)),
    # --- routine first among the rest (cheap and frequent). Only STRONG_ROUTINE rules are final; a weak
    # routine match (e.g. a newspaper ad) gives way to any material rule that also matches. ---
    r("newspaper", r"newspaper|news ?paper clipping|advertisement", Label(C.routine, S.newspaper_ad, "Newspaper ad")),
    r("trading_window", r"trading window", Label(C.routine, None, "Trading-window notice")),
    r(
        "esop",
        r"\besop|\besos|\besps|stock option|employee stock|performance stock unit",
        Label(C.routine, None, "ESOP allotment / grant"),
    ),  # fmt: skip
    r(
        "debt_raise",
        r"non[- ]convertible|\bncds?\b|debentures?|commercial paper",
        Label(C.fund_raise),
    ),  # fmt: skip
    r(
        "shareholder_admin",
        r"\bkyc\b|physical (?:securities|shares)|tax deduct|\btds\b|iepf|duplicate share|loss of share|"
        r"transfer of physical|special window|letters? (?:sent|being sent) to shareholders",
        Label(C.routine, None, "Shareholder administration"),
    ),  # fmt: skip
    r(
        "compliance_cert",
        r"regulation 74\(5\)|regulation 40\(9\)|compliance certificate|secretarial|"
        r"reconciliation of share capital|regulation 23\(9\)|related party transactions? (?:disclosure|for the half)",
        Label(C.routine, None, "Compliance certificate"),
    ),  # fmt: skip
    r(
        "investor_meet",
        r"(analyst|investor|institutional)[^.]{0,30}(meet|meeting|conference|interaction)|schedule of (?:the )?meet",
        Label(C.investor_meetings, None, "Investor-meeting notice"),
    ),  # fmt: skip
    r(
        "policy_update",
        r"\b(?:revised|amended) policy|policy on |code of (?:conduct|fair disclosure)",
        Label(C.routine, None, "Policy document"),
    ),  # fmt: skip
    # --- corporate actions ---
    r("dividend", r"dividend", Label(C.dividend)),
    r("bonus_split", r"\bbonus\b|sub-?division|stock split|split of (?:equity )?shares", Label(C.bonus_split)),
    # --- material categories ---
    r("esg_rating", r"\besg\b", Label(C.routine, None, "ESG rating")),
    r(
        "credit_rating",
        r"credit rating|\brating\b[^.]{0,40}(crisil|icra|care|india ratings|fitch|moody)",
        Label(C.credit_rating),
    ),  # fmt: skip
    r("pledge", r"pledg|encumbrance", Label(C.pledging)),
    r(
        "insider",
        r"regulation 7\(2\)|regulation 29\(|\bsast\b|insider trading|acquisition of shares by promoter",
        Label(C.insider_trading),
    ),  # fmt: skip
    r(
        "fund_raise",
        r"qualified institution|\bqip\b|preferential (?:issue|allotment)|rights issue|fund ?rais|"
        r"raising of funds|capital raise",
        Label(C.fund_raise),
    ),  # fmt: skip
    r(
        "mna",
        r"acqui(?:re|sition)|merger|amalgamation|demerger|scheme of arrangement|divest|joint venture|"
        r"\bstake\b|incorporation of (?:a )?(?:wholly owned )?subsidiary|initial public offer|\bipo\b|"
        r"offer for sale",
        Label(C.mna),
    ),  # fmt: skip
    r(
        "litigation",
        r"\bnclt\b|\bnclat\b|high court|supreme court|\bcourt\b|litigation|penalty|show cause|"
        r"demand order|tax demand|\bgst\b|order passed|arbitra|us ?fda|warning letter|observations? \(form 483\)",
        Label(C.litigation),
    ),  # fmt: skip
    r("postal_ballot", r"postal ballot", Label(C.postal_ballot)),
    r(
        "management_change",
        r"appoint|resign|cessation|re-?appointment|\bkmp\b|chief executive|\bceo\b|\bcfo\b|"
        r"managing director|whole[- ]time director|company secretary|change in (?:directors?|management)",
        Label(C.management_change),
    ),  # fmt: skip
    r(
        "capex",
        r"commission(?:ed|ing)|capacity|capex|new (?:plant|facility)|expansion|greenfield|brownfield",
        Label(C.capex),
    ),  # fmt: skip
    r(
        "order_win",
        r"\border(?:s)?\b[^.]{0,40}(secur|receiv|bag|win|won|award)|(secur|receiv|bag|win|won|award)"
        r"[^.]{0,40}\b(?:order|contract)s?\b|letter of award",
        Label(C.press_release),
    ),  # fmt: skip
    r(
        "agm_egm",
        r"annual general meeting|\bagm\b|\begm\b|extra-?ordinary general meeting|scrutini[sz]er|"
        r"chairman'?s? speech|annual report|book closure",
        Label(C.agm_egm),
    ),  # fmt: skip
    r(
        "monthly_update",
        r"monthly business update|sales (?:volume|update|numbers)|production (?:and|&) sales",
        Label(C.press_release),
    ),  # fmt: skip
    # --- weak fallbacks on the exchange label (only when the subject matched nothing above) ---
    r("desc_press_release", r"^press release$", Label(C.press_release), on="desc"),
    r("desc_shareholders_meeting", r"^shareholders meeting$", Label(C.agm_egm), on="desc"),
    r(
        "desc_investor_presentation", r"^investor presentation$", Label(C.investor_meetings, S.presentation), on="desc"
    ),  # fmt: skip
    r("desc_record_date", r"^record date$", Label(C.dividend), on="desc"),
]


# Exchange-sought clarifications quote a news headline: keyword rules would classify the headline, not the
# filing, so these always go to the model (with stage = clarification).
CLARIFICATION = re.compile(r"sought clarification|news item|rumou?r verification|news verification", re.I)


# Routine rules whose match is final. Any other routine match is "weak": if a material rule also matches the
# subject, the material category wins (wrongly hiding a material filing is worse than showing a routine one).
STRONG_ROUTINE = {"trading_window", "esop", "shareholder_admin", "compliance_cert", "policy_update", "esg_rating"}
NOT_MATERIAL = {C.routine, C.investor_meetings, C.unclassified}
NEWSPAPER = re.compile(r"newspaper|news ?paper clipping|advertisement", re.I)


def material_match(subject: str) -> tuple[Rule, Label] | None:
    """First subject rule with a material category, if any."""
    for rule in RULES:
        if rule.on == "subject" and rule.label.category not in NOT_MATERIAL and rule.pattern.search(subject):
            return rule, rule.label
    return None


def prefer_material(subject: str, routine: Label) -> tuple[Rule, Label] | None:
    """For a weak routine label: the material rule that also matches, keeping a newspaper-ad stage."""
    m = material_match(subject)
    if m is None:
        return None
    rule, lab = m
    stage = S.newspaper_ad if routine.stage == S.newspaper_ad else lab.stage
    return rule, Label(lab.category, stage, None)


def match(exchange_category: str, subject: str) -> tuple[Rule, Label] | None:
    desc = " ".join(exchange_category.lower().split())
    for rule in RULES:
        text = subject if rule.on == "subject" else desc
        if rule.pattern.search(text):
            if rule.label.category == C.routine and rule.name not in STRONG_ROUTINE:
                if better := prefer_material(subject, rule.label):
                    return better
            if rule.label.category not in NOT_MATERIAL and rule.on == "subject" and NEWSPAPER.search(subject):
                # e.g. "Newspaper publication of the Financial Results…": the results, but as an ad
                return rule, Label(rule.label.category, S.newspaper_ad, None)
            return rule, rule.label
    return None
