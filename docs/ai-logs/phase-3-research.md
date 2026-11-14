▗ ▗   ▖ ▖  Claude Code v2.1.325
           Opus 5.5 · Claude Pro
 ▘▘   ▝▝   ~/Documents/finn


[Image #1]

❯ Phase 3 — Research engine + Promise Ledger (Wed 11 Nov)                       
                                                                                
  Read first: CLAUDE.md; docs/PRODUCT.md sections 8, 9, 12 and 14;              
  docs/DECISIONS.md (especially "Promise Ledger: code judges numbers, the model 
  judges language", the LLM entries, "NSE is fetched only by GitHub Actions"    
  and "On-demand NSE data via workflow dispatch"); docs/PLAN.md "Research       
  dossier"; docs/DATA_SOURCES.md section (d).                                   
                                                                                
  Goal: a research dossier for ANY NSE ticker, grounded only in primary sources 
  (transcripts, annual reports, decks, filings, screener's standardised         
  tables), with the Promise Ledger as the hero. Demo tickers: BAJFINANCE, INFY, 
  PERSISTENT, POLYCAB. At review I'll name 2 tickers you haven't seen, so       
  nothing may be tuned to one company.                                          
                                                                                
  Timing: tomorrow I build the frontend against this, so by tonight the dossier 
  API must be deployed and its contract stable.                                 
                                                                                
  Propose a plan first and wait for my approval. The plan must include:         
  A. Where each step runs. Render reaches screener and BSE-hosted PDFs but      
  never NSE. Render's disk is wiped on every restart/deploy and the instance    
  has 512 MB RAM, so caches live in Supabase (mind the free 500 MB database / 1 
  GB storage) and PDFs are processed page by page.                              
  B. LLM budget: calls and tokens for a first-time dossier, a cached one and    
  the nightly refresh, against these free-tier limits: [check numbers in ss].   
  Leave room for the push side. Say what happens when a quota runs out          
  mid-build, and whether Groq can take a full transcript within its token       
  limits.                                                                       
  C. A degradation table: for each missing or bad input (no screener page, no   
  transcripts, fewer than 4, scanned transcript, no annual report, bank/NBFC,   
  LLM unavailable, NSE data not fetched yet), what each section shows. Never an 
  error screen, never a guess.                                                  
  D. The Dossier contract (Pydantic → generated TS), including per-section      
  status (ready / building / unavailable + reason) and job progress.            
  E. Build order with a cut line: what ships tonight no matter what, and what   
  moves to Friday if we run late.                                               
                                                                                
  Pipeline:                                                                     
  1. Discover: screener page (consolidated, else standalone) → tables +         
  document links. Use the last 8 transcripts and the latest annual report.      
  2. Extract text with PyMuPDF, keeping page numbers. Store extracted text by   
  content hash, not the PDFs. Scanned documents: say so and skip unless OCR is  
  cheap.                                                                        
  3. MAP — one cheap-model call per transcript, JSON validated by Pydantic,     
  cached by (document hash, prompt version, model):                             
     - forward-looking statements: metric, type (point / range / at least / at  
  most / qualitative), target, unit, basis (INR vs USD vs constant currency;    
  consolidated vs standalone), period, speaker, exact quote, page;              
     - actuals management reports for metrics screener lacks (AUM growth,       
  constant-currency growth, credit cost…), with quote and page;                 
     - segments, capex plans, risks, analyst questions.                         
     Annual report: find the needed sections by heading in code (auditor's      
  report, contingent liabilities, related-party transactions, segment note) and 
  send only those pages.                                                        
  4. COMPUTE in Python from screener tables: CAGR, margins, ROCE/ROE, CFO/PAT,  
  FCF, working-capital days, D/E; bank/NBFC variant.                            
  5. PROMISE LEDGER:                                                            
     - Group restatements of the same promise across calls into one promise     
  thread (same metric, period, basis).                                          
     - Numeric: code finds the delivered figure (screener when metric and basis 
  match; otherwise an actual management reported in a later call, with its      
  quote) and sets Kept / Missed by documented rules per type. Never compare     
  across bases.                                                                 
     - Code detects numeric revisions within a thread: lowered target or later  
  date = ↘ Goalposts moved; a raised target is shown as ↗ Raised, not as a      
  miss.                                                                         
     - Extra states: "Not yet due" (period not over) and "Can't score" (no      
  delivered figure in sources). Neither counts toward credibility.              
     - The strong model judges only qualitative promises and paraphrased        
  cross-call patterns, citing both calls.                                       
     - 🔇 Quietly dropped is the most serious claim we make about management:   
  require that a code-level text search finds no mention in at least 2 later    
  calls, and word it factually ("Not mentioned in the 2 calls since Q1 FY26").  
     - Credibility score: a simple formula I can explain, shown with n, hidden  
  below a minimum n; trend = recent calls vs earlier.                           
  6. REDUCE (strong model), given only extracted facts and computed numbers:    
  snapshot text, trajectory line, analyst pressure points, red flags, 3 bull    
  and 3 bear bullets, each citing fact ids.                                     
  7. CITATION CHECKER: every quote must fuzzy-match its page text (normalise    
  whitespace, hyphenation, quote marks); failures are dropped and counted.      
  Every number carries provenance: document + page + quote, or screener table + 
  row + period.                                                                 
  8. "What you're watching": 2–3 suggested drivers per company from the ledger  
  (what management guides on most + what analysts ask about most).              
  9. Jobs and progress: builds take minutes, phones drop connections, and our   
  Vercel proxy has a time limit. Run builds as background jobs on Render with   
  progress stored in Supabase; the client polls (or uses SSE that reconnects).  
  A build continues if the user leaves; one build per ticker at a time; other   
  tickers queue; stale jobs after a restart are picked up again.                
  10. Caching and refresh: serve cached dossiers instantly; rebuild only when a 
  new document appears (a document is never extracted twice). Nightly:          
  portfolio + demo tickers. Pre-warm ~15 large-caps only if the math in B       
  allows.                                                                       
  11. Ask endpoint, scoped to one company: answers from extracted facts +       
  retrieved transcript passages (keyword/BM25 is fine; no vector database       
  unless you argue for it), with numbers and citations; says "Not found in      
  sources" when it isn't.                                                       
  12. On-demand NSE dispatch exactly as in PLAN.md — enrichment only, last in   
  the build order.                                                              
  13. Tokens and estimated cost per dossier in llm_calls (for Friday's cost     
  report).                                                                      
  14. Tests: promise comparison (each type, units, bases, FY periods, not yet   
  due, revisions), citation checker, degradation paths, cache keys.             
                                                                                
  Record new decisions in DECISIONS.md and backlog items in PLAN.md as usual.   
                                                                                
  Acceptance: dossiers for the 4 demo tickers, built on the deployed API; every 
  Promise Ledger verdict links to quotes I can find in the PDF (I'll            
  spot-check 5); the 2 unseen tickers produce a dossier or a clearly labelled   
  partial one.                                                                  

  Read 16 files, called ccd_turn, ran 2 shell commands (ctrl+o to expand)

⏺ Reading the backend now (LLM router, contracts, screener, citations); next
  I'll look at migrations, the API push routes and the web proxy before drafting
  the plan.

  Listed 1 directory, ran 6 shell commands (ctrl+o to expand)

⏺ The screener's cash-flow table gives me what I need to compute and cross-check
  free cash flow. Next I'm checking Groq's free-tier token limits to see
  whether a full transcript fits. · summary

⏺ web-fetch(Fetch Groq free-tier rate limits)
  ⎿  Done (2 tool uses · 18.5k tokens · 16s)
  (ctrl+o to expand)

  Ran 2 shell commands (ctrl+o to expand)

⏺ Real transcripts run about 13K tokens, which is over the 8K-per-minute
  free-tier limit for qwen3.8-27b, so I'll need to split them. A Plan agent is
  reviewing the design while I wait for the quota numbers from you. · summary

⏺ Plan(Stress-test research engine design)
  ⎿  Backgrounded agent (↓ to manage · ctrl+o to expand)

⏺ User answered Claude's questions:
  ⎿  · Your screenshot cuts off two quota numbers the budget depends on: Gemini 
     3.5 Flash Lite's requests/day ('251 / 50…') and the row for the strong 
     model, gemini-3.8-flash (not visible). What are they? → [User did not 
     answer this question — they sent a message instead. Treat that message as 
     their response; do not re-ask.]
     · Should the management credibility score count the strong model's 
     qualitative verdicts, or only verdicts decided in code? → [User did not 
     answer this question — they sent a message instead. Treat that message as 
     their response; do not re-ask.]
     · When the strong model's daily quota runs out mid-build, what should the 
     qualitative verdicts and bull/bear section do? → [User did not answer this 
     question — they sent a message instead. Treat that message as their 
     response; do not re-ask.]
     · When management raised or lowered a numeric target before the period 
     ended, which target is the Kept/Missed verdict scored against? → [User did 
     not answer this question — they sent a message instead. Treat that message 
     as their response; do not re-ask.]

  Searched for 1 pattern (ctrl+o to expand)

❯ Flash-Lite: 15 RPM / 250K TPM / 500 RPD. The push side peaked at 251/day in   
  the last 28 days, so plan dossier work in what's left.                        
  gemini-3.8-flash: 5 RPM / 250K TPM / 20 RPD.                                  
  Other free models on this key, each with its own daily quota: Gemini 3 Flash  
  5 RPM / 20 RPD, Gemini 2.5 Flash 5 RPM / 20 RPD.                              
  Keep strong calls per first-time dossier to 2 or fewer, pre-warm only the 4   
  demo tickers, and never spend strong calls on cached dossiers.                
                                                                                
  Accept “Count both, show split”.                                              
                                                                                
  Numeric ledger and computed sections ship immediately, as in your recommended 
  option. For the strong calls, fall back through the other free Flash models,  
  each with its own daily quota (Gemini 3 Flash, then Gemini 2.5 Flash), and    
  log which model wrote each verdict. Never use Flash-Lite for qualitative      
  verdicts or bull/bear. Only if every strong model is exhausted, show          
  "Building · resumes after 13:30 IST quota reset" and resume automatically.    
                                                                                
  Accept “Last target before period end”.                                       

⏺ Agent "Stress-test research engine design" finished · 8m 36s

⏺ The design review came back with your answers folded in, and I'm now writing
  the plan. · summary

⏺ Updated plan
  ⎿  /plan to preview

⏺ User approved Claude's plan
  ⎿  Plan saved to: ~/.claude/plans/phase-3-research-cozy-umbrella.md · /plan to
     edit
     Phase 3 — Research engine + Promise Ledger

     Context

     FINN needs a research dossier for any NSE ticker, grounded only in primary
     sources, with the Promise Ledger as the hero. You build the frontend
     tomorrow, so the dossier API must be deployed with a stable contract
     tonight (Wed 11 Nov). Demo tickers: BAJFINANCE, INFY, PERSISTENT, POLYCAB.
     Two unseen tickers come at review, so nothing is tuned to one company.

     What exists today:
     - finn/llm/router.py: cache, RPM/RPD limits, Gemini→Groq fallback.
     - finn/citations.py: fuzzy quote check.
     - finn/sources/screener.py: quarters table only.
     - Dossier, Promise and DossierSection models: thin, and nothing uses them
       yet.
     - finn/research/: empty.

     Measured inputs:
     - Transcripts: about 20 pages, about 13K tokens each (POLYCAB and
       BAJFINANCE Q2 FY27).
     - Annual reports: about 23 MB.
     - Screener has a cash-flow "Free Cash Flow" row and a
       /api/company/<id>/schedules endpoint ("Fixed assets purchased"), which
       robots.txt allows.
     - The database is 21 MB.

     Your decisions (11 Nov):
     - Credibility counts both kinds of verdict and shows the split.
     - Scoring uses the last target set before the period ended.
     - Strong-model fallback goes 3.8 Flash → 3 Flash → 2.5 Flash, never
       Flash-Lite. Each verdict logs the model that wrote it.
     - If every strong model is exhausted, the section shows "Building · resumes
       after 13:30 IST quota reset" and the build resumes automatically.
     - At most 2 strong calls per first-time dossier, and none for cached
       dossiers.
     - Pre-warm only the 4 demo tickers.

     ---

     A. Where each step runs

     Step: Discover: screener tables, document links, capex schedule
     On demand: Render
     Nightly: GitHub Actions
     Why: Screener works from both (3 s spacing, polite).
     ────────────────────────────────────────
     Step: Download PDFs (BSE-hosted; company sites best effort)
     On demand: Render
     Nightly: Actions
     Why: Streamed to a temp file with a 60 MB cap and deleted after extraction.
     The
       BSE fetch uses a browser UA and Referer. NSE-hosted links are skipped on
       Render.
     ────────────────────────────────────────
     Step: Text extraction (PyMuPDF)
     On demand: Render, page by page from the file
     Nightly: Actions
     Why: Only page text is kept: a gzipped JSON array per document in Postgres,

       keyed by sha256.
     ────────────────────────────────────────
     Step: MAP (cheap), compute, ledger, checker, drivers
     On demand: Render
     Nightly: Actions
     Why:
     ────────────────────────────────────────
     Step: JUDGE + REDUCE (strong)
     On demand: Render
     Nightly: Actions
     Why:
     ────────────────────────────────────────
     Step: Ask
     On demand: Render, synchronous, under 20 s
     Nightly: —
     Why: Fits inside the Vercel proxy's 55 s.
     ────────────────────────────────────────
     Step: NSE enrichment
     On demand: Dispatched nse-ticker.yml on Actions
     Nightly: Daily ingest, with researched tickers added
     Why: Render never calls NSE.
     ────────────────────────────────────────
     Step: Job queue
     On demand: research_jobs in Supabase
     Nightly: Same table
     Why: Render's worker thread and the nightly Actions run both claim jobs
     with
       FOR UPDATE SKIP LOCKED.

     Render limits (512 MB, about 0.1 CPU, disk wiped on restart).
     - One build at a time per process. Other tickers queue.
     - The PDF is never held in RAM. PyMuPDF opens it from the path and its
       store is shrunk after each document.
     - If the annual-report pass makes /ping slow on the first real build,
       annual reports move to the Actions worker. That is a single switch.

     Supabase limits (500 MB database).
     - Per ticker: about 8 × 20 KB of gzipped transcript text, about 400 KB for
       the latest annual report, and a dossier of about 150 KB, so roughly 0.6
       MB.
     - Only the latest annual report's text is kept per ticker.
     - A size guard in the nightly job evicts document text for tickers not
       opened in 30 days once the database passes 300 MB. Extractions and
       dossiers stay.
     - Supabase Storage is not used: no new key or API.

     PyMuPDF is AGPL-3.0. That's acceptable because the repo is public, and it
     will be noted in DECISIONS. If you'd rather avoid it, pypdfium2 drops in.

     ---

     B. LLM budget

     Model (tier): Flash-Lite 3.5 (cheap)
     Free limit: 15 RPM / 250K TPM / 500 RPD
     Pushes use: up to 251/day (28-day peak)
     Research cap (env): 220/day (RESEARCH_CHEAP_RPD), Ask ≤ 40 of it; 150K TPM
       limiter for research
     ────────────────────────────────────────
     Model (tier): 3.8 Flash → 3 Flash → 2.5 Flash (strong chain)
     Free limit: 5 RPM / 250K TPM / 20 RPD each = 60/day
     Pushes use: 0
     Research cap (env): 60/day; nightly ≤ 10
     ────────────────────────────────────────
     Model (tier): Groq qwen3.8-27b
     Free limit: 30 RPM / 8K TPM / 200K TPD
     Pushes use: fallback
     Research cap (env): Ask only

     Scenario: First-time dossier
     Cheap calls: 8 MAP (1 per transcript) + 1 annual report (sections only) = 9
     Strong calls: 2 (JUDGE, REDUCE)
     Tokens (≈): cheap 150K in / 40K out; strong 35K in / 8K out
     List-price estimate (free tier = $0): ≈ $0.20
     ────────────────────────────────────────
     Scenario: Cached dossier
     Cheap calls: 0
     Strong calls: 0
     Tokens (≈): —
     List-price estimate (free tier = $0): $0
     ────────────────────────────────────────
     Scenario: New transcript appears
     Cheap calls: 1 (others hit the cache)
     Strong calls: 2
     Tokens (≈): ≈ 60K
     List-price estimate (free tier = $0): ≈ $0.06
     ────────────────────────────────────────
     Scenario: Screener-only update (new quarter numbers)
     Cheap calls: 0
     Strong calls: 0
     Tokens (≈): Code-only recompute. Earlier synthesis is kept with its own
     as-of
       time.
     List-price estimate (free tier = $0): $0
     ────────────────────────────────────────
     Scenario: Ask
     Cheap calls: 1 (cached per symbol, question and dossier version)
     Strong calls: 0
     Tokens (≈): ≈ 6K
     List-price estimate (free tier = $0): ≈ $0.003
     ────────────────────────────────────────
     Scenario: Nightly, quiet night (20 tickers)
     Cheap calls: 0 (screener discovery only)
     Strong calls: 0
     Tokens (≈): —
     List-price estimate (free tier = $0): $0
     ────────────────────────────────────────
     Scenario: Nightly, results season (about 5 new transcripts)
     Cheap calls: 5
     Strong calls: 10 (capped)
     Tokens (≈): ≈ 250K
     List-price estimate (free tier = $0): ≈ $0.30
     ────────────────────────────────────────
     Scenario: Pre-warm the 4 demo tickers (once)
     Cheap calls: 36
     Strong calls: 8
     Tokens (≈): —
     List-price estimate (free tier = $0): ≈ $0.80

     - Daily capacity: cheap is the binding limit, at about 20 first-time
       dossiers a day. A cap of 15 on-demand first-time builds per IST day
       protects the push side.
     - Strong chain: the 2 strong calls per dossier support about 30 dossiers a
       day.
     - Cost log: every call's cost is estimated and logged in llm_calls, with
       symbol and job_id stored in the request JSON. Each job's stats hold
       calls, cache hits, tokens and estimated USD, ready for Friday's cost
       report.

     If a quota runs out mid-build
     - Per-minute 429 or a 5xx: the existing backoff applies (2, 4, 8, 16 s).
     - Flash-Lite daily limit or the research cap is hit:
       - Transcripts already read are used.
       - The ledger shows partial ("Read 5 of 8 calls — the rest after 13:30
         IST").
       - The job becomes waiting_quota with resume_after set to the next Pacific
         midnight. The time is computed in code, so it is 13:30 IST under PST.
       - The job resumes automatically, and cached stages make the resume cheap.
     - Strong model exhausted:
       - Falls through 3.8 Flash → 3 Flash → 2.5 Flash, and the model that wrote
         each verdict or claim is recorded.
       - If all three are out, the numeric ledger and computed sections ship.
         Qualitative verdicts and synthesis show "Building · resumes after 13:30
         IST quota reset", and the job resumes automatically.
       - Flash-Lite never writes these.

     Can Groq take a full transcript? No. Free-tier qwen3.8-27b allows 8K tokens
     per minute, and one request must fit inside that; a transcript is about
     13–17K tokens. Chunking would mean about 4 chunks a minute apart per
     transcript, and the facts that decide verdicts would come from a weaker
     model. So Groq never runs MAP: MAP waits for the reset instead. Groq serves
     only Ask, whose prompts are 6K tokens or less. The router skips Groq for
     any request estimated above 6K tokens.

     ---

     C. Degradation: what each section shows

     The dossier never shows an error screen and never guesses. Every section
     always carries status (ready / partial / building / unavailable), a reason
     code and a note.

     Missing or bad input: No screener page
     Snapshot: Name from the equity list; segments from transcripts if there are

       any; numbers say "Not found in sources"
     Trajectory · Cash · Balance sheet: unavailable · no_screener_page ("No
       standardised financials for X")
     Promise Ledger: Transcripts come from our NSE filings once NSE data is
     fetched;
       otherwise unavailable. Numeric promises are scored only against
       management-reported actuals.
     Analysts · Red flags · Bull/Bear: From transcripts and the annual report
     where
       present
     Exchange data: normal
     ────────────────────────────────────────
     Missing or bad input: No transcripts
     Snapshot: ready
     Trajectory · Cash · Balance sheet: ready
     Promise Ledger: unavailable · no_transcripts
     Analysts · Red flags · Bull/Bear: Analysts unavailable; red flags from the
       annual report; bull/bear from computed facts and the annual report
     Exchange data: normal
     ────────────────────────────────────────
     Missing or bad input: Fewer than 4 transcripts
     Snapshot: ready
     Trajectory · Cash · Balance sheet: ready
     Promise Ledger: partial · few_transcripts ("Based on 3 calls"). Credibility
     is
       hidden below n = 5. "Quietly dropped" only applies when 2 or more
     readable
       later calls exist.
     Analysts · Red flags · Bull/Bear: partial
     Exchange data: normal
     ────────────────────────────────────────
     Missing or bad input: Scanned transcript
     Snapshot: —
     Trajectory · Cash · Balance sheet: —
     Promise Ledger: The call is listed as "Scanned — not read". It doesn't
     count as
       a later call for "quietly dropped". If all are scanned, this is the
       no-transcripts row with reason scanned_documents.
     Analysts · Red flags · Bull/Bear: same
     Exchange data: —
     ────────────────────────────────────────
     Missing or bad input: No annual report (missing, scanned or over 60 MB)
     Snapshot: Segments from transcripts only
     Trajectory · Cash · Balance sheet: ready (screener)
     Promise Ledger: ready
     Analysts · Red flags · Bull/Bear: Red flags partial · no_annual_report:
       auditor, contingent liabilities and related-party items say "Not found in

       sources"
     Exchange data: —
     ────────────────────────────────────────
     Missing or bad input: Bank / NBFC
     Snapshot: Template bank or nbfc, detected from screener rows (Financing
     Profit;
       Deposits)
     Trajectory · Cash · Balance sheet: Trajectory: NII (screener definition),
     PAT,
       ROE, GNPA/NNPA; no EBITDA, OPM or ROCE. Cash quality unavailable ·
       not_meaningful_for_lenders. Balance sheet: borrowings/deposits growth,
       equity, ROA (computed).
     Promise Ledger: NIM, AUM, credit cost and loan growth are scored only
     against
       management-reported actuals
     Analysts · Red flags · Bull/Bear: normal
     Exchange data: normal
     ────────────────────────────────────────
     Missing or bad input: Every model unavailable
     Snapshot: Headline figures only
     Trajectory · Cash · Balance sheet: ready (no model needed)
     Promise Ledger: Numeric threads already extracted are ready. The rest is
       building · llm_quota, resuming at 13:30 IST.
     Analysts · Red flags · Bull/Bear: building · llm_quota; Ask says "Resting
     until
       13:30 IST" and still serves cached answers
     Exchange data: —
     ────────────────────────────────────────
     Missing or bad input: NSE data not fetched yet
     Snapshot: —
     Trajectory · Cash · Balance sheet: —
     Promise Ledger: —
     Analysts · Red flags · Bull/Bear: Pledging item says "pending exchange
     data"
     Exchange data: building ("Fetching exchange data… ~1–2 min"); unavailable ·

       nse_unavailable ("Available after tonight's refresh") if the dispatch
     fails
     ────────────────────────────────────────
     Missing or bad input: A source is down during a refresh
     Snapshot: The last good dossier is served with its as_of (rule 7). A failed

       rebuild never replaces a ready section; the old section is kept and
     labelled
       stale.
     Trajectory · Cash · Balance sheet:
     Promise Ledger:
     Analysts · Red flags · Bull/Bear:
     Exchange data:

     ---

     D. Dossier contract

     New file finn/models/research.py; the old thin Dossier, Promise and
     DossierSection are replaced. Exported to TS with export_schema, and CI
     checks staleness.

     Every section is a fixed typed field, present from the first response;
     there's no dict[str, …], so TS never sees | undefined. Later work only
     changes status and fills content. schema_version is stored with each
     dossier; on a mismatch the dossier is rebuilt rather than returning a 500.

     SectionReason = Literal["not_built_yet","no_screener_page","no_transcripts"
     ,"few_transcripts","scanned_documents",
       "no_annual_report","not_meaningful_for_lenders","llm_quota","llm_unavaila
     ble","nse_pending","nse_unavailable",
       "below_min_n","not_found_in_sources","source_unreachable"]
     class SectionMeta:   status: ready|partial|building|unavailable; reason:
     SectionReason|None; note: str|None
                          as_of: datetime|None; resume_after: datetime|None;
     written_by: str|None  # model id for model-written
     class DocumentRef:   id, kind:
     transcript|annual_report|investor_presentation, title, period: Period|None,
                          call_date, url, status:
     read|scanned|too_large|failed|not_pdf, pages: int|None
     class PromiseStatement: doc_id, call_label ("Q1 FY27 call"), made_on, kind,
     target_low/high, unit, raw_target,
                          quote: Citation (page + verbatim quote, checked),
     speaker
     class PromiseThread (TS: MgmtPromise): id (hash of code key), metric,
     metric_key, measure: level|growth|change,
                          kind: point|range|at_least|at_most|qualitative, basis
     {currency: INR|USD|CC|unspecified,
                          scope: consolidated|standalone|segment|unspecified},
     period: Period|None, statement (built in code),
                          statements: [PromiseStatement], scored_target,
     original_target,
                          revision:
     none|raised|lowered|narrowed|delayed|revised,
                          verdict:
     kept|missed|goalposts_moved|quietly_dropped|not_yet_due|cant_score,
                          verdict_by: code|model, verdict_model: str|None,
     verdict_reason: Claim (cites both calls),
                          delivered: Figure|None, delivered_source:
     screener|management_reported|None,
                          dropped_note ("Not mentioned in the 2 calls since Q1 
     FY26"), driver_ids
     class Credibility:   shown: bool, score_pct, kept, n, numeric_n,
     qualitative_n, min_n=5,
                          trend: up|down|flat|None, recent {kept,n}, earlier
     {kept,n}, formula: str
     class Dossier:       schema_version, symbol, name, template:
     standard|bank|nbfc, basis, as_of, built_at,
                          snapshot {meta, lines: [Claim], segments: [Figure],
     headline: [Figure]},
                          trajectory {meta, series: [Series], note: Claim|None},
                          ledger {meta, threads: [PromiseThread], credibility,
     counts_by_verdict},
                          cash_quality {meta, series}, balance_sheet {meta,
     series},
                          analysts {meta, points: [PressurePoint{theme, claim,
     n_calls}]},
                          red_flags {meta, items: [RedFlag{kind, claim,
     figures}]},
                          bull_bear {meta, bull: [Claim≤3], bear: [Claim≤3]},
                          drivers {meta, items: [Driver]}, ask_chips: [str≤3],
                          exchange_data {meta, latest_results:
     ResultsDetail|None, pledging: [Figure]},
                          sources: [DocumentRef], quality {quotes_checked,
     quotes_dropped, quotes_reanchored, claims_dropped},
                          cost {calls, cache_hits, tokens_in, tokens_out,
     est_usd, models: {id: calls}}
     class DossierJob:    id, symbol, status:
     queued|running|waiting_quota|done|partial|failed, queue_position,
                          stage, steps: [{key,label,status,detail}], counters
     {transcripts_total, transcripts_read,
                          guidance_found, quotes_dropped}, message ("Reading 4 
     of 8 transcripts · 23 guidance statements
                          found"), started_at, updated_at, resume_after, error
     class DossierResponse: dossier: Dossier|None, job: DossierJob|None,
     dossier_version: int
     class AskAnswer:     status: answered|not_found|unavailable, answer:
     Claim|None, figures: [Figure], resume_after

     Endpoints (Vercel proxy allow-list extended):
     - GET /research/symbols: [symbol, name] from securities; cached for a day;
       used for autocomplete.
     - GET /research/{symbol} → DossierResponse. An unknown symbol returns 404
       "not an NSE ticker".
     - POST /research/{symbol}/build: returns the existing active job or a fresh
       dossier (under 24 h old) instead of starting another; daily cap applies.
     - GET /research/jobs/{id} → DossierJob. Poll this every 3 s; refetch the
       dossier only when dossier_version changes.
     - POST /research/{symbol}/ask → AskAnswer.

     Fixtures: validated INFY and BAJFINANCE dossiers are committed to
     web/public/fixtures/, so the frontend never waits on live quota.

     ---

     E. Build order and cut line

     Tonight (Wed): ships no matter what. Each step is deployed and checked 
     against /version when green.

     1. Router.
        - Quotas keyed per (provider, model), behind a lock: a strong 429 no
          longer disables cheap.
        - Strong chain from env GEMINI_MODEL_STRONG_FALLBACKS; ids checked with
          finn.llm.check.
        - TPM bucket; research lane caps by purpose prefix research..
        - LLMRequest.document_text: only its hash goes into llm_calls.
        - max_output_tokens up to 8K, timeout 180 s, finishReason=MAX_TOKENS
          treated as truncated.
        - LLMUnavailable.kind and retry_after; Groq skipped above 6K tokens.
          Tests included.
     2. Contract and storage. Contract (D) plus TS generation plus fixtures.
        Migration 0004_research.sql adds:
        - research_documents (url → sha, status incl. extracting)
        - research_doc_text
        - research_extractions (doc sha, extractor, prompt version → validated
          payload and model)
        - research_jobs (partial unique index: one active job per ticker;
          attempts capped at 2)
        - dossiers
        - research_requests (daily cap)

        The frontend is unblocked here.
     3. Discover and compute.
        - Screener parse_table(section): TTM, half-year column, non-March year
          ends.
        - Documents: Transcript links only, last 8, files under 3 pages dropped;
          latest annual report; capex schedule.
        - compute.py: CAGR (3/5/10 years, via pct_change), OPM/NPM, ROE, ROCE
          and working-capital days (screener's rows), D/E, CFO/PAT, FCF (CFO +
          fixed assets purchased, cross-checked against screener's FCF row);
          bank and NBFC variants.
        - Every value is a Figure with a screener:<section>/<row>/<period>
          locator, or a formula plus inputs.
        - Snapshot headline, trajectory, cash and balance sheet become ready.
     4. Jobs and API.
        - Worker thread started only when RESEARCH_WORKER=1; Render start
          command gets --workers 1.
        - Separate heartbeat thread (30 s); stale after 3 min → re-queued on
          startup and in the loop; own database connection and Router per
          thread.
        - Endpoints and proxy allow-list; deploy; build the 4 demo tickers on
          Render.
     5. Documents and MAP.
        - Stream to a temp file, PyMuPDF per page, scanned detection, gzipped
          page text.
        - One MAP call per transcript: guidance[], actuals[], segments, capex,
          risks, analyst_questions[], each Pydantic-validated, with page markers
          [[p.N]] and repeated headers and footers stripped.
        - Citation checker:
          - The quote must match its claimed page, then ±1 page, then pages that
            contain its rarest words.
          - Matching is done after de-hyphenating and normalising quote marks
            and whitespace.
          - A quote that fails is re-anchored to the best-overlapping sentence
            that contains the same number. Failing that, it is dropped and
            counted.
          - The target number is re-parsed from the verified quote and must
            equal the model's number.
          - Statements from non-management speakers are dropped; the participant
            list is on pages 1–2.

     ─────────── cut line ───────────

     6. Numeric Promise Ledger (code). Tonight's target; first thing Thursday if
        late (the fixtures cover the UI meanwhile). Rules are below.

     Thursday (planned, in priority order; anything unfinished moves to Friday)

     7. Quietly dropped: code text search.
     8. JUDGE (strong call #1): qualitative promises plus paraphrased cross-call
        links. Each must cite both calls.
     9. Annual report:
        - Code finds sections by heading (auditor's report, contingent
          liabilities, related-party transactions, segment note, cash flow); the
          PDF outline is tried first.
        - About 25 pages go to one cheap call.
        - Red flags are computed in code: auditor opinion not unmodified,
          contingent-liability growth, related-party transactions as a share of
          revenue.
     10. REDUCE (strong call #2): snapshot text, trajectory line, pressure
         points (2 or more calls), red-flag wording, 3 bull and 3 bear.
         - The model writes {f:ID} placeholders, and code renders the numbers.
         - Unknown ids, and claims with no valid fact, are dropped and counted.
     11. Drivers (2–3) and Ask: BM25 over the ticker's pages, about 40 lines, no
         new dependency; ask chips.
     12. Nightly refresh on Actions (ingest.yml job research):
         - Code-only recompute for existing dossiers.
         - A rebuild only when a new document appears.
         - First-time builds only for the 4 demo tickers.
         - Database size guard.

     Friday

     13. On-demand NSE dispatch, exactly as in PLAN.md ("Research dossier —
         on-demand NSE data"): nse_dispatches, nse-ticker.yml,
         GITHUB_DISPATCH_TOKEN, the exchange_data section.
     14. Hardening on two tickers outside the demo set; cost report; README.
     15. OCR for scanned transcripts only if Gemini PDF input proves cheap.
         Otherwise stay with "Scanned — not read".

     ---

     Pipeline rules (code decides; the model only reads)

     MAP schema (per guidance item):
     - metric as said, plus metric_key from a code vocabulary of about 40 keys
       (revenue, revenue_growth, ebitda_margin, ebit_margin, pat, capex,
       aum_growth, credit_cost, nim, gnpa, cost_to_income, loan_growth,
       order_inflow, volume_growth, capacity, …) or other
     - measure: level / growth / change
     - kind
     - target numbers as printed, and unit text
     - currency basis: INR / USD / CC / unspecified
     - scope: consolidated / standalone / segment / unspecified
     - period_text verbatim, plus period_ref {type: fy | quarter | half | by_fy
       | relative | medium_term | unspecified, fy, q, years_ahead}
     - speaker, quote, page
     - search_terms (2–4 distinctive words)

     Actuals use the same shape plus the value. The purpose string carries the
     prompt version, e.g. research.map_transcript.v1.

     Periods (research/periods.py):
     - Resolved from period_ref plus the call date.
     - The year-end month comes from screener's annual column headers; it isn't
       assumed to be March.
     - "Next year" said in a Q4 call is ambiguous, so it becomes cant_score.
     - Medium-term or unspecified targets get no due date and can never be
       numerically scored.

     Threads:
     - Key = (metric_key, measure, segment, currency, scope). Statements within
       a thread are linked by period.
     - An unspecified basis merges into the single specified thread. With none
       specified, it compares against the dossier's basis and says so.
     - Thread id = hash of the key plus the period.

     Delivered figure:
     - Screener, only for a whitelist and only with INR currency and a matching
       scope: revenue level and INR growth, PAT, EBITDA margin when the quote
       says EBITDA (OPM %), capex, borrowings, bank GNPA.
     - So INFY's operating (EBIT) margin and anything in constant currency or
       USD are never scored from screener.
     - Otherwise, the earliest later-call actual that matches key, measure,
       period and basis, with its quote. The XBRL results_filings are used where
       present.
     - Neither → cant_score.

     Verdict rules: METRIC_DIRECTION gives higher-better, lower-better or
     neutral.

     ┌─────────────┬───────────────────────────────────────────────────────────┐
     │    Type     │                         Kept when                         │
     ├─────────────┼───────────────────────────────────────────────────────────┤
     │ point       │ within ±0.5 pp (%), ±2.5 % (money/count)                  │
     ├─────────────┼───────────────────────────────────────────────────────────┤
     │             │ within the bounds ±0.1 pp / ±0.5 % rounding; beyond the   │
     │ range       │ favourable bound = kept ("beat"); neutral or unknown      │
     │             │ direction: inside only                                    │
     ├─────────────┼───────────────────────────────────────────────────────────┤
     │ at_least /  │ the threshold, with the same rounding tolerance           │
     │ at_most     │                                                           │
     └─────────────┴───────────────────────────────────────────────────────────┘

     - Comparisons are never made across currency or scope.
     - bps are converted to pp. Money goes to ₹ Cr via numbers.to_crore_any.

     Revisions (successive targets within a thread, judged by midpoint and width
     using direction):
     - Unfavourable change or a later date → ↘ Goalposts moved. This becomes the
       verdict, and it counts against credibility even if the lower target was
       then met; the note says so.
     - Favourable change → ↗ Raised.
     - Narrowed range → narrowed badge.
     - Neutral metric → revised.

     Scored against the last target before period end, with the original target
     shown.

     Timing:
     - Not yet due: the period isn't over, or results haven't arrived yet (90
       days after the end for a year, 60 for a quarter).
     - After that, with no delivered figure, the verdict is Can't score.
     - Neither counts toward credibility.

     Quietly dropped: only for a thread with no delivered figure, where at least
     2 readable later calls exist, and a lenient search finds none of its
     search_terms (or metric synonyms) in any of them. Wording: "Not mentioned
     in the 2 calls since Q1 FY26". The model may suggest it; only code can
     assert it.

     Credibility = kept ÷ (kept + missed + goalposts moved + quietly dropped).
     - Code and model verdicts both count, and the split is shown ("7 of 10 kept
       · 6 numeric, 1 qualitative").
     - Hidden below n = 5.
     - Trend compares promises settled by results reported in the last 4 calls
       against earlier ones. It is shown only when both halves have n ≥ 3 and
       differ by 15 pp or more.

     Drivers: for each metric_key, score = number of guidance statements +
     number of analyst questions. Top 2–3 are mapped to labels (Margins, Asset
     quality, Growth…), each with promise_ids and a cited source.

     ---

     Files

     - New:
       - backend/finn/research/: discover.py, documents.py, extract.py,
         annual_report.py, compute.py, metrics.py (vocabulary, direction,
         screener whitelist, synonyms), periods.py, ledger.py, checker.py,
         judge.py, reduce.py, drivers.py, bm25.py, ask.py, jobs.py, build.py,
         store.py
       - backend/finn/models/research.py
       - backend/api/research.py
       - backend/db/migrations/0004_research.sql
       - backend/jobs/research.py
     - Modified:
       - finn/llm/{base,router,gemini,groq}.py
       - finn/sources/screener.py (parse_table, documents, company id,
         schedules; keep parse_quarters)
       - finn/sources/http.py (fetch_to_file, lock around _last_hit)
       - finn/citations.py (de-hyphenation)
       - finn/models/{core,__init__}.py
       - api/main.py (router, lifespan worker)
       - web/app/api/[...path]/route.ts
       - web/lib/{schema.json,types.ts}
       - pyproject.toml (pymupdf in the api and jobs extras)
       - .env.example
       - .github/workflows/ingest.yml
       - docs/DEPLOY.md (Render: --workers 1, RESEARCH_WORKER=1, new env)
     - Reused:
       - calendar.fy_of, quarter_period, results_quarter_for
       - numbers.parse_money, to_crore_any, approx_equal, pct_change
       - extraction/results/build.margin_series (screener-cited Figures)
       - crosscheck._screener_value (bank/NBFC rows)
       - store.company_names, jsonable
       - api/diagnostics single-flight lock
       - management.build_detail quote→page pattern
       - the Fake provider in tests/test_llm_router.py
       - format.figure_text
     - Docs:
       - DECISIONS:
         - Screener is cited as a primary standardised source in research.
         - Per-model quotas and the strong chain.
         - Groq is Ask-only.
         - Ledger rules, revisions and credibility.
         - The Render worker.
         - Storage in Postgres, not Storage.
         - PyMuPDF/AGPL.
         - Your 4 answers.
       - PLAN: Phase 3 checklist (steps 1–15), ticked with commit hashes.

     Tests (backend/tests/)

     - Router:
       - A strong 429 leaves cheap alive.
       - The fallback chain runs in order and logs the model.
       - document_text is hashed, not stored.
       - Truncation is detected.
       - Groq is skipped when a request is too large.
       - Lane caps are enforced.
     - Ledger:
       - Each type: kept, missed, beat; unknown direction.
       - Units: bps vs %, lakh/million→Cr, USD never compared with INR.
       - Bases: CC vs INR, standalone vs consolidated → can't score; unspecified
         merge.
       - FY periods (table-driven): FY27, Q3 FY27, H2, by FY28, "next year" in a
         Q4 call, a September year end.
       - Not yet due and awaiting results.
       - Revisions: raised ≠ miss; lowered/delayed = moved; narrowed;
         lower-better metrics.
       - Last-target scoring.
       - Quietly dropped: needs 2 readable later calls; a scanned call doesn't
         count; lenient search.
       - Credibility: formula, minimum n, trend.
     - Checker: a hyphen break, curly quotes, a header straddle, a page
       correction, re-anchoring, a number mismatch, an analyst speaker dropped,
       failures counted.
     - Compute: CAGR on a base ≤ 0, FCF vs screener's FCF row, D/E, bank and
       NBFC templates, TTM and half-year columns.
     - Degradation: fixture builds for every row of table C. Every section has a
       status, and nothing raises.
     - Cache keys:
       - MAP key changes with doc sha, prompt version or model, not with URL.
       - The same URL is never downloaded twice.
       - The same sha under two URLs is extracted once.
       - A cached dossier makes no LLM calls (strong or cheap).
     - Jobs:
       - Two claimers get one job.
       - One active job per ticker.
       - A stale job is re-queued, with attempts capped.
       - waiting_quota resumes after resume_after.

     Verification

     1. pytest and ruff locally; CI, including the api-import job with only the
        api extras.
     2. Push, run scripts/check_deploy.sh, then /version must equal HEAD.
     3. Run POST /research/{sym}/build on the deployed API for POLYCAB, INFY,
        BAJFINANCE and PERSISTENT.
        - Poll the job until done.
        - Check the job's message and steps, quality counters, and per-job cost.
        - Then GET again: the dossier comes back at once, with no new llm_calls
          rows.
     4. Spot-check 5 ledger verdicts: open each PDF at the cited page and find
        the quote.
     5. Run one ticker outside the demo set (a bank, e.g. HDFCBANK) and one with
        few transcripts or no screener page. Both must give a full dossier or a
        clearly labelled partial one.
     6. Check Render memory and /ping latency during an annual-report build (the
        Render dashboard).
     7. Regenerate the TS types and validate the committed fixtures against the
        schema.

⏺ I'm starting on step 2 (contract + migration). Step 1 (router) and step 3
  (screener discovery + compute) touch separate files and can run at the same
  time, each in its own session.

  Searched for 1 pattern, called ccd_session, ccd_turn 3 times, ran 1 shell command (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      import re…)
  ⎿  # Research
     # --------------------------------------------------------------------
     -------------------------
     … +16 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/models/core.py (+3 -51)
      1 -"""Core FINN contracts: Filing, Event, Card, Alert, Holding, Dri
        -ver, Promise, Dossier.                                          
      1 +"""Core FINN contracts: Filing, Event, Card, Alert, Holding, Dri
        +ver (research contracts: finn/models/research.py).              
      2  
      3  Pydantic is the source of truth; web/lib/types.ts is generated f
         rom these (see scripts/gen_types).
      4  """
     ...
       9  from enum import StrEnum
      10  from typing import Annotated, Literal
      11  
      12 -from pydantic import AwareDatetime, ConfigDict, Field, field_va
         -lidator                                                        
      12 +from pydantic import AwareDatetime, Field, field_validator     
      13  
      14  from finn.models.common import (
      15      Basis,
     ...
      373  # ------------------------------------------------------------
           ---------------------------------
      374  
      375  
      376 -class Promise(Model):                                         
      377 -    """A forward-looking management statement and what happene
          -d to it (Promise Ledger).                                     
      378 -    Exported to TypeScript as `MgmtPromise` to avoid shadowing
          - the built-in JS `Promise`."""                                
      379 -                                                              
      380 -    model_config = ConfigDict(title="MgmtPromise")  # merged w
          -ith Model.model_config                                        
      381 -                                                              
      382 -    id: str                                                   
      383 -    symbol: str                                               
      384 -    statement: str = Field(description="Short normalised state
          -ment, e.g. 'EBITDA margin 20–22% in FY27'")                   
      385 -    made_in: Citation = Field(description="Transcript/deck wit
          -h page and verbatim quote")                                   
      386 -    made_on: date                                             
      387 -    speaker: str | None = None                                
      388 -    metric: str | None = Field(None, description="e.g. 'EBITDA
          - margin', 'capacity (GW)'")                                   
      389 -    target_low: float | None = None                           
      390 -    target_high: float | None = None                          
      391 -    target_unit: str | None = None                            
      392 -    due: Period | None = None                                 
      393 -    verdict: Literal["kept", "missed", "goalposts_moved", "qui
          -etly_dropped", "pending", "unverifiable"]                     
      394 -    verdict_reason: Claim | None = None                       
      395 -    delivered: Figure | None = None                           
      396 -    superseded_by: str | None = Field(None, description="Promi
          -se.id that moved the goalposts")                              
      397 -                                                              
      398 -                                                              
      399 -class DossierSection(Model):                                  
     … 26 more lines (ctrl+o to expand)

⏺ Now the research contract.

⏺ Write(backend/finn/models/research.py)
  ⎿  Wrote 336 lines to backend/finn/models/research.py
      1 """Research contracts: Dossier (any NSE ticker), Promise Ledger, 
        build jobs, Ask.
      2 
      3 Stable shape for the frontend: every section is a fixed field tha
        t is ALWAYS present, with a `meta` saying whether
      4 it is ready, partial, building or unavailable (and why). Later wo
        rk only changes `meta.status` and fills content —
      5 it never adds or removes a section. Bump SCHEMA_VERSION on any br
        eaking change; stored dossiers with an older
      6 version are rebuilt rather than served.
     … +330 lines (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/models/__init__.py'…)
  ⎿  .......
        [100%]
     7 passed in 0.14s
     … +9 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/models/__init__.py (+21 -5)
      17      AlertSettings,
      18      Card,
      19      ChipDetail,
      20 -    Dossier,                                                   
      21 -    DossierSection,                                            
      20      Driver,
      21      Event,
      22      EventStage,
     ...
      28      PersonProfile,
      29      PriceVolumeDetail,
      30      PriorRole,
      33 -    Promise,                                                   
      31      ResultsDetail,
      32      ResultsLine,
      33      ScoreBreakdown,
     ...
      35      TimelineItem,
      36      WeightRule,
      37  )
      38 +from finn.models.research import (                             
      39 +    SCHEMA_VERSION,                                            
      40 +    AskAnswer,                                                 
      41 +    Credibility,                                               
      42 +    DocumentRef,                                               
      43 +    Dossier,                                                   
      44 +    DossierJob,                                                
      45 +    DossierResponse,                                           
      46 +    Promise,                                                   
      47 +    PromiseStatement,                                          
      48 +    SectionMeta,                                               
      49 +)                                                              
      50  
      51  # Top-level contracts exported to TypeScript (nested types come
           along via $defs).
      52  EXPORTED = [
      53      Citation, Figure, Claim, Period, Filing, Event, Card, Alert
          , Holding, Driver, Promise, Dossier,
      45 -    WeightRule, AlertSettings,                                 
      54 +    WeightRule, AlertSettings, DossierJob, DossierResponse, Ask
         +Answer,                                                        
      55  ]  # fmt: skip
      56  
      57  __all__ = [
     ...
      72      "Citation",
     … 14 more lines (ctrl+o to expand)
  ⎿  … 2 more files changed

⏺ Contract generated. Now migration 0004.

⏺ Write(backend/db/migrations/0004_research.sql)
  ⎿  Wrote 106 lines to backend/db/migrations/0004_research.sql
       1 -- 0004_research: research dossiers (Phase 3). Render's disk is 
         wiped on restart, so every cache lives here.
       2 -- Applied by `python -m jobs.migrate`. RLS on, no policies (the
          anon key reads nothing).
       3 
       4 -- Documents FINN has seen (transcripts, annual reports). A URL 
         is downloaded once; its bytes' sha256 is the key
       5 -- for the extracted text, so the same PDF under two URLs is ext
         racted once.
       6 create table if not exists public.research_documents (
     … +100 lines (ctrl+o to expand)

  Ran 1 shell command (ctrl+o to expand)

⏺ Migration applied. Next: the job queue, worker and research API, so the
  contract can be deployed early with skeleton dossiers.
  Ran 2 shell commands (ctrl+o to expand)

⏺ Bash(cat >> finn/calendar.py <<'EOF'…)
  ⎿  2026-11-11 13:30:00+05:30
  ⎿  Updated backend/finn/calendar.py (+11 -0)
      131      if forward_looking and (upcoming - filed).days <= 15:
      132          return upcoming
      133      return quarter_end_on_or_before(filed)
      134 +                                                              
      135 +                                                              
      136 +def next_quota_reset(now: datetime | None = None) -> datetime:
      137 +    """Gemini's free-tier daily quotas reset at midnight Ameri
          +ca/Los_Angeles (13:30 IST in winter, 12:30 IST in             
      138 +    summer). Returned as an aware UTC datetime."""            
      139 +    from zoneinfo import ZoneInfo                             
      140 +                                                              
      141 +    la = ZoneInfo("America/Los_Angeles")                      
      142 +    local = (now or now_utc()).astimezone(la)                 
      143 +    nxt = datetime.combine(local.date() + timedelta(days=1), t
          +ime(0, 0), tzinfo=la)                                         
      144 +    return nxt.astimezone(UTC)                                

⏺ Now the skeleton dossier and the research store (jobs, dossiers).

⏺ Write(backend/finn/research/skeleton.py)
  ⎿  Wrote 49 lines to backend/finn/research/skeleton.py
       1 """A dossier with every section present and marked 'building' — 
         what a build publishes first, and the base every
       2 stage fills in. Keeping all sections present from the first resp
         onse is what keeps the contract stable."""
       3 
       4 from __future__ import annotations
       5 
       6 from datetime import datetime
       7 
       8 from finn.models.research import (
     … +41 lines (ctrl+o to expand)

⏺ Write(backend/finn/research/store.py)
  ⎿  Wrote 253 lines to backend/finn/research/store.py
       1 """Supabase persistence for research: build jobs (the queue), do
         ssiers, documents, extracted text, extractions.
       2 
       3 Every function takes a psycopg connection (dict rows, autocommit
         ). The queue is safe with several workers (Render's
       4 thread and a GitHub Actions run): jobs are claimed with FOR UPDA
         TE SKIP LOCKED, and a partial unique index allows
       5 one active job per ticker.
       6 """
       7 
     … +246 lines (ctrl+o to expand)

⏺ Write(backend/finn/research/jobs.py)
  ⎿  Wrote 172 lines to backend/finn/research/jobs.py
      1 """Background build worker and progress reporting.
      2 
      3 Render runs one worker thread inside the API process (only when R
        ESEARCH_WORKER=1, and with uvicorn --workers 1);
      4 the nightly GitHub Actions job runs the same loop in the foregrou
        nd. Both claim from `research_jobs` in Supabase,
      5 so a deploy or restart mid-build only delays a job: its heartbeat
         stops, `requeue_stale` puts it back, and every
      6 stage is cached (documents, text, extractions, model calls), so t
        he rerun is cheap.
     … +166 lines (ctrl+o to expand)

⏺ Write(backend/finn/research/build.py)
  ⎿  Wrote 34 lines to backend/finn/research/build.py
       1 """Orchestrates one dossier build: discover → compute → document
         s → extract → ledger → judge → reduce → publish.
       2 
       3 Each stage fills its sections and publishes, so the client sees 
         sections turn ready one by one. A stage that
       4 can't run (missing input, quota) leaves an honest status on its 
         sections; it never raises past this module except
       5 on a bug. The last good dossier is the starting point, so a fail
         ed rebuild never blanks a ready section.
       6 """
     … +28 lines (ctrl+o to expand)

⏺ Now the API router.

⏺ Write(backend/api/research.py)
  ⎿  Wrote 126 lines to backend/api/research.py
       1 """Research endpoints (Phase 3).
       2 
       3 GET  /research/symbols          NSE equity list for autocomplete
          ([symbol, name]); cached for a day
       4 GET  /research/{symbol}         DossierResponse: the last good d
         ossier (instant) + the active/latest build job
       5 POST /research/{symbol}/build   start a build (reuses an active 
         job; a fresh dossier isn't rebuilt); daily cap
       6 GET  /research/jobs/{id}        DossierJob — poll every ~3 s; re
         fetch the dossier when dossier_version changes
     … +120 lines (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='api/main.py'…)
  ⎿  7:/research/*     — dossiers, build jobs, Ask (api/research.py)
     24:from api.research import router as research_router
     31:async def lifespan(_app: FastAPI):
     … +8 lines (ctrl+o to expand)
  ⎿  Updated backend/api/main.py (+18 -1)
       4  GET /health/db  — reads one row from Supabase Postgres to prove
           web → API → DB.
       5  GET|HEAD /ping  — keepalive: SELECT 1 on Supabase, plain-text '
          ok', never compressed (cron-job.org).
       6  GET /health/sources — can this server reach NSE/BSE/screener? (
          cached 15 min)
       7 +/research/*     — dossiers, build jobs, Ask (api/research.py)  
       8  """
       9  
      10  from __future__ import annotations
     ...
      12  import logging
      13  import os
      14  import time
      15 +from contextlib import asynccontextmanager                     
      16  
      17  import psycopg
      18  from fastapi import FastAPI
     ...
      21  
      22  from api.diagnostics import get_probes
      23  from api.push import router as push_router
      24 +from api.research import router as research_router             
      25  from finn import __version__
      26  
      27  log = logging.getLogger("finn.api")
      25 -app = FastAPI(title="FINN API", version=__version__)           
      28 +                                                               
      29 +                                                               
      30 +@asynccontextmanager                                           
      31 +async def lifespan(_app: FastAPI):                             
      32 +    # Research builds run in a background thread of this proces
         +s — only where RESEARCH_WORKER=1 (Render, started              
      33 +    # with --workers 1), never in tests or a second uvicorn wor
         +ker.                                                           
      34 +    if os.environ.get("RESEARCH_WORKER") == "1":               
      35 +        from finn.research.jobs import Worker                  
      36 +                                                               
      37 +        Worker.start_once()                                    
      38 +    yield                                                      
      39 +                                                               
      40 +                                                               
      41 +app = FastAPI(title="FINN API", version=__version__, lifespan=l
         +ifespan)                                                       
      42  app.include_router(push_router)
      43 +app.include_router(research_router)                            
      44  
      45  _origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "
          ").split(",") if o.strip()]
     … 1 more lines (ctrl+o to expand)

⏺ Tests pass. Now a local end-to-end check of the queue against Supabase
  (enqueue, claim, skeleton publish).

  Ran 1 shell command (ctrl+o to expand)

⏺ Queue, worker and endpoints work locally. Now the Vercel proxy allow-list and
  the Render settings.

  Ran 1 shell command (ctrl+o to expand)

⏺ Update(web/app/api/[...path]/route.ts)
  ⎿  Added 6 lines
      11    ["GET", /^subscriptions\/me$/],
      12    ["PUT", /^subscriptions\/me$/],
      13    ["DELETE", /^subscriptions\/me$/],
      14 +  // Research (Phase 3): builds run in the background on the AP
         +I, so every call here returns quickly.                         
      15 +  ["GET", /^research\/symbols$/],                              
      16 +  ["GET", /^research\/jobs\/\d+$/],                            
      17 +  ["GET", /^research\/[A-Za-z0-9&_-]{1,20}$/],                 
      18 +  ["POST", /^research\/[A-Za-z0-9&_-]{1,20}\/build$/],         
      19 +  ["POST", /^research\/[A-Za-z0-9&_-]{1,20}\/ask$/],           
      20  ];
      21  
      22  async function proxy(req: Request, ctx: RouteContext<"/api/[...
          path]">) {

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(cat >> docs/DEPLOY.md <<'EOF'…)
  ⎿  All checks passed!
         |

     1 file would be reformatted, 14 files already formatted
  ⎿  Updated .env.example (+6 -0)
      29  # Raw download cache directory (default backend/.cache).
      30  # FINN_CACHE_DIR=
      31  
      32 +# --- Research dossiers (Phase 3, Render) ---                  
      33 +# Start the background build worker in this process (Render onl
         +y; uvicorn --workers 1).                                       
      34 +RESEARCH_WORKER=                                               
      35 +# New (first-time) dossiers per IST day — protects the push sid
         +e's model quota.                                               
      36 +RESEARCH_DAILY_BUILDS=15                                       
      37 +                                                               
      38  # --- Telegram (Phase 2) ---
      39  # From @BotFather. Needed on Render (webhook, test alert) and a
          s a GitHub secret (alert dispatch).
      40  TELEGRAM_BOT_TOKEN=
  ⎿  Updated docs/DEPLOY.md (+18 -0)
      181  GitHub's run list shows them as `workflow_dispatch`. A plain m
           anual **Run workflow** from GitHub's UI still forces a
      182  filings run outside the window and never skips; the scheduler'
           s `"scheduled":"true"` makes a run respect the window
      183  and skip a slot that already ran.
      184 +                                                              
      185 +## 7. Research dossiers (Phase 3) — ~3 min on Render          
      186 +                                                              
      187 +Dossier builds run in a background thread inside the API proce
          +ss, so Render needs the model keys and one flag.              
      188 +                                                              
      189 +1. Render → `finn-api` → **Settings** → **Start Command** → `u
          +vicorn api.main:app --host 0.0.0.0 --port $PORT --workers 1` →
          + **Save**. (One process, so exactly one build worker; 512 MB a
          +llows one build at a time.)                                   
      190 +2. **Environment** → add:                                     
      191 +   | Key | Value |                                            
      192 +   |---|---|                                                  
      193 +   | `RESEARCH_WORKER` | `1` |                                
      194 +   | `GEMINI_API_KEY` | same as the GitHub secret |           
      195 +   | `GEMINI_MODEL_CHEAP` | `gemini-3.5-flash-lite` |         
      196 +   | `GEMINI_MODEL_STRONG` | `gemini-3.8-flash` |             
      197 +   | `GEMINI_MODEL_STRONG_FALLBACKS` | the Gemini 3 Flash and 
          +2.5 Flash ids, comma-separated (`python -m finn.llm.check` lis
          +ts them) |                                                    
      198 +   | `GROQ_API_KEY` | same as the GitHub secret (Ask fallback 
          +only) |                                                       
      199 +3. **Save, rebuild and deploy**. Check: `https://<render-url>/
          +research/POLYCAB` returns JSON with `"symbol": "POLYCAB"`.    
      200 +                                                              
      201 +A restart or deploy mid-build is safe: the job's heartbeat sto
          +ps, it goes back to the queue after 3 minutes, and every stage
          + is cached in Supabase, so the rerun is quick. The daily cap o
          +n new dossiers is `RESEARCH_DAILY_BUILDS` (default 15).       

⏺ Bash(../.venv/bin/ruff format api finn/research finn/models && grep -n "ruff
      format" ../.github/workflows/ci.yml; cd ../web && npm run gen:schema
      >/dev/null && npm r…)
  ⎿  1 file reformatted, 14 files left unchanged
     27:      - run: ruff format --check .
      M lib/schema.json
      M lib/types.ts
  ⎿  Updated backend/finn/models/research.py (+1 -3)
      205  
      206  
      207  class RedFlag(Model):
      208 -    kind: Literal[                                            
      209 -        "auditor_opinion", "contingent_liabilities", "related_
          -party", "pledging", "disappearing_kpi", "other"               
      210 -    ]                                                         
      208 +    kind: Literal["auditor_opinion", "contingent_liabilities",
          + "related_party", "pledging", "disappearing_kpi", "other"]    
      209      claim: Claim
      210      figures: list[Figure] = Field(default_factory=list)
      211      severity: Literal["high", "medium", "low"]

  Ran 1 shell command (ctrl+o to expand)

⏺ Contract, migration, queue and API are committed (bfffd9e) and pushed; waiting
  for Render to deploy it, then I move on to documents and MAP.

  Ran 3 shell commands (ctrl+o to expand)

⏺ Background command "Wait for deploy and fetch POLYCAB dossier from Render"
failed with exit code 144

⏺ Contract and API are live on Render (bfffd9e); /research/POLYCAB returns the
  skeleton dossier. Next I need the router changes, so I'm checking whether that
  proposed session was started.

  Listed 1 directory, called ccd_session, ccd_turn 2 times, ran 2 shell commands (ctrl+o to expand)

⏺ Rewriting the router: limits per model, the strong fallback chain, a
  tokens-per-minute bucket, research caps, and document text that's hashed
  rather than logged.

⏺ Bash(python3 - <<'EOF'
      p='finn/llm/base.py'…)
  ⎿  11:from dataclasses import dataclass, field
  ⎿  Updated backend/finn/llm/base.py (+27 -1)
      22      schema: dict  # JSON schema of the expected object (OpenAPI
          -subset: type/properties/enum/required)
      23      pdf: bytes | None = None  # sent natively where supported; 
          text-only providers skip requests that need it
      24      pdf_required: bool = False
      25 -    max_output_tokens: int = 512                               
      25 +    max_output_tokens: int = 512  # up to 8192 (research MAP); 
         +thinking tokens count against it on Gemini 3.x                 
      26 +    # Long text (a transcript) sent after the prompt. Only its 
         +sha256 is logged and hashed into the cache key,                
      27 +    # so llm_calls never duplicates document text that research
         +_doc_text already stores.                                      
      28 +    document_text: str | None = None                           
      29 +    tags: dict = field(default_factory=dict)  # e.g. {"symbol":
         + "INFY", "job_id": 12} — logged, not in the cache key          
      30 +    timeout_s: float = 60                                      
      31 +    thinking_budget: int | None = None  # Gemini thinkingConfig
         +.thinkingBudget (0 = off); None = model default                
      32  
      33      def content_hash(self, model: str) -> str:
      34          h = hashlib.sha256()
     ...
      37              h.update(b"\x00")
      38          if self.pdf:
      39              h.update(hashlib.sha256(self.pdf).digest())
      40 +        if self.document_text:                                 
      41 +            h.update(b"doc:" + self.document_sha().encode())   
      42          return h.hexdigest()
      43  
      44 +    def document_sha(self) -> str | None:                      
      45 +        return hashlib.sha256(self.document_text.encode()).hexd
         +igest() if self.document_text else None                        
      46 +                                                               
      47 +    def full_prompt(self) -> str:                              
      48 +        """Prompt as sent: the instructions, then the document 
         +(if any) in a fenced block."""                                 
      49 +        if not self.document_text:                             
      50 +            return self.prompt                                 
      51 +        return f"{self.prompt}\n\n<document>\n{self.document_te
         +xt}\n</document>"                                              
      52 +                                                               
      53 +    def est_tokens(self) -> int:                               
      54 +        """Rough input + output token estimate (≈3.5 chars/toke
         +n for English filings) for TPM budgeting."""                   
      55 +        chars = len(self.system) + len(self.prompt) + len(self.
         +document_text or "")                                           
      56 +        return int(chars / 3.5) + (258 * 20 if self.pdf else 0)
         + + self.max_output_tokens                                      
      57 +                                                               
      58  
      59  @dataclass
      60  class LLMResult:
     ...
       91  
       92      def model_for(self, tier: Tier) -> str | None: ...
     … 8 more lines (ctrl+o to expand)

⏺ Now the router itself.

⏺ Bash(python3 - <<'EOF'
      p='finn/llm/router.py'…)
  ⎿  ok
  ⎿  Updated backend/finn/llm/router.py (+92 -22)
       4      result = router.run("cheap", req)      # → LLMResult, or ra
          ises LLMUnavailable
       5  
       6  - Cache: by content hash (purpose + model + prompt + schema + P
          DF hash). A hit costs nothing and skips limits.
       7 -- Limits: per-provider requests/minute (sleeps) and requests/da
         -y (counted from the log, so separate job runs                  
       8 -  share one budget). Defaults are conservative for free tiers; 
         -override with <PROVIDER>_RPM / <PROVIDER>_RPD.                 
       7 +- Limits are per MODEL (each free-tier model has its own quota)
         +: requests/minute and tokens/minute (sleeps), and              
       8 +  requests/day counted from the log, so the API, its worker and
         + job runs share one budget. Limiters are                       
       9 +  process-wide and thread-safe. A per-day 429 retires only that
         + model for the run, never the whole provider.                  
      10 +- Research lane: purposes starting 'research.' also share daily
         + caps (RESEARCH_CHEAP_RPD, RESEARCH_ASK_RPD) and a             
      11 +  lower cheap-tier TPM, so dossier builds can never starve push
         +-side classification.                                          
      12  - Retries: a 5xx/network error or a per-minute 429 is retried w
          ith exponential backoff (2, 4, 8, 16 s) before
      13    moving on; a per-day 429 or our own daily budget marks the pr
          ovider exhausted for the run.
      14 +- Strong tier = Gemini's chain (GEMINI_MODEL_STRONG, then GEMIN
         +I_MODEL_STRONG_FALLBACKS); never Flash-Lite and                
      15 +  never Groq. LLMResult.model names the model that actually ans
         +wered.                                                         
      16  - Fallback chain per tier: Gemini → Groq (text only: a PDF is r
          eplaced by its text, extracted locally; a
      17    scanned PDF with no text layer can't go to Groq) → LLMUnavail
          able, which callers turn into an honest
      18    "unclassified"/"not found" state — never a guess.
     ...
      24  import json
      25  import logging
      26  import os
      27 +import threading                                               
      28  import time
      29  from collections import deque
      30  from dataclasses import dataclass, field
      25 -from typing import Protocol                                    
      31 +from datetime import datetime                                  
      32 +from typing import Literal, Protocol                           
      33  
      34  from finn.llm.base import LLMRequest, LLMResult, Provider, Prov
          iderError, QuotaExceeded, Tier, TransientError
      35  
      36  log = logging.getLogger("finn.llm")
      37  
      31 -DEFAULT_LIMITS = {"gemini": (10, 400), "groq": (20, 800)}  # (r
         -equests/min, requests/day) — conservative                      
      38 +# (requests/min, requests/day) per provider — the push side's l
         +ong-standing defaults (GEMINI_RPM/RPD override).               
      39 +DEFAULT_LIMITS = {"gemini": (10, 400), "groq": (20, 800)}      
      40 +# Per-model free-tier limits (rpm, rpd, tpm), product owner's A
         +I Studio dashboard 11 Nov 2026. Flash-Lite's RPD is            
      41 +# shared with the push side; non-Lite Flash models are the stro
         +ng chain (5 RPM / 20 RPD each).                                
      42 +FLASH_LIMITS = (5, 20, 240_000)                                
      43 +LITE_TPM = 240_000                                             
      44 +GROQ_TPM = 8_000                                               
     … 126 more lines (ctrl+o to expand)
⏺ Bash(python3 - <<'EOF'
      p='finn/llm/router.py'…)
  ⎿  198:    def as_dict(self) -> dict:
     199-        return {**self.__dict__, "est_cost_usd": round(self.est_co
     st_usd, 6), "by_model": dict(self.by_model)}
     200-
  ⎿  Updated backend/finn/llm/router.py (+155 -80)
      27  import threading
      28  import time
      29  from collections import deque
      30 -from dataclasses import dataclass, field                       
      30 +from dataclasses import dataclass, field, replace              
      31  from datetime import datetime
      32  from typing import Literal, Protocol
      33  
     ...
      193      tokens_out: int = 0
      194      est_cost_usd: float = 0.0
      195      by_provider: dict[str, int] = field(default_factory=dict)
      196 +    by_model: dict[str, int] = field(default_factory=dict)    
      197  
      198      def as_dict(self) -> dict:
      198 -        return {**self.__dict__, "est_cost_usd": round(self.es
          -t_cost_usd, 6)}                                               
      199 +        return {**self.__dict__, "est_cost_usd": round(self.es
          +t_cost_usd, 6), "by_model": dict(self.by_model)}              
      200  
      201  
      202  class Router:
      202 -    def __init__(self, providers: list[Provider], log: LLMLog,
          - limits: dict[str, tuple[int, int]] | None = None,            
      203 +    def __init__(self, providers: list[Provider], log: LLMLog,
          + limits: dict | None = None,                                  
      204                   sleep=time.sleep):  # fmt: skip
      205 +        """limits: optional overrides keyed by provider name o
          +r (provider, model) → (rpm, rpd[, tpm])."""                   
      206          self.providers = providers
      207          self._sleep = sleep
      208          self._pdf_text: dict[str | None, str] = {}
      209          self.log = log
      210          self.stats = Stats()
      209 -        self._limiters: dict[str, _Limiter] = {}              
      210 -        self._exhausted: set[str] = set()                     
      211 -        lim = {**DEFAULT_LIMITS, **(limits or {})}            
      212 -        for p in providers:                                   
      213 -            rpm, rpd = lim.get(p.name, (10, 200))             
      214 -            rpm = int(os.environ.get(f"{p.name.upper()}_RPM", 
          -rpm))                                                         
      215 -            rpd = int(os.environ.get(f"{p.name.upper()}_RPD", 
          -rpd))                                                         
      216 -            self._limiters[p.name] = _Limiter(rpm, rpd)       
      211 +        self._limits = limits or {}                           
      212 +        self._exhausted: set[tuple[str, str]] = set()         
      213  
      214      @classmethod
     … 247 more lines (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/llm/router.py'…)
  ⎿  44:    assert row["ok"] and row["tokens_in"] == 1000 and row["est_cost
     _usd"] == pytest.approx((1000 * 1 + 100 * 2) / 1e6)
     81:    assert log.rows[-1]["ok"] is False
     … +2 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/llm/router.py (+4 -2)
       88              1
       89              for r in self.rows
       90              if r["provider"] == provider
       91 +            and r["ok"]                                       
       92              and (model is None or r["model"] == model)
       93              and (purpose_prefix is None or r["purpose"].starts
           with(purpose_prefix))
       94          )
       95  
       96  
       97  class PostgresLLMLog:
       97 -    """llm_calls table: cache + token/cost log. The day bounda
          -ry is midnight Pacific (Gemini's RPD reset)."""               
       98 +    """llm_calls table: cache + token/cost log. The day bounda
          +ry is midnight Pacific (Gemini's RPD reset).                  
       99 +    Daily counts include successful calls only: providers don'
          +t bill a 429/503 against the day's quota."""                  
      100  
      101      def __init__(self, conn):
      102          self.conn = conn
     ...
      125      def count_today(self, provider: str, model: str | None = N
           one, purpose_prefix: str | None = None) -> int:
      126          # Gemini reports the served version (e.g. 'gemini-3.8-
           flash-001'), so a model matches by prefix.
      127          r = self.conn.execute(
      126 -            "select count(*) as n from public.llm_calls where 
          -provider = %s and created_at >= "                             
      128 +            "select count(*) as n from public.llm_calls where 
          +provider = %s and ok and created_at >= "                      
      129              "(date_trunc('day', now() at time zone 'America/Lo
           s_Angeles') at time zone 'America/Los_Angeles') "
      130              "and (%s::text is null or model like %s || '%%') a
           nd (%s::text is null or purpose like %s || '%%')",
      131              (provider, model, model, purpose_prefix, purpose_p
           refix),

⏺ Now the Gemini and Groq providers.

⏺ Bash(python3 - <<'EOF'
      p='finn/llm/gemini.py'…)
  ⎿  finn/llm/groq.py:54:                timeout=req.timeout_s,
     finn/llm/gemini.py:82:                timeout=req.timeout_s,
     finn/llm/gemini.py:114:        r = requests.get(f"{BASE}/models", head
     ers={"x-goog-api-key": self.api_key or ""}, timeout=30)
  ⎿  Updated backend/finn/llm/gemini.py (+25 -8)
      20  BASE = "https://generativelanguage.googleapis.com/v1beta"
      21  DEFAULT_CHEAP = "gemini-3.5-flash-lite"
      22  DEFAULT_STRONG = "gemini-3.8-flash"
      23 +# Strong fallbacks, each with its own free daily quota (never F
         +lash-Lite: product owner, 11 Nov 2026).                        
      24 +DEFAULT_STRONG_FALLBACKS = "gemini-3-flash-preview,gemini-2.5-f
         +lash"                                                          
      25  # Paid-tier list prices (USD / 1M tokens) — used only for the c
          ost estimate in the log; free tier bills nothing.
      26  PRICES = {"flash-lite": (0.30, 2.50), "flash": (0.75, 3.75)}
      27  
     ...
      40              return os.environ.get("GEMINI_MODEL_CHEAP") or DEFA
          ULT_CHEAP
      41          return os.environ.get("GEMINI_MODEL_STRONG") or DEFAULT
          _STRONG
      42  
      43 +    def models_for(self, tier: Tier) -> list[str]:             
      44 +        """The tier's chain: cheap = [Flash-Lite]; strong = GEM
         +INI_MODEL_STRONG then GEMINI_MODEL_STRONG_FALLBACKS."""        
      45 +        first = self.model_for(tier)                           
      46 +        if tier == "cheap":                                    
      47 +            return [first] if first else []                    
      48 +        rest = os.environ.get("GEMINI_MODEL_STRONG_FALLBACKS", 
         +DEFAULT_STRONG_FALLBACKS)                                      
      49 +        chain = [first, *[m.strip() for m in rest.split(",") if
         + m.strip()]]                                                   
      50 +        return [m for i, m in enumerate(chain) if m and "lite" 
         +not in m and m not in chain[:i]]                               
      51 +                                                               
      52      def supports_pdf(self) -> bool:
      53          return True
      54  
     ...
      59          parts: list[dict] = []
      60          if req.pdf:
      61              parts.append({"inline_data": {"mime_type": "applica
          tion/pdf", "data": base64.b64encode(req.pdf).decode()}})
      51 -        parts.append({"text": req.prompt})                     
      62 +        parts.append({"text": req.full_prompt()})              
      63 +        config = {                                             
      64 +            "temperature": 0,                                  
      65 +            "maxOutputTokens": req.max_output_tokens,          
      66 +            "responseMimeType": "application/json",            
      67 +            "responseSchema": req.schema,                      
      68 +        }                                                      
      69 +        if req.thinking_budget is not None:                    
      70 +            config["thinkingConfig"] = {"thinkingBudget": req.t
         +hinking_budget}                                                
      71          body = {
      72              "system_instruction": {"parts": [{"text": req.syste
          m}]},
      73              "contents": [{"role": "user", "parts": parts}],
      55 -            "generationConfig": {                              
     … 26 more lines (ctrl+o to expand)
  ⎿  Updated backend/finn/llm/groq.py (+2 -2)
      42              "response_format": {"type": "json_object"},
      43              "messages": [
      44                  {"role": "system", "content": f"{req.system}\nR
          eply with one JSON object matching: {schema_hint}"},
      45 -                {"role": "user", "content": req.prompt},       
      45 +                {"role": "user", "content": req.full_prompt()},
      46              ],
      47          }
      48          t0 = time.perf_counter()
     ...
      51                  f"{BASE}/chat/completions",
      52                  headers={"Authorization": f"Bearer {self.api_ke
          y}"},
      53                  json=body,
      54 -                timeout=60,                                    
      54 +                timeout=req.timeout_s,                         
      55              )
      56          except requests.RequestException as e:
      57              raise TransientError(f"groq network error: {type(e)
          .__name__}") from e

⏺ Now conftest + new router tests.

⏺ Bash(cat > tests/conftest.py <<'EOF'
      import pytest…)
  ⎿  ......................................................................
     .. [ 32%]
     ......................................................................
     … +16 lines (ctrl+o to expand)
  ⎿  Created backend/tests/conftest.py (+10 -0)
       1 +import pytest                                                  
       2 +                                                               
       3 +                                                               
       4 +@pytest.fixture(autouse=True)                                  
       5 +def _fresh_llm_limiters():                                     
       6 +    """Per-model limiters are process-wide; forget per-minute h
         +istory between tests."""                                       
       7 +    from finn.llm.router import reset_limiters                 
       8 +                                                               
       9 +    reset_limiters()                                           
      10 +    yield                                                      
  ⎿  Updated backend/tests/test_llm_router.py (+104 -0)
      1 +import json                                                     
      2 +                                                                
      3  import pytest
      4  
      5  from finn.llm import LLMRequest, LLMResult, LLMUnavailable, Memo
         ryLLMLog, ProviderError, QuotaExceeded, Router
     ...
      144      g = Flaky("gemini", [QuotaExceeded("429 PerDay", daily=Tru
           e)])
      145      r = Router([g, Fake("groq", pdf=False)], MemoryLLMLog(), s
           leep=pauses.append)
      146      assert r.run("cheap", req()).provider == "groq" and pauses
            == [] and len(g.calls) == 1
      147 +                                                              
      148 +                                                              
      149 +# --- Phase 3: per-model quotas, strong chain, research lane, 
          +document text ---------------------------------               
      150 +                                                              
      151 +                                                              
      152 +class Chain(Fake):                                            
      153 +    """A provider with a strong-tier chain whose models can fa
          +il independently."""                                          
      154 +                                                              
      155 +    def __init__(self, name, chain, fails=None, **kw):        
      156 +        super().__init__(name, **kw)                          
      157 +        self.chain, self.fails = chain, fails or {}           
      158 +                                                              
      159 +    def models_for(self, tier):                               
      160 +        return self.chain[tier]                               
      161 +                                                              
      162 +    def generate(self, req, model):                           
      163 +        self.calls.append((req, model))                       
      164 +        if model in self.fails:                               
      165 +            raise self.fails[model]                           
      166 +        return LLMResult(self.data, self.name, model, tokens_i
          +n=10, tokens_out=5, latency_ms=5)                             
      167 +                                                              
      168 +                                                              
      169 +CHAIN = {"cheap": ["lite"], "strong": ["flash-38", "flash-3", 
          +"flash-25"]}                                                  
      170 +                                                              
      171 +                                                              
      172 +def test_strong_daily_quota_leaves_cheap_alive():             
      173 +    g = Chain("gemini", CHAIN, fails={"flash-38": QuotaExceede
          +d("429 PerDay", daily=True)})                                 
      174 +    r = Router([g], MemoryLLMLog(), sleep=lambda s: None)     
      175 +    assert r.run("strong", req(purpose="research.judge.v1")).m
          +odel == "flash-3"                                             
      176 +    assert r.run("cheap", req(prompt="cheap one")).model == "l
          +ite"                                                          
      177 +                                                              
      178 +                                                              
     … 70 more lines (ctrl+o to expand)

⏺ 225 pass. Quick live check that both fallback model ids answer (one tiny call
  each):

  Ran 1 shell command (ctrl+o to expand)

⏺ Thinking tokens ate the 256-token cap — exactly the case the truncation check
  exists for. Retrying with room:

  Ran 1 shell command (ctrl+o to expand)

⏺ gemini-3-flash-preview works, but gemini-2.5-flash is rejected as no longer
  available, so I'm removing it and the strong chain becomes 3.8 Flash then 3
  Flash. Flash-Lite won't accept thinkingBudget: 0, so research calls to it will
  leave that out. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(sed -i '' 's/    monkeypatch.setenv("GEMINI_MODEL_STRONG_FALLBACKS",
      "gemini-3-flash-preview, gemini-3.5-flash-lite, gemini-2.5-flash")/
      chain = "gemini-3-fl…)
  ⎿  All checks passed!
     225 passed, 1 warning in 1.02s
     248aea6 LLM router: per-model quotas, strong fallback chain, TPM, rese
     arch lane caps, hashed document text
  ⎿  Updated backend/tests/test_llm_router.py (+2 -1)
      189      from finn.llm.gemini import Gemini
      190  
      191      monkeypatch.setenv("GEMINI_MODEL_STRONG", "gemini-3.8-flas
           h")
      192 -    monkeypatch.setenv("GEMINI_MODEL_STRONG_FALLBACKS", "gemin
          -i-3-flash-preview, gemini-3.5-flash-lite, gemini-2.5-flash")  
      192 +    chain = "gemini-3-flash-preview, gemini-3.5-flash-lite, ge
          +mini-2.5-flash"                                               
      193 +    monkeypatch.setenv("GEMINI_MODEL_STRONG_FALLBACKS", chain)
      194      assert Gemini("k").models_for("strong") == ["gemini-3.8-fl
           ash", "gemini-3-flash-preview", "gemini-2.5-flash"]
      195  
      196  

  Called ccd_session, ccd_turn 2 times, ran 1 shell command (ctrl+o to expand)

⏺ Router pushed. Now screener discovery: fetching trimmed page fixtures for
  POLYCAB, BAJFINANCE, HDFCBANK and INFY (3 s apart).

⏺ Bash(mkdir -p /private/tmp/claude-501/-Users-<user>--claude-spares-spare-y
      icH6h/bb463e84-2008-445e-be1c-9b1ec9bda462/scratchpad/tools && cat >
      /private/tmp/claud…)
  ⎿  POLYCAB 200 267924 -> 140052
     BAJFINANCE 200 272367 -> 143130
     HDFCBANK 200 255344 -> 126145
     … +12 lines (ctrl+o to expand)
  ⎿  Created backend/tests/fixtures/screener_POLYCAB_cfi_schedule.json
     (+114 -0)
        1 +{                                                             
        2 +"Fixed assets purchased": {                                   
        3 +"Mar 2015": "-204",                                           
        4 +"Mar 2016": "-249",                                           
        5 +"Mar 2017": "-279",                                           
        6 +"Mar 2018": "-199",                                           
        7 +"Mar 2019": "-286",                                           
        8 +"Mar 2020": "-290",                                           
        9 +"Mar 2021": "-193",                                           
       10 +"Mar 2022": "-527",                                           
       11 +"Mar 2023": "-479",                                           
       12 +"Mar 2024": "-859",                                           
       13 +"Mar 2025": "-970",                                           
       14 +"Mar 2026": "-1,481"                                          
       15 +},                                                            
       16 +"Fixed assets sold": {                                        
       17 +"Mar 2015": "1",                                              
       18 +"Mar 2016": "3",                                              
       19 +"Mar 2017": "1",                                              
       20 +"Mar 2018": "16",                                             
       21 +"Mar 2019": "5",                                              
       22 +"Mar 2020": "1",                                              
       23 +"Mar 2021": "2",                                              
       24 +"Mar 2022": "7",                                              
       25 +"Mar 2023": "21",                                             
       26 +"Mar 2024": "1",                                              
       27 +"Mar 2025": "14",                                             
       28 +"Mar 2026": "10"                                              
       29 +},                                                            
       30 +"Investments purchased": {                                    
       31 +"Mar 2015": "0",                                              
       32 +"Mar 2016": "0",                                              
       33 +"Mar 2017": "0",                                              
       34 +"Mar 2018": "0",                                              
       35 +"Mar 2019": "0",                                              
       36 +"Mar 2020": "-29,399",                                        
       37 +"Mar 2021": "-8,058",                                         
       38 +"Mar 2022": "-9,268",                                         
       39 +"Mar 2023": "-9,647",                                         
       40 +"Mar 2024": "-12,760",                                        
     … 74 more lines (ctrl+o to expand)
  ⎿  … 4 more files changed

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(cat >> finn/sources/screener.py <<'EOF'…)
  ⎿  POLYCAB quarters consolidated [('Mar 2026', 'quarter'), ('Jun 2026', '
     quarter'), ('Sep 2026', 'quarter')] ['Sales', 'YoY Sales growth', 'Exp
     enses', 'Operating Profit']
     … +35 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/sources/screener.py (+167 -0)
       89      if not r.ok:
       90          raise FetchError(url, r.status_code)
       91      return parse_quarters(r.text, symbol, url)
       92 +                                                              
       93 +                                                              
       94 +# ------------------------------------------------------------
          +---------------------------------                             
       95 +# Research (Phase 3): every standardised table, document links
          +, and the capex schedule.                                     
       96 +# ------------------------------------------------------------
          +---------------------------------                             
       97 +                                                              
       98 +_MONTHS = {m: i for i, m in enumerate(("Jan", "Feb", "Mar", "A
          +pr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",         
       99 +                                        "Dec"), start=1)}  # f
          +mt: skip                                                      
      100 +                                                              
      101 +                                                              
      102 +@dataclass                                                    
      103 +class Column:                                                 
      104 +    label: str  # as printed: 'Mar 2026', 'TTM', 'Sep 2026'   
      105 +    end: date | None  # period end (month end); None for TTM  
      106 +    kind: str  # 'year' | 'interim' (a half-year column on the
          + balance sheet) | 'ttm' | 'quarter'                           
      107 +                                                              
      108 +                                                              
      109 +@dataclass                                                    
      110 +class Table:                                                  
      111 +    section: str  # screener section id: quarters | profit-los
          +s | balance-sheet | cash-flow | ratios | shareholding         
      112 +    basis: str  # consolidated | standalone                   
      113 +    url: str                                                  
      114 +    unit_note: str                                            
      115 +    columns: list[Column]                                     
      116 +    rows: dict[str, list[float | None]] = field(default_factor
          +y=dict)                                                       
      117 +    raw: dict[str, list[str]] = field(default_factory=dict)  #
          + values exactly as printed                                    
      118 +    fetched_at: datetime = field(default_factory=lambda: datet
          +ime.now(UTC))                                                 
      119 +                                                              
      120 +    def get(self, row: str, col: Column) -> float | None:     
      121 +        if row not in self.rows:                              
      122 +            return None                                       
      123 +        return self.rows[row][self.columns.index(col)]        
      124 +                                                              
      125 +    def raw_value(self, row: str, col: Column) -> str | None: 
      126 +        return self.raw.get(row, [None] * len(self.columns))[s
          +elf.columns.index(col)]                                       
      127 +                                                              
      128 +    def years(self) -> list[Column]:                          
     … 130 more lines (ctrl+o to expand)

⏺ Parsers work on all fixtures. Now discover.py.

⏺ Write(backend/finn/research/discover.py)
  ⎿  Wrote 139 lines to backend/finn/research/discover.py
       1 """Step 1 — discover: screener's standardised tables and the doc
         ument index for one ticker.
       2 
       3 Consolidated first; standalone when screener has no consolidated
          tables (companies without subsidiaries). The
       4 last 8 earnings-call transcripts and the latest annual report co
         me from screener's document list (mostly
       5 BSE-hosted PDFs, which Render can fetch). NSE-hosted links are s
         kipped on Render (NSE blocks it).
       6 """
     … +133 lines (ctrl+o to expand)

  Searched for 1 pattern (ctrl+o to expand)

⏺ Now compute.py: trajectory, cash quality and balance sheet in code, standard
  and lender variants.

⏺ Write(backend/finn/research/compute.py)
  ⎿  Wrote 333 lines to backend/finn/research/compute.py
       1 """Step 4 — compute: trajectory, cash quality and balance sheet 
         from screener's standardised tables, in code.
       2 
       3 Every value is a `Figure`: read straight from a screener row (ci
         tation locator 'screener:<section>/<row>/<period>',
       4 status verified — the value is what the cited table prints), or 
         computed here with its formula and inputs.
       5 Lenders (banks/NBFCs) get NII, PAT, ROE, ROA and asset quality i
         nstead of EBITDA, ROCE and cash conversion.
       6 """
     … +327 lines (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/research/compute.py'…)
  ⎿  POLYCAB standard consolidated 3 8 FY26 ['Q2 FY27', 'Q1 FY27', 'Q4 FY26
     ', 'Q3 FY26', 'Q2 FY26', 'Q1 FY26', 'Q4 FY25', 'Q3 FY25']
       traj [('Revenue', 10, 28884.0, 'FY26'), ('Operating margin (OPM)', 1
     … +42 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/compute.py (+7 -4)
      43  
      44  
      45  def year_label(end: date) -> str:
      46 -    return f"FY{(end.year if end.month <= 3 or end.month == 12 
         -and False else end.year) % 100:02d}" if end.month == 3 \       
      47 -        else end.strftime("%b %Y")  # fmt: skip                
      46 +    """Indian FY label for March year-ends (FY26 = Apr 2025–Mar
         + 2026); other year-ends by their end month."""                 
      47 +    return f"FY{end.year % 100:02d}" if end.month == 3 else end
         +.strftime("%b %Y")                                             
      48 +                                                               
      49 +                                                               
      50 +def year_start(end: date) -> date:                             
      51 +    return date(end.year, 1, 1) if end.month == 12 else date(en
         +d.year - 1, end.month + 1, 1)                                  
      52  
      53  
      54  def period_for(col: Column, ttm_end: date | None = None) -> Per
          iod:
     ...
      63          from finn.calendar import quarter_period
      64  
      65          return quarter_period(end)
      62 -    return Period(kind="year", start=date(end.year - 1, end.mon
         -th, 1) + timedelta(days=31 - 31), end=end,                     
      63 -                  label=year_label(end))  # fmt: skip          
      66 +    return Period(kind="year", start=year_start(end), end=end, 
         +label=year_label(end))                                         
      67  
      68  
      69  def _cite(t: Table, row: str, col: Column) -> Citation:

⏺ The numbers check out, but I'm making three fixes: the FCF check let POLYCAB's
  ₹10 Cr gap slip through a relative tolerance, screener's "Financing margin"
  is meaningless for banks so I'm dropping it, and capex will display as
  positive spend. · summary

⏺ Bash(python3 - <<'EOF'
      p='finn/research/compute.py'…)
  ⎿  FY23 970.0 CFO + fixed assets purchased + fixed assets sold verified s
     creener Free Cash Flow: 969 ✓
     FY24 437.0 CFO + fixed assets purchased verified screener Free Cash Fl
     … +10 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/compute.py (+7 -5)
      179          fcf = _fcf(d, cf, col, cfo)
      180          if fcf:
      181              fcf_pts.append(fcf)
      182 -            capex_pts.append(fcf.inputs[1])                   
      182 +            purchased = fcf.inputs[1]                         
      183 +            capex_pts.append(computed("Capex", -purchased.valu
          +e, "INR_CR", [purchased],  # type: ignore[operator]           
      184 +                                      "− fixed assets purchase
          +d (cash spent on fixed assets)"))  # fmt: skip                
      185      cfo_s, ratio_s = _series("CFO", "INR_CR", cfo_pts, d.basis
           ), _series("CFO/PAT", "X", ratio_pts, d.basis)
      186      fcf_s, capex_s = _series("Free cash flow", "INR_CR", fcf_p
           ts, d.basis), _series("Capex", "INR_CR", capex_pts, d.basis)
      187      c.cash = [s for s in (cfo_s, ratio_s, fcf_s, capex_s) if s
           ]
     ...
      239      screener_fcf = cf.get("Free Cash Flow", col) if "Free Cash
            Flow" in cf.rows else None
      240      note, ok = None, True
      241      if screener_fcf is not None:
      240 -        if approx_equal(v, screener_fcf, abs_tol=2.0, rel_tol=
          -0.005):                                                       
      242 +        # screener rounds each row to whole crore, so a sum of
          + 2–3 rows may differ by up to ~2                              
      243 +        if approx_equal(v, screener_fcf, abs_tol=2.0, rel_tol=
          +0.0):                                                         
      244              note = f"screener Free Cash Flow: {cf.raw_value('F
           ree Cash Flow', col)} ✓"
      242 -        elif sold_v and approx_equal(v + sold_v, screener_fcf,
          - abs_tol=2.0, rel_tol=0.005):                                 
      245 +        elif sold_v and approx_equal(v + sold_v, screener_fcf,
          + abs_tol=2.0, rel_tol=0.0):                                   
      246              sold = Figure(label="Fixed assets sold", value=sol
           d_v, unit="INR_CR", period=cfo.period, basis=cf.basis,
      247                            status="verified", citation=sched.mo
           del_copy(update={"locator": sched.locator.replace(
      248                                "Fixed assets purchased", "Fixed
            assets sold")}))  # fmt: skip
     ...
      266                                      "Revenue − Interest (scree
           ner definition)"))  # fmt: skip
      267      nii = _series("NII", "INR_CR", nii_pts, d.basis)
      268      roe = row_series(ra, "ROE %", "ROE", "PCT")
      266 -    margin = row_series(pl, "Financing Margin %", "Financing m
          -argin", "PCT")                                                
      267 -    c.trajectory = [s for s in (nii, pat, roe, margin, revenue
          -) if s]                                                       
      269 +    c.trajectory = [s for s in (nii, pat, roe, revenue) if s] 
      270      c.growth = cagrs(nii, "NII") + cagrs(pat, "PAT")
      271      gnpa = _series("Gross NPA", "PCT", [sourced(q, "Gross NPA 
           %", col, "Gross NPA", "PCT") for col in
      272                                           (q.columns if q else 
           [])], d.basis)  # type: ignore[arg-type]  # fmt: skip

⏺ Screener's FCF is CFO + fixed assets purchased + fixed assets sold; using that
  one formula every year instead of switching:

⏺ Bash(python3 - <<'EOF'
      p='finn/research/compute.py'…)
  ⎿  [('FY17', 18.0, 'verified'), ('FY18', 179.0, 'verified'), ('FY19', 949
     .0, 'verified'), ('FY20', -45.0, 'verified'), ('FY21', 1061.0, 'verifi
     ed'), ('FY22', -8.0, 'verified'), ('FY23', 970.0, 'verified'), ('FY24'
     … +2 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/compute.py (+6 -6)
      236      capex = Figure(label="Fixed assets purchased", value=capex
           _v, unit="INR_CR", period=cfo.period, basis=cf.basis,
      237                     status="verified", citation=sched, raw=d.ca
           pex[col.label], raw_unit="crore")  # fmt: skip
      238      inputs, formula, v = [cfo, capex], "CFO + fixed assets pur
           chased", cfo.value + capex_v  # type: ignore[operator]
      239 +    if sold_v:  # screener's own Free Cash Flow = CFO + fixed 
          +assets purchased + fixed assets sold                          
      240 +        sold = Figure(label="Fixed assets sold", value=sold_v,
          + unit="INR_CR", period=cfo.period, basis=cf.basis,            
      241 +                      status="verified", raw=d.fixed_assets_so
          +ld[col.label], raw_unit="crore",                              
      242 +                      citation=sched.model_copy(update={"locat
          +or": sched.locator.replace(                                   
      243 +                          "Fixed assets purchased", "Fixed ass
          +ets sold")}))  # fmt: skip                                    
      244 +        inputs, formula, v = [cfo, capex, sold], "CFO + fixed 
          +assets purchased + fixed assets sold", v + sold_v             
      245      screener_fcf = cf.get("Free Cash Flow", col) if "Free Cash
            Flow" in cf.rows else None
      246      note, ok = None, True
      247      if screener_fcf is not None:
      248          # screener rounds each row to whole crore, so a sum of
            2–3 rows may differ by up to ~2
      249          if approx_equal(v, screener_fcf, abs_tol=2.0, rel_tol=
           0.0):
      250              note = f"screener Free Cash Flow: {cf.raw_value('F
           ree Cash Flow', col)} ✓"
      245 -        elif sold_v and approx_equal(v + sold_v, screener_fcf,
          - abs_tol=2.0, rel_tol=0.0):                                   
      246 -            sold = Figure(label="Fixed assets sold", value=sol
          -d_v, unit="INR_CR", period=cfo.period, basis=cf.basis,        
      247 -                          status="verified", citation=sched.mo
          -del_copy(update={"locator": sched.locator.replace(            
      248 -                              "Fixed assets purchased", "Fixed
          - assets sold")}))  # fmt: skip                                
      249 -            inputs, formula, v = [cfo, capex, sold], "CFO + fi
          -xed assets purchased + fixed assets sold", v + sold_v         
      250 -            note = f"screener Free Cash Flow: {cf.raw_value('F
          -ree Cash Flow', col)} ✓"                                      
      251          else:
      252              note, ok = f"screener Free Cash Flow prints {cf.ra
           w_value('Free Cash Flow', col)}", False
      253      return computed("Free cash flow", v, "INR_CR", inputs, for
           mula, check_note=note, ok=ok)
⏺ FCF matches screener's own row for all 10 years. Wiring discover + compute
  into the build:

⏺ Write(backend/finn/research/build.py)
  ⎿  Added 73 lines, removed 3 lines
       8  from __future__ import annotations
       9  
      10  import logging
      11 +from datetime import datetime                                  
      12  
      13  from finn.calendar import now_utc
      14 +from finn.models.research import Dossier, SectionMeta          
      15  from finn.research import store
      16  from finn.research.jobs import Outcome, Progress
      17  from finn.research.skeleton import empty_dossier
      18  
      19  log = logging.getLogger("finn.research.build")
      20  
      21 +PIPELINE_VERSION = "1"                                         
      22  
      20 -def build(conn, symbol: str, progress: Progress, job_id: int | 
         -None = None) -> Outcome:                                       
      23 +                                                               
      24 +def meta(status: str, reason: str | None = None, note: str | No
         +ne = None, as_of: datetime | None = None,                      
      25 +         **kw) -> SectionMeta:  # fmt: skip                    
      26 +    return SectionMeta(status=status, reason=reason, note=note,
         + as_of=as_of, **kw)                                            
      27 +                                                               
      28 +                                                               
      29 +def build(conn, symbol: str, progress: Progress, job_id: int | 
         +None = None, router=None) -> Outcome:                          
      30 +    from finn.research.discover import discover                
      31 +                                                               
      32      sec = store.security(conn, symbol)
      33      name = (sec or {}).get("name") or symbol
      34      now = now_utc()
     ...
       36      d = prev.model_copy(deep=True) if prev else empty_dossier(
           symbol, name, now)
       37      d.built_at = now
       38  
       39 +    # 1. Discover (screener tables + document index)          
       40      progress.step("discover", "running", message="Finding the 
           company's financials and documents")
       41 +    disc = discover(symbol)                                   
       42 +    if disc.status == "ok":                                   
       43 +        progress.step("discover", "done", f"{len(disc.transcri
          +pts)} transcripts, "                                          
       44 +                      f"{'an' if disc.annual_report else 'no'}
          + annual report, {disc.basis} financials")  # fmt: skip        
       45 +    else:                                                     
       46 +        progress.step("discover", "failed", disc.note)        
       47 +                                                              
       48 +    # 2. Compute (code only, no model)                        
       49 +    progress.step("compute", "running", message="Computing tra
          +jectory, cash and balance sheet")                             
       50 +    apply_compute(d, disc, prev, now)                         
       51 +    progress.step("compute", "done" if disc.status == "ok" els
          +e "skipped")                                                  
       52      store.publish(conn, d, complete=False)
       30 -    for key in ("discover", "compute", "documents", "extract",
          - "ledger", "judge", "reduce"):                                
       53 +                                                              
       54 +    # 3+. Documents, extraction, ledger, synthesis — later sta
          +ges fill these sections.                                      
       55 +    for key in ("documents", "extract", "ledger", "judge", "re
          +duce"):                                                       
       56          progress.step(key, "skipped", "Not available in this b
           uild yet")
       32 -    progress.step("publish", "done", message="Published (secti
          -ons still building)")                                         
       57 +    progress.step("publish", "done", message="Published")     
       58      store.publish(conn, d, complete=False)
       59      return Outcome("partial", stats={})
       60 +                                                              
       61 +                                                              
       62 +def apply_compute(d: Dossier, disc, prev: Dossier | None, now:
          + datetime) -> None:                                           
       63 +    """Fill snapshot headline, trajectory, cash quality and ba
          +lance sheet from screener (or say why not)."""                
       64 +    from finn.research.compute import compute                 
       65 +                                                              
       66 +    if disc.status != "ok":                                   
       67 +        reason = "source_unreachable" if disc.status == "sourc
          +e_unreachable" else "no_screener_page"                        
       68 +        keep = reason == "source_unreachable" and prev is not 
          +None  # rule 7: serve the last good sections                  
       69 +        for sec in (d.trajectory, d.cash_quality, d.balance_sh
          +eet):                                                         
       70 +            if keep and sec.meta.status == "ready":           
       71 +                sec.meta = sec.meta.model_copy(update={"note":
          + f"{disc.note} — showing data as of "                         
       72 +                                                       f"{sec.
          +meta.as_of:%d %b %Y}" if sec.meta.as_of else disc.note})      
       73 +            else:                                             
       74 +                sec.meta = meta("unavailable", reason, disc.no
          +te if reason == "source_unreachable"                          
       75 +                                else f"No standardised financi
          +als for {d.symbol} (screener.in has no page)")                
       76 +        if not keep:                                          
       77 +            d.snapshot.headline = []                          
       78 +        return                                                
       79 +    c = compute(disc)                                         
       80 +    asof = disc.fetched_at                                    
       81 +    d.template, d.basis, d.screener_url, d.as_of = c.template,
          + disc.basis, disc.url, asof  # type: ignore[assignment]       
       82 +    basis_note = None if disc.basis == "consolidated" else "St
          +andalone figures (no consolidated accounts on screener)"      
       83 +    d.snapshot.headline = c.headline                          
       84 +    if d.snapshot.meta.status != "ready":                     
       85 +        d.snapshot.meta = meta("partial", "not_built_yet", "He
          +adline numbers ready; business summary is being written",     
       86 +                               asof)  # fmt: skip             
       87 +    d.trajectory.series, d.trajectory.growth = c.trajectory, c
          +.growth                                                       
       88 +    d.trajectory.meta = meta("ready", None, basis_note, asof) 
       89 +    if c.cash_applicable:                                     
       90 +        d.cash_quality.series, d.cash_quality.latest = c.cash,
          + c.cash_latest                                                
       91 +        if c.cash:                                            
       92 +            fcf_note = None if any(s.metric == "Free cash flow
          +" for s in c.cash) else "Free cash flow: capex schedule " \   
       93 +                "not available on screener"  # fmt: skip      
       94 +            d.cash_quality.meta = meta("ready" if not fcf_note
          + else "partial", None, fcf_note or basis_note, asof)          
       95 +        else:                                                 
       96 +            d.cash_quality.meta = meta("unavailable", "not_fou
          +nd_in_sources", "No cash-flow table on screener", asof)       
       97 +    else:                                                     
       98 +        d.cash_quality.series, d.cash_quality.latest = [], [] 
       99 +        d.cash_quality.meta = meta("unavailable", "not_meaning
          +ful_for_lenders",                                             
      100 +                                   "CFO/PAT and free cash flow
          + aren't meaningful for lenders: loan growth runs "            
      101 +                                   "through operating cash flo
          +w", asof)  # fmt: skip                                        
      102 +    d.balance_sheet.series, d.balance_sheet.latest = c.balance
          +, c.balance_latest                                            
      103 +    d.balance_sheet.meta = meta("ready" if c.balance else "una
          +vailable", None if c.balance else "not_found_in_sources",     
      104 +                                basis_note, asof)  # fmt: skip

  Ran 1 shell command (ctrl+o to expand)

⏺ The real POLYCAB build works locally, with trajectory, cash and balance sheet
  all ready. Adding tests, then commit.

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/research/build.py'…)
  ⎿  All checks passed!

     -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.htm
     … +2 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/build.py (+2 -2)
       99      if c.cash_applicable:
      100          d.cash_quality.series, d.cash_quality.latest = c.cash,
            c.cash_latest
      101          if c.cash:
      102 -            fcf_note = None if any(s.metric == "Free cash flow
          -" for s in c.cash) else "Free cash flow: capex schedule " \   
      103 -                "not available on screener"  # fmt: skip      
      102 +            has_fcf = any(s.metric == "Free cash flow" for s i
          +n c.cash)                                                     
      103 +            fcf_note = None if has_fcf else "Free cash flow: c
          +apex schedule not available on screener"                      
      104              d.cash_quality.meta = meta("ready" if not fcf_note
            else "partial", None, fcf_note or basis_note, asof)
      105          else:
      106              d.cash_quality.meta = meta("unavailable", "not_fou
           nd_in_sources", "No cash-flow table on screener", asof)

  Ran 1 shell command (ctrl+o to expand)

⏺ Discovery and compute are pushed. Please set the Render model keys and the
  --workers 1 start command per DEPLOY.md §7; I'm moving on to PyMuPDF
  transcript extraction next. · summary

  Called ccd_turn (ctrl+o to expand)

⏺ Bash(cd ~/Documents/finn/backend && ../.venv/bin/pip install
      -q "pymupdf>=1.24" 2>&1 | tail -2; ../.venv/bin/python -c "import pymupdf;
      print(pymupdf…)
  ⎿  2.1 2.1
     24:  "pymupdf>=1.24",
     34:  "pymupdf>=1.24",
  ⎿  Updated backend/pyproject.toml (+3 -0)
      20    # screener parsing (cross-checks now; Phase 3 research runs o
          n Render)
      21    "beautifulsoup4>=4.12",
      22    "lxml>=5.0",
      23 +  # research: transcript / annual-report text, page by page (AG
         +PL-3.0; this repo is public — DECISIONS.md)                    
      24 +  "pymupdf>=1.24",                                             
      25  ]
      26  jobs = [
      27    "requests>=2.32",
     ...
      31    "pandas>=2.2",
      32    "psycopg[binary]>=3.2",
      33    "pypdf>=5",
      34 +  "pymupdf>=1.24",                                             
      35  ]
      36  dev = [
      37    "pytest>=8",

⏺ Now fetch_to_file, documents.py and the citation checker.

⏺ Bash(python3 - <<'EOF'
      p='finn/sources/http.py'…)
  ⎿  done
  ⎿  Updated backend/finn/sources/http.py (+48 -2)
      14  import json
      15  import logging
      16  import os
      17 +import tempfile                                                
      18 +import threading                                               
      19  import time
      20  from pathlib import Path
      21  from urllib.parse import urlparse
     ...
      42  RETRY_STATUS = {401, 403, 429}
      43  
      44  _last_hit: dict[str, float] = {}
      45 +_throttle_lock = threading.Lock()  # the API's research worker 
         +and request threads share this module                          
      46  
      47  
      48  def cache_dir() -> Path:
     ...
      60  def _throttle(url: str) -> None:
      61      host = urlparse(url).netloc
      62      gap = MIN_INTERVAL.get(host, DEFAULT_INTERVAL)
      60 -    wait = _last_hit.get(host, 0.0) + gap - time.monotonic()   
      63 +    with _throttle_lock:  # reserve the next slot for this host
         +, then sleep outside the lock                                  
      64 +        slot = max(time.monotonic(), _last_hit.get(host, 0.0) +
         + gap)                                                          
      65 +        _last_hit[host] = slot                                 
      66 +    wait = slot - time.monotonic()                             
      67      if wait > 0:
      68          time.sleep(wait)
      63 -    _last_hit[host] = time.monotonic()                         
      69  
      70  
      71  def _key(url: str, params: dict | None) -> str:
     ...
      175      return bytes(buf)
      176  
      177  
      178 +def fetch_to_file(url: str, *, max_bytes: int, deadline_s: flo
          +at = 120, headers: dict | None = None,                        
      179 +                  session: requests.Session | None = None) -> 
          +tuple[Path | None, str]:  # fmt: skip                         
      180 +    """Stream a document to a temp file (never held in RAM; th
          +e caller deletes it). Returns (path, status) with             
      181 +    status 'ok' | 'too_large' | 'failed:<reason>'. Nothing is 
          +cached on disk: Render's disk is wiped anyway, and            
      182 +    research keeps only extracted text (in Supabase)."""      
      183 +    s = session or requests.Session()                         
      184 +    _throttle(url)                                            
      185 +    t0 = time.monotonic()                                     
     … 36 more lines (ctrl+o to expand)

⏺ Write(backend/finn/research/documents.py)
  ⎿  Wrote 153 lines to backend/finn/research/documents.py
      1 """Step 2 — documents: download each PDF once, extract text page 
        by page, keep only the text.
      2 
      3 - A URL is downloaded at most once (research_documents); the PDF'
        s sha256 keys its text (research_doc_text), so the
      4   same file under two URLs is extracted once. PDFs are streamed t
        o a temp file and deleted after extraction.
      5 - PyMuPDF reads one page at a time from the file (low memory on R
        ender's 512 MB).
      6 - Scanned documents (no text layer) are reported as 'scanned' and
     … +148 lines (~7 KB) (ctrl+o to expand)

  Ran 1 shell command (ctrl+o to expand)

⏺ Documents work: about 1.5 s each, call dates parsed from page 1, cached on the
  second read. Now the metric vocabulary and the citation checker.

⏺ Write(backend/finn/research/metrics.py)
  ⎿  Wrote 92 lines to backend/finn/research/metrics.py
       1 """Metric vocabulary for the Promise Ledger: keys the model choo
         ses from, which direction is good, labels for
       2 drivers, synonyms for the 'quietly dropped' text search, and whi
         ch screener rows may score a promise.
       3 
       4 Direction is decided here (code), never by the model: 'higher' (
         growth, margins), 'lower' (credit cost, NPAs,
       5 costs), 'neutral' (plans like capex, where delivering more or le
         ss than said both differ from the promise).
       6 """
     … +86 lines (ctrl+o to expand)

⏺ Write(backend/finn/research/checker.py)
  ⎿  Wrote 173 lines to backend/finn/research/checker.py
       1 """Citation checker for research (trust layer §10.6): every mode
         l quote must be found in its document's text.
       2 
       3 Order of search: the page the model named, the pages either side
          (quotes straddle page breaks), then pages that
       4 contain the quote's rarest words. Text on both sides is normalis
         ed (Unicode, case, curly quotes, dashes, line-break
       5 hyphenation, whitespace). A quote that still isn't found may be 
         re-anchored: replaced by the sentence on the
       6 claimed page (±1) that overlaps it most AND contains the number 
     … +168 lines (~6 KB) (ctrl+o to expand)

⏺ Now the MAP extraction: prompt, schema, validation, and checks against the
  page text.

⏺ Write(backend/finn/research/extract.py)
  ⎿  Wrote 258 lines to backend/finn/research/extract.py
       1 """Step 3 — MAP: one cheap-model call per transcript → validated
         , quote-checked facts.
       2 
       3 The model only reads: it copies statements, numbers as printed a
         nd verbatim quotes with page numbers. Code then
       4 validates every item (Pydantic, item by item, so one bad item ne
         ver sinks the rest), finds each quote in the
       5 page text (checker), requires the item's number to be printed in
          its own quote, drops anything said by an analyst
       6 or moderator as guidance, and stores the result per (document ha
     … +253 lines (~12 KB) (ctrl+o to expand)

  Ran 1 shell command (ctrl+o to expand)

⏺ MAP works: 53/53 quotes found in the page text, and 1 item was dropped because
  its number wasn't printed in its quote. Committing what's in hand.

  Ran 1 shell command (ctrl+o to expand)

⏺ Two over-long lines would fail CI's ruff check. Fixing them:

⏺ Bash(cd ~/Documents/finn/backend && python3 - <<'EOF'
      p='finn/research/documents.py'; s=open(p).read()…)
  ⎿  All checks passed!
     116 files already formatted
     235 passed, 1 warning in 1.31s
     e594134 Research: line length (ruff)
  ⎿  Updated backend/finn/research/documents.py (+1 -1)
      137              pages, _ = extract_pages(path)
      138              if is_scanned(pages):
      139                  store.upsert_document(conn, link.url, symbol, 
           link.kind, sha256=sha, pages=len(pages), bytes=size,
      140 -                                      status="scanned", status
          -_note="Scanned — no text layer", fetched_at=now)  # fmt: skip 
      140 +                                      status="scanned", status
          +_note="Scanned", fetched_at=now)  # fmt: skip                 
      141                  return Doc(ref("scanned", "Scanned — not read"
           , len(pages), sha), sha, None)
      142              store.save_text(conn, sha, pages, EXTRACTOR)
      143      finally:
  ⎿  Updated backend/finn/research/extract.py (+2 -1)
      86              "kind": {"type": "string", "enum": ["point", "range
          ", "at_least", "at_most", "qualitative"]},
      87              "target_low": _NUM, "target_high": _NUM, "unit_text
          ": {"type": "string", "nullable": True},
      88              **_BASIS, **_PERIOD, "statement": _STR, "search_ter
          ms": {"type": "array", "items": _STR},
      89 -            "speaker": _STR, "speaker_role": {"type": "string",
         - "enum": ["management", "analyst", "moderator", "other"]},     
      89 +            "speaker": _STR,                                   
      90 +            "speaker_role": {"type": "string", "enum": ["manage
         +ment", "analyst", "moderator", "other"]},                      
      91              **_CITE,
      92          }, "required": ["metric", "metric_key", "measure", "kin
          d", "currency", "scope", "period_text", "period_type",
      93                          "statement", "speaker", "speaker_role",
           "quote", "page"]}},

  Called ccd_turn (ctrl+o to expand)

⏺ Your usage limit was reached, so I stopped partway through. Everything
  finished so far is pushed to main, and all 235 tests pass.

  Done and live on Render (bfffd9e; later commits pushed but not yet confirmed
  via /version):
  - Contract: Dossier, MgmtPromise, DossierJob, DossierResponse and AskAnswer,
    with TypeScript types regenerated. Every section is a fixed field that
    always carries a status, reason and note, so you can build the frontend
    against it tomorrow.
  - Database and API: migration 0004_research.sql is applied to Supabase. The
    endpoints are /research/symbols, /research/{sym}, /research/{sym}/build,
    /research/jobs/{id} and /research/{sym}/ask (Ask is a stub for now). The
    Vercel proxy allow-list includes them.
  - Background builds: a worker thread claims jobs from the queue, with one
    active job per ticker, a heartbeat, re-queueing after a restart, and a cap
    of 15 new dossiers a day.

  Done and pushed:
  - Router: quotas are now per model, so a strong-model 429 no longer blocks
    Flash-Lite. The strong chain is 3.8 Flash → 3 Flash, never Flash-Lite.
    Research calls have their own daily caps and token-per-minute limit,
    document text is hashed rather than logged, and cut-off model output is
    treated as an error.
    - gemini-2.5-flash returns 404 "no longer available to new users" on your 
      key, even though it's listed. So the strong chain has 40 calls a day,
      not 60. That still covers 2 strong calls per dossier.
  - Trajectory, cash quality and balance sheet from screener, all computed in 
    code. POLYCAB's free cash flow equals screener's own Free Cash Flow row in
    all 10 years. Banks and NBFCs get NII, ROE, ROA and NPAs instead of EBITDA,
    and cash quality says it isn't meaningful for lenders. A real POLYCAB build
    through the queue publishes those sections as ready.
  - Transcripts: downloaded once, read page by page with PyMuPDF, and only the
    page text is stored in Supabase.
  - Citation checker and extraction: one Flash-Lite call per transcript. On
    POLYCAB's Q2 FY27 transcript, all 53 quotes were found in the page text. One
    item was dropped because its number wasn't printed in its own quote.

  Your action on Render (DEPLOY.md §7):
  - Change the start command to end with --workers 1.
  - Set RESEARCH_WORKER=1, GEMINI_API_KEY, GEMINI_MODEL_CHEAP,
    GEMINI_MODEL_STRONG, GEMINI_MODEL_STRONG_FALLBACKS=gemini-3-flash-preview
    and GROQ_API_KEY.
  - Until then, builds on Render won't run.

  Left to do, in order:
  1. Wire documents and extraction into the build, with job progress ("Reading 4
     of 8 transcripts…").
  2. The numeric Promise Ledger in code: periods, threads, delivered figures,
     revisions, credibility. This is the last item above tonight's cut line.
  3. Build the 4 demo tickers on Render and spot-check quotes.
  4. DECISIONS and PLAN entries.
  5. Tests for documents, the checker and extraction.
  6. Thursday and Friday work as planned:
     - Judge and reduce (the strong calls)
     - Annual report red flags
     - Drivers and Ask
     - Nightly refresh
     - NSE dispatch

❯ limit reset, continue                                                         

  Called ccd_turn, ran 1 shell command (ctrl+o to expand)

⏺ Render is running commit e594134, so PyMuPDF installs there. Next I'll build
  the numeric Promise Ledger in code. · summary

⏺ Write(backend/finn/research/periods.py)  ⎿  Wrote 90 lines to backend/finn/research/periods.py
       1 """Resolve a promise's period in code from what the model read (
         period_type, fy, quarter, …) and the call date.
       2 
       3 The model never computes dates: it reports "FY27" as fy=2027, "n
         ext year" as period_type=next_fy. Code turns that
       4 into a Period using the company's fiscal year-end month (March f
         or most Indian companies). Ambiguous phrases
       5 resolve to None, which the ledger reports as "Can't score (no cl
         ear period)" — never a guess.
       6 """
     … +84 lines (ctrl+o to expand)

  Ran 1 shell command (ctrl+o to expand)

⏺ Periods resolve correctly. Now ledger.py.

⏺ Write(backend/finn/research/ledger.py)
  ⎿  Wrote 499 lines to backend/finn/research/ledger.py
      1 """Step 5 — the Promise Ledger, decided in code (rule 1: the LLM 
        reads, code calculates).
      2 
      3 Input: per-call facts from MAP (guidance + actuals, quotes alread
        y verified). Output: promise threads with verdicts.
      4 
      5 Rules (documented in DECISIONS.md, tested in tests/test_ledger.py
        ):
      6 - Thread = same metric_key, measure, segment, unit family, curren
        cy and scope, and the same resolved period.
     … +493 lines (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/research/ledger.py'; s=open(p).read()…)
  ⎿  30:def money_cr(x: float) -> str:
     31-    return f"₹{indian(x, 0 if abs(x) >= 100 else 1)} Cr"
     32-
     33-
  ⎿  Updated backend/finn/research/ledger.py (+4 -1)
      467          from finn.format import money_cr
      468  
      469          return money_cr(v)
      470 -    return f"{v:,.2f}".rstrip("0").rstrip(".") + (f" {unit.low
          -er()}" if unit and unit not in ("X",) else "x" if unit else ""
          -)                                                             
      470 +    num = f"{v:,.2f}".rstrip("0").rstrip(".")                 
      471 +    if unit == "X":                                           
      472 +        return f"{num}x"                                      
      473 +    return f"{num} {unit.lower()}" if unit else num           
      474  
      475  
      476  _ORDER = {"goalposts_moved": 0, "quietly_dropped": 1, "missed"
           : 2, "kept": 3, "not_yet_due": 4, "cant_score": 5}

⏺ Now the code-only analyst pressure points and drivers, then wiring everything
  into the build.

⏺ Write(backend/finn/research/insights.py)
  ⎿  Wrote 120 lines to backend/finn/research/insights.py
      1 """Code-built sections from extracted facts: what analysts keep a
        sking, suggested drivers, segments, Ask chips.
      2 
      3 Counting and ranking happen here; the strong model (REDUCE) may l
        ater reword pressure points, but which topics
      4 recur, and how often, is decided in code from cited questions.
      5 """
      6 
      7 from __future__ import annotations
      8 
     … +112 lines (ctrl+o to expand)

  Read 1 file (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/research/build.py'; s=open(p).read()…)
  ⎿  502 |     )  # fmt: skip
         |
     … +2 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/build.py (+117 -5)
      11  from datetime import datetime
      12  
      13  from finn.calendar import now_utc
      14 +from finn.llm import LLMUnavailable, PostgresLLMLog, Router    
      15  from finn.models.research import Dossier, SectionMeta
      16  from finn.research import store
      17 +from finn.research.documents import get_document               
      18 +from finn.research.extract import map_transcript               
      19 +from finn.research.ledger import Call                          
      20  from finn.research.jobs import Outcome, Progress
      21  from finn.research.skeleton import empty_dossier
      22  
     ...
       55      progress.step("compute", "done" if disc.status == "ok" els
           e "skipped")
       56      store.publish(conn, d, complete=False)
       57  
       54 -    # 3+. Documents, extraction, ledger, synthesis — later sta
          -ges fill these sections.                                      
       55 -    for key in ("documents", "extract", "ledger", "judge", "re
          -duce"):                                                       
       56 -        progress.step(key, "skipped", "Not available in this b
          -uild yet")                                                    
       57 -    progress.step("publish", "done", message="Published")     
       58 +    # 3. Documents (transcripts; the annual report comes with 
          +the red-flags stage)                                          
       59 +    links = disc.transcripts if disc.status == "ok" else []   
       60 +    progress.count(transcripts_total=len(links))              
       61 +    progress.step("documents", "running")                     
       62 +    docs = []                                                 
       63 +    for link in links:                                        
       64 +        docs.append(get_document(conn, symbol, link))         
       65 +        progress.count(transcripts_read=sum(x.ref.status == "r
          +ead" for x in docs))                                          
       66 +    d.sources = [x.ref for x in docs]                         
       67 +    readable = [x for x in docs if x.ref.status == "read"]    
       68 +    progress.step("documents", "done" if links else "skipped",
          + f"{len(readable)} of {len(links)} transcripts readable")     
       69 +                                                              
       70 +    # 4. Extract (one cheap call per transcript, cached by doc
          +ument hash + prompt version)                                  
       71 +    router = router or Router.default(PostgresLLMLog(conn))   
       72 +    stats0 = router.stats.as_dict()                           
       73 +    progress.step("extract", "running")                       
       74 +    calls: list[Call] = []                                    
       75 +    quota: LLMUnavailable | None = None                       
       76 +    guidance = dropped = 0                                    
       77 +    for doc in readable:                                      
       78 +        if quota is not None:                                 
     … 97 more lines (ctrl+o to expand)

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/research/ledger.py'; s=open(p).read()…)
  ⎿  235 passed, 1 warning in 1.49s
  ⎿  Updated backend/finn/research/ledger.py (+6 -4)
      246                  continue
      247              fig = Figure(label=a["metric"], value=a["value"] *
            f, unit=_unit_enum(unit), period=p,
      248                           basis=None if s.scope not in ("consol
           idated", "standalone") else s.scope, status="verified",
      249 -                         citation=call.cite(a["page"], a["quot
          -e"]), raw=f"{a['value']:g} {a.get('unit_text') or ''}".strip()
          -,                                                             
      250 -                         raw_unit=a.get("unit_text"))  # fmt: 
          -skip                                                          
      249 +                         citation=call.cite(a["page"], a["quot
          +e"]), raw_unit=a.get("unit_text"),                            
      250 +                         raw=f"{a['value']:g} {a.get('unit_tex
          +t') or ''}".strip())  # fmt: skip                             
      251              return fig, call
      252      return None, None
      253  
     ...
      413          elif today <= period.end:
      414              verdict, why = "not_yet_due", f"Due {period.label}
            (ends {period.end:%d %b %Y})"
      415          elif delivered is not None and delivered.value is not 
           None:
      416 -            verdict, how = compare(target.item["kind"], target
          -.low, target.high, delivered.value, target.unit, direction)   
      416 +            kind = target.item["kind"]                        
      417 +            verdict, how = compare(kind, target.low, target.hi
          +gh, delivered.value, target.unit, direction)                  
      418              src = "screener" if dsrc == "screener" else (dcall
           .label if dcall else "a later call")
      419              why = f"Delivered {_fmt(delivered.value, target.un
           it)} vs target {_target_str(target)} ({how}; {src})"
      420              if delivered.citation:
     ...
      498              trend = "up" if delta >= TREND_DELTA_PP else "down
           " if delta <= -TREND_DELTA_PP else "flat"
      499      return Credibility(
      500          shown=n >= MIN_N, score_pct=round(100 * kept / n, 1) i
           f n else None, kept=kept, n=n,
      500 -        numeric_n=sum(p.verdict_by == "code" for p in scored),
          - qualitative_n=sum(p.verdict_by == "model" for p in scored),  
      501 +        numeric_n=sum(p.verdict_by == "code" for p in scored),
      502 +        qualitative_n=sum(p.verdict_by == "model" for p in sco
          +red),                                                         
      503          min_n=MIN_N, trend=trend, recent=recent, earlier=earli
           er, formula=formula,
      504      )  # fmt: skip

⏺ Now a full local POLYCAB build (7 more Flash-Lite calls; the first transcript
  is cached):

  Ran 1 shell command (ctrl+o to expand)

⏺ The full pipeline now runs end to end across transcripts, guidance, analysts
  and segments. Router stats show 14 attempts for 7 successful calls, and
  POLYCAB's guidance is almost all FY30, so nothing is scorable yet; I'm looking
  into the failed attempts first. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ The 503 "high demand" retries were handled by the backoff, so nothing is
  broken, and output stays within the 16K cap. I'm fixing the segment-share
  misuse for FMEG (its "124%" is a growth rate), then running INFY and
  BAJFINANCE. · summary

  Ran 3 shell commands (ctrl+o to expand)

⏺ While those build, I'm writing the ledger, period and checker tests.

⏺ Write(backend/tests/test_ledger.py)
  ⎿  Wrote 221 lines to backend/tests/test_ledger.py
      1 """Promise Ledger rules (decided in code): comparisons per type, 
        units, bases, periods, revisions, timing,
      2 quietly dropped, credibility."""
      3 
      4 from datetime import UTC, date, datetime
      5 
      6 import pytest
      7 
      8 from finn.research.ledger import Call, build_ledger, compare, nor
        malise_unit
     … +213 lines (ctrl+o to expand)

⏺ Background command "Build INFY and BAJFINANCE locally and print scored
promises" completed (exit code 0)

  Ran 1 shell command (ctrl+o to expand)

⏺ All 47 ledger tests pass. The BAJFINANCE build died on a dropped Supabase
  connection ("Operation timed out"), the local network. Checking the INFY
  result and the job states:

  Ran 2 shell commands (ctrl+o to expand)

⏺ Background command "Show INFY build summary and recent job states" completed
(exit code 0)

⏺ INFY came back with 4 kept, 1 missed, 1 goalposts moved, at 66.7% credibility
  over 6 verdicts. I'm fixing two bugs: loose metric keys scored against total
  headcount, and a lost DB connection that failed the BAJFINANCE build instead
  of re-queuing it. · summary

⏺ Bash(cat /private/tmp/claude-501/-Users-<user>-Documents-finn/bb463e84-200
      8-445e-be1c-9b1ec9bda462/tasks/bzrhyz6g6.output | grep -v INFO | tail -8;
      cd /Users/shl…)
  ⎿          ^^^^^^^^^^^^^^^^^^
     {'id': 5, 'symbol': 'BAJFINANCE', 'status': 'failed', 'e': "Operationa
     lError: failed to resolve host 'aws-0-ap-southeast-1.pooler.supabase.c
     … +35 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/jobs.py (+5 -1)
      86      try:
      87          out = build(conn, job["symbol"], progress, job_id=job["
          id"])
      88      except Exception as e:  # never leave a job running; the la
          st good dossier stays published
      89 +        import psycopg                                         
      90 +                                                               
      91          log.exception("research build %s failed", job["symbol"]
          )
      90 -        out = Outcome("failed", error=f"{type(e).__name__}: {st
         -r(e)[:300]}")                                                  
      92 +        transient = isinstance(e, psycopg.OperationalError) and
         + job.get("attempts", 1) < store.MAX_ATTEMPTS                   
      93 +        # a lost database connection is retried (every stage is
         + cached, so the rerun is cheap); a bug is not                  
      94 +        out = Outcome("queued" if transient else "failed", erro
         +r=f"{type(e).__name__}: {str(e)[:300]}")                       
      95      store.finish(conn, job["id"], out.status, out.stats, out.er
          ror, out.resume_after)
      96      return out
      97  
  ⎿  Updated backend/finn/research/ledger.py (+17 -1)
      225          for a in call.facts.get("actuals", []):
      226              if a["metric_key"] != s.item["metric_key"] or a["m
           easure"] != s.item["measure"]:
      227                  continue
      228 -            if s.item["metric_key"] == "other" and norm(a["met
          -ric"]) != norm(s.item["metric"]):                             
      228 +            if not _same_metric(s.item, a):                   
      229                  continue
      230              unit, f = normalise_unit(a.get("unit_text"), a.get
           ("currency", "unspecified"))
      231              if unit != s.unit:
     ...
      252      return None, None
      253  
      254  
      255 +# Keys precise enough that the key alone identifies the metric
          +; for the rest (headcount, capex, capacity, other…)           
      256 +# the names must also share a word — 'fresher hiring' is not '
          +total headcount'.                                             
      257 +TIGHT_KEYS = {"revenue", "revenue_growth", "ebitda", "ebitda_m
          +argin", "ebit_margin", "gross_margin", "pat", "pat_growth",   
      258 +              "eps", "nim", "credit_cost", "gnpa", "nnpa", "au
          +m_growth", "loan_growth", "deposit_growth",                   
      259 +              "cost_to_income", "roe", "roa", "roce", "attriti
          +on", "tax_rate", "dividend_payout"}  # fmt: skip              
      260 +_STOP = {"the", "and", "for", "our", "total", "overall", "of",
          + "in", "rate", "level", "growth", "number", "company"}        
      261 +                                                              
      262 +                                                              
      263 +def _same_metric(g: dict, a: dict) -> bool:                   
      264 +    if g["metric_key"] in TIGHT_KEYS:                         
      265 +        return True                                           
      266 +    gw = {w for w in re.findall(r"[a-z]{3,}", norm(g.get("metr
          +ic", ""))) if w not in _STOP}                                 
      267 +    aw = {w for w in re.findall(r"[a-z]{3,}", norm(a.get("metr
          +ic", ""))) if w not in _STOP}                                 
      268 +    return bool(gw & aw)                                      
      269 +                                                              
      270 +                                                              
      271  def _unit_enum(u: str | None) -> str:
      272      return {"PCT": "PCT", "INR_CR": "INR_CR", "X": "X", "DAYS"
           : "DAYS"}.get(u or "", "COUNT")
      273  
  ⎿  Updated backend/tests/test_ledger.py (+25 -4)
      121  
      122  def test_never_compares_across_currency_basis():
      123      cc = g("revenue_growth", 4, 6, measure="growth", currency=
           "constant_currency")
      124 -    p = only(ledger([call(1, date(2025, 7, 20), [cc]),        
      125 -                     call(2, date(2026, 5, 5), actuals=[a("rev
          -enue_growth", 5, measure="growth", currency="INR")])]))       
      124 +    p = only(                                                 
      125 +        ledger(                                               
      126 +            [                                                 
      127 +                call(1, date(2025, 7, 20), [cc]),             
      128 +                call(2, date(2026, 5, 5), actuals=[a("revenue_
          +growth", 5, measure="growth", currency="INR")]),              
      129 +            ]                                                 
      130 +        )                                                     
      131 +    )                                                         
      132      assert p.verdict in ("cant_score", "quietly_dropped") and 
           p.delivered is None
      133  
      134  
      135  def test_never_compares_standalone_with_consolidated():
      130 -    p = only(ledger([call(1, date(2025, 7, 20), [g(scope="stan
          -dalone")]),                                                   
      131 -                     call(2, date(2026, 5, 5), actuals=[a(scop
          -e="consolidated")])]))                                        
      136 +    p = only(                                                 
      137 +        ledger(                                               
      138 +            [                                                 
      139 +                call(1, date(2025, 7, 20), [g(scope="standalon
          +e")]),                                                        
      140 +                call(2, date(2026, 5, 5), actuals=[a(scope="co
          +nsolidated")]),                                               
      141 +            ]                                                 
      142 +        )                                                     
      143 +    )                                                         
      144      assert p.delivered is None
      145  
      146  
     ...
      231      assert (cr.kept, cr.n, cr.shown, cr.score_pct, cr.numeric_
           n) == (4, 6, True, pytest.approx(66.7), 6)
      232      small = ledger([call(1, date(2025, 7, 20), guid[:3]), call
           (2, date(2026, 5, 5), actuals=acts[:3])])
      233      assert small.credibility.shown is False and small.credibil
           ity.n == 3
      234 +                                                              
      235 +                                                              
      236 +def test_loose_metric_keys_need_matching_names():             
      237 +    hire = g("headcount", 15000, None, unit="employees", kind=
          +"at_least", metric="fresher hiring", measure="level")         
      238 +    total = {**a("headcount", 323578, unit="employees"), "metr
          +ic": "total headcount"}                                       
      239 +    p = only(                                                 
      240 +        ledger([call(1, date(2024, 7, 20), [hire]), call(2, da
          +te(2025, 5, 5), actuals=[total])], date(2025, 11, 1))         
     … 2 more lines (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/research/ledger.py'; s=open(p).read()…)
  ⎿  120 files already formatted
     283 passed, 1 warning in 1.35s
  ⎿  Updated backend/finn/research/ledger.py (+2 -2)
      254  
      255  # Keys precise enough that the key alone identifies the metric
           ; for the rest (headcount, capex, capacity, other…)
      256  # the names must also share a word — 'fresher hiring' is not '
           total headcount'.
      257 -TIGHT_KEYS = {"revenue", "revenue_growth", "ebitda", "ebitda_m
          -argin", "ebit_margin", "gross_margin", "pat", "pat_growth",   
      258 -              "eps", "nim", "credit_cost", "gnpa", "nnpa", "au
          -m_growth", "loan_growth", "deposit_growth",                   
      257 +TIGHT_KEYS = {"revenue", "revenue_growth", "ebitda", "ebitda_m
          +argin", "ebit_margin", "gross_margin", "pat",                 
      258 +              "pat_growth", "eps", "nim", "credit_cost", "gnpa
          +", "nnpa", "aum_growth", "loan_growth", "deposit_growth",     
      259                "cost_to_income", "roe", "roa", "roce", "attriti
           on", "tax_rate", "dividend_payout"}  # fmt: skip
      260  _STOP = {"the", "and", "for", "our", "total", "overall", "of",
            "in", "rate", "level", "growth", "number", "company"}
      261  
  ⎿  Updated backend/tests/test_ledger.py (+2 -1)
      27        scope="consolidated", measure="level"):  # fmt: skip
      28      return {"metric": metric_key, "metric_key": metric_key, "me
          asure": measure, "value": value, "unit_text": unit,
      29              "currency": currency, "scope": scope, "segment": No
          ne, "period_text": "FY26", "period_type": period_type,
      30 -            "fy": fy, "quarter": None, "half": None, "years": N
         -one, "quote": f"{metric_key} was {value}", "page": 2}  # fmt: s
         -kip                                                            
      30 +            "fy": fy, "quarter": None, "half": None, "years": N
         +one, "quote": f"{metric_key} was {value}",                     
      31 +            "page": 2}  # fmt: skip                            
      32  
      33  
      34  def call(i, made, guidance=(), actuals=(), text="nothing releva
          nt here"):

⏺ 283 pass. Adding checker and extraction-validation tests:

⏺ Write(backend/tests/test_research_checker.py)
  ⎿  Wrote 72 lines to backend/tests/test_research_checker.py
       1 """Citation checker + MAP validation: quotes must be in the sour
         ce text; numbers must be in their own quote."""
       2 
       3 from finn.research.checker import Checker, number_in_quote, stri
         p_boilerplate
       4 from finn.research.extract import validate
       5 
       6 PAGES = [
       7     "Polycab India Limited\nWelcome to the call.\nModerator: ple
         ase go ahead.",
     … +65 lines (ctrl+o to expand)

  Ran 2 shell commands (ctrl+o to expand)

⏺ The straddle check wrongly credited page 2 for a quote entirely on page 3, and
  re-anchoring's Jaccard overlap was penalising long source sentences. I'm
  switching to overlap measured against the quote's own words, plus the required
  number match. · summary
⏺ Bash(python3 - <<'EOF'
      p='finn/research/checker.py'; s=open(p).read()…)
  ⎿  289 passed, 1 warning in 1.53s
  ⎿  Updated backend/finn/research/checker.py (+7 -4)
      63      def _on(self, i: int, q: str) -> bool:
      64          if not (0 <= i < len(self.pages)):
      65              return False
      66 -        return q in self.pages[i] or quote_in_text(q, self.page
         -s[i]) or (                                                     
      67 -            i + 1 < len(self.pages) and q in (self.pages[i] + "
         - " + self.pages[i + 1]))  # fmt: skip                          
      66 +        if q in self.pages[i] or quote_in_text(q, self.pages[i]
         +):                                                             
      67 +            return True                                        
      68 +        # a quote straddling a page break counts for the page i
         +t starts on — not one that is wholly on the next               
      69 +        nxt = self.pages[i + 1] if i + 1 < len(self.pages) else
         + ""                                                            
      70 +        return bool(nxt) and q not in nxt and q in (self.pages[
         +i] + " " + nxt)                                                
      71  
      72      def _candidates(self, q: str, claimed: int | None) -> list[
          int]:
      73          order: list[int] = []
     ...
      122                  words = set(_WORD.findall(ns))
      123                  if not words:
      124                      continue
      122 -                score = len(want & words) / len(want | words) 
      125 +                score = len(want & words) / len(want)  # share
          + of the quote's words found (the number must match)           
      126                  if best is None or score > best[0]:
      127                      best = (score, i, " ".join(sent.split()))
      125 -        if best and best[0] >= 0.35:                          
      128 +        if best and best[0] >= 0.3:                           
      129              return Located(best[1] + 1, best[2], "reanchored")
      130          return None
      131  

⏺ Stored extractions were validated with the old page logic, so some page
  numbers may be off by one. I'm adding a validator version so that a change
  re-validates them from the cached model responses in llm_calls, at no model
  cost. · summary

⏺ Bash(python3 - <<'EOF'
      p='finn/research/extract.py'; s=open(p).read()…)
  ⎿  29:VALIDATOR_VERSION = 2
     250:    if hit and (hit["stats"] or {}).get("validator") == VALIDATOR_
     VERSION:
     … +3 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/extract.py (+5 -2)
      24  EXTRACTOR = "map_transcript"
      25  PROMPT_VERSION = "v1"
      26  PURPOSE = f"research.map_transcript.{PROMPT_VERSION}"
      27 +# Bump when validation/checking changes: stored extractions are
         + re-validated from the cached model response                   
      28 +# (llm_calls), so the fix applies without another model call.  
      29 +VALIDATOR_VERSION = 2                                          
      30  MAX_OUTPUT = 16_000
      31  
      32  SYSTEM = """You extract facts from ONE earnings-call transcript
           of an Indian listed company, for an audit trail.
     ...
      247  def map_transcript(conn, router, sha256: str, pages: list[str]
           , tags: dict | None = None) -> tuple[dict | None, dict]:
      248      """Facts for one transcript: cached extraction, else one c
           heap call. Raises LLMUnavailable on quota."""
      249      hit = store.get_extraction(conn, sha256, EXTRACTOR, PROMPT
           _VERSION)
      247 -    if hit:                                                   
      250 +    if hit and (hit["stats"] or {}).get("validator") == VALIDA
          +TOR_VERSION:                                                  
      251          return hit["payload"], {**(hit["stats"] or {}), "cache
           d": True, "model": hit["model"]}
      252      req = LLMRequest(purpose=PURPOSE, system=SYSTEM, prompt=PR
           OMPT, schema=SCHEMA, document_text=document_text(pages),
      253                       max_output_tokens=MAX_OUTPUT, timeout_s=2
           40, tags=tags or {})  # fmt: skip
      254      res = router.run("cheap", req)
      255      facts, stats = validate(res.data, pages)
      253 -    stats.update(model=res.model, tokens_in=res.tokens_in, tok
          -ens_out=res.tokens_out,                                       
      256 +    stats.update(validator=VALIDATOR_VERSION, model=res.model,
          + tokens_in=res.tokens_in, tokens_out=res.tokens_out,          
      257                   raw_counts={k: len(res.data.get(k) or []) for
            k in SHAPES})  # fmt: skip
      258      store.save_extraction(conn, sha256, EXTRACTOR, PROMPT_VERS
           ION, res.model, facts, stats)
      259      return facts, stats

  Called ccd_turn, ran 4 shell commands (ctrl+o to expand)

⏺ The Render worker isn't running because RESEARCH_WORKER and the Gemini keys
  aren't set there, so the PERSISTENT job stays queued; I'm writing up the
  DECISIONS and PLAN entries meanwhile. · summary

⏺ Bash(cat >> docs/DECISIONS.md <<'EOF'…)
  ⎿  289240a DECISIONS and PLAN: Phase 3 research engine, LLM budget, Promi
     se Ledger rules
  ⎿  Updated docs/DECISIONS.md (+94 -0)
      296    - Appointments, CFO changes and other management changes are
            held.
      297    - The broader "critical" list is unchanged for the feedback 
           floor and the budget exemption: results still go out on their 
           own and don't count against the 5-a-day budget.
      298  - **Check:** none of the 49 stored management events match as 
           an exit. The three titles mentioning a CEO/MD are appointments
            or an extended charge, so there are no false positives.
      299 +                                                              
      300 +## 2026-11-11 · Research (Phase 3): where it runs, what it cos
          +ts, how it degrades                                           
      301 +- **Plan approved by the product owner on 11 Nov.** The full p
          +lan is summarised here; details live in the code docstrings.  
      302 +- **Where it runs:**                                          
      303 +  - Builds run on a worker thread inside the Render API (`RESE
          +ARCH_WORKER=1`, `uvicorn --workers 1`).                       
      304 +  - The worker claims from `research_jobs` in Supabase with `F
          +OR UPDATE SKIP LOCKED`. A partial unique index allows one acti
          +ve job per ticker; other tickers queue.                       
      305 +  - A 30 s heartbeat runs on its own thread. A job with no hea
          +rtbeat for 3 minutes is re-queued, up to 3 attempts. A lost da
          +tabase connection re-queues the job instead of failing it.    
      306 +  - The nightly GitHub Actions run will claim from the same qu
          +eue.                                                          
      307 +  - Render's disk is wiped on restart, so every cache lives in
          + Postgres:                                                    
      308 +    - `research_documents`: URL → sha256 and status.          
      309 +    - `research_doc_text`: gzipped page text keyed by sha256. 
          +The PDF itself is never kept.                                 
      310 +    - `research_extractions`: validated facts per (sha256, ext
          +ractor, prompt version).                                      
      311 +    - `dossiers`: the last good dossier.                      
      312 +  - PDFs are streamed to a temp file and read page by page.   
      313 +- **Screener is cited in research:** its standardised tables a
          +re a primary source for the dossier (spec §8). Values read fro
          +m a row are `verified` and carry a `screener:<section>/<row>/<
          +column>` locator.                                             
      314 +  - Computed figures list their inputs.                       
      315 +  - FCF = CFO + fixed assets purchased + fixed assets sold, fr
          +om the investing-activity schedule (`/api/company/<id>/schedul
          +es/`, which robots.txt allows). This equals screener's own Fre
          +e Cash Flow row in all 10 POLYCAB years.                      
      316 +- **PyMuPDF (AGPL-3.0)** extracts text. That is acceptable bec
          +ause this repo is public; pypdfium2 would be the drop-in repla
          +cement.                                                       
      317 +- **Alternatives:**                                           
      318 +  - Builds as GitHub Actions dispatches: rejected. Dispatches 
          +are slow to start, and a public build button would spend Actio
          +ns runs.                                                      
      319 +  - Supabase Storage for text: rejected, because it means anot
          +her key and API. Postgres has room: about 0.6 MB per ticker, i
          +n a 21 MB database.                                           
      320 +                                                              
      321 +## 2026-11-11 · LLM budget for research: per-model quotas, str
          +ong fallback chain, Groq only for Ask                         
      322 +- **Free tier (product owner's AI Studio dashboard):**        
      323 +  - Flash-Lite: 15 RPM / 250K TPM / 500 RPD. The push side pea
          +ks at 251 a day.                                              
      324 +  - gemini-3.8-flash, Gemini 3 Flash and Gemini 2.5 Flash: 5 R
          +PM / 20 RPD each.                                             
      325 +- **Router changes:**                                         
      326 +  - Limits, daily counts and exhaustion are per model. A stron
          +g-model 429 no longer disables Flash-Lite.                    
      327 +  - The strong tier is a chain: `GEMINI_MODEL_STRONG` → `GEMIN
          +I_MODEL_STRONG_FALLBACKS`.                                    
      328 +    - `gemini-2.5-flash` returns 404 "no longer available to n
          +ew users" on this key, so the default chain is 3.8 Flash → `ge
          +mini-3-flash-preview`, 40 strong calls a day.                 
      329 +    - The chain never uses Flash-Lite (product owner) and neve
          +r Groq. Each verdict records its model.                       
      330 +  - Research purposes (`research.*`) have their own daily caps
          + (`RESEARCH_CHEAP_RPD` 220, `RESEARCH_ASK_RPD` 40, `RESEARCH_S
          +TRONG_RPD` 60) and 150K of Flash-Lite's TPM, so the push side 
          +keeps its share.                                              
      331 +  - Daily counts include successful calls only.               
      332 +- **Per dossier:**                                            
      333 +                                                              
      334 +  | Case | Cheap calls | Strong calls | Measured |            
      335 +  |---|---|---|---|                                           
     … 57 more lines (ctrl+o to expand)
  ⎿  Updated docs/PLAN.md (+20 -0)
      58  - [ ] `TAVILY_API_KEY` when the product owner signs up (cards a
          lready work without it).
      59  - [ ] Older results XBRL (≤ Dec-2024, `corporates-financial-res
          ults`) — only needed for year-ago comparisons before Mar-2025.
      60  
      61 +## Phase 3 — research engine + Promise Ledger (11–13 Nov 2026) 
      62 +                                                               
      63 +Plan approved 11 Nov; rules and budget in DECISIONS.md (three P
         +hase 3 entries).                                               
      64 +                                                               
      65 +- [x] Contract (Dossier with fixed sections + status/reason, Mg
         +mtPromise threads, DossierJob, DossierResponse, AskAnswer), mig
         +ration 0004, research API + proxy allow-list, background worker
         + — `bfffd9e`; live on Render                                   
      66 +- [x] Router: per-model quotas, strong chain (3.8 Flash → 3 Fla
         +sh), TPM, research lane caps, hashed document text — `248aea6` 
      67 +- [x] Screener discovery (all tables, transcripts, annual repor
         +t, capex schedule) + computed trajectory / cash / balance sheet
         + incl. lenders — `12a189a`                                     
      68 +- [x] Transcripts (PyMuPDF, text in Supabase), citation checker
         +, MAP extraction — `83eb047`                                   
      69 +- [x] Numeric Promise Ledger + analysts + drivers in builds — `
         +85c0cd4` (INFY local: 4 kept, 1 missed, 1 moved)               
      70 +- [ ] **Render env (product owner):** DEPLOY.md §7 — `--workers
         + 1`, `RESEARCH_WORKER=1`, Gemini keys/models, `GEMINI_MODEL_STR
         +ONG_FALLBACKS`                                                 
      71 +- [ ] Build the 4 demo tickers on the deployed API; spot-check 
         +5 verdicts' quotes in the PDFs                                 
      72 +- [ ] JUDGE (strong #1): qualitative promises + paraphrased cro
         +ss-call links, citing both calls                               
      73 +- [ ] Annual report sections (headings in code) → red flags (au
         +ditor opinion, contingent liabilities growth, related parties) 
      74 +- [ ] REDUCE (strong #2): snapshot text, trajectory line, press
         +ure-point wording, bull/bear with `{f:ID}` placeholders rendere
         +d in code                                                      
      75 +- [ ] Ask: BM25 over the ticker's pages + facts → Flash-Lite (G
         +roq fallback) → cited answer or "Not found in sources"         
      76 +- [ ] Nightly refresh on Actions (code-only recompute; rebuild 
         +only on a new document; first-time builds only for the 4 demo t
         +ickers); DB size guard                                         
      77 +- [ ] On-demand NSE dispatch (section above) → `exchange_data` 
      78 +- [ ] Two tickers outside the demo set (one bank); cost report;
         + README                                                        
      79 +- [ ] Frontend fixtures: validated INFY and BAJFINANCE dossiers
         + in `web/public/fixtures/`                                     
      80 +                                                               
      81  ## Phase 5
      82  
      83  - [ ] **Held-out classification eval (~20 filings, never used f
          or tuning).** The current 60-filing set is a *dev* set: the rul
          es were written from the same Aug–Nov 2026 filings, so its scor
          e is optimistic.

⏺ Pushed the decisions and backlog. While Render waits on its settings, I'm
  rebuilding BAJFINANCE locally to get fixtures for INFY, BAJFINANCE and
  POLYCAB. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ While that runs, I'm checking INFY's scored verdicts the way you will: each
  cited quote must appear on the cited page of the stored transcript text.

  Ran 1 shell command (ctrl+o to expand)

⏺ All 12 quotes check out on their pages, but two ledger problems turned up: the
  FY27 revision reason cites the first cut rather than the full path to today's
  1–2%, and INFY's FY26 growth guidance got split into two threads. I'm
  debugging that split next. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ The bucket logic was treating "constant currency + unspecified scope" as its
  own merge target, so two candidates matched and nothing merged. I'm
  restricting merge targets to fully specified bases and changing the revision
  reason to name the latest cut and the original target. · summary

⏺ Bash(python3 - <<'EOF'
      p='finn/research/ledger.py'; s=open(p).read()…)
  ⎿  E501 Line too long (122 > 120)
        --> finn/research/ledger.py:420:121
         |
     … +13 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/ledger.py (+9 -8)
      153          else:
      154              fams[(*_family_key(s), s.period.end if s.period el
           se None)].append(s)
      155      for fk, group_ in fams.items():
      156 -        specified = {(s.currency, s.scope) for s in group_ if 
          -s.currency != "unspecified" or s.scope != "unspecified"}      
      156 +        # merge targets: fully specified bases; a partly/un-sp
          +ecified statement joins the single compatible one             
      157 +        full = {(s.currency, s.scope) for s in group_ if "unsp
          +ecified" not in (s.currency, s.scope)}                        
      158          buckets: dict[tuple, list[Stmt]] = defaultdict(list)
      159          for s in group_:
      160              b = (s.currency, s.scope)
      160 -            if b == ("unspecified", "unspecified") and len(spe
          -cified) == 1:                                                 
      161 -                b = next(iter(specified))                     
      162 -            elif "unspecified" in b and len(specified) >= 1:  
      163 -                match = [x for x in specified if (b[0] in ("un
          -specified", x[0])) and (b[1] in ("unspecified", x[1]))]       
      161 +            if "unspecified" in b:                            
      162 +                match = [x for x in full if b[0] in ("unspecif
          +ied", x[0]) and b[1] in ("unspecified", x[1])]                
      163                  if len(match) == 1:
      164                      b = match[0]
      165              buckets[b].append(s)
     ...
      318          else:
      319              up = m1 > m0
      320              kind = "raised" if up == (direction == "higher") e
           lse "lowered"
      322 -        if rank[kind] > rank[best]:                           
      321 +        if rank[kind] >= rank[best] and kind != "none":  # the
          + latest change of the most significant kind                   
      322              best, by = kind, cur
      323      return best, by
      324  
     ...
      414              settled[pid] = ls.made_on
      415          elif rev == "lowered" and rev_by is not None:
      416              verdict = "goalposts_moved"
      418 -            why = f"Target changed to {_target_str(rev_by)} in
          - the {rev_by.call.label} (was {_target_str(s0)})"             
      419 -            cites.append(rev_by.call.cite(rev_by.item["page"],
          - rev_by.item["quote"]))                                       
      417 +            why = (f"Target cut to {_target_str(rev_by)} in th
          +e {rev_by.call.label}; first given as "                       
      418 +                   f"{_target_str(s0)} in the {s0.call.label}"
          +)  # fmt: skip                                                
      419 +            cites = [s0.call.cite(s0.item["page"], s0.item["qu
          +ote"]), rev_by.call.cite(rev_by.item["page"],                 
      420 +                                                              
          +                         rev_by.item["quote"])]  # fmt: skip  
      421              settled[pid] = rev_by.made_on
      422          elif qual:
      423              verdict = "not_yet_due" if period and today < resu
           lts_due(period) else "cant_score"
  ⎿  Updated backend/tests/test_ledger.py (+18 -0)
      241          ledger([call(1, date(2024, 7, 20), [hire]), call(2, da
           te(2025, 5, 5), actuals=[total])], date(2025, 11, 1))
      242      )
      243      assert p.delivered is None
      244 +                                                              
      245 +                                                              
      246 +def test_partly_specified_basis_merges_into_the_fully_specifie
          +d_thread():                                                   
      247 +    cc = {"measure": "growth", "currency": "constant_currency"
          +}                                                             
      248 +    calls = [call(1, date(2025, 4, 20), [g("revenue_growth", 0
          +, 3, **cc)]),                                                 
      249 +             call(2, date(2025, 7, 20), [g("revenue_growth", 1
          +, 3, scope="unspecified", **cc)]),                            
      250 +             call(3, date(2025, 10, 20), [g("revenue_growth", 
          +2, 3, **cc)])]  # fmt: skip                                   
      251 +    p = only(ledger(calls))                                   
      252 +    assert len(p.statements) == 3 and p.revision == "raised"  
      253 +                                                              
      254 +                                                              
      255 +def test_lowered_reason_names_latest_cut_and_original():      
      256 +    calls = [call(1, date(2025, 4, 20), [g(lo=20, hi=22)]), ca
          +ll(2, date(2025, 7, 20), [g(lo=19, hi=21)]),                  
      257 +             call(3, date(2025, 10, 20), [g(lo=17, hi=18)])]  
          +# fmt: skip                                                   
      258 +    p = only(ledger(calls))                                   
      259 +    assert (                                                  
      260 +        "17–18%" in p.verdict_reason.text and "Q3 call" in p.v
          +erdict_reason.text and "20–22%" in p.verdict_reason.text      
      261 +    )                                                         

⏺ Bash(python3 - <<'EOF'
      p='finn/research/ledger.py'; s=open(p).read()…)
  ⎿  291 passed, 1 warning in 1.29s
  ⎿  Updated backend/finn/research/ledger.py (+2 -2)
      416              verdict = "goalposts_moved"
      417              why = (f"Target cut to {_target_str(rev_by)} in th
           e {rev_by.call.label}; first given as "
      418                     f"{_target_str(s0)} in the {s0.call.label}"
           )  # fmt: skip
      419 -            cites = [s0.call.cite(s0.item["page"], s0.item["qu
          -ote"]), rev_by.call.cite(rev_by.item["page"],                 
      420 -                                                              
          -                         rev_by.item["quote"])]  # fmt: skip  
      419 +            first = s0.call.cite(s0.item["page"], s0.item["quo
          +te"])                                                         
      420 +            cites = [first, rev_by.call.cite(rev_by.item["page
          +"], rev_by.item["quote"])]                                    
      421              settled[pid] = rev_by.made_on
      422          elif qual:
      423              verdict = "not_yet_due" if period and today < resu
           lts_due(period) else "cant_score"

  Ran 1 shell command (ctrl+o to expand)

⏺ While BAJFINANCE builds, a jobs/research.py CLI: enqueue, drain (for the
  Actions worker and nightly run later) and export (the frontend fixtures).

⏺ Write(backend/jobs/research.py)
  ⎿  Wrote 65 lines to backend/jobs/research.py
      1 """Research jobs from the command line (GitHub Actions / local).
      2 
      3 python -m jobs.research enqueue --symbols INFY,POLYCAB [--reason 
        prewarm]   # add builds to the queue
      4 python -m jobs.research drain [--max 20] [--minutes 40]          
                   # run queued builds here (a worker)
      5 python -m jobs.research export --symbols INFY,BAJFINANCE --out ..
        /web/public/fixtures   # frontend fixtures
      6 
      7 Builds normally run on Render's worker thread; `drain` lets the n
     … +59 lines (~3 KB) (ctrl+o to expand)

  Called ccd_turn, ran 1 shell command (ctrl+o to expand)

⏺ The numeric Promise Ledger works end to end, and the code is pushed (40f6698).
  The step before you can check it on the deployed API is the Render settings
  from DEPLOY.md §7.

  Built since the last update:
  - Builds now run the whole path: screener tables, then the last 8 transcripts,
    then one Flash-Lite call per transcript, then quote checks, then the
    ledger, all published with step-by-step progress.
  - Promise Ledger, decided in code: each promise gets kept, missed, goalposts
    moved, raised, narrowed, not yet due, can't score or quietly dropped, plus a
    credibility score. Analyst pressure points, suggested drivers and Ask
    question chips come from the same extracted facts.
  - INFY, built locally: 4 kept, 1 missed, 1 goalposts moved, credibility 66.7%
    (n=6). The goalposts-moved verdict is FY27 growth guidance cut from 1.5–3.5%
    to 1–2% constant currency. I checked all 12 quotes behind those verdicts,
    and each one is on the page it cites. Two of the verdicts will change when
    INFY is rebuilt with today's fixes:
    - "Fresher hiring ≥ 15,000" was wrongly scored against total headcount
      (323,578). It is fixed and will become can't score.
    - The two FY26 growth threads will merge into one.
  - POLYCAB: almost all of its guidance targets FY30 or "the medium term", so
    nothing can be scored yet, and the dossier says so for each promise.

  Fixed along the way:
  - Promises split into separate threads when one call left the basis unstated;
    they now merge.
  - A quote straddling two pages could be credited to the wrong page.
    Extractions already stored get re-checked from the cached model output, with
    no new model call.
  - A dropped database connection now re-queues the build instead of failing it.

  There are 291 tests, all passing. DECISIONS.md has the budget, the ledger
  rules and your four answers, and PLAN.md has the Phase 3 checklist.

  Waiting on you: the PERSISTENT build I started on Render is still queued, so
  the worker isn't running there yet. It needs these settings from DEPLOY.md §7:
  - Start command: append --workers 1.
  - Environment: RESEARCH_WORKER=1, GEMINI_API_KEY, GEMINI_MODEL_CHEAP,
    GEMINI_MODEL_STRONG, GEMINI_MODEL_STRONG_FALLBACKS=gemini-3-flash-preview
    and GROQ_API_KEY.

  Still to do:
  - Build the 4 demo tickers on Render and spot-check them.
  - Export INFY and BAJFINANCE as frontend fixtures (jobs/research.py export is
    written but not yet committed).
  - Thursday: the strong-model judge and summary steps, annual-report red flags,
    Ask, and the nightly refresh.

⏺ Background command "Rebuild BAJFINANCE locally ahead of the queued Render job"
completed (exit code 0)

  Searched for 1 pattern (ctrl+o to expand)

⏺ BAJFINANCE scored 1 kept, 2 missed and 2 moved, but two of those verdicts are
  wrong: a customer count of 120 million was read as ₹11.9 Cr, and the FY26
  credit-cost guidance being restated for FY27 is normal, so "delayed" should
  only apply to deadline-style targets. · summary

  Searched for 1 pattern (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/research/ledger.py'; s=open(p).read()…)
  ⎿  -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.htm
     l
     293 passed, 1 warning in 1.42s
  ⎿  Updated backend/finn/research/ledger.py (+30 -4)
       99  _USD = [(r"\bbillion|\bbn\b", 1000.0), (r"\bmillion|\bmn\b|\bm
           ln\b", 1.0)]
      100  
      101  
      102 -def normalise_unit(unit_text: str | None, currency: str) -> tu
          -ple[str | None, float]:                                       
      103 -    """(unit family, multiplier to that family). bps → percent
          -age points; INR money → ₹ crore; USD → USD million."""        
      102 +# Metrics whose 'million'/'crore' is money. For anything else 
          +(customers, units, tonnes) a 'million' is a count.            
      103 +MONEY_KEYS = {"revenue", "ebitda", "pat", "eps", "capex", "ord
          +er_book", "order_inflow", "deal_wins", "debt", "net_debt",    
      104 +              "cost_savings", "dividend_payout", "other"}  # f
          +mt: skip                                                      
      105 +_COUNT = [(r"\bbillion|\bbn\b", 1e9), (r"\bmillion|\bmn\b|\bml
          +n\b", 1e6), (r"\bcrore|\bcr\b", 1e7),                         
      106 +          (r"\blakh|\blac", 1e5), (r"\bthousand|\bk\b", 1e3)] 
          + # fmt: skip                                                  
      107 +                                                              
      108 +                                                              
      109 +def normalise_unit(unit_text: str | None, currency: str, metri
          +c_key: str = "other") -> tuple[str | None, float]:            
      110 +    """(unit family, multiplier to that family). bps → percent
          +age points; INR money → ₹ crore; USD → USD million;           
      111 +    a count metric's 'million'/'lakh' → COUNT (never money).""
          +"                                                             
      112      u = (unit_text or "").strip().lower()
      113      if not u:
      114          return None, 1.0
      115 +    money = currency in ("INR", "USD") or "₹" in u or "rs" in 
          +u.split() or "inr" in u or (                                  
      116 +        currency != "not_money" and metric_key in MONEY_KEYS) 
          + # fmt: skip                                                  
      117      if "bps" in u or "basis point" in u:
      118          return "PCT", 0.01
      119      if "%" in u or "percent" in u or "per cent" in u:
      120          return "PCT", 1.0
      121 +    if not money and not re.search(r"usd|\$|dollar", u):      
      122 +        for rx, f in _COUNT:                                  
      123 +            if re.search(rx, u):                              
      124 +                return "COUNT", f                             
      125      if currency == "USD" or "usd" in u or "$" in u or "dollar"
            in u:
      126          for rx, f in _USD:
      127              if re.search(rx, u):
     ...
      138  
      139  
      140  def _stmt(call: Call, it: dict, ye_month: int) -> Stmt:
      127 -    unit, f = normalise_unit(it.get("unit_text"), it.get("curr
          -ency", "unspecified"))                                        
      141 +    unit, f = normalise_unit(it.get("unit_text"), it.get("curr
          +ency", "unspecified"), it.get("metric_key", "other"))         
      142      lo, hi = it.get("target_low"), it.get("target_high")
      143      period = resolve(it.get("period_type", "unspecified"), it.
           get("fy"), it.get("quarter"), it.get("half"),
      144                       it.get("years"), call.made_on, ye_month) 
            # fmt: skip
     ...
      240                  continue
     … 37 more lines (ctrl+o to expand)
  ⎿  Updated backend/tests/test_ledger.py (+16 -3)
      192      assert only(ledger(calls)).revision == "narrowed"
      193  
      194  
      195 -def test_delayed_target_is_goalposts_moved():                 
      196 -    calls = [call(1, date(2025, 7, 20), [g(lo=20, hi=20, kind=
          -"point", fy=2026)]),                                          
      197 -             call(2, date(2025, 10, 20), [g(lo=20, hi=20, kind
          -="point", fy=2027, period_text="FY27")])]  # fmt: skip        
      195 +def test_delayed_deadline_is_goalposts_moved():               
      196 +    by = {"period_type": "by_fy", "kind": "point"}            
      197 +    calls = [call(1, date(2025, 7, 20), [g(lo=20, hi=20, fy=20
          +26, **by)]),                                                  
      198 +             call(2, date(2025, 10, 20), [g(lo=20, hi=20, fy=2
          +027, period_text="by FY27", **by)])]  # fmt: skip             
      199      led = ledger(calls)
      200      fy26 = next(p for p in led.promises if p.period.label == "
           FY26")
      201      assert fy26.revision == "delayed" and fy26.verdict == "goa
           lposts_moved"
      202  
      203  
      204 +def test_same_level_restated_for_next_year_is_not_a_delay():  
      205 +    calls = [call(1, date(2025, 7, 20), [g("credit_cost", 1.85
          +, 1.95, fy=2026)]),                                           
      206 +             call(2, date(2025, 10, 20), [g("credit_cost", 1.8
          +5, 1.95, fy=2027, period_text="FY27")])]  # fmt: skip         
      207 +    assert all(p.revision != "delayed" for p in ledger(calls).
          +promises)                                                     
      208 +                                                              
      209 +                                                              
      210 +def test_count_millions_are_not_money():                      
      211 +    assert normalise_unit("million", "unspecified", "customer_
          +growth") == ("COUNT", 1e6)                                    
      212 +    assert normalise_unit("million", "unspecified", "revenue")
          + == ("INR_CR", 0.1)                                           
      213 +    assert normalise_unit("million", "not_money", "other") == 
          +("COUNT", 1e6)                                                
      214 +                                                              
      215 +                                                              
      216  # --- quietly dropped ----------------------------------------
           --------------------------------------------------------
      217  
      218  

⏺ 293 pass. Rebuilding the three local dossiers with the fixed rules. Model
  output is cached, so this costs no model calls:

  Ran 1 shell command (ctrl+o to expand)

⏺ The rules now behave correctly, with the bogus credit-cost delay and the
  fresher-hiring mis-score gone. One display issue remains: 119.3 million
  customers shows as 11.93 crore against a "≥ 120 million" target, so I'm
  switching the count to the target's scale. · summary

⏺ Bash(python3 - <<'EOF'
      p='finn/research/ledger.py'; s=open(p).read()…)
  ⎿  465:            why = f"Delivered {_fmt(delivered.value, target.unit,
     target.item.get('unit_text'))} vs target {_target_str(target)} ({how};
      {src})"
     … +21 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/ledger.py (+10 -5)
      285      return {"PCT": "PCT", "INR_CR": "INR_CR", "X": "X", "DAYS"
           : "DAYS"}.get(u or "", "COUNT")
      286  
      287  
      288 -def _fmt_count(v: float) -> str:                              
      289 -    for div, name in ((1e7, "crore"), (1e6, "million"), (1e5, 
          -"lakh")):                                                     
      288 +def _fmt_count(v: float, like: str | None = None) -> str:     
      289 +    """A count in the scale the target was given in ('million'
          + target → '119.3 million')."""                                
      290 +    scales = ((1e9, "billion"), (1e7, "crore"), (1e6, "million
          +"), (1e5, "lakh"))                                            
      291 +    for div, name in scales:                                  
      292 +        if like and name in like.lower():                     
      293 +            return f"{v / div:,.2f}".rstrip("0").rstrip(".") +
          + f" {name}"                                                   
      294 +    for div, name in scales:                                  
      295          if abs(v) >= div:
      296              return f"{v / div:,.2f}".rstrip("0").rstrip(".") +
            f" {name}"
      297      return f"{v:,.0f}"
     ...
      462              kind = target.item["kind"]
      463              verdict, how = compare(kind, target.low, target.hi
           gh, delivered.value, target.unit, direction)
      464              src = "screener" if dsrc == "screener" else (dcall
           .label if dcall else "a later call")
      460 -            why = f"Delivered {_fmt(delivered.value, target.un
          -it)} vs target {_target_str(target)} ({how}; {src})"          
      465 +            why = f"Delivered {_fmt(delivered.value, target.un
          +it, target.item.get('unit_text'))} vs target {_target_str(targ
          +et)} ({how}; {src})"                                          
      466              if delivered.citation:
      467                  cites.append(delivered.citation)
      468              settled[pid] = dcall.made_on if dcall else results
           _due(period)
     ...
      507      return c if c in ("INR", "USD", "constant_currency", "unsp
           ecified", "not_money") else "unspecified"
      508  
      509  
      505 -def _fmt(v: float, unit: str | None) -> str:                  
      510 +def _fmt(v: float, unit: str | None, like: str | None = None) 
          +-> str:                                                       
      511      if unit == "PCT":
      512          return f"{v:.1f}%"
      513      if unit == "INR_CR":
     ...
      518      if unit == "X":
      519          return f"{num}x"
      520      if unit == "COUNT":
      516 -        return _fmt_count(v)                                  
      521 +        return _fmt_count(v, like)                            
      522      return f"{num} {unit.lower()}" if unit else num
      523  
      524  
  ⎿  … 3 more files changed

⏺ Bash(python3 - <<'EOF'
      p='finn/research/ledger.py'; s=open(p).read()…)
  ⎿  293 passed, 1 warning in 1.50s
        missed           raised   customer franchise ≥ 120 million (FY26)
                         | Delivered 119.3 million vs target ≥ 120 million
     … +10 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/ledger.py (+2 -1)
      462              kind = target.item["kind"]
      463              verdict, how = compare(kind, target.low, target.hi
           gh, delivered.value, target.unit, direction)
      464              src = "screener" if dsrc == "screener" else (dcall
           .label if dcall else "a later call")
      465 -            why = f"Delivered {_fmt(delivered.value, target.un
          -it, target.item.get('unit_text'))} vs target {_target_str(targ
          -et)} ({how}; {src})"                                          
      465 +            got = _fmt(delivered.value, target.unit, target.it
          +em.get("unit_text"))                                          
      466 +            why = f"Delivered {got} vs target {_target_str(tar
          +get)} ({how}; {src})"                                         
      467              if delivered.citation:
      468                  cites.append(delivered.citation)
      469              settled[pid] = dcall.made_on if dcall else results
           _due(period)
  ⎿  … 1 more file changed
⏺ Customer franchise now reads "Delivered 119.3 million vs target ≥ 120
  million". All three fixtures validate against the contract. Committing:

⏺ Bash(cd ~/Documents/finn && python3 - <<'EOF'
      p='docs/PLAN.md'; s=open(p).read()…)
  ⎿  29cf2f2 Ledger: count units stay counts, delays only for deadline targ
     ets; research CLI; frontend fixtures
     render job 6: queued | Queued
  ⎿  Updated docs/PLAN.md (+1 -1)
      76  - [ ] Nightly refresh on Actions (code-only recompute; rebuild 
          only on a new document; first-time builds only for the 4 demo t
          ickers); DB size guard
      77  - [ ] On-demand NSE dispatch (section above) → `exchange_data`
      78  - [ ] Two tickers outside the demo set (one bank); cost report;
           README
      79 -- [ ] Frontend fixtures: validated INFY and BAJFINANCE dossiers
         - in `web/public/fixtures/`                                     
      79 +- [x] Frontend fixtures: validated INFY, BAJFINANCE, POLYCAB do
         +ssiers in `web/public/fixtures/` (`python -m jobs.research expo
         +rt`; built locally against Supabase — rebuild on Render once §7
         + is set)                                                       
      80  
      81  ## Phase 5
      82  

  Called ccd_turn (ctrl+o to expand)

⏺ BAJFINANCE built locally and exposed two wrong verdicts, which are now fixed.
  Fixtures for three demo tickers are committed for your frontend work tomorrow
  (29cf2f2).

  The two fixes:
  - Counts treated as money: "customer franchise ≥ 120 million" was converted
    into ₹ crore. Metrics that aren't money now keep "million"/"lakh" as counts
    and show them in the target's own scale. It now reads "Delivered 119.3
    million vs target ≥ 120 million (below)".
  - False "delays": credit cost guided at 1.85–1.95% for FY26 and again for FY27
    was flagged as goalposts moved. Restating a level for the next year is
    normal, so only deadline-style targets ("by FY28") can count as delayed now.

  Ledgers after the fixes (built locally against Supabase; credibility shows
  only from 5 scored promises):

  ┌────────────┬──────┬────────┬─────────────────┬────────────┐
  │   Ticker   │ Kept │ Missed │ Goalposts moved │ Scored (n) │
  ├────────────┼──────┼────────┼─────────────────┼────────────┤
  │ INFY       │ 2    │ 1      │ 1               │ 4          │
  ├────────────┼──────┼────────┼─────────────────┼────────────┤
  │ BAJFINANCE │ 1    │ 2      │ 1               │ 4          │
  ├────────────┼──────┼────────┼─────────────────┼────────────┤
  │ POLYCAB    │ 0    │ 0      │ 0               │ 0          │
  └────────────┴──────┴────────┴─────────────────┴────────────┘

  - INFY: FY27 constant-currency growth guidance cut from 1.5–3.5% to 1–2%; FY25
    growth delivered 4.2% against 4.5–5%; FY26 operating margin delivered 21%
    against 20–22%.
  - BAJFINANCE: FY26 AUM growth guidance cut from 24–25% to 22–23%; profit
    growth 24% beat 22–23%; MSME growth delivered 6% against 10–12%.
  - POLYCAB: its targets are FY30 or medium-term, so nothing can be scored yet;
    every promise says why.

  Fixtures: web/public/fixtures/dossier_{INFY,BAJFINANCE,POLYCAB}.json are full
  DossierResponse payloads, and all three validate against the contract. To
  regenerate them, run python -m jobs.research export. That module also has
  enqueue and drain, which the nightly run will use.

  There are 293 tests, all passing.

  Waiting on you: the PERSISTENT build on Render is still queued. Render needs
  the settings from DEPLOY.md §7 before it can build anything:
  - Start command: append --workers 1.
  - Environment: RESEARCH_WORKER=1, GEMINI_API_KEY, the Gemini model names,
    GEMINI_MODEL_STRONG_FALLBACKS=gemini-3-flash-preview and GROQ_API_KEY.

  After that, I'll build all four demo tickers on the deployed API and
  spot-check their quotes.

❯ Done, settings applied                                                        

  Called ccd_turn, ran 1 shell command (ctrl+o to expand)

❯ Thursday is frontend-only, so the dossier backend must be finished today.     
  Order for the rest of today:                                                  
  1. Confirm /version matches HEAD, build the 4 demo tickers on Render, and     
  check their quotes.                                                           
  2. The strong-model qualitative judge. Right now every demo ticker is below n 
  = 5, so the Promise Ledger shows no credibility score anywhere.               
  3. Reduce: snapshot text + bull/bear.                                         
     Move annual-report red flags, Ask and the nightly refresh to Friday        
  morning; we'll cut them if Friday gets tight. If steps 2–3 change the         
  contract, regenerate the fixtures tonight so I build the frontend on the      
  final shape.                                                                  

⏺ Render is on HEAD (29cf2f2) and its worker has started PERSISTENT, so I'm
  re-planning the order: demo, then the qualitative judge, reduce, and tonight's
  fixtures, with red flags, Ask and the nightly refresh moved to Friday. 
  · summary

  Called ccd_turn, ran 1 shell command (ctrl+o to expand)

⏺ All three are queued behind PERSISTENT on Render, and I'm drafting the
  qualitative judge while they build. The design takes one strong call per
  dossier, validates every evidence quote against its transcript in code, and
  relies on a prompt with no date so unchanged dossiers hit the cache. · summary

⏺ Write(backend/finn/research/bm25.py)
  ⎿  Wrote 69 lines to backend/finn/research/bm25.py
      1 """Tiny BM25 over transcript passages (no vector database): enoug
        h to find the later-call passages that speak to a
      2 promise (JUDGE) and the passages that answer a question (Ask)."""
      3 
      4 from __future__ import annotations
      5 
      6 import math
      7 import re
      8 from collections import Counter
      9 from dataclasses import dataclass
     … +60 lines (ctrl+o to expand)

⏺ Write(backend/finn/research/judge.py)
  ⎿  Wrote 151 lines to backend/finn/research/judge.py
      1 """Step 6 — JUDGE (strong call #1): qualitative promises and cros
        s-call patterns that code can't score.
      2 
      3 Code picks the candidates (qualitative promises, and undated nume
        ric ones whose later restatements may move the
      4 goalposts), retrieves the best passages from LATER calls for each
         (BM25), and asks the strong model for a verdict
      5 that must quote one of those passages. Code then checks every evi
        dence quote against the passage text and requires
      6 evidence from a later call than the promise for kept / missed / g
     … +146 lines (~7 KB) (ctrl+o to expand)

⏺ Now reduce.py. The model may only write numbers as {F12} placeholders, which
  code renders from the cited fact. A claim with any other number, or no valid
  fact id, is dropped and counted.

⏺ Write(backend/finn/research/reduce.py)
  ⎿  Wrote 188 lines to backend/finn/research/reduce.py
      1 """Step 7 — REDUCE (strong call #2): snapshot lines, one trajecto
        ry line, 3 bull and 3 bear bullets.
      2 
      3 The model gets only extracted facts and computed numbers, each wi
        th an id (F1, F2, …), and must cite fact ids for
      4 every sentence. It never writes a number: numbers appear as {F12}
         placeholders that code replaces with the fact's
      5 own value (rule 1 — the LLM reads, code calculates). A sentence w
        ith any other digit, or no valid fact id, is
      6 dropped and counted. Citations come from the cited facts, so ever
     … +183 lines (~7 KB) (ctrl+o to expand)

  Ran 1 shell command (ctrl+o to expand)

⏺ Render is working through PERSISTENT's extraction. Now wiring judge and reduce
  into the build.

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/research/ledger.py'; s=open(p).read()…)
  ⎿  232:        return
     283:        return
     254:    d.ask_chips = insights.ask_chips(d.drivers.items, bool(led.pro
     mises))
  ⎿  Updated backend/finn/research/build.py (+91 -8)
       95  
       96      # 5. Ledger, analysts, drivers (code)
       97      progress.step("ledger", "running", message="Scoring promis
           es against what was delivered")
       98 -    apply_ledger(d, symbol, disc, links, docs, calls, quota, n
          -ow)                                                           
       98 +    led = apply_ledger(d, symbol, disc, links, docs, calls, qu
          +ota, now)                                                     
       99      progress.step("ledger", "done" if calls else "skipped", f"
           {len(d.ledger.promises)} promises")
      100 +    store.publish(conn, d, complete=False)                    
      101  
      101 -    # 6–7. Judge + reduce (strong model) — Thursday's stage; s
          -ections say so meanwhile.                                     
      102 -    for key in ("judge", "reduce"):                           
      103 -        progress.step(key, "skipped", "Comes with the full bui
          -ld")                                                          
      102 +    # 6–7. Judge + reduce (strong model chain: 3.8 Flash → 3 F
          +lash; never Flash-Lite). An unchanged dossier hits            
      103 +    # the router's cache, so it costs no strong call.         
      104 +    tags = {"symbol": symbol, "job_id": job_id}               
      105 +    strong_quota = run_judge(d, led, calls, router, tags, prog
          +ress, now) if led else None                                   
      106 +    if disc.status == "ok" or calls:                          
      107 +        strong_quota = run_reduce(d, calls, router, tags, prog
          +ress, now) or strong_quota                                    
      108 +    else:                                                     
      109 +        progress.step("reduce", "skipped", "Nothing to summari
          +se")                                                          
      110 +        d.bull_bear.meta = meta("unavailable", "not_found_in_s
          +ources", "No financials or transcripts to summarise", now)    
      111 +    quota = quota or strong_quota                             
      112      st = router.stats.as_dict()
      113      d.cost = d.cost.model_copy(update={
      114          "calls": st["calls"] - stats0["calls"], "cache_hits": 
           st["cache_hits"] - stats0["cache_hits"],
     ...
      117      })  # fmt: skip
      118      progress.step("publish", "done", message="Published" if no
           t quota else
      119                    f"Published what's ready — the rest resumes 
           after {_ist(quota.retry_after)}")  # fmt: skip
      112 -    store.publish(conn, d, complete=False)                    
      120 +    complete = quota is None and all(getattr(d, k).meta.status
          + in ("ready", "unavailable") for k in                         
      121 +                                      ("snapshot", "trajectory
          +", "ledger", "cash_quality", "balance_sheet", "bull_bear"))   
      122 +    store.publish(conn, d, complete=complete)                 
      123      stats = {**d.cost.model_dump(), "calls_read": len(calls), 
           "guidance": guidance}
      124      if quota is not None and quota.kind == "quota" and quota.r
           etry_after:
      125          return Outcome("waiting_quota", stats=stats, error=str
           (quota)[:300], resume_after=quota.retry_after)
      116 -    return Outcome("partial", stats=stats)                    
      126 +    return Outcome("done" if complete else "partial", stats=st
          +ats)                                                          
      127 +                                                              
      128 +                                                              
      129 +def _building(resume) -> str:                                 
      130 +    return f"Building · resumes after {_ist(resume)} quota res
          +et"                                                           
     … 88 more lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/ledger.py (+6 -2)
      496              verdict_reason=Claim(text=why, status="verified", 
           citations=cites), delivered=delivered,
      497              delivered_source=dsrc, dropped_note=dropped_note,
      498          ))  # fmt: skip
      499 +    promises.sort(key=_order)                                 
      500 +    return Ledger(promises, credibility(promises, settled, cal
          +ls), count(promises), settled)                                
      501 +                                                              
      502 +                                                              
      503 +def count(promises: list[Promise]) -> LedgerCounts:           
      504      counts = LedgerCounts()
      505      for p in promises:
      506          setattr(counts, p.verdict, getattr(counts, p.verdict) 
           + 1)
      507          counts.raised += p.revision == "raised"
      503 -    promises.sort(key=_order)                                 
      504 -    return Ledger(promises, credibility(promises, settled, cal
          -ls), counts, settled)                                         
      508 +    return counts                                             
      509  
      510  
      511  def _cur(c: str) -> str:

⏺ Bash(sed -n 225,236p finn/research/build.py && python3 - <<'EOF'
      p='finn/research/build.py'; s=open(p).read()…)
  ⎿          elif scanned:
                 m = meta("unavailable", "scanned_documents", "Transcripts
     are scanned images — not read", now)
     … +16 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/build.py (+6 -3)
      117      })  # fmt: skip
      118      progress.step("publish", "done", message="Published" if no
           t quota else
      119                    f"Published what's ready — the rest resumes 
           after {_ist(quota.retry_after)}")  # fmt: skip
      120 -    complete = quota is None and all(getattr(d, k).meta.status
          - in ("ready", "unavailable") for k in                         
      121 -                                      ("snapshot", "trajectory
          -", "ledger", "cash_quality", "balance_sheet", "bull_bear"))   
      120 +    complete = quota is None and all(                         
      121 +        getattr(d, k).meta.status in ("ready", "unavailable") 
      122 +        for k in ("snapshot", "trajectory", "ledger", "cash_qu
          +ality", "balance_sheet", "bull_bear")                         
      123 +    )                                                         
      124      store.publish(conn, d, complete=complete)
      125      stats = {**d.cost.model_dump(), "calls_read": len(calls), 
           "guidance": guidance}
      126      if quota is not None and quota.kind == "quota" and quota.r
           etry_after:
     ...
      231          for sec in (d.ledger, d.analysts, d.drivers):
      232              if sec.meta.status != "ready":  # keep a previous 
           good build's sections
      233                  sec.meta = m
      232 -        return                                                
      234 +        return None                                           
      235      led = build_ledger(symbol, calls, disc, now.date(), disc.y
           ear_end_month or 3)
      236      d.ledger.promises, d.ledger.credibility, d.ledger.counts =
            led.promises, led.credibility, led.counts
      237      d.ledger.calls_read = len(calls)
     ...
      254      latest = max(calls, key=lambda c: c.made_on)
      255      d.snapshot.segments = insights.segments(latest)
      256      d.ask_chips = insights.ask_chips(d.drivers.items, bool(led
           .promises))
      257 +    return led                                                
      258  
      259  
      260  def apply_compute(d: Dossier, disc, prev: Dossier | None, now:
            datetime) -> None:
  ⎿  Updated backend/finn/research/reduce.py (+5 -1)
      131              add(f"capex plan ({latest.label}): \"{c['quote']}\
           "", c.get("purpose") or "capex plan",
      132                  [latest.cite(c["page"], c["quote"])])  # fmt: 
           skip
      133          for r in latest.facts.get("risks", [])[:4]:
      134 -            add(f"risk named by management ({latest.label}): {
          -r['text']}", r["text"], [latest.cite(r["page"], r["quote"])]) 
      134 +            add(                                              
      135 +                f"risk named by management ({latest.label}): {
          +r['text']}",                                                  
      136 +                r["text"],                                    
      137 +                [latest.cite(r["page"], r["quote"])],         
      138 +            )                                                 
      139      return out
      140  
      141  

⏺ I'm testing judge and reduce locally on HDFCBANK, a bank outside the demo set,
  so they won't collide with the Render jobs. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ While that runs, unit tests for the judge's evidence rules and reduce's number
  rule:

⏺ Write(backend/tests/test_research_synthesis.py)
  ⎿  Wrote 81 lines to backend/tests/test_research_synthesis.py
       1 """JUDGE and REDUCE guards: model verdicts need verbatim later-c
         all evidence; model text never carries a number."""
       2 
       3 from datetime import UTC, date, datetime
       4 
       5 from finn.models import Citation, Figure
       6 from finn.research import judge, reduce
       7 from finn.research.bm25 import BM25, passages
       8 from finn.research.ledger import Call, build_ledger
       9 
     … +72 lines (ctrl+o to expand)

⏺ Bash(../.venv/bin/ruff format -q tests; ../.venv/bin/ruff check -q . ;
      ../.venv/bin/python -m pytest -q tests/test_research_synthesis.py 2>&1 |
      tail -15)
  ⎿  tests/test_research_synthesis.py:60: AttributeError
     _____________________ test_bm25_finds_the_relevant_passage ___________
     __________
     … +18 lines (ctrl+o to expand)
  ⎿  Updated backend/tests/test_research_synthesis.py (+3 -1)
      40                            "quote": "we launched our first produ
          ct in the US market in December",
      41                            "reason": "Launched in December"}]}  
          # fmt: skip
      42      res = judge.apply(led.promises, data, pid_map, cs, "gemini-
          3.8-flash", led.settled)
      43 -    assert res.changed == 1 and p.verdict == "kept" and p.verdi
         -ct_by == "model" and p.verdict_model == "gemini-3.8-flash"     
      43 +    assert (                                                   
      44 +        res.changed == 1 and p.verdict == "kept" and p.verdict_
         +by == "model" and p.verdict_model == "gemini-3.8-flash"        
      45 +    )                                                          
      46      assert {c.url for c in p.verdict_reason.citations} == {"htt
          ps://x/1.pdf", "https://x/2.pdf"}
      47  
      48  

⏺ Two BM25 bugs. Short passages (≤60 characters) were discarded, and "US" was
  lower-cased into the stopword "us". Also adding light suffix stemming, so
  "launch" matches "launched":

⏺ Bash(python3 - <<'EOF'
      p='finn/research/bm25.py'; s=open(p).read()…)
  ⎿  E       AttributeError: 'Ledger' object has no attribute 'settled'. Di
     d you mean: 'settled_on'?
     E       AttributeError: 'Ledger' object has no attribute 'settled'. Di
     … +2 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/bm25.py (+11 -3)
      12  
      13  _TOK = re.compile(r"[a-z0-9]+")
      14  _STOP = set("""a an the and or of to in on for with at by from 
          as is are was were be been it its this that these those
      15 -we our us you your they their i he she will would should could 
         -can may might have has had do does did not no so if            
      15 +we our you your they their i he she will would should could can
         + may might have has had do does did not no so if               
      16  then than there here what which who whom how when where also ju
          st about into over under more most very much any some
      17  all each per vs""".split())  # fmt: skip
      18  PASSAGE_WORDS = 110
      19  
      20  
      21 +def _stem(t: str) -> str:                                      
      22 +    """Light suffix stripping so 'launched'/'launches'/'launchi
         +ng' match 'launch'."""                                         
      23 +    for suf in ("ing", "ed", "es", "s"):                       
      24 +        if len(t) > len(suf) + 3 and t.endswith(suf):          
      25 +            return t[: -len(suf)]                              
      26 +    return t                                                   
      27 +                                                               
      28 +                                                               
      29  def tokens(text: str) -> list[str]:
      22 -    return [t for t in _TOK.findall(text.lower()) if t not in _
         -STOP and len(t) > 1]                                           
      30 +    return [_stem(t) for t in _TOK.findall(text.lower()) if t n
         +ot in _STOP and len(t) > 1]                                    
      31  
      32  
      33  @dataclass
     ...
      43          words = " ".join(clean(p).split()).split(" ")
      44          for j in range(0, len(words), size - 20):  # 20-word ov
          erlap so a sentence isn't cut in half
      45              chunk = " ".join(words[j : j + size]).strip()
      38 -            if len(chunk) > 60:                                
      46 +            if len(chunk) >= 20:                               
      47                  out.append(Passage(doc_id, i, chunk))
      48      return out
      49  

⏺ The Ledger field is named settled_on, but the build calls it settled. That
  would crash the live HDFCBANK run at the judge step, so I'm renaming the
  field:

⏺ Bash(sed -i '' 's/    settled_on: dict\[str, date\]/    settled: dict[str,
      date]/' finn/research/ledger.py && grep -n "settled_on" -r finn tests;
      ../.venv/bin/ruff c…)
  ⎿  297 passed, 1 warning in 1.36s
  ⎿  Updated backend/finn/research/ledger.py (+1 -1)
      384      promises: list[Promise]
      385      credibility: Credibility
      386      counts: LedgerCounts
      387 -    settled_on: dict[str, date]                               
      387 +    settled: dict[str, date]                                  
      388  
      389  
      390  def build_ledger(symbol: str, calls: list[Call], disc, today: 
           date, ye_month: int = 3) -> Ledger:

⏺ All 297 tests pass. The HDFCBANK run loaded the old code, so it will fail at
  the judge step; its extractions stay cached for the rerun. Checking Render
  meanwhile:
  Ran 1 shell command (ctrl+o to expand)

⏺ All 4 demo tickers built on Render. Spot-checking the deployed dossiers: every
  scored verdict's quotes are checked against the stored transcript page they
  cite.

  Ran 1 shell command (ctrl+o to expand)

⏺ All 20 quotes behind the scored verdicts are on their cited pages, but
  PERSISTENT's "80–100 bps, first given as 180 bps" verdict is marked goalposts
  moved, so I'm checking those quotes next. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ Both figures come from the same call, a 180 bps wage-hike headwind with 80–100
  bps offset, so it isn't a revision. I'm adding two rules: different numbers
  from one call become separate threads, and an unsigned "change" or "impact"
  target can't produce "goalposts moved". · summary

  Searched for 1 pattern (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/research/ledger.py'; s=open(p).read()…)
  ⎿  410:            by_family[t.key[:5] + t.key[6:]].append(t)
     504:            basis=PromiseBasis(currency=_cur(t.key[-2] if not qual
      else last.currency),
     … +2 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/ledger.py (+13 -1)
      178                      b = match[0]
      179              buckets[b].append(s)
      180          for b, ss in buckets.items():
      181 -            threads.append(Thread((*fk, *b), sorted(ss, key=la
          -mbda x: x.made_on)))                                          
      181 +            # One call can give two different numbers for the 
          +same metric (a 180 bps headwind, 80–100 bps of it             
      182 +            # offset): those are separate statements, not a re
          +vision — a thread holds one statement per call.               
      183 +            lanes: list[list[Stmt]] = []                      
      184 +            for st in sorted(ss, key=lambda x: x.made_on):    
      185 +                lane = next((ln for ln in lanes if all(o.call.
          +doc_id != st.call.doc_id for o in ln)), None)                 
      186 +                if lane is None:                              
      187 +                    lanes.append([st])                        
      188 +                else:                                         
      189 +                    lane.append(st)                           
      190 +            for i, ln in enumerate(lanes):                    
      191 +                threads.append(Thread((*fk, *b) if i == 0 else
          + (*fk, *b, i), ln))                                           
      192      return threads
      193  
      194  
     ...
      432          target = scored[-1]
      433          key = s0.item["metric_key"]
      434          direction = metrics.direction(key)
      435 +        if s0.item["measure"] == "change" and all((x.low or 0)
          + >= 0 and (x.high or 0) >= 0 for x in t.stmts):               
      436 +            direction = "neutral"  # an unsigned 'impact'/'cha
          +nge' — code can't tell headwind from tailwind                 
      437          qual = t.key[0] == "qual"
      438          pid = hashlib.sha256(repr((symbol, t.key, s0.call.doc_
           id if qual else "")).encode()).hexdigest()[:16]
      439          rev, rev_by = ("none", None) if qual else revision(t.s
           tmts, direction)

⏺ Bash(python3 - <<'EOF'
      p='finn/research/ledger.py'; s=open(p).read()…)
  ⎿  299 passed, 1 warning in 1.45s
  ⎿  Updated backend/finn/research/ledger.py (+2 -2)
      501          promises.append(Promise(
      502              id=pid, symbol=symbol, metric=s0.item["metric"], m
           etric_key=key,
      503              measure="qualitative" if qual else s0.item["measur
           e"], kind=target.item["kind"],
      504 -            basis=PromiseBasis(currency=_cur(t.key[-2] if not 
          -qual else last.currency),                                     
      505 -                               scope=t.key[-1] if not qual els
          -e last.scope, segment=last.item.get("segment") or None),      
      504 +            basis=PromiseBasis(currency=_cur(t.key[6] if not q
          +ual else last.currency),                                      
      505 +                               scope=t.key[7] if not qual else
          + last.scope, segment=last.item.get("segment") or None),       
      506              period=period, statement=" ".join(statement.split(
           )), statements=[_ps(s) for s in t.stmts],
      507              scored_target=_ps(target), revision=rev, verdict=v
           erdict, verdict_by="code",
      508              verdict_reason=Claim(text=why, status="verified", 
           citations=cites), delivered=delivered,
  ⎿  Updated backend/tests/test_ledger.py (+16 -0)
      272      assert (
      273          "17–18%" in p.verdict_reason.text and "Q3 call" in p.v
           erdict_reason.text and "20–22%" in p.verdict_reason.text
      274      )
      275 +                                                              
      276 +                                                              
      277 +def test_two_numbers_in_one_call_are_not_a_revision():        
      278 +    head = g("ebit_margin", 180, 180, unit="bps", kind="point"
          +, measure="change", period_type="quarter", fy=2026,           
      279 +             quarter=3, quote="We anticipate an impact of 180 
          +basis points on next quarter's margins")  # fmt: skip         
      280 +    offset = g("ebit_margin", 80, 100, unit="bps", measure="ch
          +ange", period_type="quarter", fy=2026, quarter=3,             
      281 +               quote="up to 80 to 100 basis points of this imp
          +act is expected to get offset")  # fmt: skip                  
      282 +    led = ledger([call(1, date(2025, 10, 20), [head, offset])]
          +)                                                             
      283 +    assert len(led.promises) == 2 and all(p.verdict != "goalpo
          +sts_moved" and p.revision == "none" for p in led.promises)    
      284 +                                                              
      285 +                                                              
      286 +def test_unsigned_change_across_calls_is_revised_not_moved(): 
      287 +    a1 = g("ebit_margin", 180, 180, unit="bps", kind="point", 
          +measure="change", fy=2027)                                    
      288 +    a2 = g("ebit_margin", 100, 100, unit="bps", kind="point", 
          +measure="change", fy=2027)                                    
      289 +    p = only(ledger([call(1, date(2026, 4, 20), [a1]), call(2,
          + date(2026, 7, 20), [a2])]))                                  
      290 +    assert p.revision == "revised" and p.verdict != "goalposts
          +_moved"                                                       

⏺ 299 pass. Checking the HDFCBANK run:

  Searched for 1 pattern (ctrl+o to expand)

⏺ Still running. Meanwhile, PLAN gets your reordering: red flags, Ask and the
  nightly refresh move to Friday morning and can be cut.

⏺ Bash(cd ~/Documents/finn && python3 - <<'EOF'
      p='docs/PLAN.md'; s=open(p).read()…)
  ⎿   docs/PLAN.md | 11 +++++++----
      1 file changed, 7 insertions(+), 4 deletions(-)
  ⎿  Updated docs/PLAN.md (+7 -4)
      67  - [x] Screener discovery (all tables, transcripts, annual repor
          t, capex schedule) + computed trajectory / cash / balance sheet
           incl. lenders — `12a189a`
      68  - [x] Transcripts (PyMuPDF, text in Supabase), citation checker
          , MAP extraction — `83eb047`
      69  - [x] Numeric Promise Ledger + analysts + drivers in builds — `
          85c0cd4` (INFY local: 4 kept, 1 missed, 1 moved)
      70 -- [ ] **Render env (product owner):** DEPLOY.md §7 — `--workers
         - 1`, `RESEARCH_WORKER=1`, Gemini keys/models, `GEMINI_MODEL_STR
         -ONG_FALLBACKS`                                                 
      71 -- [ ] Build the 4 demo tickers on the deployed API; spot-check 
         -5 verdicts' quotes in the PDFs                                 
      72 -- [ ] JUDGE (strong #1): qualitative promises + paraphrased cro
         -ss-call links, citing both calls                               
      70 +- [x] **Render env (product owner):** DEPLOY.md §7 — set 11 Nov
      71 +- [x] Build the 4 demo tickers on the deployed API; quotes chec
         +ked — 20 of 20 verdict quotes on their cited pages (PERSISTENT,
         + INFY, BAJFINANCE; POLYCAB has no scorable promise yet)        
      72 +- [ ] JUDGE (strong #1): qualitative promises + paraphrased cro
         +ss-call links, citing both calls — **Wed 11 Nov**              
      73 +- [ ] REDUCE (strong #2): snapshot text, trajectory line, bull/
         +bear with `{F#}` placeholders rendered in code — **Wed 11 Nov**
      74 +- [ ] Rebuild the 4 demo tickers on Render and regenerate `web/
         +public/fixtures/` — **Wed 11 Nov** (Thursday is frontend-only) 
      75 +                                                               
      76 +**Friday morning (product owner, 11 Nov: cut if Friday gets tig
         +ht):**                                                         
      77  - [ ] Annual report sections (headings in code) → red flags (au
          ditor opinion, contingent liabilities growth, related parties)
      74 -- [ ] REDUCE (strong #2): snapshot text, trajectory line, press
         -ure-point wording, bull/bear with `{f:ID}` placeholders rendere
         -d in code                                                      
      78  - [ ] Ask: BM25 over the ticker's pages + facts → Flash-Lite (G
          roq fallback) → cited answer or "Not found in sources"
      79  - [ ] Nightly refresh on Actions (code-only recompute; rebuild 
          only on a new document; first-time builds only for the 4 demo t
          ickers); DB size guard
      80  - [ ] On-demand NSE dispatch (section above) → `exchange_data`

⏺ The HDFCBANK run will crash at the judge step on old code anyway. If its 8
  extractions are already cached, I'll stop it and rerun on the new code:

  Ran 1 shell command (ctrl+o to expand)

⏺ 5 of 8 HDFCBANK transcripts are extracted. I'll let the run finish, so all 8
  extractions are cached, then rerun HDFCBANK on the new code to test judge and
  reduce live.

❯ whats the status?                                                             

  Ran 1 shell command (ctrl+o to expand)

⏺ All 8 HDFCBANK transcripts are already extracted and cached, but the old
  process is stuck in the judge step on stale code. I'm stopping it and
  rerunning on the current code, which will reuse those cached extractions. 
  · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ Background command "Build HDFCBANK directly with judge and reduce" failed with
exit code 144

⏺ The old run's failure is expected; I stopped it. The new run is taking longer
  than it should with cached extractions, so I'm checking the strong-model
  calls:

  Ran 1 shell command (ctrl+o to expand)

⏺ Two strong-model calls are failing: gemini-3.8-flash is overloaded and timing
  out, and gemini-3-flash-preview is cut off by its unbounded thinking. I'm
  capping thinking, raising the output limit, and limiting retries to two per
  model, starting with a check that 3.8 Flash accepts a thinking budget. 
  · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ Background command "Rerun HDFCBANK with judge and reduce on current code"
failed with exit code 144

⏺ gemini-3-flash-preview answers in 2 s and honors the thinking cap while
  gemini-3.8-flash times out, so I'm adding a short circuit that skips a chain
  model after two failures for 10 minutes and caps judge and reduce thinking at
  1,024 tokens. · summary

  Searched for 1 pattern (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/llm/router.py'; s=open(p).read()…)
  ⎿  286:            if True:
  ⎿  Updated backend/finn/llm/router.py (+21 -5)
      160              sleep(pause)
      161  
      162  
      163 +# A model in a fallback chain that keeps failing (overloaded: 
          +503s, timeouts) is skipped for a while so the next            
      164 +# model answers at once instead of after minutes of retries. P
          +rocess-wide, like the limiters.                               
      165 +COOLDOWN_S = 600                                              
      166 +CHAIN_ATTEMPTS = 2  # attempts on a model that has a fallback 
          +after it (the last model keeps the full backoff)              
      167 +_COOLING: dict[tuple[str, str], float] = {}                   
      168 +                                                              
      169  _LIMITERS: dict[tuple[str, str], _Limiter] = {}
      170  _LIMITERS_LOCK = threading.Lock()
      171  
     ...
      174      """Forget per-minute history (tests)."""
      175      with _LIMITERS_LOCK:
      176          _LIMITERS.clear()
      177 +        _COOLING.clear()                                      
      178  
      179  
      180  def _env_int(name: str, default: int) -> int:
     ...
      281                  if hit:
      282                      return hit
      283                  raise LLMUnavailable(f"research daily cap {cap
           } reached ({lane})", "quota", next_quota_reset())
      277 -        for p in self.providers:                              
      278 -            for model in _models(p, tier):                    
      284 +        chain = [(p, m) for p in self.providers for m in _mode
          +ls(p, tier)]                                                  
      285 +        for idx, (p, model) in enumerate(chain):              
      286 +            if True:                                          
      287                  sendable = req if (p.supports_pdf() or not req
           .pdf) else self._as_text(req)
      288                  if sendable is None:
      289                      errors.append(f"{p.name}: needs the PDF an
           d it has no text layer")
     ...
      312                      errors.append(f"{model}: daily budget {lim
           .rpd} reached")
      313                      kinds.add("quota")
      314                      continue
      315 +                has_next = idx < len(chain) - 1               
      316 +                if has_next and _COOLING.get((p.name, model), 
          +0) > time.monotonic():                                        
      317 +                    errors.append(f"{model}: skipped — overloa
          +ded in the last {COOLDOWN_S // 60} min")                      
      318 +                    kinds.add("transient")                    
      319 +                    continue                                  
      320                  lim.wait(sendable.est_tokens(), RESEARCH_TPM i
           f lane and tier == "cheap" else None, self._sleep)
      321                  row = {
     … 24 more lines (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/llm/router.py'; lines=open(p).read().split("\n")…)
  ⎿              if self._lane_used(lane, tier) >= cap:
                     # Cached answers are still served below; only new call
     s are refused.
     … +18 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/llm/router.py (+65 -66)
      283                  raise LLMUnavailable(f"research daily cap {cap
           } reached ({lane})", "quota", next_quota_reset())
      284          chain = [(p, m) for p in self.providers for m in _mode
           ls(p, tier)]
      285          for idx, (p, model) in enumerate(chain):
      286 -            if True:                                          
      287 -                sendable = req if (p.supports_pdf() or not req
          -.pdf) else self._as_text(req)                                 
      288 -                if sendable is None:                          
      289 -                    errors.append(f"{p.name}: needs the PDF an
          -d it has no text layer")                                      
      290 -                    kinds.add("too_large")                    
      291 -                    continue                                  
      292 -                key = sendable.content_hash(model)            
      293 -                hit = self.log.get_cached(key)                
      294 -                if hit:                                       
      295 -                    self.stats.cache_hits += 1                
      296 -                    resp = hit["response"]                    
      297 -                    data = resp if isinstance(resp, dict) else
          - json.loads(resp)                                             
      298 -                    return LLMResult(                         
      299 -                        data, hit["provider"], hit["model"], h
          -it.get("tokens_in"), hit.get("tokens_out"), cached=True       
      300 -                    )                                         
      301 -                if p.name == "groq" and sendable.est_tokens() 
          -> GROQ_MAX_TOKENS:                                            
      302 -                    errors.append(f"groq: request too large fo
          -r its free tier (~{sendable.est_tokens()} tokens)")           
      303 -                    kinds.add("too_large")                    
      304 -                    continue                                  
      305 -                if (p.name, model) in self._exhausted:        
      306 -                    errors.append(f"{model}: quota exhausted e
          -arlier in this run")                                          
      307 -                    kinds.add("quota")                        
      308 -                    continue                                  
      309 -                lim = self._limiter(p.name, model)            
      310 -                if self.log.count_today(p.name, model) >= lim.
          -rpd:                                                          
      311 -                    self._exhausted.add((p.name, model))      
      312 -                    errors.append(f"{model}: daily budget {lim
          -.rpd} reached")                                               
      313 -                    kinds.add("quota")                        
      314 -                    continue                                  
      315 -                has_next = idx < len(chain) - 1               
      316 -                if has_next and _COOLING.get((p.name, model), 
          -0) > time.monotonic():                                        
      317 -                    errors.append(f"{model}: skipped — overloa
          -ded in the last {COOLDOWN_S // 60} min")                      
      318 -                    kinds.add("transient")                    
      319 -                    continue                                  
      320 -                lim.wait(sendable.est_tokens(), RESEARCH_TPM i
          -f lane and tier == "cheap" else None, self._sleep)            
      321 -                row = {                                       
      322 -                    "content_hash": key, "provider": p.name, "
          -model": model, "tier": tier, "purpose": req.purpose,          
     … 98 more lines (ctrl+o to expand)

  Ran 1 shell command (ctrl+o to expand)

⏺ That test pins the push side's deliberate behaviour: busy Gemini Flash-Lite
  gets the full 5 attempts before Groq. Limiting the short-circuit to the strong
  chain:

⏺ Bash(python3 - <<'EOF'
      p='finn/llm/router.py'; s=open(p).read()…)
  ⎿  300 passed, 1 warning in 1.26s
  ⎿  Updated backend/finn/llm/router.py (+2 -1)
      311                  errors.append(f"{model}: daily budget {lim.rpd
           } reached")
      312                  kinds.add("quota")
      313                  continue
      314 -            has_next = idx < len(chain) - 1                   
      314 +            # only the strong chain short-circuits; the push s
          +ide keeps full retries on Flash-Lite before Groq              
      315 +            has_next = tier == "strong" and idx < len(chain) -
          + 1                                                            
      316              if has_next and _COOLING.get((p.name, model), 0) >
            time.monotonic():
      317                  errors.append(f"{model}: skipped — overloaded 
           in the last {COOLDOWN_S // 60} min")
      318                  kinds.add("transient")
  ⎿  Updated backend/tests/test_llm_router.py (+12 -0)
      247      from finn.calendar import next_quota_reset, to_ist
      248  
      249      assert to_ist(next_quota_reset(datetime(2026, 11, 11, 20, 
           0, tzinfo=UTC))).strftime("%d %H:%M") == "12 13:30"
      250 +                                                              
      251 +                                                              
      252 +def test_overloaded_strong_model_is_skipped_quickly_then_coole
          +d():                                                          
      253 +    from finn.llm import TransientError                       
      254 +                                                              
      255 +    pauses = []                                               
      256 +    g = Chain("gemini", CHAIN, fails={"flash-38": TransientErr
          +or("503 high demand")})                                       
      257 +    r = Router([g], MemoryLLMLog(), sleep=pauses.append)      
      258 +    assert r.run("strong", req(purpose="research.judge.v1", pr
          +ompt="a")).model == "flash-3"                                 
      259 +    assert [m for _, m in g.calls] == ["flash-38", "flash-38",
          + "flash-3"] and pauses == [2.0]  # 2 attempts, not 5          
      260 +    r.run("strong", req(purpose="research.reduce.v1", prompt="
          +b"))                                                          
      261 +    assert [m for _, m in g.calls][-1] == "flash-3" and len(g.
          +calls) == 4  # cooled: no third try on flash-38               
⏺ Now the judge and reduce requests: thinking capped, bigger output, shorter
  timeout.

⏺ Bash(python3 - <<'EOF'
      for p, old, new in […)
  ⎿  finn/research/judge.py:105:                      timeout_s=90, thinkin
     g_budget=1024, tags=tags), pid_map  # fmt: skip
     finn/research/reduce.py:148:                      timeout_s=90, thinki
     … +67 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/judge.py (+2 -2)
      101      if not blocks:
      102          return None, {}
      103      prompt = "Promises and the later-call passages that may sp
           eak to them:\n\n" + "\n\n".join(blocks)
      104 -    return LLMRequest(purpose=PURPOSE, system=SYSTEM, prompt=p
          -rompt, schema=SCHEMA, max_output_tokens=6000,                 
      105 -                      timeout_s=180, tags=tags), pid_map  # fm
          -t: skip                                                       
      104 +    return LLMRequest(purpose=PURPOSE, system=SYSTEM, prompt=p
          +rompt, schema=SCHEMA, max_output_tokens=12000,                
      105 +                      timeout_s=90, thinking_budget=1024, tags
          +=tags), pid_map  # fmt: skip                                  
      106  
      107  
      108  def apply(promises: list[Promise], data: dict, pid_map: dict, 
           calls: list[Call], model: str,
  ⎿  Updated backend/finn/research/reduce.py (+2 -2)
      144          return None
      145      head = f"Company: {d.name} ({d.symbol}); figures are {d.ba
           sis or 'reported'}; template: {d.template}.\n\nFacts:\n"
      146      prompt = head + "\n".join(f.line for f in fs) + "\n\n" + P
           ROMPT_TAIL
      147 -    return LLMRequest(purpose=PURPOSE, system=SYSTEM, prompt=p
          -rompt, schema=SCHEMA, max_output_tokens=4000,                 
      148 -                      timeout_s=180, tags=tags)  # fmt: skip  
      147 +    return LLMRequest(purpose=PURPOSE, system=SYSTEM, prompt=p
          +rompt, schema=SCHEMA, max_output_tokens=12000,                
      148 +                      timeout_s=90, thinking_budget=1024, tags
          +=tags)  # fmt: skip                                           
      149  
      150  
      151  def render(raw: dict | None, fs: list[Fact]) -> tuple[Claim | 
           None, bool]:

⏺ HDFCBANK now builds end to end in 67 seconds, but the output still fails on
  four points: it counts repeated governance promises as kept, has the model
  judge arithmetic, leaves broken placeholders, and never fills in the
  quotes-checked counter. I'm fixing all four in code next, without
  re-extracting. · summary

  Searched for 1 pattern (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/research/ledger.py'; s=open(p).read()…)
  ⎿  88:        d.quality.quotes_checked += int(st.get("checked") or 0)
  ⎿  Updated backend/finn/research/build.py (+2 -0)
      85              break
      86          dropped += int(st.get("dropped_total") or st.get("check
          ed", 0) - st.get("found", 0) - st.get("reanchored", 0))
      87          guidance += len(facts.get("guidance", []))
      88 +        d.quality.quotes_checked += int(st.get("checked") or 0)
      89 +        d.quality.quotes_reanchored += int(st.get("reanchored")
         + or 0)                                                         
      90          made = doc.ref.call_date or (doc.ref.period.end if doc.
          ref.period else now.date())
      91          calls.append(Call(doc.ref.id, doc.ref.url, f"{doc.ref.p
          eriod.label if doc.ref.period else ''} call".strip(),
      92                            made, doc.pages, facts, now))  # fmt:
           skip
  ⎿  Updated backend/finn/research/judge.py (+4 -1)
      24  
      25  log = logging.getLogger("finn.research.judge")
      26  
      27 -PROMPT_VERSION = "v1"                                          
      27 +PROMPT_VERSION = "v2"                                          
      28  PURPOSE = f"research.judge.{PROMPT_VERSION}"
      29  MAX_CANDIDATES = 25
      30  PASSAGES_EACH = 3
     ...
      38  - raised: a later passage sets a more ambitious target for the 
          same thing (not a verdict, just a revision).
      39  - not_yet_due: a later passage says it is still in progress and
           the date has not passed.
      40  - cant_score: the passages don't say.
      41 +Use kept or missed only when the passage itself states the outc
         +ome ("we launched", "we achieved", "we could not").            
      42 +Never compare numbers yourself: if deciding would need comparin
         +g figures (e.g. growth vs a range or vs the                    
      43 +industry), answer cant_score.                                  
      44  For kept, missed, goalposts_moved and raised you MUST quote the
           passage (8–40 words, copied exactly) and give its id.
      45  Keep reasons under 25 words, plain and factual. Do not calculat
          e anything."""
      46  
  ⎿  Updated backend/finn/research/ledger.py (+32 -3)
      156      return (key, other, s.item["measure"], s.segment, s.unit)
      157  
      158  
      159 +def _qual_words(s: Stmt) -> set[str]:                         
      160 +    text = norm(f"{s.item.get('metric', '')} {s.item.get('stat
          +ement', '')}")                                                
      161 +    return {w for w in re.findall(r"[a-z]{4,}", text)}        
      162 +                                                              
      163 +                                                              
      164 +def _jaccard(a: set[str], b: set[str]) -> float:              
      165 +    return len(a & b) / len(a | b) if a and b else 0.0        
      166 +                                                              
      167 +                                                              
      168 +# Board and personnel housekeeping isn't a business promise (a
          +n interim chairman's tenure, an AGM date). Only               
      169 +# business, financial and operational commitments enter the le
          +dger.                                                         
      170 +_GOVERNANCE = re.compile(r"\b(chairman|chairperson|director|bo
          +ard|independent|appoint\w*|tenure|interim|ceo|cfo|md|"        
      171 +                         r"managing director|company secretary
          +|agm|egm|record date|book closure|auditor)\b", re.I)          
      172 +                                                              
      173 +                                                              
      174 +def is_business_promise(it: dict) -> bool:                    
      175 +    if it.get("metric_key") not in ("other", "headcount"):    
      176 +        return True                                           
      177 +    return not _GOVERNANCE.search(f"{it.get('metric', '')} {it
          +.get('statement', '')}")                                      
      178 +                                                              
      179 +                                                              
      180  def group(stmts: list[Stmt]) -> list[Thread]:
      181      """Numeric statements → threads by family + period, with '
           unspecified' basis merged into a single specified
      182      one. Qualitative statements stay one per thread (the stron
           g model links paraphrases across calls)."""
     ...
      184      fams: dict[tuple, list[Stmt]] = defaultdict(list)
      185      for s in stmts:
      186          if s.item["kind"] == "qualitative" or s.item["measure"
           ] == "qualitative":
      166 -            threads.append(Thread(("qual", s.call.doc_id, s.it
          -em["quote"][:40]), [s]))                                      
      187 +            # A restatement in a later call (same metric, most
          +ly the same words) joins the earlier thread.                  
      188 +            words = _qual_words(s)                            
      189 +            home = next((t for t in threads if t.key[0] == "qu
          +al" and t.key[1] == s.item["metric_key"]                      
      190 +                         and all(o.call.doc_id != s.call.doc_i
          +d for o in t.stmts)                                           
      191 +                         and _jaccard(words, _qual_words(t.stm
          +ts[0])) >= 0.5), None)  # fmt: skip                           
      192 +            if home is not None:                              
      193 +                home.stmts.append(s)                          
      194 +            else:                                             
      195 +                threads.append(Thread(("qual", s.item["metric_
          +key"], s.call.doc_id, s.item["quote"][:40]), [s]))            
     … 19 more lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/reduce.py (+12 -10)
      17  from finn.models.research import Dossier
      18  from finn.research.ledger import Call
      19  
      20 -PROMPT_VERSION = "v1"                                          
      20 +PROMPT_VERSION = "v2"                                          
      21  PURPOSE = f"research.reduce.{PROMPT_VERSION}"
      22  
      23  SYSTEM = """You write a short, neutral research summary of an I
          ndian listed company for a professional investor,
     ...
      26  Rules:
      27  - Every sentence cites the fact ids it rests on.
      28  - Never type a number. To mention a number, write its placehold
          er exactly, e.g. {F12}; it is filled in from the
      29 -  fact. Period names like FY26 or Q2 FY27 are fine.            
      29 +  fact. Only facts marked [number] have placeholders; cite the 
         +others by id and describe them in words.                       
      30 +  Period names like FY26 or Q2 FY27 are fine.                  
      31  - Plain English, at most 25 words per sentence. No hype words."
          ""
      32  
      33  PROMPT_TAIL = """Write:
     ...
      54  class Fact:
      55      id: str
      56      line: str  # what the model sees
      56 -    display: str  # what a placeholder renders to              
      57 +    display: str | None  # what a {F#} placeholder renders to —
         + only figures have one                                         
      58      citations: list[Citation]
      59  
      60  
     ...
       94  def facts(d: Dossier, calls: list[Call]) -> list[Fact]:
       95      out: list[Fact] = []
       96  
       96 -    def add(line: str, display: str, cites: list[Citation]) ->
          - None:                                                        
       97 +    def add(line: str, display: str | None, cites: list[Citati
          +on]) -> None:                                                 
       98          if cites:
       99              fid = f"F{len(out) + 1}"
      100              out.append(Fact(fid, f"{fid}: {line}", display, ci
           tes))
     ...
      117          if p.verdict in ("kept", "missed", "goalposts_moved", 
           "quietly_dropped") or p.revision == "raised":
      118              reason = p.verdict_reason.text if p.verdict_reason
            else ""
      119              add(f"promise '{p.statement}' → {p.verdict.replace
           ('_', ' ')}"
      119 -                f"{' (target raised)' if p.revision == 'raised
          -' else ''}: {reason}", p.statement,                           
      120 +                f"{' (target raised)' if p.revision == 'raised
          +' else ''}: {reason}", None,                                  
      121                  (p.verdict_reason.citations if p.verdict_reaso
           n else [])[:2] or [p.statements[-1].quote])  # fmt: skip
      122      cr = d.ledger.credibility
     … 34 more lines (ctrl+o to expand)

⏺ The quality counters would accumulate across rebuilds, because each build
  starts from the previous dossier. Resetting them per build, then testing:

⏺ Bash(python3 - <<'EOF'
      p='finn/research/build.py'; s=open(p).read()…)
  ⎿  tests/test_ledger.py:294:121: E501 Line too long (122 > 120)
     Found 1 error.
     … +3 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/build.py (+2 -1)
      12  
      13  from finn.calendar import now_utc
      14  from finn.llm import LLMUnavailable, PostgresLLMLog, Router
      15 -from finn.models.research import Dossier, SectionMeta          
      15 +from finn.models.research import Dossier, DossierQuality, Secti
         +onMeta                                                         
      16  from finn.research import store
      17  from finn.research.documents import get_document
      18  from finn.research.extract import map_transcript
     ...
      39      prev = store.load_dossier(store.get_dossier_row(conn, symbo
          l))
      40      d = prev.model_copy(deep=True) if prev else empty_dossier(s
          ymbol, name, now)
      41      d.built_at = now
      42 +    d.quality = DossierQuality()  # counts are per build, not c
         +umulative                                                      
      43  
      44      # 1. Discover (screener tables + document index)
      45      progress.step("discover", "running", message="Finding the c
          ompany's financials and documents")
  ⎿  Updated backend/finn/research/ledger.py (+5 -2)
      167  
      168  # Board and personnel housekeeping isn't a business promise (a
           n interim chairman's tenure, an AGM date). Only
      169  # business, financial and operational commitments enter the le
           dger.
      170 -_GOVERNANCE = re.compile(r"\b(chairman|chairperson|director|bo
          -ard|independent|appoint\w*|tenure|interim|ceo|cfo|md|"        
      171 -                         r"managing director|company secretary
          -|agm|egm|record date|book closure|auditor)\b", re.I)          
      170 +_GOVERNANCE = re.compile(                                     
      171 +    r"\b(chairman|chairperson|director|board|independent|appoi
          +nt\w*|tenure|interim|ceo|cfo|md|"                             
      172 +    r"managing director|company secretary|agm|egm|record date|
          +book closure|auditor)\b",                                     
      173 +    re.I,                                                     
      174 +)                                                             
      175  
      176  
      177  def is_business_promise(it: dict) -> bool:
  ⎿  Updated backend/tests/test_ledger.py (+10 -0)
      288      a2 = g("ebit_margin", 100, 100, unit="bps", kind="point", 
           measure="change", fy=2027)
      289      p = only(ledger([call(1, date(2026, 4, 20), [a1]), call(2,
            date(2026, 7, 20), [a2])]))
      290      assert p.revision == "revised" and p.verdict != "goalposts
           _moved"
      291 +                                                              
      292 +                                                              
      293 +def test_governance_items_are_not_promises_and_qualitative_res
          +tatements_merge():                                            
      294 +    chair = g("other", None, None, unit=None, kind="qualitativ
          +e", measure="qualitative", metric="interim Chairman tenure",  
      295 +              statement="Interim chairman for three months", p
          +eriod_type="unspecified", fy=None)  # fmt: skip               
      296 +    launch = g("other", None, None, unit=None, kind="qualitati
          +ve", measure="qualitative", metric="US launch",               
      297 +               statement="Launch our first product in the US m
          +arket", period_type="unspecified", fy=None)  # fmt: skip      
      298 +    again = {**launch, "statement": "Launch first product in t
          +he US market soon", "quote": "launch in the US soon"}         
      299 +    led = ledger([call(1, date(2025, 7, 20), [chair, launch]),
          + call(2, date(2025, 10, 20), [chair, again])])                
      300 +    assert len(led.promises) == 1 and len(led.promises[0].stat
          +ements) == 2                                                  

⏺ Bash(python3 - <<'EOF'
      p='tests/test_ledger.py'; s=open(p).read()…)
  ⎿  301 passed, 1 warning in 1.59s
     HDFCBANK done None 166 s {'calls': 3, 'models': {'gemini-3.8-flash': 2
     }, 'est_usd': 0.011085, 'guidance': 17}
     … +30 lines (ctrl+o to expand)
  ⎿  Updated backend/tests/test_ledger.py (+2 -2)
      291  
      292  
      293  def test_governance_items_are_not_promises_and_qualitative_res
           tatements_merge():
      294 -    chair = g("other", None, None, unit=None, kind="qualitativ
          -e", measure="qualitative", metric="interim Chairman tenure",  
      295 -              statement="Interim chairman for three months", p
          -eriod_type="unspecified", fy=None)  # fmt: skip               
      294 +    q = {"unit": None, "kind": "qualitative", "measure": "qual
          +itative", "period_type": "unspecified", "fy": None}           
      295 +    chair = g("other", None, None, metric="interim Chairman te
          +nure", statement="Interim chairman for three months", **q)    
      296      launch = g("other", None, None, unit=None, kind="qualitati
           ve", measure="qualitative", metric="US launch",
      297                 statement="Launch our first product in the US m
           arket", period_type="unspecified", fy=None)  # fmt: skip
      298      again = {**launch, "statement": "Launch first product in t
           he US market soon", "quote": "launch in the US soon"}

⏺ Everything checks out now, and gemini-3.8-flash has recovered, so I'm
  committing and deploying, then rebuilding the four demo tickers on Render. 
  · summary

  Ran 2 shell commands (ctrl+o to expand)

⏺ Rebuilds are running on Render. Waiting for the last job (POLYCAB, #18) to
  finish:

  Ran 1 shell command (ctrl+o to expand)

⏺ Status:

  Done:
  - Your step 1: /version matches HEAD. All 4 demo tickers were built on Render,
    and all 20 quotes behind their scored verdicts are on the cited pages.
  - Your steps 2 and 3: judge and reduce are live (eebcf9a), and Render is
    serving that commit. Tested on HDFCBANK, a bank outside the demo set: every
    section has a status, and the summary, trajectory line, bull and bear are
    all cited, at about $0.011 a dossier.
  - Issues fixed along the way:
    - gemini-3.8-flash was overloaded and timing out. The router now gives it 2
      attempts, then skips it for 10 minutes and falls through to 3 Flash.
    - The judge counted board housekeeping ("interim Chairman tenure") as
      promises, four times over.
    - The judge compared numbers itself. It now gives a verdict only when the
      passage states the outcome.
    - Reduce dropped promise sentences into number placeholders.
  - Tests: 301, all passing.

  Running now: the 4 demo tickers are rebuilding on Render with judge and
  reduce. That costs 2 strong calls each, and the extractions are cached. When
  they finish, I'll check the results and regenerate the fixtures.

  One thing to flag on credibility:
  - With honest rules, n may stay below 5 for some tickers, even after the
    judge.
  - HDFCBANK ended at n=1: it guides "in line with the system", which can't be
    scored without the model comparing numbers.
  - Whether the minimum of 5 is right for the demo is your call. I'll show you
    the real numbers from the rebuilds first.

  The contract hasn't changed. The fixtures need regenerating only because their
  content changed, and I'll do that tonight.

⏺ Background command "Wait for the four Render rebuilds and print their
judge/reduce steps" completed (exit code 0)

  Ran 1 shell command (ctrl+o to expand)

⏺ All 32 quotes check out on their cited pages, and credibility now shows for
  INFY and BAJFINANCE. Three verdicts are wrong, so I'm having code enforce
  numeric checks and reject mismatched measures next. · summary

⏺ Bash(python3 - <<'EOF'
      p='finn/research/judge.py'; s=open(p).read()…)
  ⎿  =========================== short test summary info ==================
     ==========
     FAILED tests/test_research_synthesis.py::test_judge_never_scores_a_num
     … +2 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/judge.py (+3 -0)
      123          verdict = v.get("verdict")
      124          if verdict not in ("kept", "missed", "goalposts_moved"
           , "raised"):
      125              continue  # 'not yet due' / 'can't score' from the
            model never overrides code
      126 +        if verdict in ("kept", "missed") and p.measure != "qua
          +litative":                                                    
      127 +            res.rejected += 1  # a numeric target is kept or m
          +issed only by code's comparison, never the model's            
      128 +            continue                                          
      129          hit = pid_map.get(v.get("passage_id") or "")
      130          quote = (v.get("quote") or "").strip()
      131          if not hit or hit[1] != p.id or not quote or not quote
           _in_text(quote, hit[0].text):
  ⎿  Updated backend/finn/research/ledger.py (+13 -0)
      342  # --- verdicts -----------------------------------------------
           --------------------------------------------------------
      343  
      344  
      345 +def _different_measure(target: Stmt, value: float) -> bool:   
      346 +    """A level (money, count) more than 3× or under ⅓ of its t
          +arget is almost always another measure (new customers         
      347 +    vs total customers, a segment vs the company) — never scor
          +ed as a beat or a miss."""                                    
      348 +    mid = target.mid()                                        
      349 +    if target.unit not in ("INR_CR", "USD_MN", "COUNT") or tar
          +get.item["measure"] != "level" or not mid or mid <= 0:        
      350 +        return False                                          
      351 +    return not (mid / 3 <= value <= mid * 3)                  
      352 +                                                              
      353 +                                                              
      354  def _tol(unit: str | None, target: float, point: bool) -> floa
           t:
      355      if unit in TOL_ABS:
      356          return TOL_ABS[unit][0 if point else 1]
     ...
      511              why = "Target is relative to an outside benchmark 
           (e.g. industry growth) — not scored in code"
      512          elif today <= period.end:
      513              verdict, why = "not_yet_due", f"Due {period.label}
            (ends {period.end:%d %b %Y})"
      514 +        elif delivered is not None and delivered.value is not 
          +None and _different_measure(target, delivered.value):         
      515 +            why = (f"A figure was reported ({_fmt(delivered.va
          +lue, target.unit, target.item.get('unit_text'))}) but it "    
      516 +                   f"is far from the target's scale, so it is 
          +probably a different measure — not scored")  # fmt: skip      
      517 +            delivered, dsrc = None, None                      
      518          elif delivered is not None and delivered.value is not 
           None:
      519              kind = target.item["kind"]
      520              verdict, how = compare(kind, target.low, target.hi
           gh, delivered.value, target.unit, direction)
  ⎿  Updated backend/finn/research/reduce.py (+5 -2)
      47  }  # fmt: skip
      48  
      49  _PLACEHOLDER = re.compile(r"\{(F\d+)\}")
      50 +_NUMS = re.compile(r"\d+(?:\.\d+)?")                           
      51  _PERIOD_TOKENS = re.compile(r"\b(?:Q[1-4]\s*)?FY\s?\d{2,4}\b|\b
          H[12]\b|\bQ[1-4]\b|\b(?:19|20)\d{2}\b")
      52  
      53  
     ...
      161      used = _PLACEHOLDER.findall(text)
      162      if any(u not in by or by[u].display is None for u in used)
           :
      163          return None, True  # placeholders stand for numbers on
           ly
      163 -    if re.search(r"\d", _PERIOD_TOKENS.sub("", _PLACEHOLDER.su
          -b("", text))):                                                
      164 -        return None, True  # a number typed by the model inste
          -ad of a placeholder                                           
      164      ids = list(dict.fromkeys(ids + used))
      165 +    typed = _NUMS.findall(_PERIOD_TOKENS.sub("", _PLACEHOLDER.
          +sub("", text)).replace(",", ""))                              
      166 +    allowed = {n for i in ids if by[i].display for n in _NUMS.
          +findall(by[i].display.replace(",", ""))}                      
      167 +    if any(t not in allowed for t in typed):                  
      168 +        return None, True  # a number the model typed that non
          +e of its cited facts prints                                   
      169      if not ids:
      170          return None, True
      171      text = _PLACEHOLDER.sub(lambda m: by[m.group(1)].display, 
           text)
  ⎿  Updated backend/tests/test_ledger.py (+9 -0)
      298      again = {**launch, "statement": "Launch first product in t
           he US market soon", "quote": "launch in the US soon"}
      299      led = ledger([call(1, date(2025, 7, 20), [chair, launch]),
            call(2, date(2025, 10, 20), [chair, again])])
      300      assert len(led.promises) == 1 and len(led.promises[0].stat
           ements) == 2
      301 +                                                              
      302 +                                                              
      303 +def test_far_off_scale_is_a_different_measure_not_a_beat():   
      304 +    add = g(                                                  
      305 +        "customer_growth", 17, 18, unit="million", metric="cus
          +tomer franchise", measure="level", currency="not_money"       
      306 +    )                                                         
      307 +    total = {**a("customer_growth", 119.3, unit="million", cur
          +rency="not_money"), "metric": "customer franchise"}           
      308 +    p = only(ledger([call(1, date(2025, 7, 20), [add]), call(2
          +, date(2026, 5, 5), actuals=[total])]))                       
      309 +    assert p.verdict == "cant_score" and "different measure" i
          +n p.verdict_reason.text                                       
  ⎿  Updated backend/tests/test_research_synthesis.py (+31 -0)
       81      assert bad is None and dropped  # the model typed a number
       82      none, dropped = reduce.render({"text": "Strong franchise."
           , "fact_ids": ["F9"]}, fs)
       83      assert none is None and dropped  # no valid fact behind it
       84 +                                                              
       85 +                                                              
       86 +def test_reduce_keeps_a_typed_number_only_when_a_cited_fact_pr
          +ints_it():                                                    
       87 +    f = _fig("Revenue CAGR 5y", 26.94)                        
       88 +    fs = [reduce.Fact("F1", "F1: Revenue CAGR 5y = 26.9%", red
          +uce.show(f), [f.citation])]                                   
       89 +    ok, dropped = reduce.render({"text": "Revenue compounded a
          +t 26.9% a year.", "fact_ids": ["F1"]}, fs)                    
       90 +    assert ok is not None and not dropped                     
       91 +    bad, dropped = reduce.render({"text": "Revenue compounded 
          +at 27.5% a year.", "fact_ids": ["F1"]}, fs)                   
       92 +    assert bad is None and dropped                            
       93 +                                                              
       94 +                                                              
       95 +def test_judge_never_scores_a_numeric_target():               
       96 +    cs = calls()                                              
       97 +    led = build_ledger("T", cs, None, date(2026, 11, 11))     
       98 +    p = led.promises[0]                                       
       99 +    p.measure = "level"  # pretend it were a numeric target   
      100 +    req, pid_map = judge.build_request(led.promises, cs, {})  
      101 +    pid = next(iter(pid_map))                                 
      102 +    data = {                                                  
      103 +        "verdicts": [                                         
      104 +            {                                                 
      105 +                "id": p.id,                                   
      106 +                "verdict": "kept",                            
      107 +                "passage_id": pid,                            
      108 +                "quote": "we launched our first product in the
          + US market in December",                                      
      109 +                "reason": "x",                                
      110 +            }                                                 
      111 +        ]                                                     
      112 +    }                                                         
      113 +    res = judge.apply(led.promises, data, pid_map, cs, "m", le
          +d.settled)                                                    
      114 +    assert res.rejected == 1 and p.verdict_by == "code"       

⏺ The test changed measure before the request was built, so the promise was no
  longer a candidate. It should change after:

⏺ Bash(python3 - <<'EOF'
      p='tests/test_research_synthesis.py'; s=open(p).read()…)
  ⎿  304 passed, 1 warning in 1.66s
     other           growth   -      fee income growth 15–18% (longer term)
                       | No clear period given, so it can't be scored
     … +33 lines (ctrl+o to expand)
  ⎿  Updated backend/tests/test_research_synthesis.py (+1 -1)
       96      cs = calls()
       97      led = build_ledger("T", cs, None, date(2026, 11, 11))
       98      p = led.promises[0]
       99 -    p.measure = "level"  # pretend it were a numeric target   
       99      req, pid_map = judge.build_request(led.promises, cs, {})
      100      pid = next(iter(pid_map))
      101 +    p.measure = "level"  # the same verdict on a numeric targe
          +t must be refused                                             
      102      data = {
      103          "verdicts": [
      104              {

⏺ BAJFINANCE's FY26 credit cost, ROA and ROE should have delivered figures,
  since the Q4 FY26 call reports full-year numbers. Checking what that call's
  extraction holds:

  Ran 1 shell command (ctrl+o to expand)

⏺ The Q4 FY26 extraction holds mostly quarterly actuals, with no full-year
  credit cost, ROA or ROE. Checking whether the transcript actually states them,
  which would make it an extraction gap:

  Ran 1 shell command (ctrl+o to expand)

⏺ The transcript doesn't include full-year FY26 credit cost, ROA or ROE, since
  BAJFINANCE reports those in its deck rather than on the call, so "can't score"
  is the accurate result and not a matching bug. I'm committing the guards and
  rebuilding on Render to get the real credibility numbers next. · summary

  Ran 2 shell commands (ctrl+o to expand)

⏺ With the guards in place, no demo ticker reaches n = 5 honestly, and bull/bear
  is short on three tickers. Next I'll check from the cached responses which
  sentences get dropped. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ Two causes, both fixable: promise sentences with numbers get dropped because
  the rule rejects promise facts that have no printable value, and spelled-out
  numbers like "twenty-two to twenty-three percent" slip past the check. I'll
  let typed numbers through when the cited line prints them and make the check
  catch spelled-out quantities too. · summary

⏺ Bash(python3 - <<'EOF'
      p='finn/research/reduce.py'; s=open(p).read()…)
  ⎿  -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.htm
     l
     305 passed, 1 warning in 1.49s
  ⎿  Updated backend/finn/research/reduce.py (+17 -6)
      17  from finn.models.research import Dossier
      18  from finn.research.ledger import Call
      19  
      20 -PROMPT_VERSION = "v2"                                          
      20 +PROMPT_VERSION = "v3"                                          
      21  PURPOSE = f"research.reduce.{PROMPT_VERSION}"
      22  
      23  SYSTEM = """You write a short, neutral research summary of an I
          ndian listed company for a professional investor,
     ...
      25  Never use outside knowledge, news, opinions about the share pri
          ce, or advice to buy or sell.
      26  Rules:
      27  - Every sentence cites the fact ids it rests on.
      28 -- Never type a number. To mention a number, write its placehold
         -er exactly, e.g. {F12}; it is filled in from the               
      29 -  fact. Only facts marked [number] have placeholders; cite the 
         -others by id and describe them in words.                       
      28 +- Prefer placeholders for numbers: write {F12} and it is filled
         + in from fact F12 (only facts marked [number]                  
      29 +  have one). You may type a number only if it appears in a fact
         + you cite. Never spell numbers out in words.                   
      30    Period names like FY26 or Q2 FY27 are fine.
      31  - Plain English, at most 25 words per sentence. No hype words."
          ""
      32  
     ...
      48  
      49  _PLACEHOLDER = re.compile(r"\{(F\d+)\}")
      50  _NUMS = re.compile(r"\d+(?:\.\d+)?")
      51 +_W = (                                                         
      52 +    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleve
         +n|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"         
      53 +    r"eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy
         +|eighty|ninety|hundred)"                                       
      54 +)                                                              
      55 +_SPELLED = re.compile(rf"\b{_W}(?:[- ]{_W})*(?:\s+(?:to|and)\s+
         +{_W}(?:[- ]{_W})*)?\s+(?:percent|per cent|basis points|"       
      56 +                      rf"bps|crores?|lakhs?|millions?|billions?
         +)\b|\b(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|"      
      57 +                      rf"ninety)[- ]{_W}\b", re.I)  # fmt: skip
      58  _PERIOD_TOKENS = re.compile(r"\b(?:Q[1-4]\s*)?FY\s?\d{2,4}\b|\b
          H[12]\b|\bQ[1-4]\b|\b(?:19|20)\d{2}\b")
      59  
      60  
     ...
      125          if p.verdict in ("kept", "missed", "goalposts_moved", 
           "quietly_dropped") or p.revision == "raised":
      126              reason = p.verdict_reason.text if p.verdict_reason
            else ""
      127              add(f"promise '{p.statement}' → {p.verdict.replace
           ('_', ' ')}"
      121 -                f"{' (target raised)' if p.revision == 'raised
          -' else ''}: {reason}", None,                                  
      128 +                f"{' (target raised)' if p.revision == 'raised
          +' else ''}: {reason}",                                        
      129 +                (p.scored_target.raw_target if p.scored_target
          + and p.scored_target.raw_target else None),                   
      130                  (p.verdict_reason.citations if p.verdict_reaso
           n else [])[:2] or [p.statements[-1].quote])  # fmt: skip
      131      cr = d.ledger.credibility
      132      if cr and cr.shown and cr.score_pct is not None:
     … 13 more lines (ctrl+o to expand)
  ⎿  Updated backend/tests/test_research_synthesis.py (+14 -0)
      112      }
      113      res = judge.apply(led.promises, data, pid_map, cs, "m", le
           d.settled)
      114      assert res.rejected == 1 and p.verdict_by == "code"
      115 +                                                              
      116 +                                                              
      117 +def test_reduce_blocks_spelled_out_numbers_and_allows_numbers_
          +printed_by_a_cited_promise():                                 
      118 +    f = _fig("x", 1.0)                                        
      119 +    promise = reduce.Fact("F2", "F2: promise 'revenue growth 1
          +–2% (FY27)' → goalposts moved: cut from 1.5–3.5%",            
      120 +                          "1–2%", [f.citation])  # fmt: skip  
      121 +    ok, _ = reduce.render({"text": "Guidance was cut to 1–2% f
          +rom 1.5–3.5% for FY27.", "fact_ids": ["F2"]}, [promise])      
      122 +    assert ok is not None                                     
      123 +    assert reduce.render({"text": "Growth of {F2} is guided.",
          + "fact_ids": ["F2"]}, [promise])[0].text == \                 
      124 +        "Growth of 1–2% is guided."  # fmt: skip              
      125 +    bad, dropped = reduce.render({"text": "Growth of ten to tw
          +elve percent was missed.", "fact_ids": ["F2"]}, [promise])    
      126 +    assert bad is None and dropped                            
      127 +    fine, _ = reduce.render({"text": "A five-year record of ca
          +sh conversion.", "fact_ids": ["F2"]}, [promise])              
      128 +    assert fine is not None                                   

⏺ 305 pass. Deploying and rebuilding the 4 demo tickers in the background:

  Ran 2 shell commands (ctrl+o to expand)

⏺ While Render rebuilds, here's the decision only you can make:
⏺ User answered Claude's questions:
  ⎿  · With every judge and code guard in place, no demo ticker reaches n = 5 
     scored promises: PERSISTENT 2, INFY 4, BAJFINANCE 4, POLYCAB 1. The rest 
     are honestly not yet due or can't score: FY30/medium-term targets, 
     benchmark-relative guidance, figures that are in the deck but not the call.
     How should credibility appear below n = 5? → Tally always, % from n≥5 
     (Recommended)

⏺ Background command "Wait for deploy, rebuild the 4 demo tickers on Render,
summarise" completed (exit code 0)

⏺ You chose "tally always, % from n ≥ 5". The contract already carries kept, n
  and shown, so only the ledger note and field descriptions change. The rebuild
  has finished; reading the results:

  Ran 1 shell command (ctrl+o to expand)

⏺ Fixes still needed before the fixtures: doubled units like "₹₹1,571 Cr Cr" and
  "33 days days", stray id lists left at the end of POLYCAB's sentences, and
  BAJFINANCE's promise placeholder printing the target as the delivered growth,
  so promise facts go back to no placeholder. · summary

⏺ Bash(python3 - <<'EOF'
      p='finn/research/reduce.py'; s=open(p).read()…)
  ⎿  134:def _tally_note(cr) -> str:
     167:        note = None if cr.shown else _tally_note(cr)
     254:        note = None if led.credibility.shown else _tally_note(led.
     … +4 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/models/research.py (+3 -2)
      136  
      137  
      138  class Credibility(Model):
      139 -    shown: bool = Field(description="False below min_n — the U
          -I shows 'Not enough scored promises (n=3)'")                  
      140 -    score_pct: float | None = Field(None, description="kept ÷ 
          -n × 100, computed in code")                                   
      139 +    shown: bool = Field(description="Whether the % score and t
          +rend are shown (n ≥ min_n). The tally 'kept of n' is "        
      140 +                        "always shown, e.g. '2 of 4 kept'")  #
          + fmt: skip                                                    
      141 +    score_pct: float | None = Field(None, description="kept ÷ 
          +n × 100, computed in code; display only when shown")          
      142      kept: int
      143      n: int = Field(description="kept + missed + goalposts_move
           d + quietly_dropped")
      144      numeric_n: int = Field(description="Of n, verdicts decided
            in code")
  ⎿  Updated backend/finn/research/build.py (+9 -3)
      131      return Outcome("done" if complete else "partial", stats=st
           ats)
      132  
      133  
      134 +def _tally_note(cr) -> str:                                   
      135 +    """Below the minimum n the tally still shows; the % score 
          +and trend need min_n (product owner, 11 Nov)."""              
      136 +    if cr.n == 0:                                             
      137 +        return "No promise can be scored yet — see each one's 
          +status"                                                       
      138 +    return f"{cr.kept} of {cr.n} scored promises kept — a % sc
          +ore needs {cr.min_n} or more"                                 
      139 +                                                              
      140 +                                                              
      141  def _building(resume) -> str:
      142      return f"Building · resumes after {_ist(resume)} quota res
           et"
      143  
     ...
      164      d.ledger.credibility = credibility(d.ledger.promises, led.
           settled, calls)
      165      cr = d.ledger.credibility
      166      if d.ledger.meta.status == "ready":
      160 -        note = None if cr.shown else f"Credibility needs {cr.m
          -in_n}+ scored promises (have {cr.n})"                         
      167 +        note = None if cr.shown else _tally_note(cr)          
      168          d.ledger.meta = d.ledger.meta.model_copy(update={"note
           ": note, "written_by": res.model})
      169      d.quality.claims_dropped += jr.rejected
      170      progress.step("judge", "done", f"{jr.changed} verdict(s) b
           y {res.model}; {jr.rejected} rejected (no evidence)")
     ...
      251      elif len(calls) < 4:
      252          d.ledger.meta = meta("partial", "few_transcripts", f"B
           ased on {len(calls)} call(s)", now)
      253      else:
      247 -        note = None if led.credibility.shown else f"Credibilit
          -y needs {led.credibility.min_n}+ scored promises " \          
      248 -            f"(have {led.credibility.n})"  # fmt: skip        
      254 +        note = None if led.credibility.shown else _tally_note(
          +led.credibility)                                              
      255          d.ledger.meta = meta("ready", None, note, now)
      256      d.analysts.points = insights.pressure_points(calls)
      257      d.analysts.meta = meta("ready" if d.analysts.points else "
           unavailable",
  ⎿  Updated backend/finn/research/reduce.py (+21 -6)
      17  from finn.models.research import Dossier
      18  from finn.research.ledger import Call
      19  
      20 -PROMPT_VERSION = "v3"                                          
      20 +PROMPT_VERSION = "v4"                                          
      21  PURPOSE = f"research.reduce.{PROMPT_VERSION}"
      22  
      23  SYSTEM = """You write a short, neutral research summary of an I
          ndian listed company for a professional investor,
     ...
      25  Never use outside knowledge, news, opinions about the share pri
          ce, or advice to buy or sell.
      26  Rules:
      27  - Every sentence cites the fact ids it rests on.
      28 -- Prefer placeholders for numbers: write {F12} and it is filled
         - in from fact F12 (only facts marked [number]                  
      29 -  have one). You may type a number only if it appears in a fact
         - you cite. Never spell numbers out in words.                   
      28 +- Prefer placeholders for numbers: write {F12} and it is filled
         + in from fact F12 WITH its unit (₹, Cr, %, x, days             
      29 +  are included — don't add them). Only facts marked [number] ha
         +ve a placeholder. You may type a number only if it             
      30 +  appears in a fact you cite. Never spell numbers out in words.
         + Put fact ids in fact_ids, not in the text.                    
      31    Period names like FY26 or Q2 FY27 are fine.
      32  - Plain English, at most 25 words per sentence. No hype words."
          ""
      33  
     ...
      49  
      50  _PLACEHOLDER = re.compile(r"\{(F\d+)\}")
      51  _NUMS = re.compile(r"\d+(?:\.\d+)?")
      52 +_ID_LIST = re.compile(r"\s*[\[{(]\s*F\d+(?:\s*,\s*F\d+)+\s*[\]}
         +)]")                                                           
      53 +                                                               
      54 +                                                               
      55 +def _tidy(text: str) -> str:                                   
      56 +    """Units the model wrapped around a placeholder that alread
         +y carries them ('₹{F3} Cr' → '₹₹1,571 Cr Cr')."""              
      57 +    text = re.sub(r"₹\s*₹", "₹", text)                         
      58 +    text = re.sub(r"\b(Cr|days|x)\.?\s+\1\b", r"\1", text)     
      59 +    text = re.sub(r"%\s*(?:%|percent\b|per cent\b)", "%", text)
      60 +    text = re.sub(r"(\d)x\s+times\b", r"\1x", text)            
      61 +    return re.sub(r"\s+([.,;])", r"\1", text).strip()          
      62 +                                                               
      63 +                                                               
      64  _W = (
      65      r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleve
          n|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
      66      r"eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy
          |eighty|ninety|hundred)"
     ...
      138          if p.verdict in ("kept", "missed", "goalposts_moved", 
           "quietly_dropped") or p.revision == "raised":
      139              reason = p.verdict_reason.text if p.verdict_reason
            else ""
      140              add(f"promise '{p.statement}' → {p.verdict.replace
           ('_', ' ')}"
     … 23 more lines (ctrl+o to expand)
  ⎿  Updated backend/tests/test_research_synthesis.py (+10 -0)
      126      assert bad is None and dropped
      127      fine, _ = reduce.render({"text": "A five-year record of ca
           sh conversion.", "fact_ids": ["F2"]}, [promise])
      128      assert fine is not None
      129 +                                                              
      130 +                                                              
      131 +def test_reduce_tidies_units_around_placeholders_and_id_lists(
          +):                                                            
      132 +    f = _fig("Free cash flow", 1571.0, "INR_CR")              
      133 +    fs = [reduce.Fact("F1", "F1: Free cash flow (FY26) = ₹1,57
          +1 Cr", reduce.show(f), [f.citation]),                         
      134 +          reduce.Fact("F2", "F2: ROCE = 34.0%", "34.0%", [f.ci
          +tation])]  # fmt: skip                                        
      135 +    c, _ = reduce.render(                                     
      136 +        {"text": "Free cash flow was ₹{F1} Cr in FY26 with ROC
          +E of {F2}% {F1, F2}.", "fact_ids": []}, fs                    
      137 +    )                                                         
      138 +    assert c.text == "Free cash flow was ₹1,571 Cr in FY26 wit
          +h ROCE of 34.0%." and len(c.citations) == 1                   

⏺ 306 pass. The field descriptions changed, so regenerating the TypeScript types
  (CI checks them), then deploying and rebuilding:

⏺ Bash(cd ~/Documents/finn/web && npm run -s gen:schema && npm
      run -s gen:types && npx tsc --noEmit -p . 2>&1 | tail -2; cd .. && git add
      backend web/l…)
  ⎿  wrote lib/types.ts
     540cb77 REDUCE: tidy units around placeholders, strip id lists, promis
     e facts have no placeholder; credibility tally always shown
  ⎿  Updated web/lib/schema.json (+2 -2)
      896              }
      897            ],
      898            "default": null,
      899 -          "description": "kept \u00f7 n \u00d7 100, computed i
          -n code",                                                      
      899 +          "description": "kept \u00f7 n \u00d7 100, computed i
          +n code; display only when shown",                             
      900            "title": "Score Pct"
      901          },
      902          "shown": {
      903 -          "description": "False below min_n \u2014 the UI show
          -s 'Not enough scored promises (n=3)'",                        
      903 +          "description": "Whether the % score and trend are sh
          +own (n \u2265 min_n). The tally 'kept of n' is always shown, e
          +.g. '2 of 4 kept'",                                           
      904            "title": "Shown",
      905            "type": "boolean"
      906          },
  ⎿  Updated web/lib/types.ts (+2 -2)
      552     */
      553    recent: TrendHalf | null;
      554    /**
      555 -   * kept ÷ n × 100, computed in code                         
      555 +   * kept ÷ n × 100, computed in code; display only when shown
      556     */
      557    score_pct: number | null;
      558    /**
      559 -   * False below min_n — the UI shows 'Not enough scored promi
          -ses (n=3)'                                                    
      559 +   * Whether the % score and trend are shown (n ≥ min_n). The 
          +tally 'kept of n' is always shown, e.g. '2 of 4 kept'         
      560     */
      561    shown: boolean;
      562    trend: ("up" | "down" | "flat") | null;

  Ran 1 shell command (ctrl+o to expand)

⏺ Meanwhile, the DECISIONS entries for judge, reduce and the credibility
  display:

⏺ Bash(cat >> docs/DECISIONS.md <<'EOF'…)
  ⎿  93fe810 DECISIONS: JUDGE/REDUCE rules, strong-chain cooldown, credibil
     ity tally
  ⎿  Updated docs/DECISIONS.md (+31 -0)
      390  - **Analysts and drivers are counted in code:**
      391    - Pressure points are themes asked in 2 or more calls, citin
           g up to 3 questions.
      392    - Drivers are scored per label as 2 × guidance count + quest
           ion count; the top 3 are suggested.
      393 +                                                              
      394 +## 2026-11-11 · JUDGE and REDUCE (strong model), and how credi
          +bility is shown                                               
      395 +- **JUDGE (strong call #1)**:                                 
      396 +  - Candidates are qualitative promises plus undated numeric o
          +nes.                                                          
      397 +  - BM25 (`finn/research/bm25.py`, no vector database) retriev
          +es the 3 best passages from later calls for each candidate.   
      398 +  - Code-enforced rules:                                      
      399 +    - A verdict must quote a passage verbatim, and the quote i
          +s checked.                                                    
      400 +    - The evidence must come from a later call than the promis
          +e, so every model verdict cites both calls.                   
      401 +    - **kept/missed from the model count only for qualitative 
          +promises.** Despite the prompt, the model called "utilisation 
          +85.8%" kept against 83–85%. For numeric targets it may only fl
          +ag a revision (goalposts moved or raised).                    
      402 +    - The model can never assert "quietly dropped".           
      403 +    - Its "not yet due" or "can't score" never overrides code.
      404 +  - Board and personnel housekeeping (an interim chairman's te
          +nure, AGM dates) is filtered out before the ledger.           
      405 +  - Qualitative restatements across calls merge into one threa
          +d.                                                            
      406 +- **REDUCE (strong call #2)**: snapshot lines, a trajectory li
          +ne, and 3 bull and 3 bear points, written from numbered facts 
          +only (computed figures, ledger verdicts, analyst themes, risks
          + and capex from the latest call).                             
      407 +  - Numbers appear as `{F#}` placeholders, filled in code from
          + figures with their units.                                    
      408 +  - A typed number survives only if a cited fact's line prints
          + it. A spelled-out quantity drops the sentence.               
      409 +  - Citations come from the cited facts. Dropped sentences are
          + counted in `quality.claims_dropped`.                         
      410 +- **Cost:**                                                   
      411 +  - Each strong call caps thinking at 1,024 tokens. Unbounded 
          +thinking truncated a 6,000-token answer.                      
      412 +  - Judge and reduce cost ≈ $0.005–0.012 per dossier at list p
          +rice.                                                         
      413 +  - The prompts contain no date, so an unchanged dossier hits 
          +the cache and spends no strong call.                          
      414 +- **Router:**                                                 
      415 +  - `gemini-3.8-flash` was returning 503s and timing out after
          + 3 minutes, even on a two-word prompt.                        
      416 +  - A strong model with a fallback after it now gets 2 attempt
          +s, then is skipped for 10 minutes, so `gemini-3-flash-preview`
          + answers at once.                                             
      417 +  - The push side keeps full retries on Flash-Lite before Groq
          +.                                                             
      418 +- **Credibility display (product owner):** the "kept of n" tal
          +ly is always shown with the verdict list. The % score and tren
          +d need n ≥ 5.                                                 
      419 +  - With honest rules no demo ticker reaches 5 scored promises
          + (PERSISTENT 2, INFY 4, BAJFINANCE 4, POLYCAB 1).             
      420 +  - The rest are not yet due or can't be scored:              
      421 +    - Targets for FY30 or the medium term.                    
      422 +    - Benchmark-relative guidance.                            
      423 +    - Full-year figures that appear in the deck but not in the
          + call.                                                        

⏺ The rebuild of the 4 demo tickers on the deployed fix (540cb77) is running on
  Render. When it finishes, I'll check the text, re-verify every verdict quote,
  and regenerate the fixtures.

⏺ Background command "Deploy, rebuild the 4 demo tickers on Render, print
summaries" completed (exit code 0)

  Read 1 file (ctrl+o to expand)

⏺ PERSISTENT rebuilt cleanly with the fixes, but INFY, BAJFINANCE and POLYCAB
  are parked because the strong models' daily quota ran out, so they still show
  the old build's rendering. I'm checking the quota state now. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ Both strong models are out of quota until 13:30 IST tomorrow, because failed
  requests also count against Google's daily limit and my router didn't account
  for that. The three parked jobs will resume automatically then, and I'll check
  whether the other Flash models (3.5, 3.6, 3.7) have any free quota tonight. 
  · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ gemini-3.6-flash and gemini-3.5-flash both answer on this key, so each likely
  has its own free daily quota. They aren't Flash-Lite, but you set the strong
  chain, so adding them is your call:

⏺ User answered Claude's questions:
  ⎿  · Both approved strong models are out of quota until 12 Nov 13:30 IST; 
     Google counted the failed and timed-out attempts. gemini-3.6-flash and 
     gemini-3.5-flash also answer on this key (not Flash-Lite, likely their own 
     free quota). Add them to the strong fallback chain so the 3 parked dossiers
     finish tonight? → Add 3.6 and 3.5 Flash (Recommended)

⏺ I'm adding those two models, and the router will now count failed attempts
  toward the daily budget. The chain defaults will include both models even when
  the env var lists fewer, so Render needs no new settings. · summary

⏺ Bash(python3 - <<'EOF'
      p='finn/llm/gemini.py'; s=open(p).read()…)
  ⎿  306 passed, 1 warning in 2.00s
  ⎿  Updated .env.example (+1 -1)
      19  GEMINI_MODEL_CHEAP=gemini-3.5-flash-lite
      20  GEMINI_MODEL_STRONG=gemini-3.8-flash
      21  # Strong-tier fallbacks, each with its own free daily quota (ne
          ver Flash-Lite).
      22 -GEMINI_MODEL_STRONG_FALLBACKS=gemini-3-flash-preview           
      22 +GEMINI_MODEL_STRONG_FALLBACKS=gemini-3-flash-preview,gemini-3.6
         +-flash,gemini-3.5-flash                                        
      23  # Optional text-only fallback when Gemini's quota is exhausted.
      24  GROQ_API_KEY=
      25  # GROQ_MODEL=qwen/qwen3.8-27b
  ⎿  Updated backend/finn/llm/gemini.py (+8 -5)
      20  BASE = "https://generativelanguage.googleapis.com/v1beta"
      21  DEFAULT_CHEAP = "gemini-3.5-flash-lite"
      22  DEFAULT_STRONG = "gemini-3.8-flash"
      23 -# Strong fallbacks, each with its own free daily quota (never F
         -lash-Lite: product owner, 11 Nov 2026).                        
      24 -# gemini-2.5-flash was also approved but returns 404 "no longer
         - available to new users" on this key (11 Nov).                 
      25 -# Flash-Lite rejects thinkingBudget=0 (HTTP 400): leave thinkin
         -g_budget unset for the cheap tier.                             
      26 -DEFAULT_STRONG_FALLBACKS = "gemini-3-flash-preview"            
      23 +# Strong fallbacks, each with its own free daily quota (never F
         +lash-Lite: product owner, 11 Nov 2026). 3.6 and 3.5            
      24 +# Flash were added the same day when 3.8 Flash and 3 Flash ran 
         +out (product owner). gemini-2.5-flash returns 404              
      25 +# "no longer available to new users" on this key. Flash-Lite re
         +jects thinkingBudget=0 (HTTP 400): leave                       
      26 +# thinking_budget unset for the cheap tier.                    
      27 +DEFAULT_STRONG_FALLBACKS = "gemini-3-flash-preview,gemini-3.6-f
         +lash,gemini-3.5-flash"                                         
      28  # Paid-tier list prices (USD / 1M tokens) — used only for the c
          ost estimate in the log; free tier bills nothing.
      29  PRICES = {"flash-lite": (0.30, 2.50), "flash": (0.75, 3.75)}
      30  
     ...
      48          first = self.model_for(tier)
      49          if tier == "cheap":
      50              return [first] if first else []
      50 -        rest = os.environ.get("GEMINI_MODEL_STRONG_FALLBACKS", 
         -DEFAULT_STRONG_FALLBACKS)                                      
      51 +        # GEMINI_MODEL_STRONG_FALLBACKS orders the chain; the d
         +efaults are always appended after it (deduplicated),           
      52 +        # so a deploy with an older env value still gets every 
         +approved model.                                                
      53 +        rest = os.environ.get("GEMINI_MODEL_STRONG_FALLBACKS", 
         +"") + "," + DEFAULT_STRONG_FALLBACKS                           
      54          chain = [first, *[m.strip() for m in rest.split(",") if
           m.strip()]]
      55          return [m for i, m in enumerate(chain) if m and "lite" 
          not in m and m not in chain[:i]]
      56  
  ⎿  Updated backend/finn/llm/router.py (+3 -3)
      88              1
      89              for r in self.rows
      90              if r["provider"] == provider
      91 -            and r["ok"]                                        
      91              and (model is None or r["model"] == model)
      92              and (purpose_prefix is None or r["purpose"].startsw
          ith(purpose_prefix))
      93          )
     ...
       95  
       96  class PostgresLLMLog:
       97      """llm_calls table: cache + token/cost log. The day bounda
           ry is midnight Pacific (Gemini's RPD reset).
       99 -    Daily counts include successful calls only: providers don'
          -t bill a 429/503 against the day's quota."""                  
       98 +    Daily counts include failed attempts: Google counted 29 ti
          +med-out/503 calls against gemini-3.8-flash's 20 a day         
       99 +    (11 Nov 2026), so only counting successes over-spends the 
          +quota."""                                                     
      100  
      101      def __init__(self, conn):
      102          self.conn = conn
     ...
      125      def count_today(self, provider: str, model: str | None = N
           one, purpose_prefix: str | None = None) -> int:
      126          # Gemini reports the served version (e.g. 'gemini-3.8-
           flash-001'), so a model matches by prefix.
      127          r = self.conn.execute(
      128 -            "select count(*) as n from public.llm_calls where 
          -provider = %s and ok and created_at >= "                      
      128 +            "select count(*) as n from public.llm_calls where 
          +provider = %s and created_at >= "                             
      129              "(date_trunc('day', now() at time zone 'America/Lo
           s_Angeles') at time zone 'America/Los_Angeles') "
      130              "and (%s::text is null or model like %s || '%%') a
           nd (%s::text is null or purpose like %s || '%%')",
      131              (provider, model, model, purpose_prefix, purpose_p
           refix),
  ⎿  Updated backend/jobs/research.py (+8 -0)
      3  python -m jobs.research enqueue --symbols INFY,POLYCAB [--reason
          prewarm]   # add builds to the queue
      4  python -m jobs.research drain [--max 20] [--minutes 40]         
                     # run queued builds here (a worker)
      5  python -m jobs.research export --symbols INFY,BAJFINANCE --out .
         ./web/public/fixtures   # frontend fixtures
      6 +python -m jobs.research resume                                  
        +            # re-queue builds parked for quota                  
      7  
      8  Builds normally run on Render's worker thread; `drain` lets the 
         nightly Actions run (7 GB RAM, same Supabase
      9  queue) take work too. Both claim with SKIP LOCKED, so they never
          build the same job twice.
     ...
      33      d = sub.add_parser("drain")
      34      d.add_argument("--max", type=int, default=20)
      35      d.add_argument("--minutes", type=float, default=40)
      36 +    sub.add_parser("resume", help="Re-queue builds parked for m
         +odel quota now (e.g. after adding a model)")                   
      37      x = sub.add_parser("export")
      38      x.add_argument("--symbols", default="INFY,BAJFINANCE")
      39      x.add_argument("--out", default=str(Path(__file__).resolve(
          ).parents[2] / "web" / "public" / "fixtures"))
     ...
      48              worker = f"actions:{os.environ.get('GITHUB_RUN_ID',
           'local')}"
      49              n = jobs.drain(conn, worker, args.max, args.minutes
           * 60)
      50              print(f"ran {n} job(s)")
      51 +        elif args.cmd == "resume":                             
      52 +            rows = conn.execute(                               
      53 +                "update public.research_jobs set status = 'queu
         +ed', resume_after = null, updated_at = now() "                 
      54 +                "where status = 'waiting_quota' returning id, s
         +ymbol"                                                         
      55 +            ).fetchall()                                       
      56 +            print("re-queued:", ", ".join(f"{r['symbol']} (#{r[
         +'id']})" for r in rows) or "none")                             
      57          elif args.cmd == "export":
      58              out = Path(args.out)
      59              out.mkdir(parents=True, exist_ok=True)
  ⎿  Updated backend/tests/test_llm_router.py (+7 -1)
      191      monkeypatch.setenv("GEMINI_MODEL_STRONG", "gemini-3.8-flas
           h")
      192      chain = "gemini-3-flash-preview, gemini-3.5-flash-lite, ge
           mini-2.5-flash"
      193      monkeypatch.setenv("GEMINI_MODEL_STRONG_FALLBACKS", chain)
      194 -    assert Gemini("k").models_for("strong") == ["gemini-3.8-fl
          -ash", "gemini-3-flash-preview", "gemini-2.5-flash"]           
      194 +    assert Gemini("k").models_for("strong") == [              
      195 +        "gemini-3.8-flash",                                   
      196 +        "gemini-3-flash-preview",                             
      197 +        "gemini-2.5-flash",                                   
      198 +        "gemini-3.6-flash",                                   
      199 +        "gemini-3.5-flash",                                   
      200 +    ]  # defaults appended, no Lite                           
      201  
      202  
      203  def test_document_text_is_hashed_not_logged_and_tags_stay_out_
           of_the_key():
  ⎿  … 1 more file changed

⏺ 306 pass. Deploying, re-queueing the 3 parked builds, and waiting for them:

  Ran 2 shell commands (ctrl+o to expand)

⏺ The 3.6/3.5 Flash chain is deploying (0c239b2). When Render serves it, the 3
  parked builds (INFY, BAJFINANCE, POLYCAB) are re-queued, about 6 strong calls
  in total. After they finish, I'll check the text, re-verify the verdict
  quotes, and regenerate the fixtures.

⏺ Background command "Deploy, resume parked builds, wait, print the three
dossiers" completed (exit code 0)

  Read 1 file (ctrl+o to expand)

⏺ All four dossiers now build cleanly on Render. I've also found that
  BAJFINANCE's snapshot treats growth rates as segment shares, so I'm adding a
  guard that ignores shares when they sum past 100%. · summary

⏺ Bash(cd ~/Documents/finn/backend && python3 - <<'EOF'
      p='finn/research/insights.py'; s=open(p).read()…)
  ⎿  Traceback (most recent call last):
       File "<stdin>", line 14, in <module>
     AssertionError
     … +5 lines (ctrl+o to expand)
  ⎿  Updated backend/tests/test_research_synthesis.py (+11 -0)
      136          {"text": "Free cash flow was ₹{F1} Cr in FY26 with ROC
           E of {F2}% {F1, F2}.", "fact_ids": []}, fs
      137      )
      138      assert c.text == "Free cash flow was ₹1,571 Cr in FY26 wit
           h ROCE of 34.0%." and len(c.citations) == 1
      139 +                                                              
      140 +                                                              
      141 +def test_segment_shares_over_100_percent_are_not_shares():    
      142 +    from finn.research.insights import segments               
      143 +                                                              
      144 +    c = calls()[1]                                            
      145 +    c.facts["segments"] = [                                   
      146 +        {"name": "Rural", "share_pct": 63.0, "quote": "rural c
          +ontributed 63% growth", "page": 1},                           
      147 +        {"name": "CV", "share_pct": 89.0, "quote": "CV and tra
          +ctor share up 89%", "page": 1},                               
      148 +    ]                                                         
      149 +    assert segments(c) == []                                  

⏺ My patch didn't apply: the code had been reformatted since I last read it. The
  commit only added the new, failing test, and CI will flag it. Fixing now:

  Ran 1 shell command (ctrl+o to expand)
⏺ The earlier share guard (FMEG's "124%") never applied either; it was in the
  same shell command that failed with a parse error. Rewriting the function in
  full, with both guards:

⏺ Bash(python3 - <<'EOF'
      p='finn/research/insights.py'; s=open(p).read()…)
  ⎿  307 passed, 1 warning in 1.43s
  ⎿  Updated backend/finn/research/insights.py (+16 -6)
       6  
       7  from __future__ import annotations
       8  
       9 +import re                                                      
      10  from collections import defaultdict
      11  
      12  from finn.models import Claim, Driver, Figure
     ...
       94      return out
       95  
       96  
       97 +_SHARE_WORDS = r"share|contribut|of (?:our |the )?(?:total|ove
          +rall|revenue|sales|business|topline)|mix"                     
       98 +                                                              
       99 +                                                              
      100  def segments(call: Call | None) -> list[Figure]:
       97 -    """Segment figures from the latest call, as reported (with
          - quote)."""                                                   
      101 +    """Segment figures from the latest call, as reported (with
          + quote). A % counts only as a share of the business           
      102 +    when its quote says so and the call's shares don't add up 
          +past 100% (else they are growth rates); other                 
      103 +    values must be money."""                                  
      104      if call is None:
      105          return []
      106 +    segs = call.facts.get("segments", [])                     
      107 +    claimed = [x["share_pct"] for x in segs if x.get("share_pc
          +t") is not None and 0 < x["share_pct"] <= 100]                
      108 +    shares_ok = sum(claimed) <= 105                           
      109      out = []
      101 -    for sgm in call.facts.get("segments", []):                
      102 -        if sgm.get("share_pct") is not None:                  
      103 -            value, unit, raw = sgm["share_pct"], "PCT", f"{sgm
          -['share_pct']:g}%"                                            
      110 +    for sgm in segs:                                          
      111 +        share = sgm.get("share_pct")                          
      112 +        if shares_ok and share is not None and 0 < share <= 10
          +0 and re.search(_SHARE_WORDS, sgm["quote"].lower()):          
      113 +            value, unit, raw = share, "PCT", f"{share:g}%"    
      114          elif sgm.get("value") is not None:
      105 -            fam, f = normalise_unit(sgm.get("unit_text"), "INR
          -")                                                            
      106 -            if fam not in ("INR_CR", "PCT"):                  
      115 +            fam, f = normalise_unit(sgm.get("unit_text"), "INR
          +", "revenue")                                                 
      116 +            if fam != "INR_CR":                               
      117                  continue
      118              value, unit, raw = sgm["value"] * f, fam, f"{sgm['
           value']:g} {sgm.get('unit_text') or ''}".strip()
      119          else:

⏺ All 307 pass. Committing, then rebuilding all four, since the snapshot facts
  changed:

  Ran 1 shell command (ctrl+o to expand)

⏺ The segment-guard fix is deploying, and the four demo tickers rebuild once
  Render serves it. The commit before it (db9543d) carried only the failing
  test; this one makes CI green again. I'll export the fixtures and run the
  final quote check when the rebuilds finish.

⏺ Background command "Commit, deploy, rebuild all four on Render, summarise"
completed (exit code 0)

  Ran 1 shell command (ctrl+o to expand)

⏺ The rebuilds are stalled again because my research lane hit its 60-call daily
  cap, with failed attempts from today's 503s and timeouts counting against it
  even though 3.6 and 3.5 Flash still have quota. I'm raising the cap to 80 to
  match the four models at 20 each, then resuming. · summary

⏺ Bash(sed -i '' 's/"research.strong": _env_int("RESEARCH_STRONG_RPD",
      60),/"research.strong": _env_int("RESEARCH_STRONG_RPD", 80),  # 4 strong
      models × 20 a day/' fin…)
  ⎿  ../.env.example:34:RESEARCH_STRONG_RPD=80
     finn/llm/router.py:192:        "research.strong": _env_int("RESEARCH_S
     TRONG_RPD", 80),  # 4 strong models × 20 a day
     … +3 lines (ctrl+o to expand)
  ⎿  Updated .env.example (+1 -1)
      31  # Research lane daily caps (Pacific day, like Gemini's): Flash-
          Lite calls for dossiers (incl. Ask), Ask alone, strong.
      32  RESEARCH_CHEAP_RPD=220
      33  RESEARCH_ASK_RPD=40
      34 -RESEARCH_STRONG_RPD=60                                         
      34 +RESEARCH_STRONG_RPD=80                                         
      35  # Raw download cache directory (default backend/.cache).
      36  # FINN_CACHE_DIR=
      37  
  ⎿  Updated backend/finn/llm/router.py (+1 -1)
      189      return {
      190          "research.ask": _env_int("RESEARCH_ASK_RPD", 40),
      191          "research.cheap": _env_int("RESEARCH_CHEAP_RPD", 220),
      192 -        "research.strong": _env_int("RESEARCH_STRONG_RPD", 60)
          -,                                                             
      192 +        "research.strong": _env_int("RESEARCH_STRONG_RPD", 80)
          +,  # 4 strong models × 20 a day                               
      193      }
      194  
      195  

  Ran 1 shell command (ctrl+o to expand)

⏺ The cap fix (28296c0) is deploying. When it's live, the 4 parked builds resume
  on 3.6/3.5 Flash. Then come the fixture export and the final quote check.

⏺ Background command "Deploy, resume parked builds, wait, print final dossiers"
completed (exit code 0)

  Read 1 file (ctrl+o to expand)

⏺ All four runs now finish on Render with gemini-3.6-flash, and the text is
  clean, with no leftover symbols or wrong figures. I'm stripping the stray
  "Fact_ids: [F24]" lines from POLYCAB's sentences in code next, since that
  doesn't need another model call. · summary

⏺ Bash(cd ~/Documents/finn/backend && python3 - <<'EOF'
      p='finn/research/reduce.py'; s=open(p).read()…)
  ⎿  308 passed, 1 warning in 1.46s
  ⎿  Updated backend/finn/research/reduce.py (+3 -2)
      49  
      50  _PLACEHOLDER = re.compile(r"\{(F\d+)\}")
      51  _NUMS = re.compile(r"\d+(?:\.\d+)?")
      52 +_ID_TAIL = re.compile(r"\s*\(?\bfacts?[_ ]?ids?\b\s*:?\s*\[?\s*
         +(?:F\d+\s*,?\s*)*\]?\)?\s*$", re.I)                            
      53  _ID_LIST = re.compile(r"\s*[\[{(]\s*F\d+(?:\s*,\s*F\d+)+\s*[\]}
          )]")
      54  
      55  
     ...
      179      by = {f.id: f for f in fs}
      180      ids = [i for i in raw.get("fact_ids") or [] if i in by]
      181      text = " ".join(str(raw["text"]).split())
      181 -    for grp in _ID_LIST.findall(text):  # '{F22, F15}' citatio
          -ns written into the text                                      
      182 +    for grp in _ID_LIST.findall(text) + _ID_TAIL.findall(text)
          +:  # '{F22, F15}' / 'Fact_ids: [F3]' in the text              
      183          ids += [i for i in re.findall(r"F\d+", grp) if i in by
           ]
      183 -    text = _ID_LIST.sub("", text).strip()                     
      184 +    text = _ID_TAIL.sub("", _ID_LIST.sub("", text)).strip()   
      185      used = _PLACEHOLDER.findall(text)
      186      if any(u not in by or by[u].display is None for u in used)
           :
      187          return None, True  # placeholders stand for numbers on
           ly
  ⎿  Updated backend/tests/test_research_synthesis.py (+12 -0)
      147          {"name": "CV", "share_pct": 89.0, "quote": "CV and tra
           ctor share up 89%", "page": 1},
      148      ]
      149      assert segments(c) == []
      150 +                                                              
      151 +                                                              
      152 +def test_reduce_strips_fact_id_tails():                       
      153 +    f = _fig("ROCE", 33.0)                                    
      154 +    fs = [reduce.Fact("F3", "F3: ROCE = 33.0%", "33.0%", [f.ci
          +tation])]                                                     
      155 +    for text in (                                             
      156 +        "ROCE stood at {F3}. Fact_ids: [F3",                  
      157 +        "ROCE stood at {F3}. Fact_ids:",                      
      158 +        "ROCE stood at {F3}. (fact ids: F3)",                 
      159 +    ):                                                        
      160 +        c, _ = reduce.render({"text": text, "fact_ids": []}, f
          +s)                                                            
      161 +        assert c.text == "ROCE stood at 33.0%." and c.citation
          +s                                                             

  Ran 1 shell command (ctrl+o to expand)

⏺ POLYCAB checks out clean. The daily-changing market cap gets noted for
  Friday's refresh, and I'm running the final verdict-quote check on all four
  dossiers before exporting fixtures from Render. · summary

⏺ Bash(cd ~/Documents/finn/backend && ../.venv/bin/python -
      <<'EOF'
      import json, urllib.request…)
  ⎿  PERSISTENT: transcript quotes on cited page 24/24; job done; {'snapsho
     t': 'ready', 'trajectory': 'ready', 'ledger': 'ready', 'cash_quality':
      'ready', 'balance_sheet': 'ready', 'analysts': 'ready', 'red_flags':
     … +21 lines (ctrl+o to expand)
  ⎿  4 files changed (binary, mode only or too large to show)

⏺ All 100 transcript quotes in the four dossiers check out on their cited pages,
  so I'm committing the fixtures and ticking off the plan. · summary

⏺ Bash(cd ~/Documents/finn && python3 - <<'EOF'
      p='docs/PLAN.md'; s=open(p).read()…)
  ⎿  75bfa59 Fixtures: final-shape dossiers for PERSISTENT, INFY, BAJFINANC
     E, POLYCAB (built on Render); PLAN ticks
  ⎿  Updated docs/PLAN.md (+6 -4)
      69  - [x] Numeric Promise Ledger + analysts + drivers in builds — `
          85c0cd4` (INFY local: 4 kept, 1 missed, 1 moved)
      70  - [x] **Render env (product owner):** DEPLOY.md §7 — set 11 Nov
      71  - [x] Build the 4 demo tickers on the deployed API; quotes chec
          ked — 20 of 20 verdict quotes on their cited pages (PERSISTENT,
           INFY, BAJFINANCE; POLYCAB has no scorable promise yet)
      72 -- [ ] JUDGE (strong #1): qualitative promises + paraphrased cro
         -ss-call links, citing both calls — **Wed 11 Nov**              
      73 -- [ ] REDUCE (strong #2): snapshot text, trajectory line, bull/
         -bear with `{F#}` placeholders rendered in code — **Wed 11 Nov**
      74 -- [ ] Rebuild the 4 demo tickers on Render and regenerate `web/
         -public/fixtures/` — **Wed 11 Nov** (Thursday is frontend-only) 
      72 +- [x] JUDGE (strong #1): qualitative promises + paraphrased cro
         +ss-call links, citing both calls — `eebcf9a`, guards `56e9442` 
      73 +- [x] REDUCE (strong #2): snapshot text, trajectory line, bull/
         +bear with `{F#}` placeholders rendered in code — `eebcf9a` … `c
         +434aa8`                                                        
      74 +- [x] Credibility tally always shown, % from n ≥ 5 (product own
         +er) — `540cb77`                                                
      75 +- [x] Strong chain + 3.6/3.5 Flash; daily budgets count failed 
         +attempts — `0c239b2`, `28296c0`                                
      76 +- [x] Rebuild the 4 demo tickers on Render and regenerate `web/
         +public/fixtures/` (4 tickers incl. PERSISTENT) — 100 of 100 cit
         +ed transcript quotes on their pages; every section ready except
         + red flags / exchange data (Friday)                            
      77  
      78  **Friday morning (product owner, 11 Nov: cut if Friday gets tig
          ht):**
      79  - [ ] Annual report sections (headings in code) → red flags (au
          ditor opinion, contingent liabilities growth, related parties)
      80  - [ ] Ask: BM25 over the ticker's pages + facts → Flash-Lite (G
          roq fallback) → cited answer or "Not found in sources"
      79 -- [ ] Nightly refresh on Actions (code-only recompute; rebuild 
         -only on a new document; first-time builds only for the 4 demo t
         -ickers); DB size guard                                         
      81 +- [ ] Nightly refresh on Actions (code-only recompute; rebuild 
         +only on a new document; first-time builds only for the 4 demo t
         +ickers); DB size guard. **Reuse the previous summary unless the
         + document set changed**: REDUCE's facts include the day's marke
         +t cap, so a forced rebuild spends a strong call even with no ne
         +w document                                                     
      82  - [ ] On-demand NSE dispatch (section above) → `exchange_data`
      83  - [ ] Two tickers outside the demo set (one bank); cost report;
           README
      84  - [x] Frontend fixtures: validated INFY, BAJFINANCE, POLYCAB do
          ssiers in `web/public/fixtures/` (`python -m jobs.research expo
          rt`; built locally against Supabase — rebuild on Render once §7
           is set)

  Called ccd_turn (ctrl+o to expand)

⏺ The dossier backend is finished for tonight. All 4 demo tickers are built on
  the deployed API, every quote they cite checks out, and the fixtures are final
  (75bfa59).

  Your 3 steps:
  1. Deployed builds: Render runs HEAD. PERSISTENT, INFY, BAJFINANCE and POLYCAB
     all finished their builds there. All 100 transcript quotes they cite are
     on the pages they cite: every verdict, plus the snapshot, bull/bear and
     analyst sentences.
  2. Qualitative judge: live, with code guards. The model may give kept or
     missed only for qualitative promises (it twice tried to compare numbers
     itself). Its evidence must be a checked, verbatim quote from a later call,
     and it can never claim "quietly dropped".
  3. Summary and bull/bear: live for all four, at 3 and 3. Numbers come only
     from cited facts. A typed number survives only if a cited fact prints it,
     and spelled-out quantities are blocked.

  Credibility, per your choice: the "kept of n" tally always shows, and the %
  needs 5 scored promises. With honest rules no demo ticker gets there yet:

  ┌────────────┬──────┬────────────┐
  │   Ticker   │ Kept │ Scored (n) │
  ├────────────┼──────┼────────────┤
  │ PERSISTENT │ 1    │ 2          │
  ├────────────┼──────┼────────────┤
  │ INFY       │ 2    │ 4          │
  ├────────────┼──────┼────────────┤
  │ BAJFINANCE │ 1    │ 4          │
  ├────────────┼──────┼────────────┤
  │ POLYCAB    │ 0    │ 1          │
  └────────────┴──────┴────────────┘

  Things that went wrong today, now fixed:
  - Both approved strong models ran out of quota. Google counted failed and
    timed-out attempts, and 3.8 Flash had a bad afternoon. The router now counts
    failures, skips an overloaded model after 2 attempts, and the chain
    includes the 3.6 and 3.5 Flash you approved. Tonight's summaries were
    written by gemini-3.6-flash.
  - Several wrong outputs were caught and corrected before the fixtures:
    - Segment growth rates shown as shares (BAJFINANCE "rural 63% + CV 89%").
    - "₹₹ … Cr Cr" and "Fact_ids:" left in the summary text.
    - A new-customer target scored against the total customer base as a 7× beat.
  - One commit (db9543d) contained only a test whose fix hadn't applied, so CI
    went red. The next commit (38273b3) made it pass again.

  For your frontend work tomorrow:
  - Fixtures:
    web/public/fixtures/dossier_{PERSISTENT,INFY,BAJFINANCE,POLYCAB}.json are
    real DossierResponse payloads from Render.
  - Contract: the shape didn't change; only field descriptions did.
  - Sections not built yet: red flags and exchange data return building with
    reason not_built_yet. Render that as "coming soon", or hide it if Friday's
    cut happens.
  - No force rebuild through the proxy: the proxy drops query strings, so a
    ?force=true rebuild can't be triggered from the app. That's fine for the UI.

  Friday morning (cut if tight): annual-report red flags, Ask, the nightly
  refresh and NSE enrichment. The nightly refresh must reuse the previous
  summary unless a new document appears. Otherwise each rebuild spends a strong
  call, because the summary's facts include the day's market cap.

❯ I'm busy for the rest of the day, so please complete and verify everything    
  below on your own. Don't ask me questions. Make reasonable choices, record    
  them in DECISIONS.md or PLAN.md, and only stop to ask if something needs a    
  dashboard click from me or can't be undone. Work in this order and keep going 
  until done or 19:30 IST, whichever comes first.                               
                                                                                
  1. UNSEEN-TICKER ACCEPTANCE                                                   
     - Pick 2 test tickers by a random draw from the NSE equity list (EQ        
  series). Exclude the 18 portfolio tickers, the 4 demo tickers and every       
  ticker we've already built or tested (HDFCBANK, TRENT, etc.). Use a fixed,    
  logged seed so the pick is reproducible and clearly not hand-chosen. Draw one 
  from banks/NBFCs and one from companies outside the Nifty 100. If a drawn     
  ticker has no screener page, keep it: that's a valid degradation test, and in 
  that case draw one more as well.                                              
     - Build each one on Render through the deployed API, the way an evaluator  
  would. Don't change any code before the first run.                            
     - Record in PLAN.md what every section showed, the build time, and the     
  cheap and strong calls used.                                                  
     - Then fix only general bugs (nothing specific to these companies),        
  rebuild, and record before/after.                                             
  2. INDEPENDENT SPOT-CHECK                                                     
     - Choose 5 verdicts at random (logged seed) across the 4 demo tickers: at  
  least one missed, one goalposts moved and one judged by the model.            
     - Have a fresh subagent that hasn't seen this session's work check each    
  one. It gets only the verdict, the cited document and the page. It confirms   
  the quote is on that page, the numbers match, and the verdict follows from    
  the evidence.                                                                 
     - Report its findings as a table in PLAN.md, and fix anything it finds     
  wrong.                                                                        
  3. DECK LOOKUP (time-boxed: stop at 18:30 IST and move what's left to Friday) 
     - For promises that are "can't score" only because the delivered figure    
  isn't on the call, read the investor deck for the quarter that closes the     
  promised period (usually the Q4 deck for an FY target).                       
     - Use one Flash-Lite call per deck needed, never all decks. The delivered  
  figure cites the deck page, with the same quote checks.                       
     - Make sure the contract exposes counts for not yet due and can't score,   
  plus the next period at which a promise falls due, so the ledger header can   
  say "2 of 4 kept · 9 not yet due · next test: FY27 results".                  
     - Don't lower the n ≥ 5 threshold.                                         
  4. SCHEDULE CHECK                                                             
     - Check ingest_runs for today's scheduler-triggered runs (filings since    
  08:00, and the 16:30 daily run once it's due).                                
     - Tick "Confirm the schedule fires" in PLAN.md if they're there; otherwise 
  diagnose and record why.                                                      
  5. WRAP UP                                                                    
     - Make sure all tests pass, CI is green, and /version matches HEAD.        
     - Rebuild the 4 demo dossiers if anything changed their content, re-run    
  the quote check, and regenerate the fixtures.                                 
     - Don't spend strong-model calls beyond what these steps need.             
     - Update PLAN.md (tick what's done, list Friday items) and DECISIONS.md.   
     - End with one short summary for me: the results of steps 1–4, the commit  
  hashes, what moved to Friday, and anything that needs me.                     
                                                                                
  Don't touch the frontend; that's tomorrow's session.                          

  Called ccd_turn, ran 1 shell command (ctrl+o to expand)

⏺ At 15:51 IST I'm building the exclusion set for a reproducible draw from every
  symbol in the database and the portfolio and demo lists, and next I'll fetch
  the Nifty 100 list from NSE's archive. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ Got the Nifty 100 list (100 symbols). Writing the draw as a committed script,
  so anyone can reproduce it from the seed:

⏺ Bash(mkdir -p ~/Documents/finn/backend/evals/research && cp
      /private/tmp/claude-501/-Users-<user>--claude-spares-spare-yicH6h/bb46
      3e84-2008-445e-…)
  ⎿  seed=20261111 pool=2375 excluded=34 banks/NBFCs=114 outside-Nifty100=2
     190
     bank/NBFC: JPOLYINVST (Jindal Poly Investment and Finance Company Limi
     … +2 lines (ctrl+o to expand)
  ⎿  Created backend/evals/research/__init__.py (+0 -0)
  ⎿  Created backend/evals/research/draw_unseen.py (+55 -0)
       1 +"""Reproducible draw of 'unseen' tickers for the research accep
         +tance test (Phase 3).                                          
       2 +                                                               
       3 +python -m evals.research.draw_unseen [--seed 20261111] [--extra
         + 0]                                                            
       4 +                                                               
       5 +- Pool: NSE equity list, EQ series (public.securities, refreshe
         +d from EQUITY_L.csv).                                          
       6 +- Excluded: the 18 demo-portfolio tickers, the 4 research demo 
         +tickers, and every symbol FINN has already built or            
       7 +  tested (anything in dossiers, research_documents, filings, re
         +sults_filings or prices_daily, plus TRENT).                    
       8 +- Draw 1 — banks/NBFCs: company name matches FIN_RE (the equity
         + list carries no industry, so the name decides).               
       9 +- Draw 2 — outside the Nifty 100 (evals/research/nifty100_2026-
         +11-11.csv, NSE archive) and not matching FIN_RE.               
      10 +- `--extra N` draws N more from pool 2 (used when a drawn ticke
         +r has no screener page — it is kept, not replaced).            
      11 +The seed is fixed and logged so the pick is reproducible and no
         +t hand-chosen.                                                 
      12 +"""                                                            
      13 +                                                               
      14 +from __future__ import annotations                             
      15 +                                                               
      16 +import argparse                                                
      17 +import csv                                                     
      18 +import random                                                  
      19 +import re                                                      
      20 +from pathlib import Path                                       
      21 +                                                               
      22 +from finn.db import connect                                    
      23 +from finn.portfolio import DEMO_PORTFOLIO                      
      24 +                                                               
      25 +DEMO = ["BAJFINANCE", "INFY", "PERSISTENT", "POLYCAB"]         
      26 +FIN_RE = re.compile(r"\b(bank|finance|financial|financials|finc
         +orp|finserv|fincap|credit|leasing|housing finance)\b",         
      27 +                    re.I)  # fmt: skip                         
      28 +NIFTY100 = Path(__file__).with_name("nifty100_2026-11-11.csv") 
      29 +                                                               
      30 +                                                               
      31 +def main() -> None:                                            
      32 +    ap = argparse.ArgumentParser()                             
      33 +    ap.add_argument("--seed", type=int, default=20261111)      
      34 +    ap.add_argument("--extra", type=int, default=0)            
      35 +    a = ap.parse_args()                                        
      36 +    nifty = {r["Symbol"] for r in csv.DictReader(NIFTY100.open(
         +))}                                                            
      37 +    with connect() as c:                                       
      38 +        rows = c.execute("select symbol, name from public.secur
         +ities where series = 'EQ' order by symbol").fetchall()         
      39 +        seen = {"TRENT"} | set(DEMO_PORTFOLIO) | set(DEMO)     
      40 +        for t in ("dossiers", "research_documents", "filings", 
         +"results_filings", "prices_daily"):                            
     … 15 more lines (ctrl+o to expand)
  ⎿  Created backend/evals/research/nifty100_2026-11-11.csv (+101 -0)
        1 +Company Name,Industry,Symbol,Series,ISIN Code                 
        2 +ABB India Ltd.,Capital Goods,ABB,EQ,INE117A01022              
        3 +Adani Energy Solutions Ltd.,Power,ADANIENSOL,EQ,INE931S01010  
        4 +Adani Enterprises Ltd.,Metals & Mining,ADANIENT,EQ,INE423A0102
          +4                                                             
        5 +Adani Green Energy Ltd.,Power,ADANIGREEN,EQ,INE364U01010      
        6 +Adani Ports and Special Economic Zone Ltd.,Services,ADANIPORTS
          +,EQ,INE742F01042                                              
        7 +Adani Power Ltd.,Power,ADANIPOWER,EQ,INE814H01029             
        8 +Ambuja Cements Ltd.,Construction Materials,AMBUJACEM,EQ,INE079
          +A01024                                                        
        9 +Apollo Hospitals Enterprise Ltd.,Healthcare,APOLLOHOSP,EQ,INE4
          +37A01024                                                      
       10 +Asian Paints Ltd.,Consumer Durables,ASIANPAINT,EQ,INE021A01026
       11 +Avenue Supermarts Ltd.,Consumer Services,DMART,EQ,INE192R01011
       12 +Axis Bank Ltd.,Financial Services,AXISBANK,EQ,INE238A01034    
       13 +BSE Ltd.,Financial Services,BSE,EQ,INE118H01025               
       14 +Bajaj Auto Ltd.,Automobile and Auto Components,BAJAJ-AUTO,EQ,I
          +NE917I01010                                                   
       15 +Bajaj Finance Ltd.,Financial Services,BAJFINANCE,EQ,INE296A010
          +32                                                            
       16 +Bajaj Finserv Ltd.,Financial Services,BAJAJFINSV,EQ,INE918I010
          +26                                                            
       17 +Bajaj Holdings & Investment Ltd.,Financial Services,BAJAJHLDNG
          +,EQ,INE118A01012                                              
       18 +Bank of Baroda,Financial Services,BANKBARODA,EQ,INE028A01039  
       19 +Bharat Electronics Ltd.,Capital Goods,BEL,EQ,INE263A01024     
       20 +Bharat Petroleum Corporation Ltd.,Oil Gas & Consumable Fuels,B
          +PCL,EQ,INE029A01011                                           
       21 +Bharti Airtel Ltd.,Telecommunication,BHARTIARTL,EQ,INE397D0102
          +4                                                             
       22 +Bosch Ltd.,Automobile and Auto Components,BOSCHLTD,EQ,INE323A0
          +1026                                                          
       23 +Britannia Industries Ltd.,Fast Moving Consumer Goods,BRITANNIA
          +,EQ,INE216A01030                                              
       24 +CG Power and Industrial Solutions Ltd.,Capital Goods,CGPOWER,E
          +Q,INE067A01029                                                
       25 +Canara Bank,Financial Services,CANBK,EQ,INE476A01022          
       26 +Cholamandalam Investment and Finance Company Ltd.,Financial Se
          +rvices,CHOLAFIN,EQ,INE121A01024                               
       27 +Cipla Ltd.,Healthcare,CIPLA,EQ,INE059A01026                   
       28 +Coal India Ltd.,Oil Gas & Consumable Fuels,COALINDIA,EQ,INE522
          +F01014                                                        
       29 +Cummins India Ltd.,Capital Goods,CUMMINSIND,EQ,INE298A01020   
       30 +DLF Ltd.,Realty,DLF,EQ,INE271C01023                           
       31 +Divi's Laboratories Ltd.,Healthcare,DIVISLAB,EQ,INE361B01024  
       32 +Dr. Reddy's Laboratories Ltd.,Healthcare,DRREDDY,EQ,INE089A010
          +31                                                            
       33 +Eicher Motors Ltd.,Automobile and Auto Components,EICHERMOT,EQ
          +,INE066A01021                                                 
       34 +Eternal Ltd.,Consumer Services,ETERNAL,EQ,INE758T01015        
       35 +GAIL (India) Ltd.,Oil Gas & Consumable Fuels,GAIL,EQ,INE129A01
          +019                                                           
       36 +Godrej Consumer Products Ltd.,Fast Moving Consumer Goods,GODRE
          +JCP,EQ,INE102D01028                                           
       37 +Grasim Industries Ltd.,Construction Materials,GRASIM,EQ,INE047
          +A01021                                                        
       38 +HCL Technologies Ltd.,Information Technology,HCLTECH,EQ,INE860
          +A01027                                                        
       39 +HDFC Asset Management Company Ltd.,Financial Services,HDFCAMC,
          +EQ,INE127D01025                                               
       40 +HDFC Bank Ltd.,Financial Services,HDFCBANK,EQ,INE040A01034    
     … 61 more lines (ctrl+o to expand)

⏺ The seeded draw picked JPOLYINVST (Jindal Poly Investment and Finance) as the
  bank/NBFC and LAXMIDENTL (Laxmi Dental) as the stock outside the Nifty 100.
  I'm building both on Render through the deployed API, unchanged, as stress
  tests. · summary

  Ran 2 shell commands (ctrl+o to expand)

⏺ JPOLYINVST built in 8 seconds. Without transcripts, the ledger, analysts and
  drivers are unavailable, and a null credibility field crashed my report
  script, so I'm printing the rest tolerantly now. · summary
  Ran 1 shell command (ctrl+o to expand)

⏺ Both unseen tickers now produce complete or honestly partial dossiers on the
  first run, with JPOLYINVST taking 8 s and LAXMIDENTL 256 s. Next I'll record
  these before-results in PLAN.md and fix the judge step that stays pending and
  the accounting schedules wrongly flagged as dropped promises. · summary

⏺ Bash(cd ~/Documents/finn && python3 - <<'EOF'
      p='docs/PLAN.md'; s=open(p).read()…)
  ⎿  78:### Unseen-ticker acceptance (11 Nov 2026, 15:52 IST)
  ⎿  Updated docs/PLAN.md (+24 -0)
       75  - [x] Strong chain + 3.6/3.5 Flash; daily budgets count failed
            attempts — `0c239b2`, `28296c0`
       76  - [x] Rebuild the 4 demo tickers on Render and regenerate `web
           /public/fixtures/` (4 tickers incl. PERSISTENT) — 100 of 100 c
           ited transcript quotes on their pages; every section ready exc
           ept red flags / exchange data (Friday)
       77  
       78 +### Unseen-ticker acceptance (11 Nov 2026, 15:52 IST)         
       79 +                                                              
       80 +Draw: `python -m evals.research.draw_unseen --seed 20261111` →
          + pool 2,375 EQ symbols after excluding 34 already built/tested
          + (demo portfolio, demo tickers, anything in dossiers / researc
          +h_documents / filings / results_filings / prices_daily, TRENT)
          +. Banks/NBFCs by company name (`FIN_RE`; the equity list carri
          +es no industry): 114 → **JPOLYINVST** (Jindal Poly Investment 
          +and Finance). Outside the Nifty 100 (NSE archive list, committ
          +ed) and not financial: 2,190 → **LAXMIDENTL** (Laxmi Dental). 
          +Both have screener pages, so no extra draw. Built on Render th
          +rough `POST /research/{sym}/build`, no code changes before the
          + first run.                                                   
       81 +                                                              
       82 +**Run 1 (deployed `75bfa59`, before fixes)**                  
       83 +                                                              
       84 +| | JPOLYINVST (job 37) | LAXMIDENTL (job 38) |               
       85 +|---|---|---|                                                 
       86 +| Build time | 8 s | 256 s |                                  
       87 +| Calls | 0 cheap · 1 strong (gemini-3.6-flash) | 8 cheap (Fla
          +sh-Lite) · 2 strong (3.6 Flash); 14 attempts incl. retries; ≈ 
          +$0.22 list |                                                  
       88 +| Documents | 0 transcripts on screener; annual report listed 
          +(not read yet) | 8/8 transcripts read (Q3 FY25–Q2 FY27); 432 q
          +uotes checked, 1 dropped, 5 re-anchored |                     
       89 +| Snapshot | ready (3 lines, headline figures) | ready |      
       90 +| Trajectory | ready (10 y; template standard — screener shows
          + this holding company in the standard format) | ready (7 y, li
          +sted Jan 2025) |                                              
       91 +| Promise Ledger | unavailable · no_transcripts | ready: 18 pr
          +omises — 1 kept, 1 missed (FY26 growth 16.3% vs 20–25%), 3 qui
          +etly dropped, 6 not yet due, 7 can't score; tally 1 of 5 |    
       92 +| Cash quality | ready (CFO, CFO/PAT, FCF ✓ screener, capex) |
          + ready |                                                      
       93 +| Balance sheet | ready | ready |                             
       94 +| Analysts | unavailable · no_transcripts | ready (Growth 8 ca
          +lls, Margins 8, Market share 4…) |                            
       95 +| Red flags | building · not_built_yet (Friday) | building · n
          +ot_built_yet (Friday) |                                       
       96 +| Bull/bear | ready (3 + 3) | ready (3 + 3) |                 
       97 +| Drivers | unavailable · no_transcripts | ready (Growth, Marg
          +ins, Profit) |                                                
       98 +| Exchange data | building · not_built_yet (Friday) | building
          + · not_built_yet (Friday) |                                   
       99 +                                                              
      100 +General bugs found: (1) the judge step stays `pending` when th
          +ere is no ledger; (2) "ESOP expense ₹2.19 Cr / ₹6.35 Cr" — sha
          +re-based-payment cost schedules — entered the ledger and were 
          +marked **quietly dropped**, the most serious claim FINN makes.
      101 +                                                              
      102  **Friday morning (product owner, 11 Nov: cut if Friday gets ti
           ght):**
      103  - [ ] Annual report sections (headings in code) → red flags (a
           uditor opinion, contingent liabilities growth, related parties
           )
      104  - [ ] Ask: BM25 over the ticker's pages + facts → Flash-Lite (
           Groq fallback) → cited answer or "Not found in sources"

⏺ Fixing both, then rebuilding both tickers:

⏺ Bash(cd ~/Documents/finn/backend && python3 - <<'EOF'
      p='finn/research/ledger.py'; s=open(p).read()…)
  ⎿  309 passed, 1 warning in 1.44s
     719bd7e Unseen-ticker acceptance run 1 (JPOLYINVST, LAXMIDENTL; seeded
      draw); fixes: ESOP/share-based cost schedules aren't promises, judge
     step skipped without a ledger
  ⎿  Updated backend/finn/research/build.py (+5 -1)
      105      # 6–7. Judge + reduce (strong model chain: 3.8 Flash → 3 F
           lash; never Flash-Lite). An unchanged dossier hits
      106      # the router's cache, so it costs no strong call.
      107      tags = {"symbol": symbol, "job_id": job_id}
      108 -    strong_quota = run_judge(d, led, calls, router, tags, prog
          -ress, now) if led else None                                   
      108 +    if led is not None:                                       
      109 +        strong_quota = run_judge(d, led, calls, router, tags, 
          +progress, now)                                                
      110 +    else:                                                     
      111 +        strong_quota = None                                   
      112 +        progress.step("judge", "skipped", "No promises to judg
          +e")                                                           
      113      if disc.status == "ok" or calls:
      114          strong_quota = run_reduce(d, calls, router, tags, prog
           ress, now) or strong_quota
      115      else:
  ⎿  Updated backend/finn/research/ledger.py (+7 -0)
      174  )
      175  
      176  
      177 +# Accounting schedules aren't commitments either: an ESOP / sh
          +are-based-payment charge forecast is arithmetic on            
      178 +# grants already made, and calling it "quietly dropped" would 
          +be a false accusation.                                        
      179 +_ACCOUNTING = re.compile(r"\b(esops?|esos|share[- ]based|stock
          + options?|employee stock|sbc)\b", re.I)                       
      180 +                                                              
      181 +                                                              
      182  def is_business_promise(it: dict) -> bool:
      183 +    if _ACCOUNTING.search(it.get("metric", "")):              
      184 +        return False                                          
      185      if it.get("metric_key") not in ("other", "headcount"):
      186          return True
      187      return not _GOVERNANCE.search(f"{it.get('metric', '')} {it
           .get('statement', '')}")
  ⎿  Updated backend/tests/test_ledger.py (+7 -0)
      307      total = {**a("customer_growth", 119.3, unit="million", cur
           rency="not_money"), "metric": "customer franchise"}
      308      p = only(ledger([call(1, date(2025, 7, 20), [add]), call(2
           , date(2026, 5, 5), actuals=[total])]))
      309      assert p.verdict == "cant_score" and "different measure" i
           n p.verdict_reason.text
      310 +                                                              
      311 +                                                              
      312 +def test_accounting_schedules_are_not_promises():             
      313 +    esop = g("other", 2.19, 2.19, unit="crore", kind="point", 
          +metric="ESOP expense", fy=2025, terms=("ESOP",))              
      314 +    sbc = g("pat", 6.35, 6.35, unit="crore", kind="point", met
          +ric="share-based payment cost", fy=2026)                      
      315 +    led = ledger([call(1, date(2024, 10, 20), [esop, sbc]), ca
          +ll(2, date(2025, 1, 20)), call(3, date(2025, 4, 20))])        
      316 +    assert led.promises == []                                 

⏺ Committed (719bd7e). The deploy and rebuild of both unseen tickers are running
  in the background. Meanwhile, step 2: drawing 5 verdicts with a logged seed.

  Ran 2 shell commands (ctrl+o to expand)

⏺ I'm handing the draw of 11 scored verdicts (2 missed, 2 goalposts moved, 1
  kept) to a fresh subagent that will check the PDFs itself. · summary

  Read 1 file, ran 1 shell command (ctrl+o to expand)

⏺ Agent(Audit 5 Promise Ledger verdicts)
  ⎿  Backgrounded agent (↓ to manage · ctrl+o to expand)

⏺ The spot-check auditor is running on its own, and I'm starting the deck lookup
  for the promises the call never gave a delivered figure for, using the deck
  that closes each promised period. · summary

  Searched for 1 pattern, ran 1 shell command (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/sources/screener.py'; s=open(p).read()…)
  ⎿  {'2026-09-30': 'Q2 FY27 investor presentation', '2026-06-30': 'Q1 FY27
      investor presentation', '2026-03-31': 'Q4 FY26 investor presentation'
     , '2025-12-31': 'Q3 FY26 investor presentation'}
  ⎿  Updated backend/finn/research/discover.py (+7 -0)
      54      tables: dict[str, Table] = field(default_factory=dict)
      55      transcripts: list[DocLink] = field(default_factory=list)  #
           newest first, ≤ 8, one per quarter
      56      annual_report: DocLink | None = None
      57 +    decks: dict = field(default_factory=dict)  # quarter end → 
         +DocLink of that quarter's investor deck                        
      58      capex: dict[str, str] | None = None  # 'Fixed assets purcha
          sed' by period label, as printed
      59      fixed_assets_sold: dict[str, str] | None = None
      60      year_end_month: int | None = None
     ...
      102          )
      103          if len(d.transcripts) >= MAX_TRANSCRIPTS:
      104              break
      105 +    for t in docs["decks"]:                                   
      106 +        qe = transcript_quarter(t["month"])                   
      107 +        if qe in d.decks or "nseindia.com" in t["url"]:       
      108 +            continue                                          
      109 +        label = quarter_period(qe).label                      
      110 +        d.decks[qe] = DocLink("investor_presentation", t["url"
          +], f"{label} investor presentation", label, t["month"], qe)   
      111      for a in docs["annual_reports"]:
      112          if "nseindia.com" in a["url"]:
      113              continue
  ⎿  Updated backend/finn/research/ledger.py (+5 -0)
      57      facts: dict
      58      retrieved_at: datetime
      59  
      60 +    kind: str = "transcript"  # transcript | deck (a deck only 
         +supplies delivered figures — never promises)                   
      61 +                                                               
      62      def cite(self, page: int, quote: str) -> Citation:
      63 +        if self.kind == "deck":                                
      64 +            return Citation(source_type="investor_presentation"
         +, url=self.url, title=self.label, page=page,                   
      65 +                            quote=quote, retrieved_at=self.retr
         +ieved_at)  # fmt: skip                                         
      66          return Citation(source_type="concall_transcript", url=s
          elf.url, title=f"{self.label} transcript", page=page,
      67                          quote=quote, retrieved_at=self.retrieve
          d_at)  # fmt: skip
      68  
  ⎿  Updated backend/finn/sources/screener.py (+10 -6)
      210  
      211  
      212  def parse_documents(soup: BeautifulSoup) -> dict:
      213 -    """Transcript links (concall entries with a 'Transcript' l
          -ink only — never notes/PPT/recordings) newest first,          
      213 +    """Transcript links and investor-deck (PPT) links per conc
          +all entry (never notes/recordings), newest first,             
      214      and annual-report links newest first."""
      215 -    out: dict[str, list[dict]] = {"transcripts": [], "annual_r
          -eports": []}                                                  
      215 +    out: dict[str, list[dict]] = {"transcripts": [], "annual_r
          +eports": [], "decks": []}                                     
      216      docs = soup.select_one("section#documents")
      217      if not docs:
      218          return out
     ...
      221          period = li.select_one(".ink-600") or li.select_one("d
           iv")
      222          label = " ".join(period.get_text(" ", strip=True).spli
           t()) if period else ""
      223          m = re.match(r"([A-Z][a-z]{2})\s+(\d{4})", label)
      224 +        if not (m and m.group(1) in _MONTHS):                 
      225 +            continue                                          
      226 +        month = date(int(m.group(2)), _MONTHS[m.group(1)], 1) 
      227          for a in li.select("a[href]"):
      225 -            if a.get_text(strip=True).lower().startswith("tran
          -script") and m and m.group(1) in _MONTHS:                     
      226 -                out["transcripts"].append({"month": date(int(m
          -.group(2)), _MONTHS[m.group(1)], 1),                          
      227 -                                           "label": m.group(0)
          -, "url": a["href"]})  # fmt: skip                             
      228 -                break                                         
      228 +            kind = a.get_text(strip=True).lower()             
      229 +            if kind.startswith("transcript"):                 
      230 +                out["transcripts"].append({"month": month, "la
          +bel": m.group(0), "url": a["href"]})                          
      231 +            elif kind in ("ppt", "presentation"):  # the inves
          +tor deck for that call (delivered figures)                    
      232 +                out["decks"].append({"month": month, "label": 
          +m.group(0), "url": a["href"]})                                
      233      ar = docs.select_one(".annual-reports")
      234      for a in ar.select("a[href]") if ar else []:
      235          text = " ".join(a.get_text(" ", strip=True).split())

⏺ Discovery now captures each quarter's deck. Next, the ledger side: a list of
  promises that lack a delivered figure, decks excluded from every
  transcript-only rule, and the next-test computation.

  Searched for 1 pattern (ctrl+o to expand)

⏺ Background command "Deploy and rebuild both unseen tickers (run 2)" completed
(exit code 0)

  Ran 1 shell command (ctrl+o to expand)

› Message from general-purpose
  I downloaded all nine BSE PDFs and read every cited page (1-based PDF page).
  All ten quotes are on the cited pages, verbatim apart from spacing. All
  numbers match the pages. All five verdicts follow under the stated rules.
  Items 3 and 4 are softer cases, explained in the notes.

  | n | symbol | quote 1 on page? | quote 2 on page? | numbers match? | verdict
  follows? | notes |
  |---|---|---|---|---|---|---|
  | 1 | BAJFINANCE | yes (p4) | yes (p4) | yes: 10–12% target, 6% delivered |
  yes | Neither call says what "growth" is measured on (probably AUM year on
  year). The Q3 call reported 11% for the quarter and gave no new FY26 target.
  Q4 p11 confirms 6%, down from 25–30% before. |
  | 2 | INFY | yes (p4) | yes (p4) | yes: 1.5–3.5% cut to 1–2%, both year on
  year in constant currency | yes | Same metric and basis on both calls; a clear
  cut in the FY27 guidance. I did not check the Q1 FY27 call, but "first given
  in Q4 FY26" is correct. |
  | 3 | POLYCAB | yes (p7) | yes (p8) | yes: margins 6.7% (Q3) and 7.6% (Q4) |
  yes, but soft | The bottom of the range drops from "high" to "mid" single
  digits, so it is a real cut. But this is a vague, open-ended outlook with no
  date. Actual margins (6.7%, 7.6%) were already below "high single digits". |
  | 4 | BAJFINANCE | yes (p4) | yes (p3) | yes: 115M in Q3, 120M target, 119.3M
  delivered | yes, but debatable | "Well on course to cross 120 million" is a
  projection more than a commitment. 119.3 is a one-decimal figure, so rounding
  does not lift it to 120 and the miss stands under the rule. Management itself
  calls it a "120 million franchise" on Q4 pp12–13, which a reader may find
  harsh. |
  | 5 | PERSISTENT | yes (p14) | yes (p13) | yes: 23–23.5% target, 23.2%
  delivered for FY25 | yes | Inside the range. The Q3 range is described as
  "revised estimates", so an earlier guidance existed, but that does not affect
  this verdict. The Q4 quote repeats the same range "going forward", which is
  fine. |

  The PDFs are in /private/tmp/claude-501/-Users-<user>--claude-spares-spare
  -yicH6h/bb463e84-2008-445e-be1c-9b1ec9bda462/scratchpad/audit/

⏺ Agent "Audit 5 Promise Ledger verdicts" finished · 1m 2s

⏺ The auditor confirmed all five sampled verdicts and flagged POLYCAB's vague
  EPC outlook and BAJFINANCE's 120-million projection as softer cases, though
  neither is a bug. Both unseen-ticker runs passed, and I'm recording that in
  PLAN.md next. · summary

⏺ Bash(cd ~/Documents/finn && python3 - <<'EOF'
      p='docs/PLAN.md'; s=open(p).read()…)
  ⎿  12cfdb1 PLAN: unseen-ticker run 2 and independent spot-check (5/5 verd
     icts confirmed)
  ⎿  Updated docs/PLAN.md (+26 -0)
       99  
      100  General bugs found: (1) the judge step stays `pending` when th
           ere is no ledger; (2) "ESOP expense ₹2.19 Cr / ₹6.35 Cr" — sha
           re-based-payment cost schedules — entered the ledger and were 
           marked **quietly dropped**, the most serious claim FINN makes.
      101  
      102 +**Run 2 (deployed `719bd7e`: ESOP / share-based cost schedules
          + aren't promises; judge step `skipped` without a ledger)**    
      103 +                                                              
      104 +| | JPOLYINVST (job 39) | LAXMIDENTL (job 40) |               
      105 +|---|---|---|                                                 
      106 +| Build time | 5 s | 15 s (transcripts and extractions cached)
          + |                                                            
      107 +| Calls | 0 cheap · 0 strong (summary cached) | 0 cheap · 1 st
          +rong (summary re-written: ledger facts changed) |             
      108 +| Promise Ledger | unavailable · no_transcripts (unchanged); j
          +udge step now `skipped` | 16 promises (was 18): 1 kept, 1 miss
          +ed, **1 quietly dropped (was 3)**, 6 not yet due, 7 can't scor
          +e; tally 1 of 3 |                                             
      109 +| Other sections | unchanged | unchanged |                    
      110 +                                                              
      111 +The remaining "quietly dropped" (advertisement spend ≤ 5% of r
          +evenue, FY26 — not mentioned in the 5 calls since Q1 FY26) is 
          +a genuine guidance item.                                      
      112 +                                                              
      113 +### Independent spot-check (11 Nov 2026, 16:20 IST)           
      114 +                                                              
      115 +Five verdicts drawn across the 4 demo dossiers with `random.Ra
          +ndom(1111)` from the 11 scored verdicts (forced: one missed, o
          +ne goalposts moved, one model-judged; then two at random). A f
          +resh subagent that had not seen this session got only each ver
          +dict, its cited PDFs and pages, downloaded the PDFs from BSE i
          +tself and read every page.                                    
      116 +                                                              
      117 +| # | Ticker | Verdict (by) | Quote 1 on page | Quote 2 on pag
          +e | Numbers match | Verdict follows | Auditor's note |        
      118 +|---|---|---|---|---|---|---|---|                             
      119 +| 1 | BAJFINANCE | missed (code): MSME growth 10–12% FY26 → 6%
          + | yes p4 | yes p4 | yes | yes | Neither call states the growt
          +h base (likely AUM YoY); Q4 p11 confirms 6% |                 
      120 +| 2 | INFY | goalposts moved (code): FY27 CC growth 1.5–3.5% →
          + 1–2% | yes p4 | yes p4 | yes | yes | Same metric and basis (Y
          +oY, constant currency) |                                      
      121 +| 3 | POLYCAB | goalposts moved (model): EPC margin "high" → "
          +mid-to-high single digits" | yes p7 | yes p8 | yes | yes, soft
          + | A real cut at the bottom of the range, but vague and undate
          +d; actual margins were already below it |                     
      122 +| 4 | BAJFINANCE | missed (code): franchise ≥ 120 M FY26 → 119
          +.3 M | yes p4 | yes p3 | yes | yes, debatable | "Well on cours
          +e to cross 120 million" is a projection; under the rule it is 
          +a miss |                                                      
      123 +| 5 | PERSISTENT | kept (code): ETR 23–23.5% FY25 → 23.2% | ye
          +s p14 | yes p13 | yes | yes | Inside the range |              
      124 +                                                              
      125 +Result: 10/10 quotes on their cited pages, numbers correct, 5/
          +5 verdicts follow from the evidence; nothing to fix. Items 3 a
          +nd 4 are softer by nature (an undated outlook; a projection ph
          +rased as "well on course") — the verdict reason already quotes
          + both calls so a reader can judge.                            
      126 +                                                              
      127 +                                                              
      128  **Friday morning (product owner, 11 Nov: cut if Friday gets ti
           ght):**
      129  - [ ] Annual report sections (headings in code) → red flags (a
           uditor opinion, contingent liabilities growth, related parties
           )
      130  - [ ] Ask: BM25 over the ticker's pages + facts → Flash-Lite (
           Groq fallback) → cited answer or "Not found in sources"

  Called ccd_turn (ctrl+o to expand)

⏺ Bash(cd ~/Documents/finn/backend && python3 - <<'EOF'
      p='finn/research/ledger.py'; s=open(p).read()…)
  ⎿  309 passed, 1 warning in 1.43s
  ⎿  Updated backend/finn/research/discover.py (+3 -1)
      107          if qe in d.decks or "nseindia.com" in t["url"]:
      108              continue
      109          label = quarter_period(qe).label
      110 -        d.decks[qe] = DocLink("investor_presentation", t["url"
          -], f"{label} investor presentation", label, t["month"], qe)   
      110 +        d.decks[qe] = DocLink(                                
      111 +            "investor_presentation", t["url"], f"{label} inves
          +tor presentation", label, t["month"], qe                      
      112 +        )                                                     
      113      for a in docs["annual_reports"]:
      114          if "nseindia.com" in a["url"]:
      115              continue
  ⎿  Updated backend/finn/research/ledger.py (+21 -3)
      448      credibility: Credibility
      449      counts: LedgerCounts
      450      settled: dict[str, date]
      451 +    # promise id → its period, for promises that are "can't sc
          +ore" only because no delivered figure was found in            
      452 +    # the calls (the deck lookup reads the deck that closes th
          +at period)                                                    
      453 +    unscored: dict[str, Period] = field(default_factory=dict) 
      454  
      455  
      456  def build_ledger(symbol: str, calls: list[Call], disc, today: 
           date, ye_month: int = 3) -> Ledger:
      457      calls = sorted(calls, key=lambda c: c.made_on)
      455 -    stmts = [_stmt(c, it, ye_month) for c in calls for it in c
          -.facts.get("guidance", []) if is_business_promise(it)]        
      458 +    transcripts = [c for c in calls if c.kind == "transcript"]
          +  # decks supply delivered figures only                       
      459 +    unscored: dict[str, Period] = {}                          
      460 +    stmts = [                                                 
      461 +        _stmt(c, it, ye_month) for c in transcripts for it in 
          +c.facts.get("guidance", []) if is_business_promise(it)        
      462 +    ]                                                         
      463      threads = group(stmts)
      464      promises: list[Promise] = []
      465      settled: dict[str, date] = {}
     ...
      547              verdict, why = "not_yet_due", f"Awaiting {period.l
           abel} results"
      548          else:
      549              why = f"No delivered figure for {period.label} fou
           nd in the sources read"
      550 +            unscored[pid] = period                            
      551          # quietly dropped: only unscored, with ≥ 2 readable la
           ter calls that never mention it
      552          dropped_note = None
      553          if verdict in ("cant_score", "not_yet_due") and delive
           red is None and not relative:
      546 -            later = [c for c in calls if c.made_on > last.made
          -_on]                                                          
      554 +            later = [c for c in transcripts if c.made_on > las
          +t.made_on]                                                    
      555              if len(later) >= 2:
      556                  terms = list(last.item.get("search_terms") or 
           []) + list(metrics.synonyms(key))
      557                  terms += [last.item.get("metric", "")]
     ...
      574              delivered_source=dsrc, dropped_note=dropped_note,
      575          ))  # fmt: skip
      576      promises.sort(key=_order)
      569 -    return Ledger(promises, credibility(promises, settled, cal
          -ls), count(promises), settled)                                
      577 +    return Ledger(promises, credibility(promises, settled, tra
          +nscripts), count(promises), settled, unscored)                
      578 +                                                              
      579 +                                                              
      580 +def next_test(promises: list[Promise], today: date) -> tuple[P
          +eriod | None, date | None, int]:                              
      581 +    """The earliest period at which a not-yet-due promise is t
          +ested, when its results are due, and how many fall due        
     … 9 more lines (ctrl+o to expand)

⏺ Contract fields for the ledger header:

⏺ Bash(python3 - <<'EOF'
      p='finn/models/research.py'; s=open(p).read()…)
  ⎿  15:from datetime import date
  ⎿  Updated backend/finn/models/research.py (+8 -0)
      180  
      181  
      182  class LedgerSection(Model):
      183 +    """Header example: '2 of 4 kept · 9 not yet due · next tes
          +t: FY27 results' — from credibility.kept/n,                   
      184 +    counts.not_yet_due and next_test_label."""                
      185 +                                                              
      186      meta: SectionMeta
      187      promises: list[Promise] = Field(default_factory=list)
      188      credibility: Credibility | None = None
      189      counts: LedgerCounts = Field(default_factory=LedgerCounts)
      190      calls_read: int = 0
      191 +    decks_read: int = Field(0, description="Investor decks rea
          +d for delivered figures the calls didn't state")              
      192 +    next_test: Period | None = Field(None, description="Earlie
          +st period at which a not-yet-due promise is tested")          
      193 +    next_test_label: str | None = Field(None, description="e.g
          +. 'FY27 results'")                                            
      194 +    next_test_on: date | None = Field(None, description="When 
          +those results should be out (period end + lag)")              
      195 +    next_test_count: int = Field(0, description="Promises that
          + fall due at next_test")                                      
      196  
      197  
      198  class SeriesSection(Model):

⏺ Now deck.py: one Flash-Lite call per deck, asking only for the metrics that
  are missing.

⏺ Write(backend/finn/research/deck.py)
  ⎿  Wrote 149 lines to backend/finn/research/deck.py
      1 """Deck lookup: delivered figures the calls didn't state, read fr
        om the investor deck that closes the period.
      2 
      3 Only for promises that are "can't score" solely because no delive
        red figure was found in the calls (an FY26 target
      4 is closed by the Q4 FY26 deck). One cheap call per deck needed — 
        never all decks — asking only for the missing
      5 metrics. The answer goes through the same checks as a transcript:
         the quote must be on the cited page, its number
      6 must be printed in the quote, and the quote must name the metric.
     … +144 lines (~7 KB) (ctrl+o to expand)

⏺ PyMuPDF splits deck table rows into separate columns, so a quote from a table
  often isn't contiguous; I'm adding a fallback that accepts the metric name and
  exact number within 250 characters on the cited page, and then wiring the
  deck step into the build. · summary

⏺ Bash(python3 - <<'EOF'
      p='finn/research/deck.py'; s=open(p).read()…)
  ⎿  All checks passed!
     309 passed, 1 warning in 1.47s
  ⎿  Updated backend/finn/research/build.py (+26 -3)
      102      progress.step("ledger", "done" if calls else "skipped", f"
           {len(d.ledger.promises)} promises")
      103      store.publish(conn, d, complete=False)
      104  
      105 +    # 5b. Decks: delivered figures the calls didn't state (one
          + cheap call per deck needed, never all decks)                 
      106 +    tags = {"symbol": symbol, "job_id": job_id}               
      107 +    if led is not None and led.unscored and disc.status == "ok
          +" and quota is None:                                          
      108 +        from finn.research import deck                        
      109 +                                                              
      110 +        progress.step("decks", "running", message="Checking in
          +vestor decks for figures the calls didn't state")             
      111 +        dr = deck.lookup(conn, router, symbol, disc, d.ledger.
          +promises, led.unscored, now, tags)                            
      112 +        if dr.found:                                          
      113 +            led = apply_ledger(d, symbol, disc, links, docs, c
          +alls, quota, now, extra=dr.calls)                             
      114 +        d.ledger.decks_read = sum(1 for x in dr.sources if x.s
          +tatus == "read")                                              
      115 +        known = {x.url for x in d.sources}                    
      116 +        d.sources += [x for x in dr.sources if x.url not in kn
          +own]                                                          
      117 +        if dr.quota is not None and dr.quota.kind == "quota": 
      118 +            quota = dr.quota                                  
      119 +        progress.step("decks", "done", f"{dr.found} of {dr.req
          +uested} missing figure(s) found in "                          
      120 +                      f"{d.ledger.decks_read} deck(s)")  # fmt
          +: skip                                                        
      121 +    else:                                                     
      122 +        progress.step("decks", "skipped", "No promise is waiti
          +ng only on a delivered figure")                               
      123 +                                                              
      124      # 6–7. Judge + reduce (strong model chain: 3.8 Flash → 3 F
           lash; never Flash-Lite). An unchanged dossier hits
      125      # the router's cache, so it costs no strong call.
      107 -    tags = {"symbol": symbol, "job_id": job_id}               
      126      if led is not None:
      127          strong_quota = run_judge(d, led, calls, router, tags, 
           progress, now)
      128      else:
     ...
      239      return f"{to_ist(dt):%H:%M} IST" if dt else "the quota res
           ets"
      240  
      241  
      224 -def apply_ledger(d: Dossier, symbol: str, disc, links, docs, c
          -alls, quota, now: datetime):                                  
      242 +def apply_ledger(d: Dossier, symbol: str, disc, links, docs, c
          +alls, quota, now: datetime, extra=()):                        
      243      from finn.research import insights
      244      from finn.research.ledger import build_ledger
      245  
     ...
      264              if sec.meta.status != "ready":  # keep a previous 
           good build's sections
      265                  sec.meta = m
      266          return None
      249 -    led = build_ledger(symbol, calls, disc, now.date(), disc.y
          -ear_end_month or 3)                                           
     … 10 more lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/deck.py (+50 -6)
      69  def _ask(p: Promise) -> str:
      70      t = p.scored_target or p.statements[-1]
      71      basis = ", ".join(x for x in (p.basis.currency, p.basis.sco
          pe, p.basis.segment) if x and x != "unspecified")
      72 -    return (f"{p.metric} — {'growth rate' if p.measure == 'grow
         -th' else 'change' if p.measure == 'change' else 'value'}"      
      73 -            f" for {p.period.label if p.period else '?'}{f' ({b
         -asis})' if basis else ''}; target was {t.raw_target}")         
      72 +    return (                                                   
      73 +        f"{p.metric} — {'growth rate' if p.measure == 'growth' 
         +else 'change' if p.measure == 'change' else 'value'}"          
      74 +        f" for {p.period.label if p.period else '?'}{f' ({basis
         +})' if basis else ''}; target was {t.raw_target}"              
      75 +    )                                                          
      76  
      77  
      78  def _names_metric(p: Promise, quote: str) -> bool:
     ...
      107          else:
      108              asks = "\n".join(f"{rid}: {_ask(p)}" for rid, p in
            ids.items())
      109              text = "\n".join(f"[[p.{i}]]\n{pg.strip()}" for i,
            pg in enumerate(strip_boilerplate(doc.pages), start=1))
      108 -            req = LLMRequest(purpose=PURPOSE, system=SYSTEM, p
          -rompt=f"Find these reported figures:\n{asks}",                
      109 -                             schema=SCHEMA, document_text=text
          -, max_output_tokens=4000, timeout_s=180, tags=tags)           
      110 +            req = LLMRequest(                                 
      111 +                purpose=PURPOSE,                              
      112 +                system=SYSTEM,                                
      113 +                prompt=f"Find these reported figures:\n{asks}"
          +,                                                             
      114 +                schema=SCHEMA,                                
      115 +                document_text=text,                           
      116 +                max_output_tokens=4000,                       
      117 +                timeout_s=180,                                
      118 +                tags=tags,                                    
      119 +            )                                                 
      120              try:
      121                  res = router.run("cheap", req)
      122              except LLMUnavailable as e:
     ...
      153          if p is None or not isinstance(f.get("value"), int | f
           loat):
      154              continue
      155          loc = chk.locate(f.get("quote"), f.get("page"), f["val
           ue"])
      146 -        if loc is None or not number_in_quote(float(f["value"]
          -), loc.quote) or not _names_metric(p, loc.quote):             
      156 +        if loc is not None and number_in_quote(float(f["value"
          +]), loc.quote) and _names_metric(p, loc.quote):               
      157 +            out.append({**f, "quote": loc.quote, "page": loc.p
          +age})                                                         
      158              continue
      148 -        out.append({**f, "quote": loc.quote, "page": loc.page}
          -)                                                             
      159 +        cell = _table_cell(p, float(f["value"]), pages, f.get(
          +"page"))                                                      
      160 +        if cell:                                              
     … 33 more lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/jobs.py (+1 -0)
      27      ("documents", "Reading transcripts and the annual report"),
      28      ("extract", "Extracting guidance, actuals and analyst quest
          ions"),
      29      ("ledger", "Scoring promises against what was delivered"),
      30 +    ("decks", "Checking investor decks for figures the calls di
         +dn't state"),                                                  
      31      ("judge", "Judging qualitative promises"),
      32      ("reduce", "Writing the summary, red flags, bull and bear")
          ,
      33      ("publish", "Publishing the dossier"),

⏺ All 309 pass. Testing the deck lookup on its own against BAJFINANCE (one
  Flash-Lite call, no strong calls). Its FY26 credit cost, ROA and ROE should be
  in the Q4 FY26 deck:

  Ran 1 shell command (ctrl+o to expand)
⏺ The BAJFINANCE decks now resolve 11 of 12 promises, up from 1 of 4, but three
  verdicts are wrong: a figure was scored against the wrong promise, tolerances
  are too loose for small targets, and display rounding hides the printed
  values. I'm fixing those three general problems next. · summary

  Searched for 1 pattern, ran 1 shell command (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/research/ledger.py'; s=open(p).read()…)
  ⎿  623:def _fmt(v: float, unit: str | None, like: str | None = None) -> s
     tr:
     624-    if unit == "PCT":
     … +5 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/deck.py (+1 -1)
      136                  "scope": f["scope"], "segment": p.basis.segmen
           t if f["scope"] == "segment" else None,
      137                  "period_text": f["period_text"], "period_type"
           : f["period_type"], "fy": f.get("fy"),
      138                  "quarter": f.get("quarter"), "half": f.get("ha
           lf"), "years": None, "quote": f["quote"],
      139 -                "page": f["page"],                            
      139 +                "page": f["page"], "for_promise": p.id,       
      140              })  # fmt: skip
      141          out.found += len(actuals)
      142          made = link.call_month or qe
  ⎿  Updated backend/finn/research/ledger.py (+35 -10)
      78      currency: str
      79      scope: str
      80      segment: str
      81 +    factor: float = 1.0  # printed unit → normalised unit (bps 
         +→ pp: 0.01)                                                    
      82  
      83      @property
      84      def made_on(self) -> date:
     ...
       88          vals = [v for v in (self.low, self.high) if v is not N
           one]
       89          return sum(vals) / len(vals) if vals else None
       90  
       91 +    def precision(self) -> float:                             
       92 +        """Half a unit of the target's last printed digit, in 
          +normalised units ('1.85%' → 0.005 pp; '40 bps' →              
       93 +        0.005 pp; '20%' → 0.5 pp): a bound can't be met by mor
          +e than the rounding of what management said."""               
       94 +        decs = 0                                              
       95 +        for v in (self.item.get("target_low"), self.item.get("
          +target_high")):                                               
       96 +            if v is not None:                                 
       97 +                txt = f"{float(v):.6f}".rstrip("0").rstrip("."
          +)                                                             
       98 +                decs = max(decs, len(txt.split(".")[1]) if "."
          + in txt else 0)                                               
       99 +        return 0.5 * 10**-decs * self.factor                  
      100 +                                                              
      101      def width(self) -> float:
      102          return (self.high - self.low) if self.low is not None 
           and self.high is not None else 0.0
      103  
     ...
      160                       it.get("years"), call.made_on, ye_month) 
            # fmt: skip
      161      seg = norm(it.get("segment") or "") if it.get("scope") == 
           "segment" else ""
      162      return Stmt(call, it, period, unit, lo * f if lo is not No
           ne else None, hi * f if hi is not None else None,
      152 -                it.get("currency", "unspecified"), it.get("sco
          -pe", "unspecified"), seg)  # fmt: skip                        
      163 +                it.get("currency", "unspecified"), it.get("sco
          +pe", "unspecified"), seg, f)  # fmt: skip                     
      164  
      165  
      166  # --- grouping -----------------------------------------------
           ------------------------------------------------------
     ...
      293                      s.period)  # fmt: skip
      294  
      295  
      285 -def _actual_delivered(t: Thread, calls: list[Call], ye_month: 
          -int) -> tuple[Figure | None, Call | None]:                    
      296 +def _actual_delivered(t: Thread, calls: list[Call], ye_month: 
          +int, pid: str | None = None):                                 
      297      s = t.stmts[-1]
      298      if s.period is None:
      299          return None, None
     ...
      301          if call.made_on < s.period.end:
     … 62 more lines (ctrl+o to expand)
  ⎿  Updated backend/tests/test_ledger.py (+21 -0)
      314      sbc = g("pat", 6.35, 6.35, unit="crore", kind="point", met
           ric="share-based payment cost", fy=2026)
      315      led = ledger([call(1, date(2024, 10, 20), [esop, sbc]), ca
           ll(2, date(2025, 1, 20)), call(3, date(2025, 4, 20))])
      316      assert led.promises == []
      317 +                                                              
      318 +                                                              
      319 +def test_bound_tolerance_follows_printed_precision():         
      320 +    # '40–50 bps' improvement delivered 36 bps → missed (a fla
          +t 0.1 pp tolerance would have kept it)                        
      321 +    assert compare("range", 0.40, 0.50, 0.36, "PCT", "neutral"
          +, precision=0.005)[0] == "missed"                             
      322 +    assert compare("range", 1.85, 1.95, 1.93, "PCT", "lower", 
          +precision=0.005)[0] == "kept"                                 
      323 +    assert compare("range", 20, 22, 19.6, "PCT", "higher", pre
          +cision=0.5)[0] == "kept"  # '20%' ≈ ±0.5 already capped       
      324 +                                                              
      325 +                                                              
      326 +def test_deck_figure_scores_only_the_promise_that_requested_it
          +():                                                           
      327 +    bps = g("debt", 10, 15, unit="bps", measure="change", metr
          +ic="cost of funds improvement", fy=2026)                      
      328 +    lvl = g("debt", 7.55, 7.6, unit="%", measure="change", met
          +ric="cost of funds", fy=2026)                                 
      329 +    led0 = ledger([call(1, date(2025, 7, 20), [bps, lvl])])   
      330 +    ids = {p.metric: p.id for p in led0.promises}             
      331 +    deck_actual = {**a("debt", 7.54, measure="change"), "metri
          +c": "cost of funds", "for_promise": ids["cost of funds"]}     
      332 +    deck = Call("deck", "https://x/deck.pdf", "Q4 FY26 investo
          +r presentation", date(2026, 4, 30), ["x"],                    
      333 +                {"guidance": [], "actuals": [deck_actual]}, NO
          +W, kind="deck")  # fmt: skip                                  
      334 +    led = ledger([call(1, date(2025, 7, 20), [bps, lvl]), deck
          +])                                                            
      335 +    by = {p.metric: p for p in led.promises}                  
      336 +    assert by["cost of funds"].delivered is not None and by["c
          +ost of funds improvement"].delivered is None                  
      337 +    assert by["cost of funds"].delivered.citation.source_type 
          +== "investor_presentation"                                    

⏺ The third assertion in my test was wrong: bounds keep their 0.1 pp cap, so
  19.6 against 20–22 is a miss. Correcting the test:

⏺ Bash(python3 - <<'EOF'
      p='tests/test_ledger.py'; s=open(p).read()…)
  ⎿  311 passed, 1 warning in 1.36s
     before {'kept': 1, 'missed': 2, 'goalposts_moved': 1, 'quietly_dropped
     ': 0, 'not_yet_due': 15, 'cant_score': 18, 'raised': 2}
     … +21 lines (ctrl+o to expand)
  ⎿  Updated backend/tests/test_ledger.py (+2 -1)
      320      # '40–50 bps' improvement delivered 36 bps → missed (a fla
           t 0.1 pp tolerance would have kept it)
      321      assert compare("range", 0.40, 0.50, 0.36, "PCT", "neutral"
           , precision=0.005)[0] == "missed"
      322      assert compare("range", 1.85, 1.95, 1.93, "PCT", "lower", 
           precision=0.005)[0] == "kept"
      323 -    assert compare("range", 20, 22, 19.6, "PCT", "higher", pre
          -cision=0.5)[0] == "kept"  # '20%' ≈ ±0.5 already capped       
      323 +    assert compare("range", 20, 22, 19.95, "PCT", "higher", pr
          +ecision=0.5)[0] == "kept"  # bound cap 0.1 pp still applies   
      324 +    assert compare("range", 20, 22, 19.6, "PCT", "higher", pre
          +cision=0.5)[0] == "missed"                                    
      325  
      326  
      327  def test_deck_figure_scores_only_the_promise_that_requested_it
           ():

⏺ Printed figures now appear as written, but the direction logic is wrong:
  cost-of-funds beats are scored as misses, and unsigned changes outside the
  range become misses too. I'll make the verdict read direction from the
  metric's own wording, and report "can't score" when no direction word exists. 
  · summary

  Searched for 2 patterns, ran 1 shell command (ctrl+o to expand)

⏺ The formatter had reflowed that call, so the whole patch aborted without
  writing anything. Reapplying it against the current text:

⏺ Bash(python3 - <<'EOF'
      p='finn/research/ledger.py'; s=open(p).read()…)
  ⎿  449:        elif direction == "neutral":
  ⎿  Updated backend/finn/research/ledger.py (+28 -3)
      367  # --- verdicts -----------------------------------------------
           --------------------------------------------------------
      368  
      369  
      370 +_LOWER_WORDS = re.compile(r"\b(cost|costs|loss|losses|npa|npas
          +|stage 3|slippage|debt|leverage|borrowing|attrition|"         
      371 +                          r"days|delinquen\w*|write[- ]?offs?|
          +provisions?)\b", re.I)                                        
      372 +_BETTER_UP = re.compile(r"\b(improv\w*|expan\w*|increas\w*|gai
          +n\w*|accretion|uplift|saving\w*|benefit)\b", re.I)            
      373 +_BETTER_DOWN = re.compile(r"\b(impact|headwind|drag|pressure|c
          +ompress\w*|dilution|erosion|hit)\b", re.I)                    
      374 +                                                              
      375 +                                                              
      376 +def direction_for(item: dict, stmts: list[Stmt]) -> str:      
      377 +    """Which way is good, decided in code: the metric key's di
          +rection; for keys without one ('other'), the metric's         
      378 +    own words (cost, loss, NPA, debt, days → lower). An unsign
          +ed change ('+40–50 bps') is read from its words —             
      379 +    'improvement/expansion/saving' (more is better) vs 'impact
          +/headwind/drag' (less is better); with neither, it            
      380 +    has no direction and an off-range result can't be scored a
          +s a miss."""                                                  
      381 +    text = f"{item.get('metric', '')} {item.get('statement', '
          +')}"                                                          
      382 +    if item.get("measure") == "change" and all((x.low or 0) >=
          + 0 and (x.high or 0) >= 0 for x in stmts):                    
      383 +        if _BETTER_DOWN.search(text):                         
      384 +            return "lower"                                    
      385 +        if _BETTER_UP.search(text):                           
      386 +            return "higher"                                   
      387 +        return "unknown"                                      
      388 +    d = metrics.direction(item.get("metric_key", "other"))    
      389 +    lower = _LOWER_WORDS.search(item.get("metric", "")) and "s
          +aving" not in text.lower()                                    
      390 +    if d == "neutral" and item.get("metric_key") in ("other", 
          +"debt") and lower:                                            
      391 +        return "lower"                                        
      392 +    return d                                                  
      393 +                                                              
      394 +                                                              
      395  def _different_measure(target: Stmt, value: float) -> bool:
      396      """A level (money, count) more than 3× or under ⅓ of its t
           arget is almost always another measure (new customers
      397      vs total customers, a segment vs the company) — never scor
           ed as a beat or a miss."""
     ...
      535          scored = [s for s in t.stmts if period is None or s.ma
           de_on <= period.end] or [last]
      536          target = scored[-1]
      537          key = s0.item["metric_key"]
      513 -        direction = metrics.direction(key)                    
      514 -        if s0.item["measure"] == "change" and all((x.low or 0)
          - >= 0 and (x.high or 0) >= 0 for x in t.stmts):               
      515 -            direction = "neutral"  # an unsigned 'impact'/'cha
          -nge' — code can't tell headwind from tailwind                 
      538 +        direction = direction_for(s0.item, t.stmts)           
      539          qual = t.key[0] == "qual"
      540          pid = hashlib.sha256(repr((symbol, t.key, s0.call.doc_
           id if qual else "")).encode()).hexdigest()[:16]
     … 9 more lines (ctrl+o to expand)

⏺ revision() must treat "unknown" like neutral, or an unsigned change would read
  as "lowered":

⏺ Bash(sed -i '' 's/        elif direction == "neutral":/        elif direction
      in ("neutral", "unknown"):/' finn/research/ledger.py && cat >>
      tests/test_ledger.py <<'…)
  ⎿  -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.htm
     l
     312 passed, 1 warning in 1.47s
  ⎿  Updated backend/finn/research/ledger.py (+6 -3)
      367  # --- verdicts -----------------------------------------------
           --------------------------------------------------------
      368  
      369  
      370 -_LOWER_WORDS = re.compile(r"\b(cost|costs|loss|losses|npa|npas
          -|stage 3|slippage|debt|leverage|borrowing|attrition|"         
      371 -                          r"days|delinquen\w*|write[- ]?offs?|
          -provisions?)\b", re.I)                                        
      370 +_LOWER_WORDS = re.compile(                                    
      371 +    r"\b(cost|costs|loss|losses|npa|npas|stage 3|slippage|debt
          +|leverage|borrowing|attrition|"                               
      372 +    r"days|delinquen\w*|write[- ]?offs?|provisions?)\b",      
      373 +    re.I,                                                     
      374 +)                                                             
      375  _BETTER_UP = re.compile(r"\b(improv\w*|expan\w*|increas\w*|gai
           n\w*|accretion|uplift|saving\w*|benefit)\b", re.I)
      376  _BETTER_DOWN = re.compile(r"\b(impact|headwind|drag|pressure|c
           ompress\w*|dilution|erosion|hit)\b", re.I)
      377  
     ...
      449          eps = _tol(cur.unit, m0, False)
      450          if abs(m1 - m0) <= eps:
      451              kind = "narrowed" if cur.width() < prev.width() - 
           eps else "none"
      449 -        elif direction == "neutral":                          
      452 +        elif direction in ("neutral", "unknown"):             
      453              kind = "revised"
      454          else:
      455              up = m1 > m0
  ⎿  Updated backend/tests/test_ledger.py (+36 -1)
      320      # '40–50 bps' improvement delivered 36 bps → missed (a fla
           t 0.1 pp tolerance would have kept it)
      321      assert compare("range", 0.40, 0.50, 0.36, "PCT", "neutral"
           , precision=0.005)[0] == "missed"
      322      assert compare("range", 1.85, 1.95, 1.93, "PCT", "lower", 
           precision=0.005)[0] == "kept"
      323 -    assert compare("range", 20, 22, 19.95, "PCT", "higher", pr
          -ecision=0.5)[0] == "kept"  # bound cap 0.1 pp still applies   
      323 +    assert (                                                  
      324 +        compare("range", 20, 22, 19.95, "PCT", "higher", preci
          +sion=0.5)[0] == "kept"                                        
      325 +    )  # bound cap 0.1 pp still applies                       
      326      assert compare("range", 20, 22, 19.6, "PCT", "higher", pre
           cision=0.5)[0] == "missed"
      327  
      328  
     ...
      338      by = {p.metric: p for p in led.promises}
      339      assert by["cost of funds"].delivered is not None and by["c
           ost of funds improvement"].delivered is None
      340      assert by["cost of funds"].delivered.citation.source_type 
           == "investor_presentation"
      341 +                                                              
      342 +                                                              
      343 +def test_direction_from_metric_words_and_unsigned_change_words
          +():                                                           
      344 +    cof = g("other", 7.55, 7.6, metric="cost of funds", fy=202
          +6)                                                            
      345 +    p = only(                                                 
      346 +        ledger(                                               
      347 +            [                                                 
      348 +                call(1, date(2025, 7, 20), [cof]),            
      349 +                call(2, date(2026, 5, 5), actuals=[{**a("other
          +", 7.54), "metric": "cost of funds"}]),                       
      350 +            ]                                                 
      351 +        )                                                     
      352 +    )                                                         
      353 +    assert p.verdict == "kept" and "beat" in p.verdict_reason.
          +text  # lower cost of funds is better                         
      354 +    imp = g("ebit_margin", 10, 15, unit="bps", measure="change
          +", metric="cost of funds improvement", fy=2026)               
      355 +    p = only(                                                 
      356 +        ledger(                                               
      357 +            [                                                 
      358 +                call(1, date(2025, 7, 20), [imp]),            
      359 +                call(2, date(2026, 5, 5), actuals=[a("ebit_mar
          +gin", 43, unit="bps", measure="change")]),                    
      360 +            ]                                                 
      361 +        )                                                     
      362 +    )                                                         
      363 +    assert p.verdict == "kept"  # an 'improvement' of 43 bps b
          +eats 10–15 bps                                                
      364 +    bare = g("ebit_margin", 10, 15, unit="bps", measure="chang
          +e", metric="ebit margin", fy=2026)                            
      365 +    p = only(                                                 
      366 +        ledger(                                               
      367 +            [                                                 
     … 6 more lines (ctrl+o to expand)

  Ran 1 shell command (ctrl+o to expand)

⏺ BAJFINANCE now reads 8 of 13 kept, so its credibility score appears and each
  deck verdict holds: credit cost and cost of funds pass, opex-to-income misses,
  and the two directionless items can't be scored. I'm adding a deck-validation
  test, then deploying and rebuilding all four demos on Render. · summary

⏺ Bash(cat > tests/test_research_deck.py <<'EOF'
      """Deck lookup validation: a deck figure needs its number and its metric's
      name on the cited page."""…)
  ⎿  -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.htm
     l
     314 passed, 1 warning in 1.67s
  ⎿  Created backend/tests/test_research_deck.py (+33 -0)
       1 +"""Deck lookup validation: a deck figure needs its number and i
         +ts metric's name on the cited page."""                         
       2 +                                                               
       3 +from datetime import date                                      
       4 +                                                               
       5 +from finn.models.research import Promise                       
       6 +from finn.research import deck                                 
       7 +from finn.research.ledger import build_ledger                  
       8 +from tests.test_ledger import call, g                          
       9 +                                                               
      10 +                                                               
      11 +def _promise(metric="credit cost", key="credit_cost") -> Promis
         +e:                                                             
      12 +    led = build_ledger("T", [call(1, date(2025, 7, 20), [g(key,
         + 1.85, 1.95, metric=metric, fy=2026)])], None,                 
      13 +                       date(2026, 11, 11))  # fmt: skip        
      14 +    return led.promises[0]                                     
      15 +                                                               
      16 +                                                               
      17 +PAGES = ["Cover", "Guidance scorecard\nCredit cost\n1.85% - 1.9
         +5%\n1.93%\nROE\n19% - 20%\n19.2%"]                             
      18 +                                                               
      19 +                                                               
      20 +def test_table_cell_fallback_when_the_row_isnt_contiguous():   
      21 +    p = _promise()                                             
      22 +    figs = deck._validate([{"request_id": "R1", "value": 1.93, 
         +"quote": "Credit cost for FY26 was 1.93%", "page": 2,          
      23 +                            "currency": "unspecified", "scope":
         + "consolidated", "period_text": "FY26",                        
      24 +                            "period_type": "fy", "fy": 2026}], 
         +{"R1": p}, PAGES)  # fmt: skip                                 
      25 +    assert len(figs) == 1 and figs[0]["page"] == 2 and "1.93%" 
         +in figs[0]["quote"] and "Credit cost" in figs[0]["quote"]      
      26 +                                                               
      27 +                                                               
      28 +def test_number_not_on_page_or_metric_not_named_is_dropped():  
      29 +    p = _promise()                                             
      30 +    wrong_num = {"request_id": "R1", "value": 2.05, "quote": "C
         +redit cost 2.05%", "page": 2}                                  
      31 +    assert deck._validate([wrong_num], {"R1": p}, PAGES) == [] 
      32 +    other = _promise("net interest margin", "nim")             
      33 +    assert deck._validate([{"request_id": "R1", "value": 1.93, 
         +"quote": "x", "page": 2}], {"R1": other}, PAGES) == []         

⏺ Bash(cd ~/Documents/finn/web && npm run -s gen:schema && npm
      run -s gen:types && npx tsc --noEmit -p . 2>&1 | tail -2; cd .. && git add
      backend web/l…)
  ⎿  wrote lib/types.ts
     71916fe Deck lookup: delivered figures from the investor deck that clo
     ses the period; ledger header fields
  ⎿  Updated web/lib/schema.json (+58 -1)
      2402      },
      2403      "LedgerSection": {
      2404        "additionalProperties": false,
      2405 +      "description": "Header example: '2 of 4 kept \u00b7 9 n
           +ot yet due \u00b7 next test: FY27 results' \u2014 from credib
           +ility.kept/n,\ncounts.not_yet_due and next_test_label.",     
      2406        "properties": {
      2407          "calls_read": {
      2408            "default": 0,
     ...
      2423            ],
      2424            "default": null
      2425          },
      2426 +        "decks_read": {                                      
      2427 +          "default": 0,                                      
      2428 +          "description": "Investor decks read for delivered f
           +igures the calls didn't state",                              
      2429 +          "title": "Decks Read",                             
      2430 +          "type": "integer"                                  
      2431 +        },                                                   
      2432          "meta": {
      2433            "$ref": "#/$defs/SectionMeta"
      2434          },
      2435 +        "next_test": {                                       
      2436 +          "anyOf": [                                         
      2437 +            {                                                
      2438 +              "$ref": "#/$defs/Period"                       
      2439 +            },                                               
      2440 +            {                                                
      2441 +              "type": "null"                                 
      2442 +            }                                                
      2443 +          ],                                                 
      2444 +          "default": null,                                   
      2445 +          "description": "Earliest period at which a not-yet-
           +due promise is tested"                                       
      2446 +        },                                                   
      2447 +        "next_test_count": {                                 
      2448 +          "default": 0,                                      
      2449 +          "description": "Promises that fall due at next_test
           +",                                                           
      2450 +          "title": "Next Test Count",                        
      2451 +          "type": "integer"                                  
      2452 +        },                                                   
      2453 +        "next_test_label": {                                 
      2454 +          "anyOf": [                                         
      2455 +            {                                                
     … 40 more lines (ctrl+o to expand)
  ⎿  Updated web/lib/types.ts (+24 -0)
      690    meta: SectionMeta;
      691    pledging: Figure[];
      692  }
      693 +/**                                                           
      694 + * Header example: '2 of 4 kept · 9 not yet due · next test: F
          +Y27 results' — from credibility.kept/n,                       
      695 + * counts.not_yet_due and next_test_label.                    
      696 + */                                                           
      697  export interface LedgerSection {
      698    calls_read: number;
      699    counts: LedgerCounts;
      700    credibility: Credibility | null;
      701 +  /**                                                         
      702 +   * Investor decks read for delivered figures the calls didn'
          +t state                                                       
      703 +   */                                                         
      704 +  decks_read: number;                                         
      705    meta: SectionMeta;
      706 +  /**                                                         
      707 +   * Earliest period at which a not-yet-due promise is tested 
      708 +   */                                                         
      709 +  next_test: Period | null;                                   
      710 +  /**                                                         
      711 +   * Promises that fall due at next_test                      
      712 +   */                                                         
      713 +  next_test_count: number;                                    
      714 +  /**                                                         
      715 +   * e.g. 'FY27 results'                                      
      716 +   */                                                         
      717 +  next_test_label: string | null;                             
      718 +  /**                                                         
      719 +   * When those results should be out (period end + lag)      
      720 +   */                                                         
      721 +  next_test_on: string | null;                                
      722    promises: MgmtPromise[];
      723  }
      724  export interface LedgerCounts {

  Ran 1 shell command (ctrl+o to expand)

⏺ While Render rebuilds, step 4, the schedule check. Today's runs from
  ingest_runs:

  Ran 1 shell command (ctrl+o to expand)

⏺ Filing checks ran every 30 minutes until 16:01 and every one ended "partial",
  and nothing has run since, even though it's now 17:05. I'm checking GitHub's
  side next, using the public read-only API. · summary

  Ran 2 shell commands (ctrl+o to expand)

⏺ The 16:30 runs aren't due yet, since it's 16:06 IST rather than 17:05. Every
  filing run since 08:31 has come back partial because Gemini refuses the
  COCHINSHIP PDF permanently, so I'm looking at the retry logic to stop it being
  retried every 30 minutes. · summary

  Searched for 1 pattern, ran 1 shell command (ctrl+o to expand)

⏺ The Gemini provider should surface refusals (promptFeedback.blockReason) as
  their own error, and the classifier should tag them "model refused" so the
  retry query stops skipping them. I'm now checking a second failure the run
  listed, 'step': 'resul…'. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ Four runs keep failing: COCHINSHIP is refused, which I'm fixing, and the ITC
  and RELIANCE cards show "couldn't verify" because their revenue doesn't match
  screener's. The tag step dies on a NUL character in one filing's text, so I'm
  stripping NUL characters from every JSON value before writing. · summary

⏺ Bash(python3 - <<'EOF'
      p='finn/db.py'; s=open(p).read()…)
  ⎿  21:_NUL = re.compile(r"(?<!\\)((?:\\\\)*)\\u0000")
     24:def _dumps(obj) -> str:
     25:    return _NUL.sub(r"\1", json.dumps(obj))
     … +5 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/classification/ladder.py (+2 -0)
      242          try:
      243              res = self.router.run("cheap", req)
      244          except LLMUnavailable as e:
      245 +            if "refused" in str(e):  # a content refusal is pe
          +rmanent: not retried every run (store retries 'llm unavailable
          +%')                                                           
      246 +                return Classification(Category.unclassified, "
          +failed", note=f"model refused: {e}"[:300])                    
      247              return Classification(Category.unclassified, "fail
           ed", note=f"llm unavailable: {e}"[:300])
      248          d = res.data
      249          try:
  ⎿  Updated backend/finn/db.py (+15 -0)
       9  import os
      10  from pathlib import Path
      11  
      12 +import json                                                    
      13 +import re                                                      
      14 +                                                               
      15  import psycopg
      16  from psycopg.rows import dict_row
      17 +from psycopg.types.json import set_json_dumps                  
      18 +                                                               
      19 +# Postgres jsonb rejects the NUL character ("\u0000 cannot be c
         +onverted to text"), and a single filing whose PDF              
      20 +# text carried one made every run's tagging step fail. Strip es
         +caped NULs (not an escaped backslash before 'u0000').          
      21 +_NUL = re.compile(r"(?<!\\)((?:\\\\)*)\\u0000")                
      22 +                                                               
      23 +                                                               
      24 +def _dumps(obj) -> str:                                        
      25 +    return _NUL.sub(r"\1", json.dumps(obj))                    
      26 +                                                               
      27 +                                                               
      28 +set_json_dumps(_dumps)                                         
      29  
      30  _ROOTS = [Path(__file__).resolve().parents[2], Path(__file__).r
          esolve().parents[1]]
      31  
  ⎿  Updated backend/finn/llm/gemini.py (+3 -0)
       96          if not r.ok:
       97              raise ProviderError(f"gemini HTTP {r.status_code}:
            {_short(r.text)}")
       98          payload = r.json()
       99 +        block = (payload.get("promptFeedback") or {}).get("blo
          +ckReason")                                                    
      100 +        if block:  # the model won't read this input at all — 
          +permanent, not worth retrying                                 
      101 +            raise ProviderError(f"gemini refused: {block}")   
      102          finish = ((payload.get("candidates") or [{}])[0]).get(
           "finishReason")
      103          if finish == "MAX_TOKENS":  # cut-off JSON — never par
           se a partial answer
      104              raise ProviderError(f"gemini output truncated at {
           req.max_output_tokens} tokens")

⏺ NULs are stripped, and a literal "\u0000" typed with a backslash is preserved.
  Tests:

⏺ Bash(python3 - <<'EOF'
      p='finn/classification/ladder.py'; s=open(p).read()…)
  ⎿  finn/db.py:7:1: I001 [*] Import block is un-sorted or un-formatted
     Found 1 error.
     [*] 1 fixable with `--fix`.
     316 passed, 1 warning in 1.64s
  ⎿  Updated backend/finn/classification/ladder.py (+1 -1)
      242          try:
      243              res = self.router.run("cheap", req)
      244          except LLMUnavailable as e:
      245 -            if "refused" in str(e):  # a content refusal is pe
          -rmanent: not retried every run (store retries 'llm unavailable
          -%')                                                           
      245 +            if "refused" in str(e):  # a content refusal is pe
          +rmanent; only 'llm unavailable…' failures are retried         
      246                  return Classification(Category.unclassified, "
           failed", note=f"model refused: {e}"[:300])
      247              return Classification(Category.unclassified, "fail
           ed", note=f"llm unavailable: {e}"[:300])
      248          d = res.data
  ⎿  Updated backend/tests/test_llm_router.py (+21 -0)
      265      assert [m for _, m in g.calls] == ["flash-38", "flash-38",
            "flash-3"] and pauses == [2.0]  # 2 attempts, not 5
      266      r.run("strong", req(purpose="research.reduce.v1", prompt="
           b"))
      267      assert [m for _, m in g.calls][-1] == "flash-3" and len(g.
           calls) == 4  # cooled: no third try on flash-38
      268 +                                                              
      269 +                                                              
      270 +def test_gemini_content_refusal_is_a_permanent_error(monkeypat
          +ch):                                                          
      271 +    from finn.llm import gemini                               
      272 +                                                              
      273 +    class Resp:                                               
      274 +        status_code, ok, text = 200, True, ""                 
      275 +                                                              
      276 +        def json(self):                                       
      277 +            return {"promptFeedback": {"blockReason": "PROHIBI
          +TED_CONTENT"}}                                                
      278 +                                                              
      279 +    monkeypatch.setattr(gemini.requests, "post", lambda *a, **
          +k: Resp())                                                    
      280 +    with pytest.raises(ProviderError, match="refused: PROHIBIT
          +ED_CONTENT"):                                                 
      281 +        gemini.Gemini("k").generate(req(), "gemini-3.5-flash-l
          +ite")                                                         
      282 +                                                              
      283 +                                                              
      284 +def test_json_written_to_postgres_has_no_nul():               
      285 +    from finn.db import _dumps                                
      286 +                                                              
      287 +    assert json.loads(_dumps({"t": "Ministry of Corporate A\x0
          +0ffairs"})) == {"t": "Ministry of Corporate Affairs"}         
      288 +    assert json.loads(_dumps({"t": "a literal \\u0000 stays"})
          +) == {"t": "a literal \\u0000 stays"}                         

⏺ Bash(../.venv/bin/ruff check --fix -q . && ../.venv/bin/ruff format -q . &&
      ../.venv/bin/ruff check -q . && ../.venv/bin/python -m pytest -q 2>&1 |
      tail -1 && cd ..…)
  ⎿  316 passed, 1 warning in 1.71s
     4f2da3c Ingest: model refusals aren't retried every run; NUL character
     s stripped from JSON written to Postgres
  ⎿  Updated backend/finn/db.py (+2 -3)
       6  
       7  from __future__ import annotations
       8  
       9 -import os                                                      
      10 -from pathlib import Path                                       
      11 -                                                               
       9  import json
      10 +import os                                                      
      11  import re
      12 +from pathlib import Path                                       
      13  
      14  import psycopg
      15  from psycopg.rows import dict_row

⏺ I pushed the commit, and the Render redeploy is safe because interrupted jobs
  resume from cache. I'm pulling up this afternoon's DECISIONS entries next. 
  · summary

⏺ Bash(cat >> docs/DECISIONS.md <<'EOF'…)  ⎿  a1bc686 DECISIONS: unseen-ticker draw, deck lookup, precision toleranc
     e, direction rules, ingest fixes
  ⎿  Updated docs/DECISIONS.md (+23 -0)
      421      - Targets for FY30 or the medium term.
      422      - Benchmark-relative guidance.
      423      - Full-year figures that appear in the deck but not in the
            call.
      424 +                                                              
      425 +## 2026-11-11 · Afternoon: acceptance on unseen tickers, deck 
          +lookup, direction and tolerance rules                         
      426 +- **Unseen-ticker draw**: `evals/research/draw_unseen.py`, see
          +d 20261111, logged. Pool: NSE EQ minus every symbol already bu
          +ilt or tested. One bank/NBFC by company name (the equity list 
          +has no industry field). One non-financial outside the Nifty 10
          +0 (NSE archive list, committed). Results are in PLAN.md.      
      427 +- **Not promises**: ESOP and share-based-payment cost schedule
          +s are excluded alongside board housekeeping. LAXMIDENTL had tw
          +o such schedules marked "quietly dropped".                    
      428 +- **Deck lookup** (product owner's step 3):                   
      429 +  - Covers promises that are "can't score" only because the ca
          +lls never printed the delivered figure.                       
      430 +  - FINN reads the investor deck for the quarter that closes t
          +he period (screener's PPT link), up to 3 decks per build, with
          + one Flash-Lite call per deck asking only for the missing metr
          +ics.                                                          
      431 +  - Checks:                                                   
      432 +    - The quote must be on the cited page, the number must app
          +ear in the quote, and the metric's name must be in the quote. 
      433 +    - Fallback for decks whose table rows PDFs split into colu
          +mns: the name and the exact number within 250 characters on th
          +e page, stored as that verbatim span.                         
      434 +  - A deck figure scores only the promise that requested it. I
          +t never adds promises, and never counts as a later call for qu
          +ietly-dropped or the trend.                                   
      435 +  - Cached per (deck sha, sorted list of requested metrics).  
      436 +  - BAJFINANCE: 11 of 12 waiting figures found in 2 decks, and
          + the tally went from 1 of 4 to 8 of 13.                       
      437 +- **Bound tolerance follows the target's printed precision**: 
          +half a unit of its last digit. "40–50 bps" is ±0.5 bp, "1.85–1
          +.95%" is ±0.005 pp. It is never above the old caps (0.1 pp, 0.
          +5 % relative). Point targets keep their ±0.5 pp / ±2.5 % allow
          +ance for spoken rounding.                                     
      438 +- **Direction when the metric key has none**:                 
      439 +  - Code reads the metric's own words: cost, loss, NPA, debt, 
          +attrition or days mean lower is better.                       
      440 +  - For an unsigned change, "improvement/expansion/saving" mea
          +ns more is better, and "impact/headwind/drag" means less is be
          +tter.                                                         
      441 +  - With neither, an off-range result is "can't score" with th
          +at reason, never a miss.                                      
      442 +- **Delivered figures are shown as printed** ("7.54 %", "43 bp
          +s"), not rounded for the reason line.                         
      443 +- **Ledger header**: `next_test`, `next_test_label` ("FY27 res
          +ults"), `next_test_on` (period end + results lag) and `next_te
          +st_count`, plus `decks_read`. The n ≥ 5 threshold is unchanged
          +.                                                             
      444 +- **Ingest**:                                                 
      445 +  - A Gemini content refusal (`promptFeedback.blockReason`) is
          + recorded as "model refused" and not retried every 30 minutes.
      446 +  - JSON written to Postgres drops NUL characters. One filing'
          +s NUL made every run's tagging step fail.                     

⏺ The decisions are recorded locally (a1bc686, pushed at wrap-up). I'm waiting
  for the 4 demo rebuilds with the deck lookup on Render; that background check
  reports when they finish.

⏺ Background command "Deploy and rebuild all 4 demos on Render with the deck
lookup" completed (exit code 0)

  Ran 1 shell command (ctrl+o to expand)

⏺ Render results are in: INFY finished at 66.7% (4 of 6 kept) and BAJFINANCE at
  61.5% (8 of 13 kept), while PERSISTENT and POLYCAB found nothing new. I'm
  fixing the router bug that makes gemini-3.5-flash wrongly report its daily
  budget as reached, because its count also includes every gemini-3.5-flash-lite
  call. · summary

⏺ Bash(cd ~/Documents/finn/backend && python3 - <<'EOF'
      p='finn/llm/router.py'; s=open(p).read()…)
  ⎿  memory-log patched
     91:            and (model is None or r["model"] == model)
     92-            and (purpose_prefix is None or r["purpose"].startswith(
     purpose_prefix))
  ⎿  Updated backend/finn/llm/router.py (+5 -3)
      123          )  # fmt: skip
      124  
      125      def count_today(self, provider: str, model: str | None = N
           one, purpose_prefix: str | None = None) -> int:
      126 -        # Gemini reports the served version (e.g. 'gemini-3.8-
          -flash-001'), so a model matches by prefix.                    
      126 +        # A model matches itself and its served versions ('gem
          +ini-3.8-flash-001') — never a longer sibling name:            
      127 +        # a plain prefix made 'gemini-3.5-flash' count every '
          +gemini-3.5-flash-lite' call against its own 20/day.           
      128          r = self.conn.execute(
      129              "select count(*) as n from public.llm_calls where 
           provider = %s and created_at >= "
      130              "(date_trunc('day', now() at time zone 'America/Lo
           s_Angeles') at time zone 'America/Los_Angeles') "
      130 -            "and (%s::text is null or model like %s || '%%') a
          -nd (%s::text is null or purpose like %s || '%%')",            
      131 -            (provider, model, model, purpose_prefix, purpose_p
          -refix),                                                       
      131 +            "and (%s::text is null or model = %s or model ~ ('
          +^' || regexp_replace(%s, '([.+*?^$()])', '\\\1', 'g') "       
      132 +            "|| '-[0-9]+$')) and (%s::text is null or purpose 
          +like %s || '%%')",                                            
      133 +            (provider, model, model, model, purpose_prefix, pu
          +rpose_prefix),                                                
      134          ).fetchone()
      135          return int(r["n"])
      136  

⏺ The in-memory log already matched exactly; only the Postgres query used a
  prefix. Checking the fixed query against today's data:

  Ran 1 shell command (ctrl+o to expand)

⏺ The three parked summaries will run on gemini-3.5-flash, which has spare
  quota, so I'm committing and deploying next. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ Waiting on the resumed builds; they report when done. After that: the quote
  check across all four, fixture regeneration, and the 16:30 schedule check.

⏺ Background command "Deploy the count fix, resume parked builds, print results"
completed (exit code 0)

  Ran 1 shell command (ctrl+o to expand)

⏺ INFY is finished and BAJFINANCE has its new summary, with one unsupported
  sentence dropped. PERSISTENT and POLYCAB are still parked, so I'm checking why
  they stopped. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ The strong models are all unavailable until 12 Nov 13:30 IST after
  gemini-3.5-flash returned a 429 with no quota. PERSISTENT and POLYCAB keep
  their earlier summaries and resume automatically after the reset; I'm running
  the final quote and deck-citation check across all four, then exporting the
  fixtures from Render. · summary

⏺ Bash(../.venv/bin/python - <<'EOF'
      import json, urllib.request…)
  ⎿  PERSISTENT: transcript quotes 33/33, deck quotes 0/0 | tally 1 of 2 ·
     4 not yet due · 5 can't score · next test: FY27 results | decks read 1
     INFY: transcript quotes 44/44, deck quotes 2/2 | tally 4 of 6 · 66.7%
     … +8 lines (ctrl+o to expand)
  ⎿  4 files changed (binary, mode only or too large to show)

⏺ All 183 transcript quotes and 13 deck quotes check out on their cited pages.
  Next I'm updating the PLAN and checking CI. · summary

⏺ Bash(cd ~/Documents/finn && python3 - <<'EOF'
      p='docs/PLAN.md'; s=open(p).read()…)
  ⎿  8d1135e Fixtures and PLAN: deck lookup results; 196/196 cited quotes v
     erified on Render dossiers
     ci push completed success 9b0ccbe
     … +7 lines (ctrl+o to expand)
  ⎿  Updated docs/PLAN.md (+15 -1)
      33  - [x] Tests: dedup, threading, unit normalisation, classificati
          on rules, LLM router — 105 passing
      34  - [x] Run against tickers outside the demo set (TRENT, POLYCAB)
           — clean
      35  - [x] **Daily job verified on GitHub Actions** — run 4280431844
          1 (dispatched 10 Nov 16:33 IST, commit `85ccaa4`): success in 2
           m 54 s; `ingest_runs` #5 status ok, 0 failures; NSE reachable 
          from the runner for every source; prices skipped (exchange holi
          day).
      36 -- [ ] **Confirm the schedule fires.** No scheduled `ingest` run
         - had started by 16:40 IST on 10 Nov (new crons can take a while
         - to register on GitHub). Check on 11 Nov that the 30-min filing
         - checks (`check_filings`) and the 16:30 daily run appear in `in
         -gest_runs` with trigger `schedule`.                            
      36 +- [ ] **Confirm the schedule fires.** *(11 Nov: see the schedul
         +e check under Phase 3.)* No scheduled `ingest` run had started 
         +by 16:40 IST on 10 Nov (new crons can take a while to register 
         +on GitHub). Check on 11 Nov that the 30-min filing checks (`che
         +ck_filings`) and the 16:30 daily run appear in `ingest_runs` wi
         +th trigger `schedule`.                                         
      37  - [x] **Review the eval labels** — reviewed 10 Nov: 4 corrected
          , 7 checked against the PDF and confirmed; material-over-routin
          e rule added (`05536be`).
      38  - [ ] **Held-out eval set** — moved to Phase 5 (below).
      39  - [x] **Content-free newspaper ads** read by the model from the
          ir first PDF pages — full-ladder eval 98.3 %; 20 of 49 stored a
          ds turned out material (see DECISIONS, "Ambiguous between routi
          ne and material").
     ...
      125  Result: 10/10 quotes on their cited pages, numbers correct, 5/
           5 verdicts follow from the evidence; nothing to fix. Items 3 a
           nd 4 are softer by nature (an undated outlook; a projection ph
           rased as "well on course") — the verdict reason already quotes
            both calls so a reader can judge.
      126  
      127  
      128 +### Deck lookup (11 Nov 2026, 16:05 IST) — `71916fe`, count fi
          +x `9b0ccbe`                                                   
      129 +                                                              
      130 +Promises that were can't-score only because the call never pri
          +nted the delivered figure now read the deck for the quarter th
          +at closes the period (one Flash-Lite call per deck).          
      131 +                                                              
      132 +| Ticker | Decks read | Waiting figures found | Tally before →
          + after | Header now |                                         
      133 +|---|---|---|---|---|                                         
      134 +| BAJFINANCE | 2 (Q4 FY26, Q4 FY25) | 11 of 12 | 1 of 4 → **8 
          +of 13 · 61.5%** | 15 not yet due · next test: FY27 results (14
          +) |                                                           
      135 +| INFY | 1 (Q4 FY25) | 2 of 2 | 2 of 4 → **4 of 6 · 66.7%** | 
          +5 not yet due · next test: FY27 results (5) |                 
      136 +| PERSISTENT | 1 | 0 of 1 | 1 of 2 → 1 of 2 | 4 not yet due · 
          +next test: FY27 results |                                     
      137 +| POLYCAB | 0 (nothing waiting on a figure) | — | 0 of 1 | 8 n
          +ot yet due · next test: FY28 results |                        
      138 +                                                              
      139 +Quote check on the deployed dossiers (every cited quote, all s
          +ections): **183/183 transcript quotes and 13/13 deck quotes on
          + their cited pages.** Fixtures regenerated from Render.       
      140 +Strong models: all four are out for the Pacific day (3.8 Flash
          +, 3 Flash and 3.6 Flash used; 3.5 Flash answers our requests w
          +ith a quota 429 — it has no free quota on this key). PERSISTEN
          +T and POLYCAB keep this afternoon's 3.6 Flash summaries; their
          + parked jobs rewrite them after 13:30 IST on 12 Nov automatica
          +lly.                                                          
      141 +                                                              
      142  **Friday morning (product owner, 11 Nov: cut if Friday gets ti
           ght):**
      143  - [ ] Annual report sections (headings in code) → red flags (a
           uditor opinion, contingent liabilities growth, related parties
           )
      144  - [ ] Ask: BM25 over the ticker's pages + facts → Flash-Lite (
           Groq fallback) → cited answer or "Not found in sources"

⏺ CI is green through 9b0ccbe, and while I wait for the 16:30 runs, I'm testing
  the deck lookup on the unseen LAXMIDENTL using only Flash-Lite. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ The deck lookup found 2 of 3 waiting figures on the unseen ticker, so
  LAXMIDENTL's FY26 margin target is now a cited miss at 10.4%. The traceback
  came from my print script rather than the API, and I'm recording the result
  next. · summary

⏺ Bash(python3 - <<'EOF'
      p='docs/PLAN.md'; s=open(p).read()…)
  ⎿  16:12 IST
  ⎿  Updated docs/PLAN.md (+2 -0)
      110  
      111  The remaining "quietly dropped" (advertisement spend ≤ 5% of r
           evenue, FY26 — not mentioned in the 5 calls since Q1 FY26) is 
           a genuine guidance item.
      112  
      113 +**Run 3 (LAXMIDENTL with the deck lookup, `9b0ccbe`, job 45):*
          +* decks 2 read, 2 of 3 waiting figures found; FY26 PAT margin 
          +13–15% → **missed** at 10.4% (Q4 FY26 investor presentation); 
          +tally 1 of 3 → 1 of 4; header "1 of 4 kept · 6 not yet due · n
          +ext test: FY27 results (5)". 2 Flash-Lite calls, no strong cal
          +l available (summary refresh parked until the 13:30 IST reset;
          + the earlier summary stays).                                  
      114 +                                                              
      115  ### Independent spot-check (11 Nov 2026, 16:20 IST)
      116  
      117  Five verdicts drawn across the 4 demo dossiers with `random.Ra
           ndom(1111)` from the 11 scored verdicts (forced: one missed, o
           ne goalposts moved, one model-judged; then two at random). A f
           resh subagent that had not seen this session got only each ver
           dict, its cited PDFs and pages, downloaded the PDFs from BSE i
           tself and read every page.

⏺ It's 16:12. The 16:30 daily run and the 16:31 filing check (the first on the
  refusal/NUL fix) aren't due yet. A background check waits for them, up to
  17:15 IST:

  Ran 1 shell command (ctrl+o to expand)

⏺ While that waits, the Friday list in PLAN.md gets this afternoon's
  carry-overs:

⏺ Bash(python3 - <<'EOF'
      p='docs/PLAN.md'; s=open(p).read()…)
  ⎿  5bedb20 PLAN: LAXMIDENTL deck run; Friday list (cost report, results r
     econciliation, summary reuse)
  ⎿  Updated docs/PLAN.md (+5 -1)
      146  - [ ] Ask: BM25 over the ticker's pages + facts → Flash-Lite (
           Groq fallback) → cited answer or "Not found in sources"
      147  - [ ] Nightly refresh on Actions (code-only recompute; rebuild
            only on a new document; first-time builds only for the 4 demo
            tickers); DB size guard. **Reuse the previous summary unless 
           the document set changed**: REDUCE's facts include the day's m
           arket cap, so a forced rebuild spends a strong call even with 
           no new document
      148  - [ ] On-demand NSE dispatch (section above) → `exchange_data`
      149 -- [ ] Two tickers outside the demo set (one bank); cost report
          -; README                                                      
      149 +- [x] Two tickers outside the demo set — seeded draw JPOLYINVS
          +T (NBFC/holding co, no transcripts → labelled partial) and LAX
          +MIDENTL (full dossier); runs 1–3 recorded above               
      150 +- [ ] Cost report (per-dossier tokens/cost from `research_jobs
          +.stats` / `llm_calls.request->tags`); README research section 
      151 +- [ ] Results cards: ITC and RELIANCE revenue doesn't reconcil
          +e with screener (ITC ~50 % higher: gross vs net of excise/GST?
          +) — logged as a run failure every 30 min; decide the reconcili
          +ation or log it as a card state, not a run failure            
      152 +- [ ] Deck lookup: guidance items the extraction labels `chang
          +e` that are really levels (BAJFINANCE "cost of funds 7.75–7.85
          +%") stay can't-score — consider a MAP prompt v2 note on measur
          +e                                                             
      153 +- [ ] Summary refresh reuse: nightly/forced rebuilds re-run RE
          +DUCE whenever any fact changes (market cap moves daily); reuse
          + the stored summary unless the document set or ledger verdicts
          + changed                                                      
      154  - [x] Frontend fixtures: validated INFY, BAJFINANCE, POLYCAB d
           ossiers in `web/public/fixtures/` (`python -m jobs.research ex
           port`; built locally against Supabase — rebuild on Render once
            §7 is set)
      155  
      156  ## Phase 5

⏺ The background check reports the 16:30 runs when they finish. Then I'll tick
  or diagnose the schedule item and do the final checks: tests, CI and /version.

⏺ Background command "Wait for the 16:30 daily and filing runs, then list them"
completed (exit code 0)

  Ran 1 shell command (ctrl+o to expand)

⏺ The daily run finished at 16:37 and the queued 16:30 filing check ran at
  16:38, with COCHINSHIP now marked "model refused" and the NUL-character
  failure gone. The runs still show "partial" only because of the ITC and
  RELIANCE reconciliation, which is on the Friday list, and I'm ticking that off
  next. · summary

⏺ Bash(python3 - <<'EOF'
      p='docs/PLAN.md'; s=open(p).read()…)  ⎿  d86c947 PLAN: schedule confirmed firing (filings every 30 min, daily 1
     6:31 by scheduler)
  ⎿  Updated docs/PLAN.md (+1 -1)
      33  - [x] Tests: dedup, threading, unit normalisation, classificati
          on rules, LLM router — 105 passing
      34  - [x] Run against tickers outside the demo set (TRENT, POLYCAB)
           — clean
      35  - [x] **Daily job verified on GitHub Actions** — run 4280431844
          1 (dispatched 10 Nov 16:33 IST, commit `85ccaa4`): success in 2
           m 54 s; `ingest_runs` #5 status ok, 0 failures; NSE reachable 
          from the runner for every source; prices skipped (exchange holi
          day).
      36 -- [ ] **Confirm the schedule fires.** *(11 Nov: see the schedul
         -e check under Phase 3.)* No scheduled `ingest` run had started 
         -by 16:40 IST on 10 Nov (new crons can take a while to register 
         -on GitHub). Check on 11 Nov that the 30-min filing checks (`che
         -ck_filings`) and the 16:30 daily run appear in `ingest_runs` wi
         -th trigger `schedule`.                                         
      36 +- [x] **Confirm the schedule fires.** Verified 11 Nov 2026 in `
         +ingest_runs`: scheduler-triggered `check_filings` every 30 min 
         +from 08:31 to 16:38 IST (the 08:00 slot is outside the 08:30 wi
         +ndow; the 16:30 slot queued behind the daily run in the shared 
         +concurrency group and ran at 16:38), `ingest_daily` at 16:31 (t
         +rigger `scheduler`), alerts at 00:43 and 07:00. Runs end `parti
         +al` only because ITC/RELIANCE results don't reconcile with scre
         +ener (Friday item). Two causes fixed on the way (`4f2da3c`): a 
         +Gemini content refusal on one COCHINSHIP PDF was retried every 
         +run, and a NUL character in one filing failed the whole tagging
         + step on every run.                                            
      37  - [x] **Review the eval labels** — reviewed 10 Nov: 4 corrected
          , 7 checked against the PDF and confirmed; material-over-routin
          e rule added (`05536be`).
      38  - [ ] **Held-out eval set** — moved to Phase 5 (below).
      39  - [x] **Content-free newspaper ads** read by the model from the
          ir first PDF pages — full-ladder eval 98.3 %; 20 of 49 stored a
          ds turned out material (see DECISIONS, "Ambiguous between routi
          ne and material").

  Called ccd_turn (ctrl+o to expand)

⏺ Final checks: tests, lint, generated types up to date, CI and /version.

  Ran 2 shell commands (ctrl+o to expand)

⏺ Render redeploys only on backend commits, and the last one is 9b0ccbe, so the
  /version check should compare against that instead of HEAD. I'm now checking
  CI on HEAD. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ Background command "Run tests, lint, schema check; confirm /version and CI for
HEAD" failed with exit code 144

⏺ CI is green on every commit through HEAD (d86c947); the stopped background
  check is expected. One lesson worth keeping for future sessions: updating the
  deploy-check memory note.

  Called ccd_turn, ran 1 shell command, recalled 1 memory, wrote 1 memory (ctrl+o to expand)

⏺ All four steps are done and verified, finishing at 16:52 IST. Nothing needs a
  dashboard click from you.

  1. Unseen tickers: the seed (20261111, evals/research/draw_unseen.py) picked
  JPOLYINVST (a holding/NBFC company) and LAXMIDENTL (Laxmi Dental). I built
  both on Render with no code changes first.
  - First run:
    - JPOLYINVST took 8 s and 1 strong call. It has no transcripts, so it's a
      clearly labelled partial dossier: the ledger, analysts and drivers say "no
      transcripts", everything else is ready.
    - LAXMIDENTL took 256 s, with 8 Flash-Lite and 2 strong calls. It's a full
      dossier: 18 promises, 432 quotes checked.
  - Two general bugs fixed:
    - ESOP cost schedules had entered the ledger and two were marked "quietly
      dropped".
    - The judge step showed "pending" when there was no ledger.
  - Second run: 5 s and 15 s, with 3 quietly-dropped verdicts reduced to 1
    genuine one. Before and after are both in PLAN.md (719bd7e, 12cfdb1).

  2. Spot-check: a fresh subagent downloaded the PDFs itself and checked 5
  verdicts (seed 1111). All 10 quotes were on their cited pages, the numbers
  matched, and all 5 verdicts follow from the evidence. It called two softer:
  POLYCAB's undated EPC margin outlook, and BAJFINANCE's "well on course to
  cross 120 million". Nothing needed fixing. The table is in PLAN.md.

  3. Deck lookup: done before the 18:30 time-box (71916fe, 9b0ccbe).
  - Credibility now shows on two demo tickers:
    - BAJFINANCE went from 1 of 4 to 8 of 13 kept (61.5%), with 11 figures from
      2 decks.
    - INFY went from 2 of 4 to 4 of 6 kept (66.7%).
    - LAXMIDENTL gained a cited miss: FY26 PAT margin 10.4% against a 13–15%
      target.
  - The ledger header is in the contract: fields for decks read, the next test
    and how many promises fall due then. It renders as "8 of 13 kept · 15 not
    yet due · next test: FY27 results". The n ≥ 5 threshold is unchanged.
  - Testing exposed four general bugs, all fixed:
    - A deck figure scored the wrong promise.
    - Tolerance was too loose for basis-point targets.
    - There was no direction for metrics like "cost of funds", so lower cost
      read as a miss.
    - 3.5 Flash's daily count included every 3.5 Flash-Lite call.
  - Quote check: all 183 transcript quotes and 13 deck quotes on the deployed
    demo dossiers are on their cited pages. The fixtures were regenerated from
    Render (8d1135e).

  4. Schedule: it fires. Filing checks ran every 30 minutes from 08:31 to 16:38,
  and the daily run at 16:31, all triggered by the scheduler. Every run ended
  "partial" because of two bugs, both fixed (4f2da3c):
  - Gemini refuses one COCHINSHIP PDF, and that was retried every run.
  - One filing's NUL character made the whole tagging step fail every run.

  Runs now stay "partial" only because ITC and RELIANCE results don't reconcile
  with screener. That's on the Friday list. The schedule item is ticked
  (d86c947).

  Wrap-up:
  - Tests and CI: 316 tests pass, and CI is green through HEAD (d86c947).
  - Deploy: Render serves 9b0ccbe, the last backend commit. Later commits were
    docs and fixtures only, which Render doesn't redeploy for.

  Moved to Friday:
  - Annual-report red flags, Ask, the nightly refresh, NSE enrichment and the
    cost report.
  - The ITC/RELIANCE revenue reconciliation.
  - Reusing the stored summary when nothing material changed.

  What you should know: every strong model is out of quota until 13:30 IST on 12
  Nov. Google counts failed attempts, and gemini-3.5-flash turned out to have
  no free quota on this key. Until the reset:
  - PERSISTENT and POLYCAB keep this afternoon's clean summaries. Their
    verdicts, counts and header are current, and their summaries refresh
    automatically after the reset.
  - LAXMIDENTL's summary also refreshes then.

  The frontend wasn't touched.

❯ /export docs/ai-logs/phase-0-setup.md                                         
  ⎿  Conversation exported to:
     ~/Documents/finn/docs/ai-logs/phase-0-setup.md