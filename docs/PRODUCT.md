# FINN — Product Spec

> FINN is your portfolio's editor. It reads every filing, price move and transcript, and shows you only what changes your view — with proof.

Built for the ENAM Holdings AI Engineer Build Challenge (deadline 15 Nov 2026). Grading: creativity, product sense, judgment, architecture, efficiency — not completeness. **Thin-but-working beats broad-but-broken. A demo that doesn't run is the worst outcome.**

---

## 1. Users

- **The investor (real user):** PM/analyst at a lean, long-term, high-conviction fund. Checks phone between meetings, one-handed, ~30 seconds at a time. Distrusts any number without a source.
- **The evaluator (deciding user):** opens the link (probably on a laptop first), no portfolio set up, ~5 minutes. May type a ticker we never tested. May open the app weeks after submission.

## 2. Product principles

1. **Default to silence; earn every interruption.** Hiding routine filings is the core value.
2. **Show your proof.** Every number/claim links to its source document + page. If unverifiable, say so — never guess.
3. **Personal, not generic.** Importance depends on the user's holdings, position sizes, and what they're watching.
4. **Under 30 seconds to value.** Instant load, answer first, detail one tap away.
5. **Push and pull are one loop.** Research knowledge makes alerts smarter; alerts lead straight into research.

## 3. App map (mobile-first PWA)

- **Desktop landing** (desktop/laptop widths only): live phone-frame preview + QR "Open on your phone". Phones go straight into the app.
- **Brief** (main tab) — ranked cards for the chosen window.
- **Portfolio** — holdings, "What you're watching", calendar, results scoreboard, notes.
- **Research** — dossier for any NSE ticker.
- **Rules** — alert thresholds, categories, notification settings.
- **Ask bar** — always visible; scoped to the current screen/company.
- **Telegram bot** — real push delivery.

## 4. Brief

**Header:** "Since your last visit (9:12 am) · 3 things matter · ~90 sec · 41 routine filings hidden · ~35 min saved" + "Data as of HH:MM IST". The header always names the actual window.

**Window chips:** Since last visit (default) · 24h · 3d · 7d · Custom.

**Results-season strip** (only during results season): "Q2 FY27: 7/18 reported · 4 met guidance · 2 margin misses →" opens the scoreboard.

**Ranked cards** — sorted by importance score, not time. Every card has: ticker · category · impact tag · headline · "So what" (≤10 words) · key numbers · source chip (one tap to the exchange PDF) · next action · 2–3 Ask chips.

**Gestures:** swipe right = Reviewed; swipe left = Not useful; tap = expand.
- Swipe only commits past ~40% drag, with haptic tick; shorter swipes spring back.
- **Undo toast** for ~5s ("Marked reviewed · UNDO"). Weight changes apply only after the toast expires.
- "Reviewed today (n) ▸" section at the bottom to restore any card later.

**Event threads:** all filings for one event (intimation → outcome → deck → call → transcript → newspaper ad) collapse into one card with a timeline.

**Hidden drawer:** "Hidden (41) ▸" grouped by reason (compliance certificates, trading-window notices, newspaper ads, investor-meeting notices, ESOP allotments…). Every item still tappable.

**Caught-up state:** "You're caught up. Nothing else material since 9:12 am."

### Card types

1. **Results card** — Revenue, EBITDA, PBT, PAT: current quarter, QoQ %, YoY %. Consolidated by default, labelled. 8-quarter margin sparkline. "vs guidance" line from the Promise Ledger. "✓ Cross-checked" badge or "Couldn't verify — open filing".
   - Numbers come from NSE XBRL. Each XBRL filing holds only the current quarter (+ YTD), so QoQ and YoY use **three filings** — current, previous and year-ago quarter — matched on consolidated/standalone, cross-checked against screener's quarterly table. Fallback: the results PDF, whose table has current / previous / year-ago columns in one document.
   - EBITDA computed in code (PBT + finance costs + depreciation; document the other-income choice); formula shown on tap.
   - Sector-aware: banks/NBFCs show NII, PPOP, PAT instead of EBITDA.
2. **Management change card** — mini-CV of the *incoming* person: prior companies/roles/tenure, qualifications, insider vs outside hire, outgoing person's tenure. Source order: profile in the filing itself (usually required by disclosure rules) → web-search snippets (no LinkedIn scraping).
3. **Price/volume alert card** — move + likely explanation in priority order: a filing → bulk/block deal → sector/index move → otherwise "⚠️ No disclosure explains this move". At most one price/volume event per stock per trading day (one card per event: card id = event id).
4. **"What to watch" card** — when a results board meeting is announced: the promises the upcoming results will test. After results, the results card scores them.
5. **One-liner card** — M&A, fund raise, litigation, credit rating, pledging, capex, order wins, insider trades: one line + key number.
6. **Inline chip** — dividend, bonus/split: e.g. "₹8 dividend · record 21 Nov".

### Category treatment

