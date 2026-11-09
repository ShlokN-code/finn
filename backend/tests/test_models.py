from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from finn.models import Card, Citation, Claim, Figure, Period, Promise, ScoreBreakdown
from finn.models.export_schema import build

NOW = datetime(2026, 11, 10, 6, 0, tzinfo=UTC)
CITE = Citation(
    source_type="xbrl",
    url="https://nsearchives.nseindia.com/corporate/xbrl/x.xml",
    locator="in-capmkt:ProfitBeforeTax@OneD",
    retrieved_at=NOW,
)
Q2 = Period(kind="quarter", start=date(2026, 7, 1), end=date(2026, 9, 30), label="Q2 FY27")


def fig(**kw):
    base = dict(
        label="PBT", value=11063.0, unit="INR_CR", period=Q2, basis="consolidated", status="verified", citation=CITE
    )
    return Figure(**{**base, **kw})


def test_figure_roundtrip():
    f = fig()
    assert Figure.model_validate_json(f.model_dump_json()) == f


def test_not_found_must_not_carry_a_value():
    with pytest.raises(ValidationError):
        fig(status="not_found")  # value present → rejected (never guess)
    assert fig(status="not_found", value=None, citation=None).value is None


def test_sourced_figure_needs_citation_or_inputs():
    with pytest.raises(ValidationError):
        fig(citation=None)
    computed = fig(
        label="EBITDA",
        value=11689.0,
        citation=None,
        status="verified",
        formula="PBT + finance costs + D&A − other income",
        inputs=[fig()],
    )
    assert computed.inputs


def test_claim_needs_citation():
    with pytest.raises(ValidationError):
        Claim(text="Margins expanded", status="verified")


def test_card_so_what_limit():
    score = ScoreBreakdown(category_weight=1, position_weight=1, relevance=1, novelty=1, surprise=1, total=1)
    kw = dict(
        id="e1",
        event_id="e1",
        symbol="INFY",
        card_type="results",
        category="results",
        headline="Q2 FY27 results",
        score=score,
        as_of=NOW,
    )
    Card(so_what="Margins beat guidance; deal wins steady", **kw)
    with pytest.raises(ValidationError):
        Card(so_what="one two three four five six seven eight nine ten eleven", **kw)


def test_naive_datetimes_rejected():
    with pytest.raises(ValidationError):
        Citation(source_type="xbrl", url="u", retrieved_at=datetime(2026, 11, 10))


def test_schema_exports_promise_as_mgmtpromise():
    defs = build()["$defs"]
    assert defs["Promise"]["title"] == "MgmtPromise"
    assert {"Filing", "Event", "Card", "Alert", "Holding", "Driver", "Dossier", "Citation", "Figure"} <= set(defs)
    assert Promise.model_config["extra"] == "forbid"  # inherited config survives the title override
