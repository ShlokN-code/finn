from datetime import date

import pytest

from finn.extraction.results.compute import build_lines
from finn.extraction.results.pdf_table import find_statement, parse_rows, quarters_from_pdf

PAGE = """COCHIN SHIPYARD LIMITED
Statement of Consolidated Unaudited Financial Results for the Quarter and Half Year ended 30th September 2026
(₹ in lakhs)
Sl Particulars Quarter ended Half year ended Year ended
30.09.2026 30.06.2026 30.09.2025 30.09.2026 30.09.2025 31.03.2026
1 Revenue from operations 1,35,012.40 1,09,420.10 1,32,055.00 2,44,432.50 2,50,010.00 5,10,000.00
2 Other income (Refer Note 4) 7,100.25 6,700.00 6,950.10 13,800.25 13,000.00 27,000.00
3 Total income 1,42,112.65 1,16,120.10 1,39,005.10 2,58,232.75 2,63,010.00 5,37,000.00
4 Expenses
(c) Finance costs 2,800.00 2,500.00 2,650.00 5,300.00 5,100.00 10,500.00
(d) Depreciation and amortisation expense 3,300.00 3,200.00 3,100.00 6,500.00 6,000.00 12,800.00
Total expenses 1,17,412.65 96,120.10 1,19,005.10 2,13,532.75 2,23,010.00 4,57,000.00
5 Profit before exceptional items and tax 24,700.00 20,000.00 20,000.00 44,700.00 40,000.00 80,000.00
6 Exceptional items - - - - - -
7 Profit before tax 24,700.00 20,000.00 20,000.00 44,700.00 40,000.00 80,000.00
9 Net Profit for the period 18,500.00 15,100.00 14,900.00 33,600.00 30,000.00 60,000.00
"""
STANDALONE = PAGE.replace("Consolidated", "Standalone").replace("1,35,012.40", "1,30,000.00")


def test_find_and_parse_consolidated():
    st = find_statement([STANDALONE, PAGE], "consolidated")
    assert st.page == 2 and st.unit == "lakh"
    rows = parse_rows(st)
    assert rows["revenue"][0] == ["1,35,012.40", "1,09,420.10", "1,32,055.00"]
    assert rows["other_income"][0][0] == "7,100.25"  # "(Refer Note 4)" ignored
    assert rows["exceptional"][0] == ["0", "0", "0"]
    assert rows["pbt"][0][0] == "24,700.00"


def test_quarters_in_crore_with_page_citations():
    basis, q = quarters_from_pdf([PAGE], date(2026, 9, 30), "https://nsearchives.nseindia.com/x.pdf", None)
    assert basis == "consolidated"
    cur, prev, ya = q["current"], q["previous"], q["year_ago"]
    assert cur.get("revenue").value_cr == pytest.approx(1350.124)
    assert prev.quarter_end == date(2026, 6, 30) and ya.quarter_end == date(2025, 9, 30)
    assert ya.get("pat").value_cr == pytest.approx(149.0)
    assert cur.get("revenue").citation.page == 1 and "Revenue from operations" in cur.get("revenue").citation.quote
    ebitda = next(x for x in build_lines("standard", cur, prev, ya) if x.metric == "EBITDA")
    assert ebitda.current.value == pytest.approx(247 + 28 + 33 - 71.0025)


def test_no_unit_no_extraction():
    assert quarters_from_pdf([PAGE.replace("(₹ in lakhs)", "")], date(2026, 9, 30), "u", None) is None


def test_falls_back_to_standalone():
    basis, q = quarters_from_pdf([STANDALONE], date(2026, 9, 30), "u", None)
    assert basis == "standalone" and q["current"].get("revenue").value_cr == pytest.approx(1300.0)