| Category | Treatment |
|---|---|
| results, M&A, management_change, litigation, credit_rating (downgrade), pledging (increase) | Full card / one-liner, high priority |
| capex, press_release (order wins), insider_trading, fund_raise | One-liner, medium |
| dividend, bonus_split | Inline chip |
| earnings_call, agm_egm, postal_ballot | Folded into event threads |
| investor_meetings, unclassified | Hidden drawer |

## 5. Ranking

`score = category_weight × position_weight × relevance × novelty × surprise`

- **category_weight** — from the table above; adjustable via feedback.
- **position_weight** — grows with the holding's % of portfolio (e.g. ~0.8× for 2%, ~1.5× for 15%), capped so a huge event in a small holding can still top the list. Cards show ₹ impact.
- **relevance** (3-level hybrid, never requires typing):
  - Level 0 (automatic): impact tag 🟢 Positive / 🔴 Negative / 🟡 Mixed / ⚪ Neutral *for the company's business*, with a one-line reason. Not a stock call.
  - Level 1 ("What you're watching"): FINN suggests 2–3 drivers per holding from the company's own disclosures (reuses Promise Ledger extraction); the user ticks them. Events touching a confirmed driver get the biggest boost and a 👁 "affects: Margins" label.
  - Level 2: optional user-written thesis line.
  - Ask for confirmation at the right moment (when adding a stock, or when an event first touches a suggested driver), never via an upfront form.
- **novelty** — new information beats repeat filings on the same event.
- **surprise** — deviation from the stock's normal behaviour or from guidance.
- "Why is this #1?" shows the breakdown.

**Feedback (transparent, not ML):** "Not useful" → choose scope (this stock / all stocks / just this one) → weight × 0.8 per swipe; "Useful"/pin raises it. Critical categories (results, M&A, management change, rating downgrade) have a floor and can never be fully hidden. Rules screen lists every adjustment with Reset.

## 6. Alerts and notifications

| Setting | Default |
|---|---|
| Price move | ±4%, global + per-stock override |
| Volume | 2× 20-day average |
| Volatility-aware (z-score vs own history) | On |
| Sector-relative (stock-specific part of move) | On |
| Push categories | results, M&A, management_change, litigation, credit_rating, pledging |
| Notification budget | 5/day; overflow goes to the next Brief |
| Batching | On ("3 updates on your holdings") |
| Quiet hours | 10 pm–7 am; only critical items break through |
| Snooze | Per stock, 1 day / 1 week |

**Corporate actions:** use adjusted prices/volumes; on ex-dates (dividend, bonus, split) the mechanical drop never triggers an alert, but a genuine move beyond it still does. Label the day ("Ex-dividend today"). Ex-dates and action labels come from NSE's corporate-actions feed — it is the source of truth; price-feed action records are not trusted (Yahoo shows BAJFINANCE's split + bonus as one 2:1 split).

**Delivery:** Telegram bot + PWA web push. "Connect Telegram" sends a test alert immediately. Telegram messages carry buttons: Open in FINN / Snooze.

## 7. Portfolio

- Holdings list: weight, day change, 1-month sparkline, latest event, status dot (🟢 intact / 🟡 watch / 🔴 under pressure).
- "What you're watching" per holding (suggested, one-tap confirm).
- Upcoming events calendar: results dates, concall times, record dates, AGMs.
- Results-season scoreboard.
- Import: paste tickers / CSV, each with a share **quantity or** a portfolio **weight %** (either is enough for position weight; quantity also enables ₹ impact). Stored in the browser — no login ("your holdings stay on your phone unless you connect Telegram").
- **Opt-in server copy:** connecting Telegram (or web push) uploads only symbols + weights, tied to that chat — needed so the server can rank and push alerts. Shown before connecting; "Disconnect & delete" removes it. Ranking for the in-app Brief still runs on the phone.
- Notes on any card/holding → decision journal.

## 8. Research dossier (any NSE ticker)

Search with autocomplete over the full NSE equity list. First run streams progress ("Reading 4 transcripts · 23 guidance statements found…"); cached afterwards. Portfolio + ~15 popular large-caps pre-warmed nightly.

Sections (one scrolling page):
1. **Snapshot** — business, segments, revenue mix, headline numbers and ratios.
2. **Trajectory** — 5–10 yr sparklines (revenue, margins, ROCE, PAT) + one line on what's growing/compressing.
3. **⭐ Promise Ledger** — every forward-looking claim from the last 4–8 calls vs what was delivered: ✅ Kept / ❌ Missed / ↘ Goalposts moved / 🔇 Quietly dropped. Management credibility score + trend.
   - **Numeric promises** (target value or range for a metric and period): the model only extracts the target; **code** compares the delivered figure against it and sets Kept / Missed.
   - **The model judges** only qualitative promises (e.g. "launch in the US this year") and the cross-call patterns: ↘ goalposts moved (a later call revises the target or date) and 🔇 quietly dropped (no longer mentioned). Every verdict cites both calls.
