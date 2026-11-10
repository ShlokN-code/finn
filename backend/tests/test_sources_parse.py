import json
from datetime import date
from pathlib import Path

from finn.sources.nse import announcement_to_filing, parse_action_subject, subject_core, to_corporate_action
from finn.sources.prices import Bar, needs_restatement

FX = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FX / name).read_text())


def test_corporate_actions_from_nse_samples():
    acts = {(a.ex_date, a.kind): a for a in map(to_corporate_action, load("c_corporate_actions_BAJFINANCE.json"))}
    bonus = acts[(date(2025, 6, 16), "bonus")]
    split = acts[(date(2025, 6, 16), "split")]
    assert (bonus.ratio_new, bonus.ratio_held) == (4.0, 1.0)
    assert (split.ratio_new, split.ratio_held) == (2.0, 1.0)  # FV ₹2 → ₹1
    assert acts[(date(2025, 5, 30), "dividend")].amount_per_share == 44.0


def test_action_subject_variants():
    assert parse_action_subject("Dividend - Rs 19.50 Per Share") == {"kind": "dividend", "amount_per_share": 19.5}
    assert parse_action_subject(" Annual General Meeting/Dividend - Rs 10 Per Share")["amount_per_share"] == 10.0
    assert parse_action_subject("Bonus 1:1")["kind"] == "bonus"
    assert parse_action_subject("Something new")["kind"] == "other"


def test_announcement_to_filing():
    row = load("b_nse_ann_INFY.json")[0]
    f = announcement_to_filing(row)
    assert f.id == f"NSE:{row['seq_id']}" and f.symbol == "INFY"
    assert f.filed_at.isoformat() == "2026-11-04T15:31:37+00:00"  # 21:01:37 IST
    assert subject_core(f.subject) == "Investor Conference"


def test_subject_core_keeps_informative_subjects():
    s = "In continuation of our letter dated October 27, 2026, we wish to inform you"
    assert subject_core(s) == s


def test_restatement_detection():
    stored = {date(2026, 11, 2): 1964.10, date(2026, 11, 3): 1970.0}
    same = [Bar("X", date(2026, 11, 3), None, None, None, 1970.5, None, None)]
    halved = [Bar("X", date(2026, 11, 3), None, None, None, 985.0, None, None)]
    assert not needs_restatement(stored, same)
    assert needs_restatement(stored, halved)
