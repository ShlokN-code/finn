# Data sources

Verified 10 Nov 2026 by the scripts in `backend/spikes/` (trimmed responses in `backend/spikes/samples/`).
"Local" = dev machine in India; "GitHub" = `spike-ci` on GitHub-hosted runners (US datacenter IPs), which is where scheduled jobs run; "Render" = the deployed API's `GET /health/sources` probe (AWS Singapore).

## Summary

| # | Source | Local | GitHub | Render | Use for | Fallback |
|---|---|---|---|---|---|---|
| a | Yahoo EOD prices (yfinance) | ✅ works (rate-limits bursts) | ✅ works | — (not needed) | Adjusted daily OHLCV, 20-day volume, z-scores | NSE raw history + own adjustment |
| a2 | Demo tickers on Yahoo `.NS` | ✅ 20/20 resolve | ✅ 20/20 | — | — | — |
| b | NSE announcements | ✅ works | ✅ works | ⛔ 403 | Primary filing feed | Last good snapshot; BSE only from non-datacenter IPs |
| b2 | BSE announcements | ✅ works | ⚠️ **partly**: APIs blocked (HTTP 403); PDFs download | ⚠️ same: APIs 403, PDFs ✅ | Local/backup only (finer subcategories) | NSE |
| c | NSE calendar / board meetings / corporate actions / bulk & block deals | ✅ works | ✅ works | ⛔ 403 | Calendar, ex-dates, deal explanations | NSE archive CSVs (deals) |
| d | screener.in company page | ✅ works | ✅ works | ✅ works | Cross-check tables, document links | Exchange filings directly |
| e | NSE equity list (`EQUITY_L.csv`) | ✅ works (browser session only) | ✅ works | ⛔ 403 | Autocomplete (2,645 securities) | BSE scrip master (5,269 active) |
| f | NSE XBRL for results | ✅ works | ✅ works | ⛔ 403 (archive files too) | Results extraction (XBRL first) | Results PDF |
---

### What the GitHub-runner results mean

- Runner egress: **US (Iowa / Wyoming), AS8075 Microsoft** — a datacenter IP, the worst case for exchange bot protection.
- **NSE does not block it** (announcements, calendar, corporate actions, deals, archives, XBRL all pass). So scheduled ingest can run on GitHub Actions as planned, with NSE as the primary feed.
- **BSE blocks its APIs** (scrip master and announcements → 403 HTML) **but serves its PDFs** (`xml-data/corpfiling/…` and `stockinfo/AnnPdfOpen.aspx`). So BSE announcements are a *local/backup* source only — finer subcategories and NSE↔BSE dedup are unavailable in scheduled jobs; classification relies on NSE `desc` + subject-text rules, then the cheap model. Screener's document index (mostly BSE PDF links) **is** usable from servers.
- **Render (AWS Singapore, AS16509) is blocked by NSE completely** — homepage warm-up, every API, archive PDFs (with or without cookies), XBRL files and the equity list all return 403. BSE APIs are 403 too; **BSE PDFs and screener work**. Re-check any time at `https://finn-api-4ejm.onrender.com/health/sources` (cached 15 min).
- **Consequence:** the API on Render must never call NSE. All NSE data (filings, corporate actions, calendar, deals, XBRL, equity list) is fetched by GitHub Actions jobs and stored in Supabase; Render reads from Supabase. On-demand research on Render can use screener tables and BSE-hosted documents (transcripts, annual reports, decks) directly.
- If NSE ever starts blocking datacenter IPs: serve the last good snapshot (rule 7) and run ingest from a residential machine as a stopgap.

---

## (a) EOD prices — Yahoo via yfinance 1.8 — **works**

