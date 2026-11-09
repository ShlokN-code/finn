"""Spike (f): does NSE expose XBRL for financial-results filings?

Findings drive the results-card design:
- Which endpoint lists results filings with XBRL links (old vs integrated filing)?
- Which periods does one XBRL instance contain (current quarter only? prior columns?)
- Units/rounding; consolidated vs standalone; bank taxonomy differences.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from lxml import etree

from _common import Result, log, nse_session, polite_get, save_sample

API = "https://www.nseindia.com/api"
NS = {"xbrli": "http://www.xbrl.org/2003/instance"}
WANT = ["RevenueFromOperations", "OtherIncome", "FinanceCosts", "DepreciationDepletionAndAmortisationExpense",
        "ProfitBeforeTax", "ProfitLossForPeriod",
        # banks
        "InterestEarned", "InterestExpended", "OperatingProfitBeforeProvisionAndContingencies",
        "ProvisionsOtherThanTaxAndContingencies", "GrossNonPerformingAssets", "PercentageOfGrossNpa"]

res = Result("f_xbrl")
s = nse_session()


def integrated_filings(sym: str) -> list[dict]:
    r = polite_get(s, f"{API}/integrated-filing-results", use_cache=False, params={
        "index": "equities", "symbol": sym, "period_ended": "all", "type": "Integrated Filing- Financials"})
    return r.json().get("data", []) if r.ok and "json" in r.headers.get("content-type", "") else []


def parse_xbrl(xml: bytes) -> dict:
    root = etree.fromstring(xml)
    ctx = {}
    for c in root.findall("xbrli:context", NS):
        p = c.find("xbrli:period", NS)
        start, end, inst = (p.findtext(f"xbrli:{k}", namespaces=NS) for k in ("startDate", "endDate", "instant"))
        dims = [m.text for m in c.iter("{http://xbrl.org/2006/xbrldi}explicitMember")]
        ctx[c.get("id")] = {"start": start, "end": end or inst, "dims": dims}
    facts: dict[str, list] = defaultdict(list)
    meta = {}
    for el in root:
        if not isinstance(el.tag, str):
            continue
        local = etree.QName(el).localname
        if local in ("NatureOfReportStandaloneConsolidated", "LevelOfRounding", "Symbol",
                     "DescriptionOfPresentationCurrency", "TypeOfReportingPeriod", "WhetherResultsAreAuditedOrUnaudited"):
            meta[local] = el.text
        if local in WANT:
            c = ctx.get(el.get("contextRef"), {})
            if not c.get("dims"):  # top-level line items only (no segment/axis members)
                facts[local].append({"ctx": el.get("contextRef"), "start": c.get("start"), "end": c.get("end"),
                                     "value_inr": float(el.text), "decimals": el.get("decimals"),
                                     "value_cr": round(float(el.text) / 1e7, 2)})
    return {"meta": meta, "facts": facts, "n_contexts": len(ctx)}


# Old endpoint: does it still get new filings?
r = polite_get(s, f"{API}/corporates-financial-results", use_cache=False,
               params={"index": "equities", "symbol": "INFY", "period": "Quarterly"})
old = r.json() if r.ok else []
latest_old = max((datetime.strptime(x["toDate"], "%d-%b-%Y").date() for x in old if x.get("toDate")),
                 default=None)
res.check("corporates-financial-results lists XBRL links", any(x.get("xbrl") for x in old),
          f"{len(old)} rows; latest period end {latest_old}")

summary = {}
for sym in ("INFY", "HDFCBANK"):
    log(f"\n--- {sym} integrated filings ---")
    rows = integrated_filings(sym)
    res.check(f"{sym}: integrated-filing-results lists filings", bool(rows), f"{len(rows)} filings")
    for x in rows[:6]:
        log(f"    qe {x.get('qe_Date')} | {x.get('consolidated')} | {x.get('audited')} | {x.get('type_Sub')} | "
            f"xbrl={'y' if x.get('xbrl') else 'n'} ixbrl={'y' if x.get('ixbrl') else 'n'} | {x.get('broadcast_Date')}")
    cons = [x for x in rows if (x.get("consolidated") or "").lower().startswith("consol") and x.get("xbrl")]
    res.check(f"{sym}: consolidated filing with XBRL exists", bool(cons), f"{len(cons)} consolidated")
    quarters_available = sorted({x.get("qe_Date") for x in cons})
    log(f"    consolidated quarters available: {quarters_available}")
    if not cons:
        continue
    x = cons[0]
    xr = polite_get(s, x["xbrl"])
    res.check(f"{sym}: XBRL instance downloads", xr.ok and xr.content.lstrip()[:5] == b"<?xml",
              f"HTTP {xr.status_code}, {len(xr.content) / 1e6:.2f} MB")
    if not xr.ok:
        continue
    parsed = parse_xbrl(xr.content)
    log(f"    meta: {parsed['meta']}  contexts: {parsed['n_contexts']}")
    for k, vals in parsed["facts"].items():
        log(f"    {k}: " + "; ".join(f"{v['start']}→{v['end']} ₹{v['value_cr']:,} Cr (dec {v['decimals']})" for v in vals))
    periods = {(v["start"], v["end"]) for vals in parsed["facts"].values() for v in vals}
    log(f"    distinct periods in instance: {sorted(periods)}")
    # Finding, not a source failure: instances carry only current quarter + YTD.
    log(f"    FINDING: {len(periods)} periods per instance -> QoQ/YoY need the prior filings' XBRL")
    summary[sym] = {"filing": x, "parsed": parsed, "quarters_available": quarters_available}

save_sample("f_xbrl_summary.json", summary)
res.finish()
