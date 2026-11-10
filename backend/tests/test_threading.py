import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from finn.classification.ladder import Classifier
from finn.events.threader import quarter_from_text, thread
from finn.models import Filing
from finn.sources.nse import announcement_to_filing

FX = Path(__file__).parent / "fixtures"


def classified(name):
    clf = Classifier(None)
    out = []
    for row in json.loads((FX / name).read_text()):
        f = announcement_to_filing(row)
        clf.classify(f).apply(f)
        out.append(f)
    return out


def test_reliance_results_thread():
    fs = classified("b_nse_ann_RELIANCE.json")
    events, assign = thread(fs)
    ev = {e.key: e for e in events}["RELIANCE:results:Q2 FY27"]
    stages = [t.stage for t in ev.timeline]
    assert ev.title == "Q2 FY27 results" and ev.period.label == "Q2 FY27"
    for s in ("outcome", "presentation", "call", "transcript"):
        assert s in stages
    assert len(ev.timeline) >= 6
    # timeline is chronological and every member points back at the event
    assert [t.at for t in ev.timeline] == sorted(t.at for t in ev.timeline)
    assert all(assign[t.filing_id] == ev.id for t in ev.timeline)
    # the CLSA investor-meeting notice and nothing routine is threaded
    assert sum(1 for v in assign.values() if v is None) >= 1


def test_hdfcbank_management_change_filings_merge():
    events, _ = thread(classified("b_nse_ann_HDFCBANK.json"))
    mc = [e for e in events if e.category == "management_change"]
    # 27 Oct Reg-30 disclosure, 31 Oct and 6 Nov change-in-management filings: each within 7 days of the last
    assert len(mc) == 1 and len(mc[0].timeline) == 3


def test_infy_newspaper_ad_joins_results_thread():
    events, assign = thread(classified("b_nse_ann_INFY.json"))
    res = {e.key: e for e in events}["INFY:results:Q2 FY27"]
    assert "newspaper_ad" in [t.stage for t in res.timeline]


def test_threading_is_idempotent():
    fs = classified("b_nse_ann_RELIANCE.json")
    a, _ = thread(fs)
    b, _ = thread(list(reversed(fs)))
    assert [e.model_dump() for e in a] == [e.model_dump() for e in b]


def test_duplicates_are_skipped():
    fs = classified("b_nse_ann_RELIANCE.json")
    fs[0].duplicate_of = "BSE:x"
    _, assign = thread(fs)
    assert assign[fs[0].id] is None


@pytest.mark.parametrize(
    "text,qe",
    [
        ("Unaudited Financial Results for the quarter ended 30th June 2026", date(2026, 6, 30)),
        ("financial results for the period ended September 30, 2026", date(2026, 9, 30)),
        ("the financial results for the period ended Jun 30, 2026", date(2026, 6, 30)),
        ("Q1 FY2027 - Earnings Conference Call Transcript", date(2026, 6, 30)),
        ("Schedule of Conference Call for Q1FY27 financial results", date(2026, 6, 30)),
        ("results of the Company for the Half Yearly ended September 2026", date(2026, 9, 30)),
        ("Q4 FY26 results", date(2026, 3, 31)),
        ("Credit Rating", None),
    ],
)
def test_quarter_from_text(text, qe):
    assert quarter_from_text(text) == qe


def test_results_quarter_falls_back_to_filing_date():
    f = Filing(id="NSE:1", exchange="NSE", exchange_id="1", symbol="X", exchange_category="Updates",
               subject="Transcript", filed_at=datetime(2026, 11, 1, 10, tzinfo=UTC), category="earnings_call",
               stage="transcript")  # fmt: skip
    events, _ = thread([f])
    assert events[0].key == "X:results:Q2 FY27"


def test_post_results_filings_never_point_at_an_unfinished_quarter():
    # COCHINSHIP filed a Q1 transcript on 18 Sep (12 days before Q2 ended); it must not join Q2's thread.
    f = Filing(id="NSE:2", exchange="NSE", exchange_id="2", symbol="X", exchange_category="Updates",
               subject="Transcript", filed_at=datetime(2026, 9, 18, 5, tzinfo=UTC), category="earnings_call",
               stage="transcript")  # fmt: skip
    intimation = Filing(id="NSE:3", exchange="NSE", exchange_id="3", symbol="X", exchange_category="Board Meeting",
                        subject="Board meeting", filed_at=datetime(2026, 9, 20, 5, tzinfo=UTC), category="results",
                        stage="intimation")  # fmt: skip
    keys = {e.key for e in thread([f, intimation])[0]}
    assert keys == {"X:results:Q1 FY27", "X:results:Q2 FY27"}


def test_results_newspaper_ad_threads_into_its_quarter():
    ad = Filing(id="NSE:9", exchange="NSE", exchange_id="9", symbol="X", exchange_category="Newspaper",
                subject="Intimation under Regulations 33 and 47", filed_at=datetime(2026, 8, 3, 10, tzinfo=UTC),
                category="results", stage="newspaper_ad")  # fmt: skip
    events, assign = thread([ad])
    assert assign["NSE:9"] == "X:results:Q1 FY27" and events[0].timeline[0].stage == "newspaper_ad"