- `Ticker.history(period, auto_adjust=False, actions=True)` → `Open High Low Close Adj Close Volume Dividends Stock Splits`, index tz `Asia/Kolkata`. Latest bar = previous session (9 Nov 2026 when run on 10 Nov).
- **`Close` is already split/bonus-adjusted; `Volume` too.** Verified against NSE's raw history for the HDFCBANK 1:1 bonus (ex 26-Aug-2025): NSE raw close 25-Aug = ₹1,964.10, Yahoo = ₹982.05; NSE volume 8,759,022, Yahoo 17,518,044 (exactly 2×). Yahoo has no raw series.
- **`Adj Close` additionally adjusts for dividends** (gap vs `Close` up to 4.4 % over 3 years for HDFCBANK). For daily-move alerts use `Adj Close` returns, so ex-dividend drops are not alerts; label the day from NSE corporate actions.
- **Yahoo's action metadata is wrong for combined actions:** BAJFINANCE's 16-Jun-2025 1:2 split + 4:1 bonus (10× in total) appears as one `Stock Splits = 2.0` row, though prices are adjusted correctly. → Use NSE corporate actions for ex-dates and labels.
- **Rate limit:** after ~5 runs in ~30 min, `YFRateLimitError: Too Many Requests` for 8 of 20 tickers. Mitigation: one nightly batch in chunks of 5 with pauses, cache results, retry the failures once.
- **Fallback:** NSE `api/historicalOR/generateSecurityWiseHistoricalData?symbol=…&type=priceVolumeDeliverable&series=EQ&from=dd-mm-yyyy&to=dd-mm-yyyy` → raw OHLC, volume, **delivery %** (bonus: useful signal), VWAP. We'd apply adjustments ourselves from corporate actions.

### (a2) Demo tickers

All 18 portfolio + 4 research tickers resolve on NSE (`EQ` series) and on Yahoo `.NS` with fresh data. No ticker renames needed. Corporate actions in the last 3 years to be aware of:

| Ticker | Event (ex-date) | Why it matters |
|---|---|---|
| ITC | **Demerger** of ITC Hotels (06-Jan-2025) | Pre-2025 financials include hotels; trajectory charts need a note |
| BAJFINANCE | 1:2 split **and** 4:1 bonus (16-Jun-2025) | Yahoo shows it as a 2:1 split (wrong); prices pre-Jun-2025 are /10 |
| HDFCBANK | 1:1 bonus (26-Aug-2025) | Price/volume halved historically; HDFC Ltd merger (Jul-2023) affects older financials |
| RELIANCE | 1:1 bonus (28-Oct-2024) | (Jio Financial demerger in 2023 is just outside the 3-yr window) |
| INFY | Buyback (14-Nov-2025) | Share count change |
| COCHINSHIP | 2:1 split (10-Jan-2024) | — |
| PERSISTENT | 2:1 split (28-Mar-2024) | — |
| GRASIM | Rights 6:179 (10-Jan-2024) | Partly-paid rights shares traded separately |
| TITAGARH | Name is "Titagarh Rail Systems" (formerly Titagarh Wagons); symbol unchanged | Display name |
| IDEA | Vodafone Idea | Display name |

## (b) NSE corporate announcements — **works**

