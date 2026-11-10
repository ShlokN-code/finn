import json
from pathlib import Path

import pytest

from finn.ingest.dedup import Doc, mark_duplicates, match, subject_similarity
from finn.sources import bse
from finn.sources.nse import announcement_to_filing

FX = Path(__file__).parent / "fixtures"


def docs(sym):
    nse = [Doc(announcement_to_filing(r), size_text=r.get("fileSize"))
           for r in json.loads((FX / f"b_nse_ann_{sym}.json").read_text())]  # fmt: skip
    bse_docs = [Doc(bse.announcement_to_filing(r, sym), size_bytes=bse.attachment_bytes(r))
                for r in json.loads((FX / f"b2_bse_ann_{sym}.json").read_text())]  # fmt: skip
    return nse, bse_docs


@pytest.mark.parametrize("sym,expected", [("RELIANCE", 10), ("INFY", 10), ("HDFCBANK", 9)])
def test_nse_bse_pairs(sym, expected):
    nse, b = docs(sym)
    pairs = match(nse, b)
    assert len(pairs) == expected
    for n, x in pairs:
        assert (
            abs((n.filing.filed_at - x.filing.filed_at).total_seconds()) < 2 * 3600
        )  # NSE and BSE can disseminate up to ~1 h apart (RELIANCE 31 Oct)


def test_same_size_results_pair_by_time():
    # RELIANCE 30 Oct: the 8.41 MB results PDF appears twice on each exchange; pairs must be one-to-one
    nse, b = docs("RELIANCE")
    pairs = [(n, x) for n, x in match(nse, b) if n.size_text == "8.41 MB"]
    assert len(pairs) == 2 and len({x.filing.id for _, x in pairs}) == 2


def test_hdfcbank_unmatched_filing_stays_unique():
    nse, b = docs("HDFCBANK")
    mark_duplicates(nse, b)
    lone = [d for d in nse if d.filing.filed_at.isoformat().startswith("2026-11-06T09:51")]
    assert lone and lone[0].filing.duplicate_of is None


def test_later_copy_points_at_earlier():
    nse, b = docs("INFY")
    n = mark_duplicates(nse, b)
    assert n == 10
    for d in nse + b:
        if d.filing.duplicate_of:
            other = next(x for x in nse + b if x.filing.id == d.filing.duplicate_of)
            assert other.filing.filed_at <= d.filing.filed_at and other.filing.duplicate_of is None


def test_subject_similarity():
    assert subject_similarity("Investor Presentation", "Announcement under Regulation 30 (LODR)-Investor "
                              "Presentation") >= 0.6  # fmt: skip
    assert subject_similarity("Credit Rating", "Transcript") == 0.0
