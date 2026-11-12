# Live push check: one real filing from scheduler to Telegram

Traced 12 Nov 2026 from `filings`, `events`, `ingest_runs`, `alerts` and the GitHub Actions run log. Nothing was triggered by hand.

**The filing:** ALKEM, NSE `106856547`, "Appointment of Mr Gopal Kothari as Chief Financial Officer of the Company w.e.f. December 02, 2026" ([PDF](https://nsearchives.nseindia.com/corporate/ALKEM_12112026135747_Reg30AppointmentofCFO.pdf)).

| Time (IST) | Step | Evidence |
|---|---|---|
| 13:58:26 | Filed on NSE | `filings.filed_at` |
| 14:00:25 | cron-job.org's 14:00 slot calls `workflow_dispatch` (`job=filings`, `scheduled=true`) | [Actions run 43183494955](https://github.com/ShlokN-code/finn/actions/runs/43183494955) |
| 14:00:57 | `check_filings` starts (trigger `scheduler`), fetches 23 announcements for the 18 holdings | `ingest_runs` #61 |
| ~14:01 | **Classified** by tier (a), NSE's own label: `desc=Appointment` → `management_change`. No model call. | `filings.classify_tier = exchange`, `classify_note = desc=Appointment` |
| ~14:01 | Threaded into event `ALKEM:management_change:2026-11-12`; Level-0 tag (Flash-Lite): **neutral**; management profile: the filing names the role, and a web search found nothing to add | `events`, run stats `tag: {tagged 1, management 1, web: nothing_found 1}` |
| ~14:03 | **Ranked**: 0.9 (management change) × 1.04 (5% position) × 0.8 (neutral) × 1.0 (new) × 1.0 = **0.7468** | `alerts.score` |
| ~14:03 | Dispatch rules: 14:03 is outside quiet hours (22:00–07:00); a management change is critical, so it doesn't count against the 5-a-day budget | `alerts.status = sent` |
| **14:03:28** | **Sent to Telegram**: subscription 1 → message 18; subscription 3 → message 20 | `alerts` #14, #16 (`telegram_message_id`) |

**Filed → on the phone: 5 minutes 2 seconds.**

Most of that wait is the 30-minute slot spacing (this filing landed 2 minutes before a slot) plus about 2.5 minutes of run time.

The same run also sent ALKEM's Q2 FY27 results card. That card's numbers came from the PDF fallback (ALKEM's Q2 XBRL wasn't on NSE yet) and failed the sanity check, so the alert said "Couldn't verify — open the filing" with the filing link instead of numbers. That is the honest failure state working as designed.

**Held alerts:** none were held today. On 11 Nov, five price/volume signals went out as one batched message (`batch_id 713d2fc91892`) instead of five pushes; that is the batching rule. The quiet-hours path is unit-tested and recorded in DECISIONS (11 Nov: a KALYANKJIL results alert at 00:43 IST led to the "only M&A, CEO/MD exit, rating downgrade break through" rule).