- Warm-up: `GET https://www.nseindia.com/` with a browser UA → cookies `AKA_A2, _abck, ak_bmsc, bm_sz` (Akamai). Then `GET /api/corporate-announcements?index=equities&symbol=RELIANCE&from_date=dd-mm-yyyy&to_date=dd-mm-yyyy`.
- **Always pass a date window.** Without one the API returns the full history (RELIANCE: 3,382 rows, 3 MB).
- Fields: `symbol, sm_name, sm_isin, desc` (NSE's category, e.g. "Change in Management", "Credit Rating", "Investor Presentation"), `attchmntText` (subject), `attchmntFile` (PDF URL on `nsearchives.nseindia.com/corporate/…`), `an_dt / sort_date / exchdisstime` (IST), `seq_id`, **`hasXbrl`**, `fileSize`, `smIndustry`.
- PDFs download fine (`%PDF`), even without cookies.
- No blocking at 1 request / 2.5 s (5 rapid repeats all 200).
- NSE's `desc` is coarse ("Updates" covers transcripts and press releases alike) → classification needs the subject text too.
- **Blocked:** `/api/quote-equity` returns 403 to scripts even after warm-up. Not needed: names/ISINs come from `EQUITY_L.csv`.

## (b2) BSE corporate announcements — **works**

- Scrip master: `GET https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?segment=Equity&status=Active` → 5,269 rows with `SCRIP_CD, scrip_id, ISIN_NUMBER, Scrip_Name, INDUSTRY`. Map NSE symbol → BSE code by **ISIN** (RELIANCE 500325, HDFCBANK 500180, INFY 500209).
- Announcements: `GET …/AnnSubCategoryGetData/w?pageno=1&strCat=-1&strPrevDate=YYYYMMDD&strToDate=YYYYMMDD&strScrip=500325&strSearch=P&strType=C&subcategory=-1` with `Referer/Origin: https://www.bseindia.com`. Paged (`Table1.ROWCNT`).
- Fields: `NEWSID, NEWS_DT, DissemDT, CATEGORYNAME, SUBCATNAME, NEWSSUB, HEADLINE, ATTACHMENTNAME, CRITICALNEWS, XML_NAME, QUARTER_ID, AUDIO_VIDEO_FILE`…
- **Better categories than NSE:** `SUBCATNAME` distinguishes "Earnings Call Transcript", "Change in Management", "Allotment of ESOP / ESPS", "Newspaper Publication", "Analyst / Investor Meet - Intimation/Outcome" → many filings can be classified by rule with no model call.
- PDF: `https://www.bseindia.com/xml-data/corpfiling/AttachLive/<ATTACHMENTNAME>` (older ones under `AttachHis/`). Same file as NSE's copy (identical size) → dedupe across exchanges.

## (c) NSE calendar, board meetings, corporate actions, deals — **works**

| Endpoint | Returns |
|---|---|
| `/api/event-calendar?index=equities&from_date=…&to_date=…` | All companies' upcoming board meetings: `symbol, company, purpose, bm_desc, date` (652 in next 30 days) |
| `/api/corporate-board-meetings?index=equities&symbol=…` | Per company: `bm_date, bm_purpose, bm_desc, attachment`, **`ixbrl`** (prior-intimation XBRL) |
| `/api/corporates-corporateActions?index=equities&symbol=…` | `exDate, recDate, subject` ("Bonus 1:1", "Dividend - Rs 13 Per Share", "Face Value Split…"), `faceVal`, book closure dates |
| `/api/historicalOR/bulk-block-short-deals?optionType=bulk_deals\|block_deals&from=…&to=…` | `BD_DT_DATE, BD_SYMBOL, BD_CLIENT_NAME, BD_BUY_SELL, BD_QTY_TRD, BD_TP_WATP, BD_REMARKS` |
| `nsearchives.nseindia.com/content/equities/bulk.csv`, `block.csv` | Latest session's deals (CSV). The API lags the latest session by a day or more (10 Nov: API's newest bulk deal 5 Nov, CSV 9 Nov), so ingest unions both |
| `/api/holiday-master?type=trading` | Trading holidays per segment (`CM` = equities): `tradingDate, weekDay, description`. 20 for 2026, incl. 10 Nov (Diwali-Balipratipada); "Diwali Laxmi Pujan*" (8 Nov) marks the Muhurat session. Committed copy: `backend/finn/data/nse_holidays.json` |

Phase 1 notes (10 Nov 2026, local): results **intimations** are mostly absent from the announcements feed. They come from `corporate-board-meetings` (`bm_timestamp` = filed, `bm_date` = meeting, `bm_purpose` e.g. "Financial Results", "Board Meeting Intimation"). NSE's announcement `fileSize` ("228.94 KB") equals BSE's `Fld_Attachsize` bytes at that precision, and the two exchanges disseminate up to ~1 h apart (RELIANCE 31 Oct). Companies file on trading holidays.

## (d) screener.in — **works** (polite use)

