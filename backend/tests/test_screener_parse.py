from datetime import date

from finn.sources.screener import parse_quarters

HTML = """<html><body><section id="quarters"><p class="sub">Consolidated Figures in Rs. Crores / View Standalone</p>
<table class="data-table"><thead><tr><th></th><th>Mar 2026</th><th>Jun 2026</th><th>Sep 2026</th></tr></thead>
<tbody>
<tr><td>Sales&nbsp;+</td><td>1,484</td><td>1,094</td><td>1,350</td></tr>
<tr><td>YoY Sales growth</td><td>+18%</td><td>-16%</td><td>+2%</td></tr>
<tr><td>Operating Profit</td><td>310</td><td>193</td><td>(12)</td></tr>
<tr><td>OPM %</td><td>21%</td><td>18%</td><td></td></tr>
<tr><td>Raw PDF</td><td></td><td></td><td></td></tr>
</tbody></table></section></body></html>"""


def test_parse_quarters():
    t = parse_quarters(HTML, "X", "https://www.screener.in/company/X/consolidated/")
    assert t.basis == "consolidated"
    assert t.periods == [date(2026, 3, 31), date(2026, 6, 30), date(2026, 9, 30)]
    assert t.value("Sales", date(2026, 9, 30)) == 1350
    assert t.value("Operating Profit", date(2026, 9, 30)) == -12
    assert t.value("OPM %", date(2026, 9, 30)) is None
    assert "YoY Sales growth" not in t.rows and "Raw PDF" not in t.rows
    assert not t.has(date(2025, 12, 31))


def test_unit_must_be_crore():
    assert parse_quarters(HTML.replace("Crores", "Lakhs"), "X", "u") is None
    assert parse_quarters(HTML.replace("Consolidated Figures", "Standalone Figures"), "X", "u").basis == "standalone"