4. **Cash quality** — CFO/PAT over time, FCF.
5. **Balance sheet** — D/E, working-capital days trend, funding.
6. **What analysts keep asking** — repeated questions across calls.
7. **Red flags** — KPIs that disappeared from decks, auditor qualifications, contingent-liability growth, related-party transactions, pledging trend.
8. **Bull vs bear** — 3 cited bullets each.

Rules: primary sources only (annual reports, transcripts, decks, filings, screener standardised tables). No news, broker notes, or model's outside knowledge. Every number tappable → provenance drawer (document, page, highlighted quote). Unsupported claims removed by the citation checker; gaps say "Not found in sources".

## 9. Ask

Scoped to context; 3 suggested question chips per screen; structured answers (number + one line + source chips); honest about gaps.

## 10. Trust layer (applies everywhere)

1. Adjusted prices for corporate actions; ex-dates from NSE's corporate-actions feed.
2. Unit normalisation (lakh / crore / million → ₹ Cr).
3. Results (from three XBRL filings) cross-validated against screener's quarterly table + sanity checks (PAT ≤ PBT normally, plausible margin ranges).
4. Freshness stamps on every screen and card.
5. Consolidated vs standalone always labelled.
6. Citation checker: every quote must exist in source text (fuzzy match).
7. Sector-aware templates (banks/NBFCs).
8. NSE holiday calendar.
9. Honest failure states (raw filing link instead of a guess).
10. Indian formatting: ₹ Cr, lakh separators, IST, FY quarter labels (Q2 FY27).

## 11. Evaluator experience

| Moment | Behaviour |
|---|---|
| Opens on laptop | Landing with phone preview + QR |
| Opens on phone | Populated Brief in <1s; no login; demo portfolio pre-loaded |
| First visit | 3-step skippable tour: swipe to triage, tap a number for its source, ask anything |
| Quiet market day | "Showcase replay" toggle loads a saved rich results day (clearly labelled) |
| Types a random ticker | Streaming progress → dossier; popular large-caps pre-warmed |
| Wants real push | "Connect Telegram" → test alert in seconds |
| Opens weeks later | Scheduled jobs still running; keep-alive pings prevent free-tier sleep |

## 12. Key decisions (keep DECISIONS.md in sync)

- **PWA over native/Expo/TestFlight:** the evaluator's first experience is a link, not an install. One codebase, instant deploys, fixes go live after submission.
- **Telegram for push:** PWA push works on Android Chrome without install, but on iPhone only after "Add to Home Screen" (iOS 16.4+), which most evaluators won't do; some Android phones popular in India (Xiaomi, Vivo, Oppo) delay web notifications via battery optimisation. Telegram behaves identically on every phone with no install or permission steps. WhatsApp would be ideal for Indian users but business messaging needs verification/template approval — out of scope for 6 days. Both PWA push and Telegram are offered.
- **"The LLM reads, code calculates."** No arithmetic in the model.
- **Model routing:** rules → cheap model (classification, extraction) → strong model only for synthesis (qualitative Promise Ledger verdicts, goalposts moved / quietly dropped across calls, bull/bear). Numeric verdicts are computed in code.
- **Long-context over RAG for concalls** (they fit in a cheap long-context model); RAG/chunking only for annual reports.
- **XBRL first** for results: current + previous + year-ago quarter filings (one XBRL instance holds only the current quarter), cross-checked against screener; PDF tables second; multimodal model for scanned PDFs.
- **Explicit, visible feedback rules instead of learned ranking** (one user, little data, must be explainable).
- **"What you're watching" suggested from disclosures** instead of manual thesis entry (most users never fill blank boxes).
- **No login; portfolio stored in the browser.** Opt-in server copy (symbols + weights only) when the user connects Telegram/web push, deletable any time.
- **"Brief", not "Today"**, because the window is configurable.

## 13. Deliberately left out

- Intraday/real-time data — brief specifies EOD; feeds the noise FINN filters; needs paid feeds.
- Login/multi-user — friction for evaluators; days of secure-auth work. Team sharing is a next step.
- Portfolio P&L accounting — brokers already do it; needs tax lots; different product.
- Buy/sell recommendations and trading — SEBI-regulated advice; FINN informs judgment, doesn't replace it.
- News and broker notes — excluded by principle (primary sources only for research). Exception allowed by the brief: background on incoming executives.

## 14. Priorities

- **P0:** Brief (ranking, hidden drawer, window chips, caught-up, undo) · results card · management change card · price/volume alerts with explanations + configurable rules · any-ticker dossier with Promise Ledger + provenance · trust layer · evaluator experience (no login, QR landing, speed, showcase replay).
- **P1:** "What you're watching" · Telegram · "What to watch" card · calendar + scoreboard · notification budget/quiet hours · bulk/block deals · credibility score · evals + cost report.
- **P2:** disappearing KPIs · analyst pressure points · decision journal · screenshot import · audio brief.