- robots.txt allows `/company/<SYM>/consolidated/`; disallows `/company/source/quarter/*` (we don't follow those). Plain identifying UA works; 1 request / 3 s, cached.
- `section#quarters`: 13 quarters; `#profit-loss`: 12 years + TTM; `#balance-sheet`, `#cash-flow`, `#ratios`, `#shareholding`. Units: "Consolidated Figures in Rs. Crores" (`/standalone/` URL for standalone).
- **Sector-aware rows:** non-financials (POLYCAB) → `Sales, Expenses, Operating Profit, OPM %, Other Income, Interest, Depreciation, PBT, Tax %, Net Profit, EPS`; NBFCs (BAJFINANCE) → `Revenue, Interest, Expenses, Financing Profit, Financing Margin %, …, Gross NPA %, Net NPA %`. Ratios: ROCE + working-capital days (non-fin) vs ROE only (fin).
- Documents: 16 annual-report links and 53 concall entries for BAJFINANCE, each with `Transcript / PPT / REC`. Links point mostly to **BSE PDFs** (77 of 115) — i.e. primary sources — plus the company's own site and YouTube.
- Use: cross-validation of results and the trajectory tables (spec: "screener standardised tables"), and a document index.
- Risk: HTML scraping can break on a redesign; the parser is ~40 lines with per-section checks.

## (e) NSE equity list — **works (browser session only)**

- `https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv` → 2,645 rows: `SYMBOL, NAME OF COMPANY, SERIES (EQ 2,396 / BE 207 / BZ 42), DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE`.
- With a plain UA the request **hangs (read timeout)**; with the warmed-up NSE session it returns in < 1 s.
- Plan: refresh nightly, commit/serve as a static JSON for autocomplete (works offline, no API call). Fallback: BSE scrip master.

## (f) XBRL for financial results — **works; changes the results design**

- **`/api/integrated-filing-results?index=equities&symbol=…&period_ended=all&type=Integrated Filing- Financials`** — every quarter from **Mar-2025**, standalone and consolidated, each with `xbrl` (XML, ~0.1–2 MB) and `ixbrl` (HTML) links, `audited`, `type_Sub` (Original/Revised), `broadcast_Date`.
- `/api/corporates-financial-results?index=equities&symbol=…&period=Quarterly` — older filings up to **Dec-2024**, each with an `xbrl` link. Together: continuous coverage.
- `/api/results-comparision?symbol=…` — NSE's own parsed comparison (values in ₹ lakh), useful as a cross-check.
- Instance format: SEBI taxonomy `in-capmkt` (2026-01-31), contexts `OneD` (quarter) and `FourD` (YTD), values in **rupees**, `decimals="-7"` (rounded to ₹ 1 Cr) or `-5` (₹ lakh), plus `LevelOfRounding`, `NatureOfReportStandaloneConsolidated`.
  - Non-financials: `RevenueFromOperations, OtherIncome, FinanceCosts, DepreciationDepletionAndAmortisationExpense, ProfitBeforeTax, ProfitLossForPeriod` → EBITDA computable in code.
  - Banks: `InterestEarned, InterestExpended, OperatingProfitBeforeProvisionAndContingencies, ProvisionsOtherThanTaxAndContingencies` → NII and PPOP directly. Asset-quality fields are 0 in consolidated filings → take NPA from standalone.
- **Each instance has only the current quarter + YTD — no previous-quarter or year-ago columns.** QoQ/YoY need the previous and year-ago filings' XBRL (both available), cross-checked against screener's quarterly table. The PDF still has three columns and is the fallback.

## Politeness & resilience (applies to all)

- Per-host spacing: NSE 2.5 s, NSE archives 1.5 s, BSE 2 s, screener 3 s. Retries with exponential backoff on 401/403/429/5xx; every raw download cached on disk.
- User-Agent: browser UA for NSE/BSE (they reject anything else), `FINN-research/0.1 (+repo URL)` elsewhere. No personal data in headers.
- Every source has a fallback; when a live source fails, serve the last good snapshot with its timestamp.
