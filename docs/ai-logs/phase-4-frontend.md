▗ ▗   ▖ ▖  Claude Code v2.1.325
           Opus 5.5 · Claude Pro
 ▘▘   ▝▝   ~/Documents/finn


❯ Phase 4 — Frontend (Thu 12 Nov)                                               
                                                                                
  Read first: CLAUDE.md; docs/PRODUCT.md sections 3, 4, 7, 8, 9, 11, 14;        
  docs/DECISIONS.md; docs/PLAN.md; web/lib/types.ts; the fixtures in            
  web/public/fixtures/.                                                         
                                                                                
  Goal: the product experience. Evaluators weigh this most: dense, calm,        
  editorial, fast. No AI slop: no walls of prose, no generic dashboard look, no 
  decorative gradients or emoji-heavy UI. Colour only for signal.               
                                                                                
  Propose a plan first and wait for my approval. The plan must include:         
  A. Visual direction: type scale, colour tokens (light + dark), spacing, how a 
  card looks, and one ASCII sketch each of the Brief and the Promise Ledger at  
  375 px.                                                                       
  B. Screen list and component breakdown, reusing the Phase 2 card components.  
  C. How we get <1 s first paint on a phone while Render may be cold: render    
  the last Brief from localStorage (or the static showcase snapshot)            
  immediately, then refresh from the API.                                       
  D. Build order with a cut line: what ships tonight no matter what, and what   
  moves to Friday.                                                              
  E. How "What you're watching" gets drivers for the 18 holdings, given the     
  Gemini quota. Drivers need only Flash-Lite extraction, not strong calls.      
  Propose how and when to queue those builds without touching the strong quota. 
                                                                                
  After I approve, work on your own until done. Don't ask me questions unless   
  something needs a dashboard click or can't be undone. Record choices in       
  DECISIONS.md.                                                                 
                                                                                
  Screens, in priority order:                                                   
  1. Brief (P0):                                                                
     - header with window name, counts, est. time saved (document the formula   
  and label it "est."), freshness "Data as of HH:MM IST";                       
     - window chips;                                                            
     - results-season strip;                                                    
     - ranked cards (all card types);                                           
     - "Why is this #1?" breakdown;                                             
     - event thread timeline;                                                   
     - swipe right = Reviewed, left = Not useful with scope choice: commit past 
  40% drag, spring back otherwise, haptics where supported (navigator.vibrate   
  is Android only; fine to skip on iOS);                                        
     - undo toast ~5 s, with weight changes applied only after it expires;      
     - "Reviewed today" section;                                                
     - hidden drawer grouped by reason;                                         
     - caught-up state.                                                         
  2. Research (P0):                                                             
     - ticker search with autocomplete over the NSE equity list;                
     - build progress (poll the job);                                           
     - dossier sections, each rendering its own status. Sections with status    
  building + reason not_built_yet (red flags, exchange data) show a quiet       
  "Coming soon" line, never an error.                                           
  3. Promise Ledger (P0, the hero):                                             
     - header "8 of 13 kept · 15 not yet due · next test: FY27 results";        
     - % score only when n ≥ 5;                                                 
     - verdict list with ✅ ❌ ↘ ↗ 🔇 states;                                   
     - original vs revised target;                                              
     - every verdict and number tappable → provenance drawer (document, page,   
  quote, link to the PDF page).                                                 
  4. Evaluator experience (P0):                                                 
     - desktop widths: landing with a live phone-frame preview + QR "Open on    
  your phone";                                                                  
     - phones go straight into the app with the demo portfolio pre-loaded, no   
  login;                                                                        
     - 3-step skippable first-run tour: swipe to triage, tap a number for its   
  source, research any ticker;                                                  
     - "Showcase replay" toggle (clearly labelled) loading the saved snapshot   
  day.                                                                          
  5. Portfolio (P1):                                                            
     - holdings with weight, day change, sparkline, latest event, status dot;   
     - "What you're watching": suggested drivers with one-tap confirm, shown    
  where a dossier exists, otherwise "Drivers appear after research";            
     - upcoming-events calendar; results scoreboard;                            
     - paste/CSV import (quantity or weight %, stored in the browser).          
  6. Rules (P1):                                                                
     - thresholds, categories, budget, quiet hours, snoozes;                    
     - feedback adjustments with Reset;                                         
     - Connect Telegram (reuse /connect), with the privacy wording from         
  DECISIONS exactly.                                                            
  7. Ask (P1): the Ask endpoint isn't built yet (Friday). Build the bar and 3   
  context-aware suggested chips per screen; for now a chip jumps to the dossier 
  section or card that answers it. Design it so wiring /ask on Friday is a      
  small change.                                                                 
  8. PWA (P2): manifest, icons, offline cache of the latest Brief. Web push is  
  below the cut line (Telegram covers push).                                    
                                                                                
  Rules:                                                                        
  - Conventions: ₹ Cr with Indian separators, IST, Q2 FY27 labels, tabular      
  numerals, thumb-zone primary actions, 44 px tap targets.                      
  - Holdings and feedback rules live in localStorage. /brief gets symbols +     
  weights only; quantities never leave the phone.                               
  - Develop Research against the fixtures. Don't trigger dossier rebuilds; the  
  strong-model quota is shared with evaluators.                                 
  - Every screen has loading, empty, error and stale states.                    
  - Check your own work: screenshot every screen at 375 px and at desktop       
  width, light and dark, and fix what looks off before telling me it's done.    
  Make sure the Vercel deploy builds and the deployed site works.               
                                                                                
  Acceptance: on my phone I can triage the Brief, open a card's source,         
  research a ticker and read its Promise Ledger with provenance, one-handed and 
  without confusion; on a laptop I see the QR landing.                          

  Read 3 files, listed 1 directory, called ccd_turn, ran 3 shell commands (ctrl+o to expand)

⏺ Reading the contracts and existing web code now; next I'll check the backend
  API surface (/brief, research, snapshot) before drafting the plan.

  Read 1 file (ctrl+o to expand)

⏺ Explore(Map backend API for frontend)
  ⎿  Backgrounded agent (↓ to manage · ctrl+o to expand)

  Listed 1 directory, ran 4 shell commands (ctrl+o to expand)

⏺ Waiting on the backend API survey (brief/research/snapshot endpoints) to
  finish; meanwhile I've read the spec, decisions, types, existing card
  components and fixtures.

  Ran 3 shell commands (ctrl+o to expand)

⏺ Drafting the plan file while the backend survey finishes.

  Ran 1 shell command (ctrl+o to expand)

⏺ Agent "Map backend API for frontend" finished · 2m 18s

⏺ The backend survey found gaps that matter for the plan: no showcase mode, no
  season strip or portfolio endpoint, hidden-drawer counts without items, and no
  map-only build mode for drivers. I'm checking feedback multipliers and job
  claim order before writing the plan. · summary

  Ran 2 shell commands (ctrl+o to expand)

⏺ I have what I need. Writing the plan now.

  Called ccd_turn (ctrl+o to expand)

⏺ Updated plan
  ⎿  /plan to preview

  Called ccd_turn (ctrl+o to expand)
  ⎿  Error: The user doesn't want to proceed with this tool use. The tool use 
     was rejected (eg. if it was a file edit, the new_string was NOT written to 
     the file). To tell you how to proceed, the user said:
     Approved with these amendments. Record them in DECISIONS.md.

     1. Push and verify the deployed site after step 3 (Brief) and after step 5 
     (Ledger), not only at the end.
     2. No empty tabs: Portfolio lists the holdings with their latest Brief 
     event; Rules has Connect Telegram + Reset. Add a visible "Connect Telegram"
     entry on the Brief too.
     3. Drivers queue: before enqueuing, read today's remaining Flash-Lite count
     from llm_calls and cap drivers at 50 (failed attempts count against 
     quota). Skip enqueuing if remaining headroom after 50 would be under 150.
     4. All strong models are out of quota until 13:30 IST. BuildProgress must 
     explain that clearly and show the ready sections meanwhile. First-time 
     builds ask for a one-tap confirmation before starting.
     5. Verify the landing iframe works on the deployed site (no X-Frame-Options
     conflict).
     6. Screenshots: 375 px light + dark for Brief, Research, Ledger and the 
     provenance sheet; 1280 px for the landing only. Spend the saved time on 
     loading, error and stale states.

     … +1 line (ctrl+o to expand)

⏺ The plan is approved with your amendments. I'll fold them into the plan file
  and exit plan mode so I can start building.

⏺ Updated plan
  ⎿  /plan to preview

⏺ User approved Claude's plan
  ⎿  Plan saved to: 
     ~/.claude/plans/pasted-content-id-fb24-phase-4-immutable-crown.md · /plan 
     to edit
     Phase 4 — Frontend plan

     Amendments (product owner, approved; recorded in DECISIONS.md)

     1. Push and verify the deployed site after step 3 (Brief) and after step 5
        (Ledger), as well as at the end.
     2. No empty tabs. Portfolio lists the holdings, each with its latest event
        from the Brief. Rules has Connect Telegram and Reset. The Brief also
        gets a visible "Connect Telegram" entry.
     3. Drivers queue:
        - Before enqueuing, read today's remaining Flash-Lite count from
          llm_calls; failed attempts count against the quota.
        - Cap drivers at 50 calls.
        - Skip enqueuing if the headroom left after those 50 would be under 150.
     4. Every strong model is out of quota until 13:30 IST.
        - BuildProgress explains this clearly and shows the ready sections
          meanwhile.
        - A first-time build asks for one-tap confirmation before it starts.
     5. Verify the landing iframe works on the deployed site, with no
        X-Frame-Options conflict.
     6. Screenshots:
        - 375 px, light and dark: Brief, Research, Ledger and the provenance
          sheet.
        - 1280 px: the landing only.
        - The time saved goes into the loading, error and stale states.
     - The visual direction stays exactly as proposed. Work autonomously; ask
       only for dashboard clicks or irreversible steps.

     Context

     The backend is in place: Brief ranking, cards, Telegram, and research
     dossiers with the Promise Ledger. The web app is still a skeleton: a
     health-check /, /e/[id], /connect and the Phase 2 card components. This
     phase builds the product experience the evaluators will judge. It should be
     dense, calm, editorial and fast, phone-first, with the QR landing on
     laptops.

     Backend gaps found while planning. The P0 screens need these, so the plan
     adds small, backward-compatible backend pieces:
     - /brief returns hidden-drawer counts but not the items (the spec says
       every item stays tappable).
     - /brief has no season strip, no time-saved inputs and no showcase mode.
       Its response has no Pydantic model, so it isn't in types.ts.
     - Feedback multipliers (×0.8, bounds) live only in Python
       (finn/ranking/feedback.py). The phone must not copy them.
     - Drivers come only from a full dossier build, which also spends strong
       calls. There's no endpoint to fetch drivers for 18 symbols without
       pulling 18 × 300 KB dossiers.
     - There is no portfolio endpoint (prices, day change, calendar,
       scoreboard). This is P1, so it's Friday.

     ---

     A. Visual direction

     Feel: printed financial page, not dashboard. Ink on warm paper, hairline
     rules between items, a serif for what you read, sans for what you scan,
     tabular numerals everywhere. No shadows, gradients or decorative colour.

     Type (next/font, latin subset, preloaded, display: swap):

     ┌──────────┬─────────────────────┬───────────────┬───────────────────────┐
     │  Token   │        Font         │   Size/line   │          Use          │
     ├──────────┼─────────────────────┼───────────────┼───────────────────────┤
     │          │                     │ 30/34,        │ Screen titles, the    │
     │ display  │ Newsreader 500      │ −0.01em       │ ledger tally "8 of 13 │
     │          │                     │               │  kept"                │
     ├──────────┼─────────────────────┼───────────────┼───────────────────────┤
     │ title    │ Newsreader 500      │ 22/28         │ Company name, sheet   │
     │          │                     │               │ titles                │
     ├──────────┼─────────────────────┼───────────────┼───────────────────────┤
     │ headline │ Newsreader 500      │ 18/24         │ Card headline         │
     ├──────────┼─────────────────────┼───────────────┼───────────────────────┤
     │ body     │ Geist 400           │ 15/22         │ So-what, prose,       │
     │          │                     │               │ claims                │
     ├──────────┼─────────────────────┼───────────────┼───────────────────────┤
     │ small    │ Geist 400           │ 13/18         │ Meta, tables,         │
     │          │                     │               │ timeline              │
     ├──────────┼─────────────────────┼───────────────┼───────────────────────┤
     │ micro    │ Geist 600, caps,    │ 11/14         │ Eyebrows: "RESULTS",  │
     │          │ +0.06em             │               │ "PROMISE LEDGER"      │
     ├──────────┼─────────────────────┼───────────────┼───────────────────────┤
     │          │ Geist 500,          │ 15/20; 28/32  │                       │
     │ figure   │ tabular-nums        │ in drawers    │ Every number          │
     │          │ lining-nums         │               │                       │
     └──────────┴─────────────────────┴───────────────┴───────────────────────┘

     Geist Mono appears only for formulas and locators.

     Colour tokens. shadcn's tokens are remapped onto these: background = paper,
     card = surface, muted = surface-2, muted-foreground = ink-2, border =
     rule, destructive = neg.

     ┌────────────┬────────────┬────────────┬────────────────────────────────┐
     │   Token    │   Light    │    Dark    │              Role              │
     ├────────────┼────────────┼────────────┼────────────────────────────────┤
     │ paper      │ #F7F6F2    │ #0F0F0E    │ App background                 │
     ├────────────┼────────────┼────────────┼────────────────────────────────┤
     │ surface    │ #FFFFFF    │ #171715    │ Cards, sheets                  │
     ├────────────┼────────────┼────────────┼────────────────────────────────┤
     │ surface-2  │ #EFEDE7    │ #22221F    │ Chips, pressed state, swipe    │
     │            │            │            │ reveal                         │
     ├────────────┼────────────┼────────────┼────────────────────────────────┤
     │ ink        │ #16150F    │ #EDECE6    │ Primary text                   │
     ├────────────┼────────────┼────────────┼────────────────────────────────┤
     │ ink-2      │ #55534C    │ #A8A69D    │ Secondary text                 │
     ├────────────┼────────────┼────────────┼────────────────────────────────┤
     │ ink-3      │ #737067    │ #85837A    │ Meta (≥ 4.5:1 on paper)        │
     ├────────────┼────────────┼────────────┼────────────────────────────────┤
     │ rule       │ #E3E0D8    │ #2B2A26    │ Hairlines                      │
     ├────────────┼────────────┼────────────┼────────────────────────────────┤
     │ pos /      │ #0B7A4B /  │ #4CC38A /  │ Kept, positive, cross-checked  │
     │ pos-bg     │ #E6F2EC    │ #11291E    │                                │
     ├────────────┼────────────┼────────────┼────────────────────────────────┤
     │ neg /      │ #B3261E /  │ #FF7B6E /  │ Missed, negative, couldn't     │
     │ neg-bg     │ #F8E8E6    │ #331A17    │ verify                         │
     ├────────────┼────────────┼────────────┼────────────────────────────────┤
     │ warn /     │ #9A5B00 /  │ #E7A93F /  │ Goalposts moved, mixed,        │
     │ warn-bg    │ #F6EEDF    │ #2E2414    │ unverified, "no disclosure     │
     │            │            │            │ explains"                      │
     └────────────┴────────────┴────────────┴────────────────────────────────┘

     Colour is used only for impact, verdicts, verification and warnings. Up and
     down moves stay ink, with ▲/▼ glyphs. Dark mode follows
     prefers-color-scheme, switched from the .dark class to a media-query
     variant, so no script runs and nothing flashes.

     Symbols (your call — flagging it): the spec's ✅ ❌ ↘ ↗ 🔇 and 🟢🔴🟡⚪ are
     drawn as monochrome glyphs in signal colour, not system emoji: ✓ ✕ ↘ ↗, a
     muted-speaker icon, and a 6 px dot plus a word ("● Mixed"). The 📄 and 👁
     emoji become lucide icons. Same states, calmer page, and it renders
     identically on every phone.

     Spacing: 4-pt grid, 16 px gutter, 16/14 px card padding, section gap 32.
     Tap targets are ≥ 44 px; chips are 32 px tall visually with a 44 px hit
     area. Primary actions sit at the bottom: tab bar, Ask bar, and sheet
     buttons.

     How a card looks: a full-bleed row on surface with a 1 px rule hairline
     between rows. It has no box, shadow or radius, and the rank number sits in
     the left gutter in ink-3.
     - Collapsed (~120 px), top to bottom:
       - eyebrow line: ticker · category · period, with the impact dot on the
         right;
       - serif headline;
       - so-what in ink-2;
       - one key-figure row, tappable;
       - footer: source · verification · time · "Why #1 ›".
     - Tap to expand inline: the full body (results table, sparkline, management
       CV and so on), event timeline, next action, Ask chips, and Reviewed /
       Not useful buttons. The buttons are the non-gesture path for mouse and
       accessibility users.
     - While dragging: the row lifts to a 12 px radius. The reveal behind it is
       neutral surface-2 with the label "✓ Reviewed" or "Not useful". At 40 %
       the label inverts (ink background, paper text) and the phone gives a
       haptic tick. Crossing the threshold is signalled without colour.

     Brief at 375 px

     ┌─────────────────────────────────────────────┐
     │ FINN                       Showcase replay ○│ 44px top bar
     │                                             │
     │ Since your last visit                       │ display, serif
     │ 9:12 am · 3 things matter · ~90 sec         │ small, ink-2
     │ 41 routine hidden · est. 35 min saved  ⓘ    │ ⓘ → formula sheet
     │ Data as of 16:38 IST                        │ micro, ink-3
     │ [Since last visit] [24h] [3d] [7d] [Custom] │ chips, h-scroll
     ├─────────────────────────────────────────────┤
     │ Q2 FY27 · 12/18 reported · PAT up 8, down 3›│ season strip
     ├─────────────────────────────────────────────┤
     │1 DIXON · RESULTS · Q2 FY27       ● Positive │
     │  Revenue doubles as phone volumes scale     │ headline, serif
     │  Fastest-growing holding this quarter       │ so-what
     │  PAT ₹… ▲…% YoY · EBITDA margin …% ▼… bps   │ tappable figures
     │  NSE p.2 · ✓ Cross-checked · 16:05  Why #1› │
     ├─────────────────────────────────────────────┤
     │2 GRASIM · M&A                    ● Neutral  │
     │  Completes Solenergi Power acquisition      │
     │  …                                          │
     ├─────────────────────────────────────────────┤
     │3 ALKEM · LITIGATION              ● Negative │
     │  US FDA inspection at an API facility       │
     ├─────────────────────────────────────────────┤
     │ ALSO  BAJFINANCE NCD allotment · ₹… Cr      │ one-liners, compact
     │       INFY ₹… dividend · record 21 Nov      │ inline chips
     ├─────────────────────────────────────────────┤
     │ You're caught up.                           │ serif
     │ Nothing else material since 9:12 am.        │
     │ Reviewed today (2) ›          Hidden (41) › │
     │╭───────────────────────────────────────────╮│
     ││ Ask about today's Brief…                  ││ Ask bar
     │╰───────────────────────────────────────────╯│
     │  ▣ Brief   ○ Portfolio  ○ Research  ○ Rules │ tab bar + safe area
     └─────────────────────────────────────────────┘
      swipe →  ░ ✓ Reviewed ░│1 DIXON · RESULTS …     (label inverts at 40%)

     Promise Ledger at 375 px (BAJFINANCE fixture values)

     ┌─────────────────────────────────────────────┐
     │ ‹ Research          BAJFINANCE              │
     │ Bajaj Finance                               │ title, serif
     │ NBFC · consolidated · as of 11 Nov 16:10 IST│
     │ Snapshot  Trajectory [Ledger]  Cash  Bal… → │ sticky section tabs
     ├─────────────────────────────────────────────┤
     │ PROMISE LEDGER                              │ micro
     │ 8 of 13 kept                        61.5% ↗ │ % and trend only if n ≥ 5
     │ 15 not yet due · next test: FY27 results    │
     │ ████████▓▓▓▓░  ✓ 8 · ✕ 4 · ↘ 1 · dropped 0  │ tally bar, signal colours
     │ 8 calls · 2 decks · 13 decided in code      │
     │ [Scored 13] [Due FY27 14] [Can't score 9]…  │ filters
     ├─────────────────────────────────────────────┤
     │ ✕ MISSED                              FY26  │
     │   Franchise ≥ 120 M                         │
     │   Delivered 119.3 M                         │ tappable
     │   Q3 FY26 call p.4 → Q4 FY26 call p.3     › │
     ├─────────────────────────────────────────────┤
     │ ↘ GOALPOSTS MOVED                     FY26  │
     │   AUM growth  2̶4̶–̶2̶5̶%̶ → 22–23%              │ original struck through
     │   Cut in Q2 FY26 call · delivered 22%       │
     │   Q4 FY25 call p.6 → Q2 FY26 call p.4     › │
     ├─────────────────────────────────────────────┤
     │ ✓ KEPT · beat                         FY26  │
     │   Cost of funds 7.55–7.6%                   │
     │   Delivered 7.54%                           │
     │   Q3 FY26 call p.4 → Q4 FY26 deck p.23    › │
     ├─────────────────────────────────────────────┤
     │ ○ Not yet due (15)                        › │ collapsed groups
     │ – Can't score (9)                         › │
     └─────────────────────────────────────────────┘
      tap any row/number → provenance sheet:
     ╭─────────────────────────────────────────────╮
     │ AUM growth · FY26           ↘ Goalposts moved│
     │ Decided in code: later target is lower      │
     │ Q4 FY25 call · 29 Apr 2025 · p.6   Open p.6↗│
     │ “…estimates of AUM remain at 24 to 25%…”    │
     │ Q2 FY26 call · 10 Nov 2025 · p.4   Open p.4↗│
     │ “…circle up our guidance to 22-23%…”        │
     │ Delivered 22% · Q4 FY26 call p.7        ↗   │
     ╰─────────────────────────────────────────────╯

     ---

     B. Screens and components

     Routes
     - /: landing at ≥ 1024 px, the Brief below that. The switch is CSS-only, so
       there's no flash; on desktop the hidden Brief doesn't fetch.
     - /brief: what the tab bar and the landing iframe load.
     - /portfolio.
     - /research and /research/[symbol] (with section anchors).
     - /rules.
     - /e/[id] and /connect: kept and restyled into the shell.
     - Every app route renders in a centred 430 px column on desktop.

     Shell (components/shell/)
     - AppShell, TopBar, TabBar (4 tabs) and AskBar, which is always visible
       above the tab bar.
     - Sheet: the bottom-drawer primitive used for provenance, scope choice, Why
       #1, the hidden drawer and import.
     - UndoToast.
     - Freshness: "Data as of HH:MM IST" / "Updating…" / "Couldn't refresh ·
       Retry".
     - StateView: loading skeleton, empty, error and stale states. Every screen
       uses it.
     - Tour.

     Reused Phase 2 components (components/cards/)
     - CardView, CardShell (gains collapsed/expanded modes) and the bodies:
       ResultsBody, ManagementBody, PriceVolumeBody, OneLinerBody, InlineChip.
     - FigureValue; its drawer is extracted into a shared ProvenanceSheet that
       handles Figure, Citation and Claim.
     - Sparkline and primitives (ImpactTag, VerificationBadge, SourceChip,
       Timeline), restyled to the tokens.
     - New: a WhatToWatchBody (board-meeting date, plus "Promises this tests ›"
       when a dossier exists).

     Brief (components/brief/)
     - Header and window chips: BriefHeader, WindowChips (Custom opens a date
       sheet and sends window=since), TimeSavedSheet (the formula).
     - SeasonStrip, which opens SeasonSheet, a per-holding mini scoreboard.
     - Card handling: SwipeRow (framer-motion drag around CardView), ScopeSheet,
       WhyRankSheet (ScoreBreakdown factors and notes, shown exactly as Python
       sent them).
     - End of the list: AlsoList (one-liners and chips), ReviewedSection,
       HiddenDrawer, CaughtUp.

     Research (components/research/)
     - TickerSearch: autocomplete over symbol and name word-starts; recent
       searches and demo tickers when empty.
     - BuildProgress: polls the job every 3 s and shows steps, message, queue
       position, waiting_quota with "resumes 13:30 IST", and a 429 explained in
       words.
     - DossierView with SectionTabs and a SectionFrame that reads SectionMeta:
       - ready: content;
       - partial: content plus the note;
       - building + not_built_yet: a quiet "Coming soon" line;
       - building + llm_quota: "resumes HH:MM IST";
       - unavailable + reason: the reason in plain words.
     - Sections: Snapshot, Trajectory (SVG sparklines + CAGRs + note), Ledger,
       Cash, Balance sheet, Analysts, Red flags, Bull/Bear, Drivers, Exchange
       data, Sources.

     Ledger (components/ledger/)
     - LedgerHeader: the tally, the % and trend only when credibility.shown,
       then "15 not yet due · next test: FY27 results".
     - TallyBar, VerdictFilter.
     - PromiseRow: verdict glyph; statement; original → revised target, taken
       from statements (oldest first, original struck through when revision ≠ 
       none); delivered figure; citation path.
     - PromiseSheet: every statement with call, date, page, verbatim quote and
       "Open PDF p.N" (url#page=N); the delivered figure's document, page and
       quote; the reason; and "Decided in code" or "Judged by <model>".

     Evaluator
     - Landing: a server component with:
       - the wordmark and a one-line pitch;
       - a phone frame holding an <iframe src="/brief">;
       - a QR code rendered server-side to SVG (uqr, zero client JS) for the
         canonical URL, labelled "Open on your phone".
     - ShowcaseToggle with a persistent banner: "Showcase replay · Fri 30 Oct
       2026 · saved day, not live".
     - Tour, 3 steps, skippable, shown once:
       a. A ghost swipe nudge on the top card: "Swipe to triage".
       b. A pulse on a figure: "Tap any number for its source".
       c. A pointer to the Research tab: "Research any NSE ticker".

     State (lib/store.ts)
     - Versioned localStorage keys (finn.v1.*) behind useSyncExternalStore,
       every access in try/catch.
     - Stored: holdings (demo portfolio by default, weights from /connect),
       weight rules, pending feedback, reviewed and not-useful marks with
       timestamps, last visit, cached Briefs per window, symbols list, tour
       done, showcase on/off, confirmed drivers, Telegram secret.
     - Holdings go to /brief as symbols and weights only. Quantities never leave
       the phone.

     Swipe mechanics
     - drag="x" with dragDirectionLock, touch-action: pan-y and elastic edges.
     - On release past 40 % of the row width the card commits: it flies out and
       the layout collapses. Shorter swipes spring back.
     - navigator.vibrate(10) fires when crossing the threshold (Android); on iOS
       there's no haptic.
     - Swipe right: Reviewed. The card moves to "Reviewed today". No weight
       change.
     - Swipe left: Not useful. ScopeSheet offers the spec's three scopes:
       - this stock → stock_category;
       - all stocks → category;
       - just this one → event.
       - Dismissing the sheet means "just this one".
     - Then the undo toast shows for 5 s. Only when it expires is the action
       queued, and it goes out with the next /brief refresh, which fires
       immediately. The server applies apply_feedback and returns the updated
       rules. No ranking maths runs in TypeScript.
     - Critical-category floors stay on the server.

     Ask (P1)
     - lib/ask.ts defines ask(context, question) → AskResult.
     - Tonight it resolves the 3 context chips locally. Dossier chips jump to a
       section or a ledger filter by metric keyword. Card chips expand the card
       or open its source.
     - Friday's change: swap the resolver for POST /research/{sym}/ask, render
       the AskAnswer in a sheet, and enable free text.

     ---

     C. First paint < 1 s with Render possibly asleep

     The app shell is static, prerendered HTML+CSS served from Vercel's edge.
     Nothing on the critical path waits on Render.

     1. Repeat visit: the last Brief for this holdings + window comes from
        localStorage and renders on hydration, with "Data as of 16:38 IST ·
        Updating…".
     2. First visit: GET /api/brief/demo?window=24h is a Vercel route handler.
        It calls /brief for the demo portfolio and replies with Cache-Control: 
        public, s-maxage=300, stale-while-revalidate=86400. Vercel's edge serves
        the last good copy at once while Render wakes in the background.
        Evaluators have the demo portfolio and no rules, so this is their real
        Brief.
     3. Nothing within 1.5 s (a cold edge and a cold Render): show the static
        showcase day (/showcase/brief.json) under its banner. When live data
        lands, a "Live Brief ready — Show" pill appears; content never swaps
        under your thumb.
     4. Then always: POST /api/brief with holdings, rules, pending feedback and
        window.
        - Success: swap in, keeping scroll position.
        - Failure: keep the stale copy and show "Couldn't refresh · Retry".
        - data_as_of older than one trading session: show the stale state.
     5. Weight budget:
        - First-load JS for /brief stays ≤ 140 KB gzip: framer-motion through
          LazyMotion + m, lucide per-icon, SVG sparklines with no chart library.
        - Fonts are preloaded subsets.
        - Dossier JSON is never bundled. It is fetched per ticker, about 45 KB
          gzipped.
     6. Measured on the deployed URL in the browser pane at 375 px: FCP/LCP from
        the Performance API with Render asleep (checked via /version latency),
        plus next build's route-size table. What this can't show: a real
        mid-range Android on 4G. I'll say so.

     ---

     D. Build order and cut line

     Ships tonight no matter what, in this order
     1. Foundation. Tokens, fonts, media-query dark mode, shell (tab bar, top
        bar, Sheet, Toast, StateView, Freshness), store, API client with
        cold-start states. Restyle the card components (emoji → glyphs).
     2. Brief backend (small and backward compatible; tests in pytest):
        - A BriefResponse Pydantic model → types.ts. It adds hidden_items (id,
          symbol, subject, filed_at, url, group; newest 300) and counts
          (material filings in the window, hidden, cards, read_seconds,
          est_minutes_saved, and the formula string).
        - season (strip summary + per-holding rows).
        - feedback[] in, rules out.
        - The showcase freeze job and its committed JSON. Push, then confirm
          Render /version = HEAD.
     3. Brief screen. Header and window chips, season strip, ranked cards (every
        card type including what-to-watch, plus the Also list), Why #1,
        timeline, swipe → scope → undo → Reviewed today, hidden drawer,
        caught-up, cache-first loading and every state.
     4. Research. Static public/nse-symbols.json (committed from
        /research/symbols, refreshed in the background from the API),
        autocomplete, dossier page with every section rendering its own status,
        and build progress. Progress is tested against a mocked job sequence; no
        real builds. The 4 demo fixtures double as the offline fallback,
        labelled "Saved copy · 11 Nov".
     5. Promise Ledger. Header, tally, filters, verdict rows, original → revised
        target, and the provenance sheet on every verdict and number.
     6. Evaluator. QR landing with the live phone frame, demo portfolio by
        default with no login, the tour, and the Showcase replay toggle.
     7. Drivers queue (backend, see E). Queued before I stop, so it runs
        overnight.
     8. Verify and ship.
        - Screenshot matrix: every screen × 375/1280 × light/dark, fixing what
          looks off.
        - next build passes, then push.
        - Check the Vercel deployment, walk through the deployed site, and
          confirm Render /version.

     ── cut line ──

     Tonight if time remains, in order
     - Ask bar with 3 context chips per screen (local jumps).
     - Rules: the feedback-adjustments list with Reset, and Connect Telegram
       reusing the /connect logic with the DECISIONS privacy wording verbatim.
     - Portfolio: holdings list (weight, latest event from the Brief) and
       paste/CSV import (quantity or weight %, kept in the browser).

     Friday
     - POST /portfolio (last close, day change, 1-month sparkline, latest event,
       status dot, calendar, scoreboard) and the rest of Portfolio. The
       status-dot rule is written in code and in DECISIONS.
     - "What you're watching" UI and the confirmed-driver ×1.5 boost wired into
       /brief. Today brief() never passes drivers to score().
     - Rules: thresholds, categories, budget, quiet hours, snoozes, synced
       through PUT /subscriptions/me when Telegram is connected.
     - PWA: manifest, icons, offline cache of the latest Brief.
     - Wire /ask once Friday's backend lands.

     ---

     E. Drivers for the 18 holdings without touching the strong quota

     - Drivers are pure code over MAP output (insights.drivers(), called from
       apply_ledger() in finn/research/build.py:287, before JUDGE and REDUCE).
       Only the Flash-Lite MAP is needed.
     - New drivers build mode: discover → latest 4 transcripts → MAP
       (Flash-Lite) → apply_ledger → write only the drivers section to a small
       drivers table (migration 0005: symbol, section jsonb, calls_read,
       built_at). It does not publish a dossier, so Research for that ticker
       still shows the normal "Build" flow, now cheaper because MAP is cached.
     - No strong calls, enforced twice:
       - the mode returns before decks, JUDGE and REDUCE;
       - the router raises on any strong-tier request tagged mode=drivers.
       - A unit test with a mocked router asserts zero strong requests.
     - Queue: python -m jobs.research drivers --portfolio enqueues the 16
       holdings without drivers (BAJFINANCE and INFY have them).
       - reason="drivers" (a contract enum addition), priority=90. Evaluator
         requests are priority 10 and claim() orders by priority, so evaluators
         always go first.
       - Not counted in RESEARCH_DAILY_BUILDS.
     - Own cheap cap: RESEARCH_DRIVERS_RPD=70 inside the 220/day research lane,
       so evaluators keep ≥ 150 Flash-Lite calls (≈ 16 first-time builds). Over
       the cap, the job parks waiting_quota and resumes after the 13:30 IST
       reset.
     - Cost: ≤ 64 Flash-Lite calls, about $1.35 at list price; the free tier
       bills nothing. 0 strong calls.
     - When: enqueued tonight once the Brief ships. The Render worker runs them
       overnight, when evaluator traffic is lowest.
     - Into the UI: GET /research/drivers?symbols=… → {symbol: DriversSection | 
       null}. It reads the drivers table, falling back to the dossier's drivers.
       Portfolio shows the suggestions with one-tap confirm, or "Drivers appear
       after research" when a ticker has no transcripts. Confirmations live in
       localStorage and are sent with /brief.

     ---

     DECISIONS.md entries I'll add

     - Visual direction.
     - First-paint strategy (edge-cached demo Brief, showcase fallback).
     - Showcase replay as a frozen Brief: re-ranked at freeze time; swipes in it
       still create real rules.
     - Time-saved formula: est. = 30 s × routine filings hidden + 3 min × 
       material filings in the window − the Brief's read time (30 s per card, 10
       s per one-liner or chip), rounded to 5 min. This matches the spec's "41
       hidden · ~35 min".
     - Season-strip metrics: reported/total, PAT up/down, margins up/down. "Met
       guidance" waits until results cards carry the ledger's guidance line.
     - Feedback applied server-side via /brief.
     - Drivers-only mode and its cap.

     PLAN.md gets a Phase 4 section with these items, ticked with commit hashes.

     Risks

     - Next 16.4 with cacheComponents differs from what I know. I'll read
       node_modules/next/dist/docs before writing route handlers or client-only
       storage code.
     - Swipe vs vertical scroll on real iOS: I can test only touch-emulated
       mouse drags. You'll be the first real-iPhone check.
     - Render deploys: every backend change is additive (new optional fields and
       endpoints), so the deployed app never breaks mid-phase.
     - RELIANCE in the showcase shows "Couldn't verify — open filing" (the known
       screener reconciliation issue). That's honest, and a good trust-layer
       demo.
     - Optional dashboard click: Vercel → Settings → Functions → region Mumbai
       (bom1) for a faster /api/*.

     Verification

     - pytest: brief counts and time saved, season strip, feedback in → rules
       out, showcase freeze, drivers mode makes zero strong calls.
     - npm run typecheck, npm run lint, next build (route sizes).
     - Browser pane on the dev server, then on the deployed URL:
       - each screen at 375 and 1280, light and dark, in loading, empty, error
         and stale states;
       - a swipe past and short of 40 %, undo, Reviewed today, the hidden
         drawer, Why #1;
       - search and open each of the 4 fixtures plus one non-demo ticker (GET
         only, no build);
       - the ledger provenance sheet opening the PDF page;
       - the QR landing on desktop and the showcase toggle.
     - A cold-Render first paint measurement.
     - Render /version = HEAD after each backend push.

⏺ Plan approved, and your six amendments are folded in. Starting with the
  backend Brief additions so Render can deploy while I build the frontend.

  Called ccd_session, ccd_turn 2 times, ran 4 shell commands (ctrl+o to expand)

⏺ Now writing the contract additions: a typed BriefResponse with hidden items,
  counts and time saved, the season strip, and feedback in → rules out.

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(sed -n 10,16p finn/models/common.py && python3 - <<'EOF'
      import re…)
  ⎿  class Model(BaseModel):
         # serialization_defaults_required: the API always emits every fiel
     d, so TS types mark them required.
     … +7 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/models/core.py (+96 -0)
      277          return v
      278  
      279  
      280 +class HiddenItem(Model):                                      
      281 +    """A filing kept out of the Brief (hidden drawer). Still t
          +appable: `url` opens the exchange PDF."""                     
      282 +                                                              
      283 +    id: str                                                   
      284 +    symbol: str                                               
      285 +    subject: str                                              
      286 +    filed_at: AwareDatetime                                   
      287 +    url: str | None = None                                    
      288 +    group: str = Field(description="Drawer group, e.g. 'Tradin
          +g-window notice', 'Investor-meeting notice'")                 
      289 +                                                              
      290 +                                                              
      291 +class BriefCounts(Model):                                     
      292 +    """What the Brief header says. Computed in code (finn/card
          +s/brief.py); the formula string is shown on tap."""           
      293 +                                                              
      294 +    cards: int = Field(description="Full cards: results, manag
          +ement change, price/volume, what to watch")                   
      295 +    one_liners: int                                           
      296 +    chips: int                                                
      297 +    material_filings: int = Field(description="Filings inside 
          +the window that belong to the events shown")                  
      298 +    hidden_filings: int                                       
      299 +    read_seconds: int = Field(description="Estimated time to r
          +ead this Brief")                                              
      300 +    est_minutes_saved: int = Field(description="Estimate; alwa
          +ys labelled 'est.' in the UI")                                
      301 +    formula: str                                              
      302 +                                                              
      303 +                                                              
      304 +class SeasonRow(Model):                                       
      305 +    """One holding in the results-season scoreboard."""       
      306 +                                                              
      307 +    symbol: str                                               
      308 +    status: Literal["reported", "scheduled", "awaited"]       
      309 +    event_id: str | None = None                               
      310 +    reported_at: AwareDatetime | None = None                  
      311 +    verification: Literal["cross_checked", "partial", "pending
          +", "mismatch"] | None = None                                  
      312 +    revenue_yoy: Figure | None = Field(None, description="Reve
          +nue YoY % (NII for lenders)")                                 
      313 +    pat_yoy: Figure | None = None                             
      314 +    margin_yoy: Figure | None = Field(None, description="EBITD
          +A margin YoY change in bps (standard template)")              
      315 +                                                              
      316 +                                                              
     … 62 more lines (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/models/__init__.py'…)
  ⎿  dict_keys(['holdings', 'window', 'since', 'rules', 'feedback'])
     True
  ⎿  Updated backend/finn/models/__init__.py (+17 -1)
      15  from finn.models.core import (
      16      Alert,
      17      AlertSettings,
      18 +    BriefCounts,                                               
      19 +    BriefHolding,                                              
      20 +    BriefRequest,                                              
      21 +    BriefResponse,                                             
      22      Card,
      23      ChipDetail,
      24      Driver,
      25      Event,
      26      EventStage,
      27 +    FeedbackAction,                                            
      28      Filing,
      29 +    HiddenItem,                                                
      30      Holding,
      31      ManagementDetail,
      32      MoveExplanation,
     ...
      37      ResultsDetail,
      38      ResultsLine,
      39      ScoreBreakdown,
      40 +    SeasonRow,                                                 
      41 +    SeasonStrip,                                               
      42      Series,
      43      TimelineItem,
      44      WeightRule,
     ...
      59  # Top-level contracts exported to TypeScript (nested types come
           along via $defs).
      60  EXPORTED = [
      61      Citation, Figure, Claim, Period, Filing, Event, Card, Alert
          , Holding, Driver, Promise, Dossier,
      54 -    WeightRule, AlertSettings, DossierJob, DossierResponse, Ask
         -Answer,                                                        
      62 +    WeightRule, AlertSettings, DossierJob, DossierResponse, Ask
         +Answer, BriefRequest, BriefResponse,                           
      63  ]  # fmt: skip
      64  
      65  __all__ = [
     ...
      73      "ResultsDetail",
      74      "ResultsLine",
      75      "WeightRule",
      76 +    "BriefCounts",                                             
      77 +    "BriefHolding",                                            
      78 +    "BriefRequest",                                            
     … 8 more lines (ctrl+o to expand)

  Searched for 2 patterns, ran 1 shell command (ctrl+o to expand)

⏺ Writing the Brief builder changes now (hidden items, time-saved counts, season
  strip, feedback).

⏺ Bash(python3 - <<'EOF'
      p='finn/cards/brief.py'…)
  ⎿  25:def now_utc() -> datetime:
     34:    return to_ist(now or now_utc()).date()
  ⎿  Updated backend/finn/cards/brief.py (+60 -17)
       8  
       9  from datetime import datetime, timedelta
      10  
      11 +from finn.calendar import now_utc                              
      12  from finn.cards.build import NEUTRAL_SCORE, build_card
      12 -from finn.models import Card, WeightRule                       
      13 +from finn.cards.counts import brief_counts                     
      14 +from finn.cards.season import season_strip                     
      15 +from finn.models import BriefResponse, Card, FeedbackAction, Hi
         +ddenItem, WeightRule                                           
      16 +from finn.ranking.feedback import apply_feedback               
      17  from finn.ranking.score import HIDDEN, REPEAT_WINDOW_DAYS, repe
          at_counts, score
      18  
      19  EVENT_COLS = (
     ...
      52      ).fetchall()
      53  
      54  
      51 -def hidden_counts(conn, symbols: list[str], since: datetime | N
         -one) -> dict[str, int]:                                        
      52 -    """Hidden drawer groups: routine filings by their hidden_re
         -ason, plus investor meetings and unclassified."""              
      55 +HIDDEN_GROUP = (                                               
      56 +    "coalesce(case when category = 'routine' then hidden_reason
         + end, case category "                                          
      57 +    "when 'investor_meetings' then 'Investor-meeting notice' wh
         +en 'unclassified' then 'Unclassified' end, "                   
      58 +    "'Other routine filing')"                                  
      59 +)                                                              
      60 +MAX_HIDDEN_ITEMS = 300                                         
      61 +                                                               
      62 +                                                               
      63 +def hidden_filings(conn, symbols: list[str], since: datetime | 
         +None, until: datetime | None = None) -> list[dict]:            
      64 +    """Hidden drawer: routine filings (grouped by hidden_reason
         +), investor meetings and unclassified, newest first."""        
      65      q = (
      54 -        "select coalesce(case when category = 'routine' then hi
         -dden_reason end, case category "                               
      55 -        "when 'investor_meetings' then 'Investor-meeting notice
         -' when 'unclassified' then 'Unclassified' end, "               
      56 -        "'Other routine filing') as grp, count(*) as n from pub
         -lic.filings where symbol = any(%s) "                           
      66 +        f"select id, symbol, subject, filed_at, coalesce(attach
         +ment_url, xbrl_url) as url, {HIDDEN_GROUP} as grp "            
      67 +        "from public.filings where symbol = any(%s) and duplica
         +te_of is null "                                                
      68          "and category in ('routine', 'investor_meetings', 'uncl
          assified')"
      69      )
      70      params: list = [symbols]
      71      if since is not None:
      72          q += " and filed_at >= %s"
      73          params.append(since)
     … 67 more lines (ctrl+o to expand)
⏺ Bash(cat > finn/cards/counts.py <<'EOF'
      """Brief header numbers (PRODUCT §4): how much there is to read and an
      estimate of the time FINN saved.…)
  ⎿  """Brief, card and Telegram endpoints.

     POST /brief                  holdings + window + rules → ranked cards
     … +28 lines (ctrl+o to expand)
  ⎿  Updated backend/api/push.py (+3 -15)
      32  WINDOWS = {"24h": timedelta(hours=24), "3d": timedelta(days=3),
           "7d": timedelta(days=7)}
      33  
      34  
      35 -class HoldingIn(BaseModel):                                    
      36 -    symbol: str = Field(min_length=1, max_length=20)           
      37 -    weight_pct: float | None = Field(None, gt=0, le=100)       
      38 -                                                               
      39 -                                                               
      40 -class BriefIn(BaseModel):                                      
      41 -    holdings: list[HoldingIn] = Field(min_length=1, max_length=
         -subs.MAX_SYMBOLS)                                              
      42 -    window: Literal["since", "24h", "3d", "7d", "all"] = "7d"  
      43 -    since: datetime | None = Field(None, description="For windo
         -w='since' (last visit) or a custom start")                     
      44 -    rules: list[WeightRule] = Field(default_factory=list, max_l
         -ength=500)                                                     
      45 -                                                               
      46 -                                                               
      35  @router.post("/brief")
      48 -def post_brief(body: BriefIn):                                 
      36 +def post_brief(body: BriefRequest):                            
      37      # Holdings are used only to rank this response: never store
          d, never logged.
      38      since = (
      39          body.since if body.window == "since" else (None if body
          .window == "all" else now_utc() - WINDOWS[body.window])
     ...
      42      if all(w is None for w in weights.values()):
      43          weights = {s: round(100 / len(weights), 4) for s in wei
          ghts}
      44      with connect() as conn:
      57 -        b = brief(conn, weights, since, body.rules)            
      58 -    return {**b, "cards": [c.model_dump(mode="json") for c in b
         -["cards"]]}                                                    
      45 +        b = brief(conn, weights, since, body.rules, body.feedba
         +ck, window=body.window)                                        
      46 +    return b.model_dump(mode="json")                           
      47  
      48  
      49  @router.get("/events/{event_id}/card")
  ⎿  Created backend/finn/cards/counts.py (+46 -0)
       1 +"""Brief header numbers (PRODUCT §4): how much there is to read
         + and an estimate of the time FINN saved.                       
       2 +                                                               
       3 +The estimate is deliberately simple and is shown with its formu
         +la (DECISIONS: "est. time saved"):                             
       4 +    est. = 30 s × routine filings hidden + 3 min × material fil
         +ings in the window − the Brief's own read time                 
       5 +    (30 s per full card, 10 s per one-liner or chip); nearest m
         +inute under 10, else nearest 5; never below 0.                 
       6 +"""                                                            
       7 +                                                               
       8 +from __future__ import annotations                             
       9 +                                                               
      10 +from datetime import datetime                                  
      11 +                                                               
      12 +from finn.models import BriefCounts, Card                      
      13 +                                                               
      14 +ROUTINE_S, MATERIAL_S = 30, 180                                
      15 +CARD_READ_S, LINE_READ_S = 30, 10                              
      16 +FULL_CARDS = {"results", "management_change", "price_volume", "
         +what_to_watch"}                                                
      17 +FORMULA = (                                                    
      18 +    "est. = 30 s × routine filings hidden + 3 min × material fi
         +lings in the window − this Brief's read time "                 
      19 +    "(30 s per card, 10 s per one-liner or chip); nearest minut
         +e under 10, else nearest 5"                                    
      20 +)                                                              
      21 +                                                               
      22 +                                                               
      23 +def material_filings(cards: list[Card], since: datetime | None)
         + -> int:                                                       
      24 +    """Distinct filings behind the shown cards that were filed 
         +inside the window (all of them for 'all')."""                  
      25 +    ids = {t.filing_id for c in cards for t in c.timeline if si
         +nce is None or t.at >= since}                                  
      26 +    return len(ids)                                            
      27 +                                                               
      28 +                                                               
      29 +def round_minutes(seconds: float) -> int:                      
      30 +    if seconds <= 0:                                           
      31 +        return 0                                               
      32 +    m = seconds / 60                                           
      33 +    return int(m + 0.5) if m < 10 else 5 * int(m / 5 + 0.5)    
      34 +                                                               
      35 +                                                               
      36 +def brief_counts(cards: list[Card], hidden_n: int, since: datet
         +ime | None) -> BriefCounts:                                    
      37 +    full = sum(1 for c in cards if c.card_type in FULL_CARDS)  
      38 +    chips = sum(1 for c in cards if c.card_type == "inline_chip
         +")                                                             
      39 +    lines = len(cards) - full - chips                          
      40 +    material = material_filings(cards, since)                  
     … 6 more lines (ctrl+o to expand)
  ⎿  Created backend/finn/cards/season.py (+88 -0)
       1 +"""Results-season strip and scoreboard (PRODUCT §4, §7): which 
         +holdings have reported this quarter, and how.                  
       2 +                                                               
       3 +Shown from a quarter's end until 60 days after it (75 for Q4, w
         +hose results are due later). Counts are taken                  
       4 +in code from the stored results cards; a card that failed its c
         +ross-check ("Couldn't verify") counts as reported              
       5 +but contributes no numbers. Event keys are '<SYM>:results:<Q la
         +bel>' (DECISIONS: event threading).                            
       6 +"""                                                            
       7 +                                                               
       8 +from __future__ import annotations                             
       9 +                                                               
      10 +from datetime import date, datetime                            
      11 +                                                               
      12 +from finn.calendar import quarter_end_on_or_before, quarter_per
         +iod, to_ist                                                    
      13 +from finn.models import Figure, SeasonRow, SeasonStrip         
      14 +                                                               
      15 +                                                               
      16 +def season_quarter(today: date) -> date | None:                
      17 +    qe = quarter_end_on_or_before(today)                       
      18 +    lag = 75 if qe.month == 3 else 60                          
      19 +    return qe if 0 < (today - qe).days <= lag else None        
      20 +                                                               
      21 +                                                               
      22 +def _ts(x) -> datetime:                                        
      23 +    return x if isinstance(x, datetime) else datetime.fromisofo
         +rmat(str(x).replace("Z", "+00:00"))                            
      24 +                                                               
      25 +                                                               
      26 +def _line(detail: dict, *metrics: str) -> Figure | None:       
      27 +    for m in metrics:                                          
      28 +        ln = next((ln for ln in detail.get("lines", []) if ln.g
         +et("metric") == m), None)                                      
      29 +        if ln and ln.get("yoy") and ln["yoy"].get("value") is n
         +ot None:                                                       
      30 +            return Figure.model_validate(ln["yoy"])            
      31 +    return None                                                
      32 +                                                               
      33 +                                                               
      34 +def season_row(symbol: str, event: dict | None, as_of: datetime
         +) -> SeasonRow:                                                
      35 +    if event is None:                                          
      36 +        return SeasonRow(symbol=symbol, status="awaited")      
      37 +    timeline = [t for t in (event.get("timeline") or []) if _ts
         +(t["at"]) <= as_of]                                            
      38 +    outcome = min((_ts(t["at"]) for t in timeline if t["stage"]
         + == "outcome"), default=None)                                  
      39 +    if outcome is None:                                        
      40 +        return SeasonRow(symbol=symbol, status="scheduled" if t
         +imeline else "awaited", event_id=event["id"])                  
     … 48 more lines (ctrl+o to expand)

⏺ Bash(sed -i '' 's/^from finn.models import AlertSettings, WeightRule$/from
      finn.models import AlertSettings, BriefRequest, WeightRule/' api/push.py
      && sed -i '' 's/…)
  ⎿      """The best card for these holdings in the last 7 days, labelled '
     Test alert'."""
         weights = subs.weights_of(sub)
     … +23 lines (ctrl+o to expand)
  ⎿  Updated backend/api/push.py (+1 -1)
      21  from finn.calendar import now_utc
      22  from finn.cards.brief import brief, single_card
      23  from finn.db import connect
      24 -from finn.models import AlertSettings, WeightRule              
      24 +from finn.models import AlertSettings, BriefRequest, WeightRule
      25  from finn.push import subscriptions as subs
      26  from finn.push.bot import handle_update
      27  from finn.push.telegram import Telegram
  ⎿  Updated backend/finn/push/bot.py (+2 -2)
      49  def send_test_alert(conn, tg: Telegram, sub: dict) -> str:
      50      """The best card for these holdings in the last 7 days, lab
          elled 'Test alert'."""
      51      weights = subs.weights_of(sub)
      52 -    b = brief(conn, weights, now_utc() - TEST_WINDOW, subs.rule
         -s(conn, sub["id"]))                                            
      53 -    cards = [c for c in b["cards"] if c.card_type != "what_to_w
         -atch"] or b["cards"]                                           
      52 +    b = brief(conn, weights, now_utc() - TEST_WINDOW, subs.rule
         +s(conn, sub["id"]), window="7d")                               
      53 +    cards = [c for c in b.cards if c.card_type != "what_to_watc
         +h"] or b.cards                                                 
      54      if not cards:
      55          tg.send(sub["chat_id"], "🔔 <b>Test alert</b> — FINN is
           connected. Nothing material on your holdings in "
      56                  "the last 7 days; the next real event will arri
          ve here.")  # fmt: skip

⏺ Bash(sed -i '' 's/list\[HoldingIn\]/list[BriefHolding]/g; s/^from finn.models
      import AlertSettings, BriefRequest, WeightRule$/from finn.models import
      AlertSettings,…)
  ⎿  Found 2 errors (2 fixed, 0 remaining).
     12 files left unchanged
     ok
  ⎿  Updated backend/api/push.py (+4 -5)
      12  import hmac
      13  import logging
      14  import os
      15 -from datetime import datetime, timedelta                       
      16 -from typing import Literal                                     
      15 +from datetime import timedelta                                 
      16  
      17  from fastapi import APIRouter, Header, HTTPException, Request
      18  from pydantic import BaseModel, Field
     ...
      20  from finn.calendar import now_utc
      21  from finn.cards.brief import brief, single_card
      22  from finn.db import connect
      24 -from finn.models import AlertSettings, BriefRequest, WeightRule
      23 +from finn.models import AlertSettings, BriefHolding, BriefReque
         +st, WeightRule                                                 
      24  from finn.push import subscriptions as subs
      25  from finn.push.bot import handle_update
      26  from finn.push.telegram import Telegram
     ...
      55  
      56  
      57  class LinkIn(BaseModel):
      59 -    holdings: list[HoldingIn] = Field(min_length=1, max_length=
         -subs.MAX_SYMBOLS)                                              
      58 +    holdings: list[BriefHolding] = Field(min_length=1, max_leng
         +th=subs.MAX_SYMBOLS)                                           
      59      settings: AlertSettings | None = None
      60  
      61  
     ...
      106  
      107  
      108  class MeIn(BaseModel):
      110 -    holdings: list[HoldingIn] | None = Field(None, max_length=
          -subs.MAX_SYMBOLS)                                             
      109 +    holdings: list[BriefHolding] | None = Field(None, max_leng
          +th=subs.MAX_SYMBOLS)                                          
      110      settings: AlertSettings | None = None
      111      rules: list[WeightRule] | None = Field(None, max_length=50
           0)
      112  

⏺ Backend imports cleanly. Adding unit tests for time saved, the season strip
  and feedback-in/rules-out.

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(cat > tests/test_brief_header.py <<'EOF'
      """Brief header numbers, season strip and feedback passthrough (Phase 4
      contract)."""…)
  ⎿      def _line(detail: dict, *metrics: str) -> Figure | None:
             for m in metrics:
                 ln = next((ln for ln in detail.get("lines", []) if ln.get(
     … +15 lines (ctrl+o to expand)
  ⎿  Created backend/tests/test_brief_header.py (+104 -0)
        1 +"""Brief header numbers, season strip and feedback passthrough
          + (Phase 4 contract)."""                                       
        2 +                                                              
        3 +from datetime import UTC, date, datetime, timedelta           
        4 +                                                              
        5 +import pytest                                                 
        6 +                                                              
        7 +from finn.cards.brief import apply_actions                    
        8 +from finn.cards.build import NEUTRAL_SCORE, build_card        
        9 +from finn.cards.counts import brief_counts, material_filings, 
          +round_minutes                                                 
       10 +from finn.cards.season import build_strip, season_quarter     
       11 +from finn.models import FeedbackAction                        
       12 +                                                              
       13 +NOW = datetime(2026, 11, 11, 10, 0, tzinfo=UTC)               
       14 +                                                              
       15 +                                                              
       16 +def card(category, at, n_filings=1, eid=None, detail=None, sta
          +ge="outcome"):                                                
       17 +    timeline = [                                              
       18 +        {"filing_id": f"{eid or category}-{i}", "stage": stage
          +, "at": (at - timedelta(hours=i)).isoformat(),                
       19 +         "label": "x"}                                        
       20 +        for i in range(n_filings)                             
       21 +    ]  # fmt: skip                                            
       22 +    e = {"id": eid or f"S:{category}", "symbol": "S", "categor
          +y": category, "title": "t", "timeline": timeline,             
       23 +         "detail": detail, "updated_at": at}  # fmt: skip     
       24 +    return build_card(e, {}, NEUTRAL_SCORE)                   
       25 +                                                              
       26 +                                                              
       27 +@pytest.mark.parametrize("secs,mins", [(0, 0), (-50, 0), (89, 
          +1), (90, 2), (539, 9), (600, 10), (2220, 35),                 
       28 +                                       (2280, 40), (3300, 55)]
          +)  # fmt: skip                                                
       29 +def test_round_minutes(secs, mins):                           
       30 +    assert round_minutes(secs) == mins                        
       31 +                                                              
       32 +                                                              
       33 +def test_counts_match_the_spec_example():                     
       34 +    # Spec: "3 things matter · ~90 sec · 41 routine filings hi
          +dden · ~35 min saved"                                         
       35 +    since = NOW - timedelta(days=1)                           
       36 +    cards = [card("results", NOW, 2, "a"), card("management_ch
          +ange", NOW, 1, "b"), card("mna", NOW, 1, "c"),                
       37 +             card("results", NOW, 2, "d")]  # fmt: skip       
       38 +    cards = cards[:3]  # 2 full cards + 1 one-liner, 4 filings
          + in the window                                                
       39 +    c = brief_counts(cards, hidden_n=41, since=since)         
       40 +    assert (c.cards, c.one_liners, c.chips, c.material_filings
          +) == (2, 1, 0, 4)                                             
     … 64 more lines (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='tests/test_brief_header.py'…)
  ⎿  =========================== short test summary info ==================
     ==========
     FAILED tests/test_brief_header.py::test_season_strip_counts - pydantic
     … +7 lines (ctrl+o to expand)
  ⎿  Updated backend/tests/test_brief_header.py (+3 -1)
      11  from finn.models import FeedbackAction
      12  
      13  NOW = datetime(2026, 11, 11, 10, 0, tzinfo=UTC)
      14 +CIT = {"source_type": "xbrl", "url": "https://x", "title": None
         +, "exchange": "NSE", "page": None, "quote": None,              
      15 +       "locator": None, "published_at": None, "retrieved_at": "
         +2026-11-11T00:00:00Z"}                                         
      16  
      17  
      18  def card(category, at, n_filings=1, eid=None, detail=None, stag
          e="outcome"):
     ...
      72  def _results_event(sym, at, pat_yoy, margin_bps, verification="
          cross_checked"):
      73      def fig(v, unit):
      74          return {"label": "x", "value": v, "unit": unit, "status
          ": "verified", "basis": "consolidated",
      73 -                "period": None, "citation": None, "raw": None, 
         -"raw_unit": None, "check_note": None,                          
      75 +                "period": None, "citation": CIT, "raw": None, "
         +raw_unit": None, "check_note": None,                           
      76                  "formula": "f", "inputs": []}  # fmt: skip
      77  
      78      lines = [{"metric": "PAT", "yoy": fig(pat_yoy, "PCT")}, {"m
          etric": "EBITDA margin", "yoy": fig(margin_bps, "BPS")}]

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(sed -i '' 's/    b = brief(conn, weights, now_utc() - TEST_WINDOW,
      subs.rules(conn, sub\["id"\]), window="7d")/    b = brief(conn, weights,
      now_utc() - TEST_WIN…)
  ⎿  3:import pytest

     -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.htm
     … +2 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/push/bot.py (+1 -1)
      49  def send_test_alert(conn, tg: Telegram, sub: dict) -> str:
      50      """The best card for these holdings in the last 7 days, lab
          elled 'Test alert'."""
      51      weights = subs.weights_of(sub)
      52 -    b = brief(conn, weights, now_utc() - TEST_WINDOW, subs.rule
         -s(conn, sub["id"]), window="7d")                               
      52 +    b = brief(conn, weights, now_utc() - TEST_WINDOW, subs.rule
         +s(conn, sub["id"]))                                            
      53      cards = [c for c in b.cards if c.card_type != "what_to_watc
          h"] or b.cards
      54      if not cards:
      55          tg.send(sub["chat_id"], "🔔 <b>Test alert</b> — FINN is
           connected. Nothing material on your holdings in "
  ⎿  Updated backend/tests/test_brief_header.py (+19 -5)
      11  from finn.models import FeedbackAction
      12  
      13  NOW = datetime(2026, 11, 11, 10, 0, tzinfo=UTC)
      14 -CIT = {"source_type": "xbrl", "url": "https://x", "title": None
         -, "exchange": "NSE", "page": None, "quote": None,              
      15 -       "locator": None, "published_at": None, "retrieved_at": "
         -2026-11-11T00:00:00Z"}                                         
      14 +CIT = {                                                        
      15 +    "source_type": "xbrl",                                     
      16 +    "url": "https://x",                                        
      17 +    "title": None,                                             
      18 +    "exchange": "NSE",                                         
      19 +    "page": None,                                              
      20 +    "quote": None,                                             
      21 +    "locator": None,                                           
      22 +    "published_at": None,                                      
      23 +    "retrieved_at": "2026-11-11T00:00:00Z",                    
      24 +}                                                              
      25  
      26  
      27  def card(category, at, n_filings=1, eid=None, detail=None, stag
          e="outcome"):
     ...
      82      def fig(v, unit):
      83          return {"label": "x", "value": v, "unit": unit, "status
          ": "verified", "basis": "consolidated",
      84                  "period": None, "citation": CIT, "raw": None, "
          raw_unit": None, "check_note": None,
      76 -                "formula": "f", "inputs": []}  # fmt: skip     
      85 +                "formula": None, "inputs": []}  # fmt: skip    
      86  
      87      lines = [{"metric": "PAT", "yoy": fig(pat_yoy, "PCT")}, {"m
          etric": "EBITDA margin", "yoy": fig(margin_bps, "BPS")}]
      88      return {"id": f"{sym}:results:Q2 FY27", "key": f"{sym}:resu
          lts:Q2 FY27", "symbol": sym,
     ...
       97          _results_event("A", at, 12.0, 40),
       98          _results_event("B", at, -5.0, -120),
       99          _results_event("C", at, 30.0, 10, verification="mismat
           ch"),  # reported, no numbers
       91 -        {"id": "D:results:Q2 FY27", "key": "D:results:Q2 FY27"
          -, "symbol": "D", "detail": None,                              
       92 -         "timeline": [{"stage": "intimation", "at": at.isoform
          -at()}]},  # fmt: skip                                         
      100 +        {                                                     
      101 +            "id": "D:results:Q2 FY27",                        
      102 +            "key": "D:results:Q2 FY27",                       
      103 +            "symbol": "D",                                    
      104 +            "detail": None,                                   
      105 +            "timeline": [{"stage": "intimation", "at": at.isof
          +ormat()}],                                                    
      106 +        },  # fmt: skip                                       
      107          _results_event("F", NOW + timedelta(days=1), 1.0, 1), 
            # outcome after as_of → not yet reported
     … 2 more lines (ctrl+o to expand)
  ⎿  Updated backend/tests/test_telegram.py (+2 -1)
      1  from datetime import UTC, datetime
      2 +from types import SimpleNamespace                               
      3  
      4  import pytest
      5  from fastapi.testclient import TestClient
     ...
      54      monkeypatch.setattr(bot.subs, "rules", lambda conn, i: [])
      55      monkeypatch.setattr(bot.subs, "snooze", lambda conn, i, s, 
          d: state["snoozes"].append((s, d)) or NOW)
      56      card = build_card(EVENT, FILINGS, NEUTRAL_SCORE)
      56 -    monkeypatch.setattr(bot, "brief", lambda conn, w, since, ru
         -les: {"cards": [card]})                                        
      57 +    monkeypatch.setattr(bot, "brief", lambda conn, w, since, ru
         +les: SimpleNamespace(cards=[card]))                            
      58      monkeypatch.setattr(bot, "record_alert", lambda *a, **k: st
          ate["alerts"].append(a[3:5]))
      59      return state
      60  

⏺ All 331 tests pass. Next, the showcase freeze: rank the 30 Oct snapshot day
  for the demo portfolio and write it as a static Brief JSON.

⏺ Bash(python3 - <<'EOF'
      p='finn/portfolio.py'…)
  ⎿  showcase brief 2026-10-30: 8 cards, 4 hidden, counts={'cards': 4, 'one
     _liners': 4, 'chips': 0, 'material_filings': 14, 'hidden_filings': 4,
     'read_seconds': 160, 'est_minutes_saved': 40, 'formula': "est. = 30 s
     … +5 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/portfolio.py (+9 -0)
      11  ]  # fmt: skip
      12  
      13  
      14 +# Demo weights (% of portfolio; sum 100). Mirrored in web/lib/d
         +emo.ts — the phone sends these with /brief.                    
      15 +DEMO_WEIGHTS: dict[str, float] = {                             
      16 +    "HAL": 6, "EICHERMOT": 6, "GRASIM": 5, "TATAPOWER": 5, "ALK
         +EM": 5, "KALYANKJIL": 5, "COCHINSHIP": 5,                      
      17 +    "TITAGARH": 4, "IDEA": 3, "RELIANCE": 8, "HDFCBANK": 8, "BA
         +JFINANCE": 6, "INFY": 7, "ITC": 6, "DIVISLAB": 5,              
      18 +    "TATASTEEL": 5, "JUBLFOOD": 5, "DIXON": 6,                 
      19 +}  # fmt: skip                                                 
      20 +assert set(DEMO_WEIGHTS) == set(DEMO_PORTFOLIO) and sum(DEMO_WE
         +IGHTS.values()) == 100                                         
      21 +                                                               
      22 +                                                               
      23  def tracked_symbols(override: str | None = None, conn=None) -> 
          list[str]:
      24      """Symbols for a job run: a comma-separated override (CLI/w
          orkflow input), else the demo portfolio plus
      25      every Telegram subscriber's symbols (their opt-in server co
          py) when a DB connection is given."""
  ⎿  Updated backend/jobs/snapshot.py (+55 -1)
       8  python -m jobs.snapshot                 # suggest the richest d
          ay of the last 30 and freeze it
       9  python -m jobs.snapshot --date 2026-10-30
      10  python -m jobs.snapshot --suggest       # only print the rankin
          g
      11 +python -m jobs.snapshot --brief 2026-10-30   # freeze that day'
         +s ranked Brief for the web's Showcase replay                   
      12 +                                                               
      13 +The frozen Brief ranks the snapshot day's events (as stored now
         +, with their built card details) for the demo                  
      14 +portfolio, with each timeline cut at the end of that IST day, a
         +nd writes it to                                                
      15 +backend/data/snapshots/<D>.brief.json and web/public/showcase/b
         +rief.json (DECISIONS: Showcase replay).                        
      16  """
      17  
      18  from __future__ import annotations
     ...
      24  
      25  from finn import store
      26  from finn.calendar import IST, ist_today
      27 +from finn.cards.brief import EVENT_COLS, hidden_counts, hidden_
         +filings, hidden_items, load_filings, rank                      
      28 +from finn.cards.counts import brief_counts                     
      29 +from finn.cards.season import season_strip                     
      30  from finn.db import connect
      23 -from finn.portfolio import tracked_symbols                     
      31 +from finn.models import BriefResponse                          
      32 +from finn.portfolio import DEMO_WEIGHTS, tracked_symbols       
      33 +from finn.ranking.score import REPEAT_WINDOW_DAYS              
      34  
      35  OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "snaps
          hots"
      36 +WEB_SHOWCASE = Path(__file__).resolve().parents[2] / "web" / "p
         +ublic" / "showcase" / "brief.json"                             
      37  MATERIAL = ("results", "earnings_call", "mna", "management_chan
          ge", "litigation", "credit_rating", "pledging",
      38              "capex", "press_release", "fund_raise", "insider_tr
          ading")  # fmt: skip
      39  
     ...
      107      })  # fmt: skip
      108  
      109  
      110 +def _ts(x) -> datetime:                                       
      111 +    return x if isinstance(x, datetime) else datetime.fromisof
          +ormat(str(x).replace("Z", "+00:00"))                          
      112 +                                                              
      113 +                                                              
      114 +def freeze_brief(conn, d: date, weights: dict[str, float]) -> 
          +BriefResponse:                                                
      115 +    """The demo portfolio's Brief for IST day d, from the comm
          +itted snapshot's events."""                                   
      116 +    snap = json.loads((OUT_DIR / f"{d.isoformat()}.json").read
          +_text())                                                      
      117 +    start = datetime(d.year, d.month, d.day, tzinfo=IST).astim
          +ezone(UTC)                                                    
      118 +    end = start + timedelta(days=1)                           
     … 43 more lines (ctrl+o to expand)
  ⎿  … 2 more files changed

  Ran 1 shell command (ctrl+o to expand)

⏺ The showcase day is frozen with 8 cards, 4 hidden, and 5 of 18 reported for Q2
  FY27 as of 30 Oct. I'm checking the payload size, then I'll commit and push
  the backend so Render deploys while I build the frontend. · summary

⏺ Bash(gzip -c web/public/showcase/brief.json | wc -c; cd web && npm run
      gen:schema >/dev/null 2>&1 && npm run gen:types 2>&1 | tail -2 && git -C
      .. status --short &&…)
  ⎿  15681

     wrote lib/types.ts
     … +20 lines (ctrl+o to expand)
  ⎿  Updated web/lib/types.ts (+169 -26)
      281    resume_after: string | null;
      282    status: "answered" | "not_found" | "unavailable";
      283  }
      284 -export interface BullBearSection {                            
      284 +/**                                                           
      285 + * What the Brief header says. Computed in code (finn/cards/br
          +ief.py); the formula string is shown on tap.                  
      286 + */                                                           
      287 +export interface BriefCounts {                                
      288    /**
      286 -   * @maxItems 3                                              
      289 +   * Full cards: results, management change, price/volume, wha
          +t to watch                                                    
      290     */
      288 -  bear: [] | [Claim] | [Claim, Claim] | [Claim, Claim, Claim];
      291 +  cards: number;                                              
      292 +  chips: number;                                              
      293    /**
      290 -   * @maxItems 3                                              
      294 +   * Estimate; always labelled 'est.' in the UI               
      295     */
      292 -  bull: [] | [Claim] | [Claim, Claim] | [Claim, Claim, Claim];
      293 -  meta: SectionMeta;                                          
      296 +  est_minutes_saved: number;                                  
      297 +  formula: string;                                            
      298 +  hidden_filings: number;                                     
      299 +  /**                                                         
      300 +   * Filings inside the window that belong to the events shown
      301 +   */                                                         
      302 +  material_filings: number;                                   
      303 +  one_liners: number;                                         
      304 +  /**                                                         
      305 +   * Estimated time to read this Brief                        
      306 +   */                                                         
      307 +  read_seconds: number;                                       
      308 +}                                                             
      309 +export interface BriefHolding {                               
      310 +  symbol: string;                                             
      311 +  weight_pct: number | null;                                  
      312 +}                                                             
      313 +/**                                                           
      314 + * POST /brief. Holdings are used only to rank this response: 
          +never stored, never logged.                                   
     … 174 more lines (ctrl+o to expand)
  ⎿  … 1 more file changed

  Read 1 file, ran 2 shell commands (ctrl+o to expand)

⏺ Backend pushed (f7c253c); Render is deploying in the background. Moving to the
  frontend foundation, starting with the bundled Next 16 docs for route
  handlers and cacheComponents.

  Called ccd_turn, ran 3 shell commands (ctrl+o to expand)

⏺ Writing the design tokens, type scale and fonts.

⏺ Write(web/app/globals.css)
  ⎿  Added 173 lines, removed 109 lines
        2  @import "tw-animate-css";
        3  @import "shadcn/tailwind.css";
        4  
        5 -@custom-variant dark (&:is(.dark *));                         
        5 +/* FINN visual direction (DECISIONS: Phase 4 visual direction)
          +: ink on warm paper, hairlines between items,                 
        6 +   a serif for what you read, sans for what you scan, tabular 
          +numerals everywhere. Colour only for signal. */               
        7  
        8 +@custom-variant dark (@media (prefers-color-scheme: dark));   
        9 +                                                              
       10  @theme inline {
        8 -  --color-background: var(--background);                      
        9 -  --color-foreground: var(--foreground);                      
       11 +  --color-paper: var(--paper);                                
       12 +  --color-surface: var(--surface);                            
       13 +  --color-surface-2: var(--surface-2);                        
       14 +  --color-ink: var(--ink);                                    
       15 +  --color-ink-2: var(--ink-2);                                
       16 +  --color-ink-3: var(--ink-3);                                
       17 +  --color-rule: var(--rule);                                  
       18 +  --color-pos: var(--pos);                                    
       19 +  --color-pos-bg: var(--pos-bg);                              
       20 +  --color-neg: var(--neg);                                    
       21 +  --color-neg-bg: var(--neg-bg);                              
       22 +  --color-warn: var(--warn);                                  
       23 +  --color-warn-bg: var(--warn-bg);                            
       24 +                                                              
       25 +  --color-background: var(--paper);                           
       26 +  --color-foreground: var(--ink);                             
       27 +  --color-card: var(--surface);                               
       28 +  --color-card-foreground: var(--ink);                        
       29 +  --color-popover: var(--surface);                            
       30 +  --color-popover-foreground: var(--ink);                     
       31 +  --color-primary: var(--ink);                                
       32 +  --color-primary-foreground: var(--paper);                   
       33 +  --color-secondary: var(--surface-2);                        
       34 +  --color-secondary-foreground: var(--ink);                   
       35 +  --color-muted: var(--surface-2);                            
       36 +  --color-muted-foreground: var(--ink-2);                     
       37 +  --color-accent: var(--surface-2);                           
       38 +  --color-accent-foreground: var(--ink);                      
       39 +  --color-destructive: var(--neg);                            
       40 +  --color-border: var(--rule);                                
       41 +  --color-input: var(--rule);                                 
       42 +  --color-ring: var(--ink-3);                                 
       43 +                                                              
       44    --font-sans: var(--font-geist-sans);
       45 +  --font-serif: var(--font-newsreader);                       
       46    --font-mono: var(--font-geist-mono);
       12 -  --font-heading: var(--font-sans);                           
       13 -  --color-sidebar-ring: var(--sidebar-ring);                  
       14 -  --color-sidebar-border: var(--sidebar-border);              
       15 -  --color-sidebar-accent-foreground: var(--sidebar-accent-fore
          -ground);                                                      
       16 -  --color-sidebar-accent: var(--sidebar-accent);              
       17 -  --color-sidebar-primary-foreground: var(--sidebar-primary-fo
          -reground);                                                    
       18 -  --color-sidebar-primary: var(--sidebar-primary);            
       19 -  --color-sidebar-foreground: var(--sidebar-foreground);      
       20 -  --color-sidebar: var(--sidebar);                            
       21 -  --color-chart-5: var(--chart-5);                            
       22 -  --color-chart-4: var(--chart-4);                            
       23 -  --color-chart-3: var(--chart-3);                            
       24 -  --color-chart-2: var(--chart-2);                            
       25 -  --color-chart-1: var(--chart-1);                            
       26 -  --color-ring: var(--ring);                                  
       27 -  --color-input: var(--input);                                
       28 -  --color-border: var(--border);                              
       29 -  --color-destructive: var(--destructive);                    
       30 -  --color-accent-foreground: var(--accent-foreground);        
       31 -  --color-accent: var(--accent);                              
       32 -  --color-muted-foreground: var(--muted-foreground);          
       33 -  --color-muted: var(--muted);                                
       34 -  --color-secondary-foreground: var(--secondary-foreground);  
       35 -  --color-secondary: var(--secondary);                        
       36 -  --color-primary-foreground: var(--primary-foreground);      
       37 -  --color-primary: var(--primary);                            
       38 -  --color-popover-foreground: var(--popover-foreground);      
       39 -  --color-popover: var(--popover);                            
       40 -  --color-card-foreground: var(--card-foreground);            
       41 -  --color-card: var(--card);                                  
       42 -  --radius-sm: calc(var(--radius) * 0.6);                     
       43 -  --radius-md: calc(var(--radius) * 0.8);                     
       44 -  --radius-lg: var(--radius);                                 
       45 -  --radius-xl: calc(var(--radius) * 1.4);                     
       46 -  --radius-2xl: calc(var(--radius) * 1.8);                    
       47 -  --radius-3xl: calc(var(--radius) * 2.2);                    
       48 -  --radius-4xl: calc(var(--radius) * 2.6);                    
       47 +  --font-heading: var(--font-newsreader);                     
       48 +                                                              
       49 +  --radius-sm: 6px;                                           
       50 +  --radius-md: 8px;                                           
       51 +  --radius-lg: 12px;                                          
       52 +  --radius-xl: 16px;                                          
       53 +  --radius-2xl: 20px;                                         
       54  }
       55  
       56  :root {
       52 -  --background: oklch(1 0 0);                                 
       53 -  --foreground: oklch(0.145 0 0);                             
       54 -  --card: oklch(1 0 0);                                       
       55 -  --card-foreground: oklch(0.145 0 0);                        
       56 -  --popover: oklch(1 0 0);                                    
       57 -  --popover-foreground: oklch(0.145 0 0);                     
       58 -  --primary: oklch(0.205 0 0);                                
       59 -  --primary-foreground: oklch(0.985 0 0);                     
       60 -  --secondary: oklch(0.97 0 0);                               
       61 -  --secondary-foreground: oklch(0.205 0 0);                   
       62 -  --muted: oklch(0.97 0 0);                                   
       63 -  --muted-foreground: oklch(0.556 0 0);                       
       64 -  --accent: oklch(0.97 0 0);                                  
       65 -  --accent-foreground: oklch(0.205 0 0);                      
       66 -  --destructive: oklch(0.577 0.245 27.325);                   
       67 -  --border: oklch(0.922 0 0);                                 
       68 -  --input: oklch(0.922 0 0);                                  
       69 -  --ring: oklch(0.708 0 0);                                   
       70 -  --chart-1: oklch(0.87 0 0);                                 
       71 -  --chart-2: oklch(0.556 0 0);                                
       72 -  --chart-3: oklch(0.439 0 0);                                
       73 -  --chart-4: oklch(0.371 0 0);                                
       74 -  --chart-5: oklch(0.269 0 0);                                
       75 -  --radius: 0.625rem;                                         
       76 -  --sidebar: oklch(0.985 0 0);                                
       77 -  --sidebar-foreground: oklch(0.145 0 0);                     
       78 -  --sidebar-primary: oklch(0.205 0 0);                        
       79 -  --sidebar-primary-foreground: oklch(0.985 0 0);             
       80 -  --sidebar-accent: oklch(0.97 0 0);                          
       81 -  --sidebar-accent-foreground: oklch(0.205 0 0);              
       82 -  --sidebar-border: oklch(0.922 0 0);                         
       83 -  --sidebar-ring: oklch(0.708 0 0);                           
       57 +  --paper: #f7f6f2;                                           
       58 +  --surface: #ffffff;                                         
       59 +  --surface-2: #efede7;                                       
       60 +  --ink: #16150f;                                             
       61 +  --ink-2: #55534c;                                           
       62 +  --ink-3: #737067;                                           
       63 +  --rule: #e3e0d8;                                            
       64 +  --pos: #0b7a4b;                                             
       65 +  --pos-bg: #e6f2ec;                                          
       66 +  --neg: #b3261e;                                             
       67 +  --neg-bg: #f8e8e6;                                          
       68 +  --warn: #9a5b00;                                            
       69 +  --warn-bg: #f6eedf;                                         
       70 +  --radius: 12px;                                             
       71 +  color-scheme: light;                                        
       72  }
       73  
       86 -.dark {                                                       
       87 -  --background: oklch(0.145 0 0);                             
       88 -  --foreground: oklch(0.985 0 0);                             
       89 -  --card: oklch(0.205 0 0);                                   
       90 -  --card-foreground: oklch(0.985 0 0);                        
       91 -  --popover: oklch(0.205 0 0);                                
       92 -  --popover-foreground: oklch(0.985 0 0);                     
       93 -  --primary: oklch(0.922 0 0);                                
       94 -  --primary-foreground: oklch(0.205 0 0);                     
       95 -  --secondary: oklch(0.269 0 0);                              
       96 -  --secondary-foreground: oklch(0.985 0 0);                   
       97 -  --muted: oklch(0.269 0 0);                                  
       98 -  --muted-foreground: oklch(0.708 0 0);                       
       99 -  --accent: oklch(0.269 0 0);                                 
      100 -  --accent-foreground: oklch(0.985 0 0);                      
      101 -  --destructive: oklch(0.704 0.191 22.216);                   
      102 -  --border: oklch(1 0 0 / 10%);                               
      103 -  --input: oklch(1 0 0 / 15%);                                
      104 -  --ring: oklch(0.556 0 0);                                   
      105 -  --chart-1: oklch(0.87 0 0);                                 
      106 -  --chart-2: oklch(0.556 0 0);                                
      107 -  --chart-3: oklch(0.439 0 0);                                
      108 -  --chart-4: oklch(0.371 0 0);                                
      109 -  --chart-5: oklch(0.269 0 0);                                
      110 -  --sidebar: oklch(0.205 0 0);                                
      111 -  --sidebar-foreground: oklch(0.985 0 0);                     
      112 -  --sidebar-primary: oklch(0.488 0.243 264.376);              
      113 -  --sidebar-primary-foreground: oklch(0.985 0 0);             
      114 -  --sidebar-accent: oklch(0.269 0 0);                         
      115 -  --sidebar-accent-foreground: oklch(0.985 0 0);              
      116 -  --sidebar-border: oklch(1 0 0 / 10%);                       
      117 -  --sidebar-ring: oklch(0.556 0 0);                           
       74 +@media (prefers-color-scheme: dark) {                         
       75 +  :root {                                                     
       76 +    --paper: #0f0f0e;                                         
       77 +    --surface: #171715;                                       
       78 +    --surface-2: #22221f;                                     
       79 +    --ink: #edece6;                                           
       80 +    --ink-2: #a8a69d;                                         
       81 +    --ink-3: #85837a;                                         
       82 +    --rule: #2b2a26;                                          
       83 +    --pos: #4cc38a;                                           
       84 +    --pos-bg: #11291e;                                        
       85 +    --neg: #ff7b6e;                                           
       86 +    --neg-bg: #331a17;                                        
       87 +    --warn: #e7a93f;                                          
       88 +    --warn-bg: #2e2414;                                       
       89 +    color-scheme: dark;                                       
       90 +  }                                                           
       91  }
       92  
       93 +/* Type scale. Serif = what you read; sans = what you scan. */
       94 +@utility t-display {                                          
       95 +  font-family: var(--font-serif);                             
       96 +  font-size: 30px;                                            
       97 +  line-height: 34px;                                          
       98 +  font-weight: 500;                                           
       99 +  letter-spacing: -0.01em;                                    
      100 +  font-optical-sizing: auto;                                  
      101 +}                                                             
      102 +@utility t-title {                                            
      103 +  font-family: var(--font-serif);                             
      104 +  font-size: 22px;                                            
      105 +  line-height: 28px;                                          
      106 +  font-weight: 500;                                           
      107 +  letter-spacing: -0.005em;                                   
      108 +}                                                             
      109 +@utility t-headline {                                         
      110 +  font-family: var(--font-serif);                             
      111 +  font-size: 18px;                                            
      112 +  line-height: 24px;                                          
      113 +  font-weight: 500;                                           
      114 +}                                                             
      115 +@utility t-body {                                             
      116 +  font-size: 15px;                                            
      117 +  line-height: 22px;                                          
      118 +}                                                             
      119 +@utility t-small {                                            
      120 +  font-size: 13px;                                            
      121 +  line-height: 18px;                                          
      122 +}                                                             
      123 +@utility t-micro {                                            
      124 +  font-size: 11px;                                            
      125 +  line-height: 14px;                                          
      126 +  font-weight: 600;                                           
      127 +  letter-spacing: 0.06em;                                     
      128 +  text-transform: uppercase;                                  
      129 +}                                                             
      130 +@utility t-figure {                                           
      131 +  font-size: 15px;                                            
      132 +  line-height: 20px;                                          
      133 +  font-weight: 500;                                           
      134 +  font-variant-numeric: tabular-nums lining-nums;             
      135 +}                                                             
      136 +@utility t-figure-lg {                                        
      137 +  font-size: 28px;                                            
      138 +  line-height: 32px;                                          
      139 +  font-weight: 500;                                           
      140 +  font-variant-numeric: tabular-nums lining-nums;             
      141 +  letter-spacing: -0.01em;                                    
      142 +}                                                             
      143 +/* 44 px hit area around a smaller visual control. */         
      144 +@utility hit {                                                
      145 +  position: relative;                                         
      146 +  &::after {                                                  
      147 +    content: "";                                              
      148 +    position: absolute;                                       
      149 +    left: 50%;                                                
      150 +    top: 50%;                                                 
      151 +    width: max(100%, 44px);                                   
      152 +    height: max(100%, 44px);                                  
      153 +    transform: translate(-50%, -50%);                         
      154 +  }                                                           
      155 +}                                                             
      156 +@utility no-scrollbar {                                       
      157 +  scrollbar-width: none;                                      
      158 +  &::-webkit-scrollbar {                                      
      159 +    display: none;                                            
      160 +  }                                                           
      161 +}                                                             
      162 +                                                              
      163  @layer base {
      164    * {
      122 -    @apply border-border outline-ring/50;                     
      165 +    @apply border-rule outline-ink-3/50;                      
      166    }
      124 -  body {                                                      
      125 -    @apply bg-background text-foreground;                     
      126 -  }                                                           
      167    html {
      168      @apply font-sans;
      169 +    -webkit-text-size-adjust: 100%;                           
      170 +    -webkit-tap-highlight-color: transparent;                 
      171    }
      130 -}                                                             
      172   No newline at end of file
      173 +  body {                                                      
      174 +    @apply bg-paper text-ink;                                 
      175 +    font-size: 15px;                                          
      176 +    line-height: 22px;                                        
      177 +    font-variant-numeric: tabular-nums lining-nums;           
      178 +    text-rendering: optimizeLegibility;                       
      179 +  }                                                           
      180 +  button {                                                    
      181 +    cursor: pointer;                                          
      182 +  }                                                           
      183 +  :focus-visible {                                            
      184 +    outline: 2px solid var(--ink);                            
      185 +    outline-offset: 2px;                                      
      186 +  }                                                           
      187 +  @media (prefers-reduced-motion: reduce) {                   
      188 +    *,                                                        
      189 +    *::before,                                                
      190 +    *::after {                                                
      191 +      animation-duration: 0.01ms !important;                  
      192 +      transition-duration: 0.01ms !important;                 
      193 +    }                                                         
      194 +  }                                                           
      195 +}                                                             

⏺ Write(web/app/layout.tsx)
  ⎿  Added 16 lines, removed 16 lines
       1  import type { Metadata, Viewport } from "next";
       2 -import { Geist, Geist_Mono } from "next/font/google";          
       2 +import { Geist, Geist_Mono, Newsreader } from "next/font/google
         +";                                                             
       3  import "./globals.css";
       4  
       5 -const geistSans = Geist({                                      
       6 -  variable: "--font-geist-sans",                               
       5 +const geistSans = Geist({ variable: "--font-geist-sans", subset
         +s: ["latin"], display: "swap" });                              
       6 +const geistMono = Geist_Mono({ variable: "--font-geist-mono", s
         +ubsets: ["latin"], display: "swap", preload: false });         
       7 +const newsreader = Newsreader({                                
       8 +  variable: "--font-newsreader",                               
       9    subsets: ["latin"],
      10 +  display: "swap",                                             
      11 +  axes: ["opsz"],                                              
      12 +  style: ["normal"],                                           
      13  });
      14  
      10 -const geistMono = Geist_Mono({                                 
      11 -  variable: "--font-geist-mono",                               
      12 -  subsets: ["latin"],                                          
      13 -});                                                            
      14 -                                                               
      15  export const metadata: Metadata = {
      16 -  title: "FINN",                                               
      16 +  title: { default: "FINN", template: "%s · FINN" },           
      17    description: "Your portfolio's editor for Indian equities — o
          nly what changes your view, with proof.",
      18 +  applicationName: "FINN",                                     
      19 +  appleWebApp: { capable: true, title: "FINN", statusBarStyle: 
         +"default" },                                                   
      20  };
      21  
      22  export const viewport: Viewport = {
      23    width: "device-width",
      24    initialScale: 1,
      25 +  viewportFit: "cover",                                        
      26    themeColor: [
      24 -    { media: "(prefers-color-scheme: light)", color: "#ffffff" 
         -},                                                             
      25 -    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" }
         -,                                                              
      27 +    { media: "(prefers-color-scheme: light)", color: "#f7f6f2" 
         +},                                                             
      28 +    { media: "(prefers-color-scheme: dark)", color: "#0f0f0e" }
         +,                                                              
      29    ],
      30  };
      31  
      32  export default function RootLayout({ children }: LayoutProps<"/
          ">) {
      33    return (
      31 -    <html                                                      
      32 -      lang="en"                                                
      33 -      className={`${geistSans.variable} ${geistMono.variable} h
         --full antialiased`}                                            
      34 -    >                                                          
      35 -      <body className="min-h-full flex flex-col">{children}</bo
         -dy>                                                            
      34 +    <html lang="en-IN" className={`${geistSans.variable} ${geis
         +tMono.variable} ${newsreader.variable} h-full antialiased`}>   
      35 +      <body className="min-h-full">{children}</body>           
      36      </html>
      37    );
      38  }

⏺ Bash(mkdir -p ~/Documents/finn/web/lib && cat >
      ~/Documents/finn/web/lib/demo.ts <<'EOF'
      // The demo portfolio every phone starts wit…)
  ⎿  Created web/lib/demo.ts (+12 -0)
       1 +// The demo portfolio every phone starts with (no login). Mirro
         +rs backend/finn/portfolio.py DEMO_WEIGHTS.                     
       2 +export const DEMO_WEIGHTS: Record<string, number> = {          
       3 +  HAL: 6, EICHERMOT: 6, GRASIM: 5, TATAPOWER: 5, ALKEM: 5, KALY
         +ANKJIL: 5, COCHINSHIP: 5, TITAGARH: 4, IDEA: 3,                
       4 +  RELIANCE: 8, HDFCBANK: 8, BAJFINANCE: 6, INFY: 7, ITC: 6, DIV
         +ISLAB: 5, TATASTEEL: 5, JUBLFOOD: 5, DIXON: 6,                 
       5 +};                                                             
       6 +                                                               
       7 +// Dossiers built and checked in Phase 3 (also shipped as fixtu
         +res in /public/fixtures for offline fallback).                 
       8 +export const DEMO_TICKERS = ["BAJFINANCE", "INFY", "PERSISTENT"
         +, "POLYCAB"] as const;                                         
       9 +export const FIXTURE_DATE = "11 Nov 2026";                     
      10 +                                                               
      11 +export const SHOWCASE_DATE = "2026-10-30";                     
      12 +export const SHOWCASE_LABEL = "Fri 30 Oct 2026";               
  ⎿  Created web/lib/store.ts (+202 -0)
        1 +"use client";                                                 
        2 +// Everything the phone remembers lives here, in localStorage 
          +under versioned keys (finn.v1.*). No login.                   
        3 +// Holdings (with any quantities) never leave the phone except
          + as symbols + weights in a /brief request.                    
        4 +// Every access is wrapped: private mode or a full quota falls
          + back to memory for the session.                              
        5 +import { useSyncExternalStore } from "react";                 
        6 +import { DEMO_WEIGHTS } from "@/lib/demo";                    
        7 +import type { BriefResponse, Category, FeedbackAction, WeightR
          +ule } from "@/lib/types";                                     
        8 +                                                              
        9 +const PREFIX = "finn.v1.";                                    
       10 +                                                              
       11 +export type LocalHolding = { symbol: string; weight_pct: numbe
          +r | null; quantity: number | null; added_at: string };        
       12 +export type MarkKind = "reviewed" | "not_useful";             
       13 +export type Mark = { kind: MarkKind; at: string; symbol: strin
          +g; category: Category; headline: string; scope?: string };    
       14 +export type Visit = { current: string; previous: string | null
          +; active: string };                                           
       15 +export type CachedBrief = { resp: BriefResponse; at: string; s
          +ig: string };                                                 
       16 +export type WindowKey = "since" | "24h" | "3d" | "7d" | "custo
          +m";                                                           
       17 +                                                              
       18 +const DEMO_HOLDINGS: LocalHolding[] = Object.entries(DEMO_WEIG
          +HTS).map(([symbol, w]) => ({                                  
       19 +  symbol,                                                     
       20 +  weight_pct: w,                                              
       21 +  quantity: null,                                             
       22 +  added_at: "2026-11-01T00:00:00Z",                           
       23 +}));                                                          
       24 +                                                              
       25 +// Stable fallbacks (useSyncExternalStore needs referentially 
          +stable snapshots).                                            
       26 +export const FALLBACK = {                                     
       27 +  holdings: DEMO_HOLDINGS,                                    
       28 +  rules: [] as WeightRule[],                                  
       29 +  pending: [] as FeedbackAction[],                            
       30 +  marks: {} as Record<string, Mark>,                          
       31 +  visit: null as Visit | null,                                
       32 +  tour: false,                                                
       33 +  showcase: false,                                            
       34 +  drivers: {} as Record<string, string[]>,                    
       35 +  recent: [] as string[],                                     
       36 +  symbols: null as { at: string; list: [string, string][] } | 
          +null,                                                         
       37 +  brief: null as CachedBrief | null,                          
       38 +};                                                            
       39 +                                                              
       40 +const mem = new Map<string, string>();                        
     … 162 more lines (ctrl+o to expand)

⏺ Background command "Wait until Render serves the new commit" completed (exit
code 0)

  Ran 2 shell commands (ctrl+o to expand)

⏺ Render serves f7c253c and the new /brief answers in 0.6 s warm, with the
  feedback rule echoed back. Next: the browser API client and the edge-cached
  demo Brief route.

⏺ Bash(mkdir -p ~/Documents/finn/web/app/api/brief/demo && cat >
      ~/Documents/finn/web/app/api/brief/demo/route.ts <<'EOF'
      // The demo p…)
  ⎿  200 110063
     2645 [['20MICRONS', '20 Microns Limited'], ['21STCENMGM', '21st Centur
     y Management Services Limited'], ['360ONE', '360 ONE WAM LIMITED']]
     … +3 lines (ctrl+o to expand)
  ⎿  Created web/app/api/brief/demo/route.ts (+42 -0)
       1 +// The demo portfolio's Brief, cached at Vercel's edge (DECISIO
         +NS: Phase 4 first paint).                                      
       2 +// Evaluators start with the demo portfolio and no rules, so th
         +is *is* their Brief. The edge serves the last good             
       3 +// copy instantly (stale-while-revalidate) while Render wakes; 
         +only successful answers are cached.                            
       4 +import { apiFetch } from "@/lib/api";                          
       5 +                                                               
       6 +export const maxDuration = 60;                                 
       7 +                                                               
       8 +const WINDOWS = new Set(["24h", "3d", "7d"]);                  
       9 +const DEMO_WEIGHTS: Record<string, number> = {                 
      10 +  HAL: 6, EICHERMOT: 6, GRASIM: 5, TATAPOWER: 5, ALKEM: 5, KALY
         +ANKJIL: 5, COCHINSHIP: 5, TITAGARH: 4, IDEA: 3,                
      11 +  RELIANCE: 8, HDFCBANK: 8, BAJFINANCE: 6, INFY: 7, ITC: 6, DIV
         +ISLAB: 5, TATASTEEL: 5, JUBLFOOD: 5, DIXON: 6,                 
      12 +};                                                             
      13 +                                                               
      14 +export async function GET(req: Request) {                      
      15 +  const window = new URL(req.url).searchParams.get("window") ??
         + "7d";                                                         
      16 +  if (!WINDOWS.has(window)) return Response.json({ detail: "win
         +dow must be 24h, 3d or 7d" }, { status: 400 });                
      17 +  try {                                                        
      18 +    const r = await apiFetch("/brief", {                       
      19 +      method: "POST",                                          
      20 +      headers: { "content-type": "application/json" },         
      21 +      body: JSON.stringify({                                   
      22 +        holdings: Object.entries(DEMO_WEIGHTS).map(([symbol, we
         +ight_pct]) => ({ symbol, weight_pct })),                       
      23 +        window,                                                
      24 +      }),                                                      
      25 +    });                                                        
      26 +    const text = await r.text();                               
      27 +    return new Response(text, {                                
      28 +      status: r.status,                                        
      29 +      headers: {                                               
      30 +        "content-type": "application/json",                    
      31 +        "cache-control": "public, max-age=0, must-revalidate", 
      32 +        ...(r.ok ? { "vercel-cdn-cache-control": "max-age=300, 
         +stale-while-revalidate=86400" } : {}),                         
      33 +      },                                                       
      34 +    });                                                        
      35 +  } catch (e) {                                                
      36 +    const timedOut = e instanceof Error && e.name === "TimeoutE
         +rror";                                                         
      37 +    return Response.json(                                      
      38 +      { detail: timedOut ? "API timed out — it may still be wak
         +ing up" : "API unreachable" },                                 
      39 +      { status: 502, headers: { "cache-control": "no-store" } }
         +,                                                              
      40 +    );                                                         
     … 2 more lines (ctrl+o to expand)
  ⎿  Created web/lib/client.ts (+56 -0)
       1 +"use client";                                                  
       2 +// Browser → Vercel proxy (/api/*) → Render. Render's free tier
         + can take ~50 s to wake: callers show progress,                
       3 +// never a blank screen, and keep the last good data (CLAUDE.md
         + rule 7).                                                      
       4 +import type { BriefRequest, BriefResponse, DossierJob, DossierR
         +esponse } from "@/lib/types";                                  
       5 +                                                               
       6 +export class FetchError extends Error {                        
       7 +  constructor(                                                 
       8 +    public status: number,                                     
       9 +    message: string,                                           
      10 +  ) {                                                          
      11 +    super(message);                                            
      12 +  }                                                            
      13 +  get waking() {                                               
      14 +    return this.status === 502 || this.status === 503 || this.s
         +tatus === 504 || this.status === 0;                            
      15 +  }                                                            
      16 +}                                                              
      17 +                                                               
      18 +async function call<T>(url: string, init: RequestInit = {}, tim
         +eoutMs = 58_000): Promise<T> {                                 
      19 +  let r: Response;                                             
      20 +  try {                                                        
      21 +    r = await fetch(url, { cache: "no-store", ...init, signal: 
         +init.signal ?? AbortSignal.timeout(timeoutMs) });              
      22 +  } catch (e) {                                                
      23 +    if (e instanceof DOMException && e.name === "AbortError") t
         +hrow e;                                                        
      24 +    throw new FetchError(0, navigator.onLine === false ? "You'r
         +e offline" : "Couldn't reach FINN");                           
      25 +  }                                                            
      26 +  if (!r.ok) {                                                 
      27 +    let detail = `FINN answered ${r.status}`;                  
      28 +    try {                                                      
      29 +      const b = await r.json();                                
      30 +      if (typeof b?.detail === "string") detail = b.detail;    
      31 +    } catch {}                                                 
      32 +    throw new FetchError(r.status, detail);                    
      33 +  }                                                            
      34 +  return (await r.json()) as T;                                
      35 +}                                                              
      36 +                                                               
      37 +const json = (body: unknown): RequestInit => ({                
      38 +  method: "POST",                                              
      39 +  headers: { "content-type": "application/json" },             
      40 +  body: JSON.stringify(body),                                  
     … 16 more lines (ctrl+o to expand)
  ⎿  … 1 more file changed

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(npm view uqr version time.modified 2>/dev/null | head -3 && npm install
      --save-exact uqr@0.1.2 2>&1 | tail -2 && node -e "const
      {renderSVG}=require('uqr'); cons…)
  ⎿  version = '0.1.3'
     time.modified = '2026-04-03T01:23:47.719Z'
     … +3 lines (ctrl+o to expand)
  ⎿  Updated web/package-lock.json (+8 -1)
      17          "react": "19.3.0",
      18          "react-dom": "19.3.0",
      19          "shadcn": "^4.23.0",
      20 -        "tw-animate-css": "^1.4.0"                             
      20 +        "tw-animate-css": "^1.4.0",                            
      21 +        "uqr": "0.1.2"                                         
      22        },
      23        "devDependencies": {
      24          "@tailwindcss/turbopack": "^4",
     ...
      8996          "browserslist": ">= 4.21.0"
      8997        }
      8998      },
      8999 +    "node_modules/uqr": {                                    
      9000 +      "version": "0.1.2",                                    
      9001 +      "resolved": "https://registry.npmjs.org/uqr/-/uqr-0.1.2
           +.tgz",                                                       
      9002 +      "integrity": "sha512-MJu7ypHq6QasgF5YRTjqscSzQp/W11zoUk
           +6kvmlH+fmWEs63Y0Eib13hYFwAzagRJcVY8WVnlV+eBDUGMJ5IbA==",     
      9003 +      "license": "MIT"                                       
      9004 +    },                                                       
      9005      "node_modules/uri-js": {
      9006        "version": "4.4.1",
      9007        "resolved": "https://registry.npmjs.org/uri-js/-/uri-js
            -4.4.1.tgz",
  ⎿  Updated web/package.json (+2 -1)
      21      "react": "19.3.0",
      22      "react-dom": "19.3.0",
      23      "shadcn": "^4.23.0",
      24 -    "tw-animate-css": "^1.4.0"                                 
      24 +    "tw-animate-css": "^1.4.0",                                
      25 +    "uqr": "0.1.2"                                             
      26    },
      27    "devDependencies": {
      28      "@tailwindcss/turbopack": "^4",
⏺ Writing the app shell: dock (Ask bar + tab bar), bottom sheet, undo toast,
  state views and signal glyphs.

⏺ Bash(mkdir -p ~/Documents/finn/web/components/shell && cd
      ~/Documents/finn/web/components/shell && cat > ui-store.ts
      <<'EOF'
      "use cli…)
  ⎿  ok
  ⎿  Created web/components/shell/AppShell.tsx (+25 -0)
       1 +"use client";                                                  
       2 +// Phone-width column + bottom dock (Ask bar above the tab bar,
         + thumb zone) + undo toast.                                     
       3 +// On desktop every app route renders in a centred 430 px colum
         +n; only "/" shows the QR landing.                              
       4 +import type { ReactNode } from "react";                        
       5 +import { LazyMotion, domAnimation } from "framer-motion";      
       6 +import { AskBar } from "./AskBar";                             
       7 +import { TabBar } from "./TabBar";                             
       8 +import { ToastHost } from "./Toast";                           
       9 +                                                               
      10 +export function AppShell({ children }: { children: ReactNode })
         + {                                                             
      11 +  return (                                                     
      12 +    <LazyMotion features={domAnimation} strict>                
      13 +      <div className="mx-auto flex min-h-dvh w-full max-w-[430p
         +x] flex-col bg-paper pb-[calc(112px+env(safe-area-inset-bottom)
         +)] min-[431px]:border-x min-[431px]:border-rule">              
      14 +        {children}                                             
      15 +      </div>                                                   
      16 +      <div className="fixed inset-x-0 bottom-0 z-30">          
      17 +        <div className="mx-auto w-full max-w-[430px] bg-paper/9
         +5 pb-[env(safe-area-inset-bottom)] backdrop-blur-sm min-[431px]
         +:border-x min-[431px]:border-rule">                            
      18 +          <AskBar />                                           
      19 +          <TabBar />                                           
      20 +        </div>                                                 
      21 +      </div>                                                   
      22 +      <ToastHost />                                            
      23 +    </LazyMotion>                                              
      24 +  );                                                           
      25 +}                                                              
  ⎿  Created web/components/shell/AskBar.tsx (+77 -0)
       1 +"use client";                                                  
       2 +// Always-visible Ask bar, scoped to the screen. Until /ask is 
         +wired (Friday), the 3 suggestions jump to the                  
       3 +// section or card that answers them; free text says so honestl
         +y. lib/ask.ts is the one place to change.                      
       4 +import { useState } from "react";                              
       5 +import { MessageSquareText } from "lucide-react";              
       6 +import { Sheet } from "./Sheet";                               
       7 +import { useAskContext } from "./ui-store";                    
       8 +                                                               
       9 +export function AskBar() {                                     
      10 +  const ctx = useAskContext();                                 
      11 +  const [open, setOpen] = useState(false);                     
      12 +  const [q, setQ] = useState("");                              
      13 +  return (                                                     
      14 +    <>                                                         
      15 +      <div className="px-3 pb-2 pt-2">                         
      16 +        <button                                                
      17 +          type="button"                                        
      18 +          onClick={() => setOpen(true)}                        
      19 +          className="flex h-11 w-full items-center gap-2 rounde
         +d-full border border-rule bg-surface px-4 text-left text-[15px]
         + text-ink-3"                                                   
      20 +        >                                                      
      21 +          <MessageSquareText className="size-[18px] shrink-0" s
         +trokeWidth={1.5} />                                            
      22 +          <span className="truncate">{ctx.placeholder}</span>  
      23 +        </button>                                              
      24 +      </div>                                                   
      25 +      <Sheet open={open} onClose={() => setOpen(false)} eyebrow
         +="Ask" title={ctx.placeholder.replace(/…$/, "")}>              
      26 +        <div className="space-y-2">                            
      27 +          {ctx.chips.length > 0 ? (                            
      28 +            <>                                                 
      29 +              <p className="t-small text-ink-2">Suggested for t
         +his screen — each opens the part that answers it.</p>          
      30 +              <ul className="space-y-2">                       
      31 +                {ctx.chips.map((c) => (                        
      32 +                  <li key={c.label}>                           
      33 +                    <button                                    
      34 +                      type="button"                            
      35 +                      onClick={() => {                         
      36 +                        setOpen(false);                        
      37 +                        c.run();                               
      38 +                      }}                                       
      39 +                      className="w-full rounded-xl border borde
         +r-rule px-4 py-3 text-left text-[15px] hover:bg-surface-2"     
      40 +                    >                                          
     … 37 more lines (ctrl+o to expand)
  ⎿  Created web/components/shell/Sheet.tsx (+76 -0)
       1 +"use client";                                                  
       2 +// Bottom sheet: provenance, scope choice, Why #1, hidden drawe
         +r, import. Thumb-zone actions, Esc/backdrop closes.            
       3 +import { useEffect, useRef, type ReactNode } from "react";     
       4 +import { createPortal } from "react-dom";                      
       5 +import { X } from "lucide-react";                              
       6 +import { useHydrated } from "@/lib/store";                     
       7 +                                                               
       8 +export function Sheet({                                        
       9 +  open,                                                        
      10 +  onClose,                                                     
      11 +  title,                                                       
      12 +  eyebrow,                                                     
      13 +  children,                                                    
      14 +  footer,                                                      
      15 +}: {                                                           
      16 +  open: boolean;                                               
      17 +  onClose: () => void;                                         
      18 +  title?: ReactNode;                                           
      19 +  eyebrow?: ReactNode;                                         
      20 +  children: ReactNode;                                         
      21 +  footer?: ReactNode;                                          
      22 +}) {                                                           
      23 +  const hydrated = useHydrated();                              
      24 +  const panel = useRef<HTMLDivElement>(null);                  
      25 +  useEffect(() => {                                            
      26 +    if (!open) return;                                         
      27 +    const prev = document.activeElement as HTMLElement | null; 
      28 +    panel.current?.focus();                                    
      29 +    const onKey = (e: KeyboardEvent) => e.key === "Escape" && o
         +nClose();                                                      
      30 +    window.addEventListener("keydown", onKey);                 
      31 +    const overflow = document.body.style.overflow;             
      32 +    document.body.style.overflow = "hidden";                   
      33 +    return () => {                                             
      34 +      window.removeEventListener("keydown", onKey);            
      35 +      document.body.style.overflow = overflow;                 
      36 +      prev?.focus?.();                                         
      37 +    };                                                         
      38 +  }, [open, onClose]);                                         
      39 +  if (!hydrated || !open) return null;                         
      40 +  return createPortal(                                         
     … 36 more lines (ctrl+o to expand)
  ⎿  Created web/components/shell/StateView.tsx (+85 -0)
       1 +// Loading, empty, error and stale states — every screen uses t
         +hese so they look and read the same.                           
       2 +import type { ReactNode } from "react";                        
       3 +import { AlertTriangle, CloudOff, RotateCcw } from "lucide-reac
         +t";                                                            
       4 +                                                               
       5 +export function Skeleton({ rows = 3, label }: { rows?: number; 
         +label?: string }) {                                            
       6 +  return (                                                     
       7 +    <div aria-busy className="divide-y divide-rule border-y bor
         +der-rule bg-surface" role="status">                            
       8 +      {label && <span className="sr-only">{label}</span>}      
       9 +      {Array.from({ length: rows }).map((_, i) => (            
      10 +        <div key={i} className="animate-pulse px-4 py-4">      
      11 +          <div className="h-2.5 w-28 rounded bg-surface-2" />  
      12 +          <div className="mt-3 h-4 w-4/5 rounded bg-surface-2" 
         +/>                                                             
      13 +          <div className="mt-2 h-3 w-3/5 rounded bg-surface-2" 
         +/>                                                             
      14 +          <div className="mt-3 h-3 w-2/5 rounded bg-surface-2" 
         +/>                                                             
      15 +        </div>                                                 
      16 +      ))}                                                      
      17 +    </div>                                                     
      18 +  );                                                           
      19 +}                                                              
      20 +                                                               
      21 +export function Empty({ title, children, action }: { title: str
         +ing; children?: ReactNode; action?: ReactNode }) {             
      22 +  return (                                                     
      23 +    <div className="px-4 py-10">                               
      24 +      <p className="t-headline">{title}</p>                    
      25 +      {children && <div className="t-body mt-1 text-ink-2">{chi
         +ldren}</div>}                                                  
      26 +      {action && <div className="mt-4">{action}</div>}         
      27 +    </div>                                                     
      28 +  );                                                           
      29 +}                                                              
      30 +                                                               
      31 +export function ErrorState({                                   
      32 +  title = "Couldn't load this",                                
      33 +  detail,                                                      
      34 +  onRetry,                                                     
      35 +  offline,                                                     
      36 +}: {                                                           
      37 +  title?: string;                                              
      38 +  detail?: string;                                             
      39 +  onRetry?: () => void;                                        
      40 +  offline?: boolean;                                           
     … 45 more lines (ctrl+o to expand)
  ⎿  Created web/components/shell/TabBar.tsx (+37 -0)
       1 +"use client";                                                  
       2 +import Link from "next/link";                                  
       3 +import { usePathname } from "next/navigation";                 
       4 +import { Briefcase, Newspaper, Search, SlidersHorizontal } from
         + "lucide-react";                                               
       5 +                                                               
       6 +const TABS = [                                                 
       7 +  { href: "/brief", label: "Brief", Icon: Newspaper, match: (p:
         + string) => p === "/" || p.startsWith("/brief") || p.startsWith
         +("/e/") },                                                     
       8 +  { href: "/portfolio", label: "Portfolio", Icon: Briefcase, ma
         +tch: (p: string) => p.startsWith("/portfolio") },              
       9 +  { href: "/research", label: "Research", Icon: Search, match: 
         +(p: string) => p.startsWith("/research") },                    
      10 +  { href: "/rules", label: "Rules", Icon: SlidersHorizontal, ma
         +tch: (p: string) => p.startsWith("/rules") || p.startsWith("/co
         +nnect") },                                                     
      11 +];                                                             
      12 +                                                               
      13 +export function TabBar() {                                     
      14 +  const path = usePathname() ?? "/";                           
      15 +  return (                                                     
      16 +    <nav aria-label="Main" className="grid grid-cols-4 border-t
         + border-rule bg-paper">                                        
      17 +      {TABS.map(({ href, label, Icon, match }) => {            
      18 +        const on = match(path);                                
      19 +        return (                                               
      20 +          <Link                                                
      21 +            key={href}                                         
      22 +            href={href}                                        
      23 +            data-tour={href === "/research" ? "research-tab" : 
         +undefined}                                                     
      24 +            aria-current={on ? "page" : undefined}             
      25 +            className={`relative flex h-14 flex-col items-cente
         +r justify-center gap-0.5 text-[11px] ${                        
      26 +              on ? "font-semibold text-ink" : "text-ink-3"     
      27 +            }`}                                                
      28 +          >                                                    
      29 +            {on && <span aria-hidden className="absolute inset-
         +x-6 top-0 h-0.5 bg-ink" />}                                    
      30 +            <Icon className="size-[22px]" strokeWidth={on ? 2 :
         + 1.5} />                                                       
      31 +            {label}                                            
      32 +          </Link>                                              
      33 +        );                                                     
      34 +      })}                                                      
      35 +    </nav>                                                     
      36 +  );                                                           
      37 +}                                                              
  ⎿  … 3 more files changed

⏺ Now restyling the Phase 2 card components to the new tokens, with a shared
  provenance sheet for every tappable number.

⏺ Bash(cd ~/Documents/finn/web && cat > lib/format.ts <<'EOF'
      // Display formatting (Indian conventions). Display only — never feed
      these strings back…)
  ⎿  ok
  ⎿  Created web/components/cards/ClaimLink.tsx (+30 -0)
       1 +"use client";                                                  
       2 +// A sentence with provenance: tap → its citations with page an
         +d quote.                                                       
       3 +import { useState, type ReactNode } from "react";              
       4 +import type { Claim } from "@/lib/types";                      
       5 +import { Sheet } from "@/components/shell/Sheet";              
       6 +import { ClaimProvenance } from "./Provenance";                
       7 +                                                               
       8 +export function ClaimText({ claim, className = "", children }: 
         +{ claim: Claim; className?: string; children?: ReactNode }) {  
       9 +  const [open, setOpen] = useState(false);                     
      10 +  const unverified = claim.status !== "verified";              
      11 +  return (                                                     
      12 +    <>                                                         
      13 +      <button                                                  
      14 +        type="button"                                          
      15 +        onClick={(e) => {                                      
      16 +          e.stopPropagation();                                 
      17 +          setOpen(true);                                       
      18 +        }}                                                     
      19 +        className={`text-left underline decoration-dotted decor
         +ation-1 underline-offset-[5px] ${                              
      20 +          unverified ? "decoration-warn" : "decoration-ink-3/50
         +"                                                              
      21 +        } ${className}`}                                       
      22 +      >                                                        
      23 +        {children ?? claim.text}                               
      24 +      </button>                                                
      25 +      <Sheet open={open} onClose={() => setOpen(false)} eyebrow
         +="Source">                                                     
      26 +        <ClaimProvenance claim={claim} />                      
      27 +      </Sheet>                                                 
      28 +    </>                                                        
      29 +  );                                                           
      30 +}                                                              
  ⎿  Updated web/components/cards/FigureValue.tsx (+27 -63)
       1  "use client";
       2 -// A number with provenance: tap → drawer with document, page, 
         -quote, formula and inputs (PRODUCT §8 rule).                   
       2 +// A number with provenance: tap → sheet with document, page, q
         +uote, formula and inputs (PRODUCT §8 rule).                    
       3  import { useState } from "react";
       4  import type { Figure } from "@/lib/types";
       5  import { figureText } from "@/lib/format";
       6 +import { Sheet } from "@/components/shell/Sheet";              
       7 +import { FigureProvenance } from "./Provenance";               
       8  
       7 -export function FigureValue({ f, signed = false, className = ""
         - }: { f: Figure | null | undefined; signed?: boolean; className
         -?: string }) {                                                 
       9 +export function FigureValue({                                  
      10 +  f,                                                           
      11 +  signed = false,                                              
      12 +  className = "",                                              
      13 +}: {                                                           
      14 +  f: Figure | null | undefined;                                
      15 +  signed?: boolean;                                            
      16 +  className?: string;                                          
      17 +}) {                                                           
      18    const [open, setOpen] = useState(false);
       9 -  if (!f) return <span className="text-muted-foreground">—</spa
         -n>;                                                            
      19 +  if (!f) return <span className="text-ink-3">—</span>;        
      20    const unverified = f.status !== "verified";
      21 +  const text = figureText(f, { signed });                      
      22    return (
      23      <>
      24        <button
      25          type="button"
      15 -        onClick={() => setOpen(true)}                          
      16 -        className={`tabular-nums underline decoration-dotted un
         -derline-offset-4 ${unverified ? "decoration-amber-500" : "decor
         -ation-foreground/30"} ${className}`}                           
      17 -        aria-label={`${f.label}: ${figureText(f, { signed })} —
         - show source`}                                                 
      26 +        data-figure                                            
      27 +        onClick={(e) => {                                      
      28 +          e.stopPropagation();                                 
      29 +          setOpen(true);                                       
      30 +        }}                                                     
      31 +        className={`hit tabular-nums underline decoration-dotte
         +d decoration-1 underline-offset-[5px] ${                       
      32 +          unverified ? "decoration-warn" : "decoration-ink-3/70
         +"                                                              
      33 +        } ${className}`}                                       
      34 +        aria-label={`${f.label}: ${text}${unverified ? " (unver
         +ified)" : ""} — show source`}                                  
     … 66 more lines (ctrl+o to expand)
  ⎿  Created web/components/cards/Provenance.tsx (+118 -0)
        1 +"use client";                                                 
        2 +// The provenance drawer: every number and claim opens its doc
          +ument, page and verbatim quote (PRODUCT §8, rule 3).          
        3 +import { ArrowUpRight } from "lucide-react";                  
        4 +import type { Citation, Claim, Figure } from "@/lib/types";   
        5 +import { figureText, ist, sourceHref, sourceLabel } from "@/li
          +b/format";                                                    
        6 +                                                              
        7 +const STATUS: Record<string, { text: string; cls: string }> = 
          +{                                                             
        8 +  verified: { text: "Verified in source", cls: "text-pos" },  
        9 +  unverified: { text: "Unverified", cls: "text-warn" },       
       10 +  not_found: { text: "Not found in sources", cls: "text-warn" 
          +},                                                            
       11 +};                                                            
       12 +                                                              
       13 +export function CitationBlock({ c, label }: { c: Citation; lab
          +el?: string }) {                                              
       14 +  return (                                                    
       15 +    <div className="border-t border-rule py-3 first:border-t-0
          +">                                                            
       16 +      <div className="flex items-start justify-between gap-3">
       17 +        <div className="min-w-0">                             
       18 +          {label && <p className="t-micro text-ink-3">{label}<
          +/p>}                                                          
       19 +          <p className="t-small font-medium">{c.title ?? sourc
          +eLabel(c)}</p>                                                
       20 +          <p className="t-small text-ink-3">                  
       21 +            {[sourceLabel(c), c.published_at ? ist(c.published
          +_at, false) : null].filter(Boolean).join(" · ")}              
       22 +          </p>                                                
       23 +        </div>                                                
       24 +        <a                                                    
       25 +          href={sourceHref(c)}                                
       26 +          target="_blank"                                     
       27 +          rel="noopener noreferrer"                           
       28 +          className="t-small inline-flex h-9 shrink-0 items-ce
          +nter gap-1 rounded-full border border-rule px-3 font-medium"  
       29 +        >                                                     
       30 +          {c.page ? `Open p.${c.page}` : "Open"} <ArrowUpRight
          + className="size-3.5" />                                      
       31 +        </a>                                                  
       32 +      </div>                                                  
       33 +      {c.quote && (                                           
       34 +        <blockquote className="mt-2 border-l-2 border-ink-3/40
          + pl-3 font-serif text-[16px] leading-[23px] text-ink">        
       35 +          “{c.quote}”                                         
       36 +        </blockquote>                                         
       37 +      )}                                                      
       38 +      {c.locator && !c.quote && <p className="mt-1 break-all f
          +ont-mono text-[11px] text-ink-3">{c.locator}</p>}             
       39 +    </div>                                                    
       40 +  );                                                          
     … 78 more lines (ctrl+o to expand)
  ⎿  Updated web/lib/format.ts (+115 -15)
       1  // Display formatting (Indian conventions). Display only — neve
          r feed these strings back into arithmetic.
       2 -import type { Figure } from "@/lib/types";                     
       2 +import type { Card, Citation, Figure } from "@/lib/types";     
       3  
       4  const inr0 = new Intl.NumberFormat("en-IN", { maximumFractionDi
          gits: 0 });
       5  const inr1 = new Intl.NumberFormat("en-IN", { minimumFractionDi
          gits: 1, maximumFractionDigits: 1 });
       6  const inr2 = new Intl.NumberFormat("en-IN", { minimumFractionDi
          gits: 2, maximumFractionDigits: 2 });
       7 +const upTo2 = new Intl.NumberFormat("en-IN", { maximumFractionD
         +igits: 2 });                                                   
       8  
       9  const minus = (s: string) => s.replace("-", "−");
      10  
     ...
      12    return `₹${minus(Math.abs(v) >= 100 ? inr0.format(v) : inr1.f
          ormat(v))} Cr`;
      13  }
      14  
      15 +/** Signed change with ▲/▼ (moves stay ink; the glyph carries d
         +irection). */                                                  
      16  export function signed(v: number, digits = 1, suffix = "%"): st
          ring {
      17    const r = Number(v.toFixed(digits));
      16 -  const sign = r > 0 ? "+" : r < 0 ? "−" : "±";                
      17 -  return `${sign}${Math.abs(r).toFixed(digits)}${suffix}`;     
      18 +  const glyph = r > 0 ? "▲" : r < 0 ? "▼" : "±";               
      19 +  return `${glyph}${Math.abs(r).toFixed(digits)}${suffix}`;    
      20 +}                                                              
      21 +                                                               
      22 +export function count(v: number): string {                     
      23 +  const a = Math.abs(v);                                       
      24 +  if (a >= 1e7) return `${minus(upTo2.format(v / 1e7))} Cr`;   
      25 +  if (a >= 1e5) return `${minus(upTo2.format(v / 1e5))} lakh`; 
      26 +  return minus(inr0.format(v));                                
      27  }
      28  
      29  export function figureText(f: Figure | null | undefined, opts: 
          { signed?: boolean } = {}): string {
     ...
      31    const v = f.value;
      32    switch (f.unit) {
      33      case "INR_CR":
      25 -      return moneyCr(v);                                       
      34 +      return opts.signed ? `${v >= 0 ? "▲" : "▼"}${moneyCr(Math
         +.abs(v))}` : moneyCr(v);                                       
      35      case "PCT":
      36        return opts.signed ? signed(v) : `${minus(inr1.format(v))
          }%`;
      37      case "BPS":
      38        return signed(v, 0, " bps");
     … 137 more lines (ctrl+o to expand)

⏺ Bash(cat > primitives.tsx <<'EOF'
      // Shared card primitives: impact, verification, source chip, event-thread
      timeline. Pure presentational.…)
  ⎿  ok
  ⎿  Updated web/components/cards/InlineChip.tsx (+4 -3)
       3  
       4  export function InlineChip({ symbol, d }: { symbol: string; d: 
          ChipDetail }) {
       5    const body = (
       6 -    <span className="inline-flex items-center gap-1 rounded-ful
         -l border px-2.5 py-1 text-xs">                                 
       7 -      <span className="font-semibold">{symbol}</span> {d.text} 
       6 +    <span className="t-small inline-flex items-center gap-1.5">
       7 +      <span className="font-semibold">{symbol}</span>          
       8 +      <span className="text-ink-2">{d.text}</span>             
       9      </span>
      10    );
      11    return d.citation ? (
      11 -    <a href={d.citation.url} target="_blank" rel="noopener nore
         -ferrer">                                                       
      12 +    <a href={d.citation.url} target="_blank" rel="noopener nore
         +ferrer" className="underline decoration-ink-3/40 underline-offs
         +et-4">                                                         
      13        {body}
      14      </a>
      15    ) : (
  ⎿  Updated web/components/cards/OneLinerCard.tsx (+18 -13)
       1  // One-liner (M&A, fund raise, litigation, rating, pledging, ca
          pex, orders, insider trades): one line + key number.
       2  import type { OneLinerDetail } from "@/lib/types";
       3 +import { ClaimText } from "./ClaimLink";                       
       4  import { FigureValue } from "./FigureValue";
       5  
       5 -const DIRECTION: Record<string, string> = { up: "▲ Up", down: "
         -▼ Down", new: "New", unchanged: "Unchanged" };                 
       6 +export function oneLinerDirection(d: OneLinerDetail, category: 
         +string): string | null {                                       
       7 +  if (!d.direction) return null;                               
       8 +  if (category === "credit_rating")                            
       9 +    return { up: "▲ Upgrade", down: "▼ Downgrade", new: "New ra
         +ting", unchanged: "Reaffirmed" }[d.direction];                 
      10 +  if (category === "pledging")                                 
      11 +    return { up: "▲ Pledge increased", down: "▼ Pledge reduced"
         +, new: "New pledge", unchanged: "Unchanged" }[d.direction];    
      12 +  return { up: "▲ Up", down: "▼ Down", new: "New", unchanged: "
         +Unchanged" }[d.direction];                                     
      13 +}                                                              
      14  
      15  export function OneLinerBody({ d, category }: { d: OneLinerDeta
          il; category: string }) {
       8 -  const dir =                                                  
       9 -    d.direction && category === "credit_rating"                
      10 -      ? { up: "▲ Upgrade", down: "▼ Downgrade", new: "New ratin
         -g", unchanged: "Reaffirmed" }[d.direction]                     
      11 -      : d.direction && category === "pledging"                 
      12 -        ? { up: "▲ Pledge increased", down: "▼ Pledge reduced",
         - new: "New pledge", unchanged: "Unchanged" }[d.direction]      
      13 -        : d.direction                                          
      14 -          ? DIRECTION[d.direction]                             
      15 -          : null;                                              
      16 +  const dir = oneLinerDirection(d, category);                  
      17    return (
      17 -    <div className="space-y-1 text-sm">                        
      18 +    <div className="t-small space-y-1.5">                      
      19 +      <p className="text-ink-2">                               
      20 +        <ClaimText claim={d.line} />                           
      21 +      </p>                                                     
      22        {d.key_figure && (
      23          <p>
      20 -          {d.key_figure.label}: <FigureValue f={d.key_figure} c
         -lassName="font-semibold" />                                    
      24 +          <span className="text-ink-2">{d.key_figure.label}: </
         +span>                                                          
      25 +          <FigureValue f={d.key_figure} className="font-medium"
         + />                                                            
      26          </p>
      27        )}
      23 -      {dir && <p className="text-xs font-medium">{dir}</p>}    
      28 +      {dir && <p className={`font-medium ${category === "credit
         +_rating" && d.direction === "down" ? "text-neg" : ""}`}>{dir}</
         +p>}                                                            
     … 6 more lines (ctrl+o to expand)
  ⎿  Updated web/components/cards/PriceVolumeAlertCard.tsx (+37 -19)
       4  
       5  export function PriceVolumeBody({ d }: { d: PriceVolumeDetail }
          ) {
       6    return (
       7 -    <div className="space-y-2 text-sm">                        
       7 +    <div className="t-small space-y-2">                        
       8        <div className="flex flex-wrap gap-x-4 gap-y-1">
       9          <span>
      10 -          Move <FigureValue f={d.move_pct} signed className="fo
         -nt-semibold" />                                                
      10 +          <span className="text-ink-2">Move </span>            
      11 +          <FigureValue f={d.move_pct} signed className="font-me
         +dium" />                                                       
      12          </span>
      13 +        {d.relative_move_pct && (                              
      14 +          <span>                                               
      15 +            <span className="text-ink-2">vs sector </span>     
      16 +            <FigureValue f={d.relative_move_pct} signed />     
      17 +          </span>                                              
      18 +        )}                                                     
      19          {d.sector_move_pct && (
      13 -          <span className="text-muted-foreground">             
      20 +          <span className="text-ink-2">                        
      21              {d.sector_index} <FigureValue f={d.sector_move_pct}
           signed />
      22            </span>
      23          )}
      24          {d.volume_ratio && (
      25            <span>
      19 -            Volume <FigureValue f={d.volume_ratio} /> 20-day av
         -g                                                              
      26 +            <span className="text-ink-2">Volume </span>        
      27 +            <FigureValue f={d.volume_ratio} />                 
      28 +            <span className="text-ink-2"> of 20-day avg</span> 
      29            </span>
      30          )}
      22 -        {d.z_score !== null && <span className="text-muted-fore
         -ground">{Math.abs(d.z_score).toFixed(1)}σ day</span>}          
      31 +        {d.z_score !== null && <span className="text-ink-3">{Ma
         +th.abs(d.z_score).toFixed(1)}σ for this stock</span>}          
      32 +      </div>                                                   
      33 +      {d.day_label && <p className="font-medium">{d.day_label}<
         +/p>}                                                           
      34 +      <div>                                                    
      35 +        <p className="t-micro text-ink-3">Likely explanation</p
         +>                                                              
      36 +        <ol className="mt-1 space-y-1">                        
      37 +          {d.explanations.map((e, i) => (                      
      38 +            <li key={i} className={e.kind === "none" ? "font-me
         +dium text-warn" : ""}>                                         
     … 34 more lines (ctrl+o to expand)
  ⎿  Updated web/components/cards/ResultsCard.tsx (+33 -21)
      1  // Results: current quarter, QoQ, YoY per line; ✓ Cross-checked 
         / pending / "Couldn't verify — open filing".
      2 +import { ArrowUpRight } from "lucide-react";                    
      3  import type { Card, ResultsDetail } from "@/lib/types";
      4  import { FigureValue } from "./FigureValue";
      5  import { VerificationBadge } from "./primitives";
     ...
       9    if (d.verification === "mismatch") {
      10      const url = d.filing_url ?? card.sources[0]?.url;
      11      return (
      11 -      <div className="rounded-xl border border-red-200 p-3 text
         --sm dark:border-red-900">                                      
      12 +      <div className="rounded-xl bg-neg-bg p-3">               
      13          <VerificationBadge state="mismatch" note={d.verificatio
          n_note} />
      13 -        <p className="mt-1 text-xs text-muted-foreground">     
      14 -          The numbers didn&apos;t match an independent source, 
         -so FINN won&apos;t show them.                                  
      14 +        <p className="t-small mt-1 text-ink-2">                
      15 +          These numbers didn&apos;t match an independent source
         +, so FINN won&apos;t show them.                                
      16 +          {d.verification_note ? ` ${d.verification_note}` : ""
         +}                                                              
      17          </p>
      18          {url && (
      17 -          <a href={url} target="_blank" rel="noopener noreferre
         -r" className="mt-2 inline-block text-sm font-medium underline">
      18 -            Open the results filing →                          
      19 +          <a                                                   
      20 +            href={url}                                         
      21 +            target="_blank"                                    
      22 +            rel="noopener noreferrer"                          
      23 +            className="t-small mt-2 inline-flex h-9 items-cente
         +r gap-1 rounded-full border border-rule bg-surface px-3 font-me
         +dium"                                                          
      24 +          >                                                    
      25 +            Open the results filing <ArrowUpRight className="si
         +ze-3.5" />                                                     
      26            </a>
      27          )}
      28        </div>
     ...
      30    }
      31    return (
      32      <div>
      26 -      <div className="mb-2 flex items-center justify-between te
         -xt-xs text-muted-foreground">                                  
      33 +      <div className="t-small mb-1 flex items-center justify-be
         +tween gap-2 text-ink-3">                                       
      34          <span className="capitalize">
      35            {d.quarter.label} · {d.basis}
      36            {d.source_path !== "xbrl" && " · from PDF"}
      37          </span>
      38          <VerificationBadge state={d.verification} note={d.verif
          ication_note} />
     … 56 more lines (ctrl+o to expand)
  ⎿  Updated web/components/cards/Sparkline.tsx (+23 -9)
       1  // Tiny inline sparkline (SVG). Values are plotted as given; no
           maths beyond scaling to the box.
       2 -export function Sparkline({ values, width = 96, height = 24 }: 
         -{ values: number[]; width?: number; height?: number }) {       
       3 -  if (values.length < 2) return null;                          
       4 -  const lo = Math.min(...values);                              
       5 -  const hi = Math.max(...values);                              
       2 +export function Sparkline({                                    
       3 +  values,                                                      
       4 +  width = 96,                                                  
       5 +  height = 24,                                                 
       6 +  className = "",                                              
       7 +}: {                                                           
       8 +  values: (number | null)[];                                   
       9 +  width?: number;                                              
      10 +  height?: number;                                             
      11 +  className?: string;                                          
      12 +}) {                                                           
      13 +  const pts = values.map((v, i) => [i, v] as const).filter((p):
         + p is readonly [number, number] => p[1] !== null);             
      14 +  if (pts.length < 2) return null;                             
      15 +  const ys = pts.map((p) => p[1]);                             
      16 +  const lo = Math.min(...ys);                                  
      17 +  const hi = Math.max(...ys);                                  
      18    const span = hi - lo || 1;
       7 -  const pts = values                                           
       8 -    .map((v, i) => `${((i / (values.length - 1)) * width).toFix
         -ed(1)},${(height - ((v - lo) / span) * height).toFixed(1)}`)   
       9 -    .join(" ");                                                
      19 +  const n = values.length - 1 || 1;                            
      20 +  const xy = pts.map(([i, v]) => [(i / n) * (width - 2) + 1, he
         +ight - 1 - ((v - lo) / span) * (height - 2)] as const);        
      21 +  const d = xy.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(
         +1)},${y.toFixed(1)}`).join(" ");                               
      22 +  const [lx, ly] = xy[xy.length - 1];                          
      23    return (
      11 -    <svg width={width} height={height} viewBox={`0 0 ${width} $
         -{height}`} aria-hidden className="shrink-0">                   
      12 -      <polyline points={pts} fill="none" stroke="currentColor" 
         -strokeWidth={1.5} />                                           
      24 +    <svg width={width} height={height} viewBox={`0 0 ${width} $
         +{height}`} aria-hidden className={`shrink-0 overflow-visible ${
         +className}`}>                                                  
      25 +      <path d={d} fill="none" stroke="currentColor" strokeWidth
         +={1.25} strokeLinejoin="round" strokeLinecap="round" />        
      26 +      <circle cx={lx} cy={ly} r={1.75} fill="currentColor" />  
      27      </svg>
      28    );
      29  }
  ⎿  … 1 more file changed

⏺ Bash(sed -i '' 's/text-\[11px\] text-amber-700 underline-offset-2
      hover:underline dark:text-amber-300/text-[12px] text-warn
      underline-offset-2 hover:underline/; s/cl…)
  ⎿  Updated web/components/cards/CardShell.tsx (+143 -34)
        1 -// The frame every card shares: ticker · category · impact, he
          -adline, so-what, body, sources, timeline, freshness.          
        2 -// No data fetching and no gestures: the Brief wraps this with
          - swipe/undo.                                                  
        1 +"use client";                                                 
        2 +// The frame every card shares. Collapsed: eyebrow · serif hea
          +dline · so-what · key figures · source/verification.          
        3 +// Expanded (tap): the full body, event thread, next action, A
          +sk chips, and Reviewed / Not useful buttons.                  
        4 +// No data fetching and no gestures here: the Brief wraps this
          + with swipe/undo.                                             
        5  import type { ReactNode } from "react";
        4 -import type { Card } from "@/lib/types";                      
        5 -import { CATEGORY_LABEL, ist } from "@/lib/format";           
        6 -import { ImpactTag, SourceChip, Timeline } from "./primitives"
          -;                                                             
        6 +import { ChevronRight, Eye } from "lucide-react";             
        7 +import type { Card, Figure } from "@/lib/types";              
        8 +import { CATEGORY_LABEL, displayHeadline, istWhen } from "@/li
          +b/format";                                                    
        9 +import { ImpactLabel } from "@/components/ui/signal";         
       10 +import { FigureValue } from "./FigureValue";                  
       11 +import { SourceChip, Timeline, VerificationBadge } from "./pri
          +mitives";                                                     
       12 +import { ClaimText } from "./ClaimLink";                      
       13  
        8 -export function CardShell({ card, children, showTimeline = tru
          -e }: { card: Card; children?: ReactNode; showTimeline?: boolea
          -n }) {                                                        
       14 +function cardTime(card: Card): string | null {                
       15 +  const t = card.timeline;                                    
       16 +  if (!t.length) return null;                                 
       17 +  const outcome = t.filter((x) => x.stage === "outcome").map((
          +x) => x.at).sort()[0];                                        
       18 +  const latest = [...t].map((x) => x.at).sort().at(-1)!;      
       19 +  return outcome ?? latest;                                   
       20 +}                                                             
       21 +                                                              
       22 +function line(card: Card, metric: string) {                   
       23 +  const d = card.detail;                                      
       24 +  return d?.kind === "results" ? d.lines.find((l) => l.metric 
          +=== metric) : undefined;                                      
       25 +}                                                             
       26 +                                                              
       27 +function KeyFigures({ card }: { card: Card }) {               
       28 +  const d = card.detail;                                      
       29 +  const items: { label: string; f: Figure; delta?: Figure | nu
          +ll }[] = [];                                                  
       30 +  if (d?.kind === "results") {                                
       31 +    if (d.verification === "mismatch") return null;           
       32 +    const top = line(card, "PAT") ?? d.lines[0];              
       33 +    const second = line(card, "EBITDA margin") ?? line(card, "
          +NII") ?? line(card, "Revenue");                               
       34 +    if (top) items.push({ label: top.metric, f: top.current, d
          +elta: top.yoy });                                             
     … 145 more lines (ctrl+o to expand)
  ⎿  Updated web/components/cards/CardView.tsx (+25 -10)
      1  // Switches on card_type and renders the right body inside the s
         hared shell. Reused by /e/[id] and the Brief.
      2 +import type { ComponentProps } from "react";                    
      3  import type { Card } from "@/lib/types";
      4  import { CardShell } from "./CardShell";
      5  import { InlineChip } from "./InlineChip";
     ...
       7  import { OneLinerBody } from "./OneLinerCard";
       8  import { PriceVolumeBody } from "./PriceVolumeAlertCard";
       9  import { ResultsBody } from "./ResultsCard";
      10 +import { WhatToWatchBody } from "./WhatToWatchCard";           
      11  
      10 -export function CardView({ card }: { card: Card }) {           
      12 +export function CardBody({ card }: { card: Card }) {           
      13 +  const d = card.detail;                                       
      14 +  if (d?.kind === "results") return <ResultsBody card={card} d=
         +{d} />;                                                        
      15 +  if (d?.kind === "management_change") return <ManagementBody d
         +={d} />;                                                       
      16 +  if (d?.kind === "price_volume") return <PriceVolumeBody d={d}
         + />;                                                           
      17 +  if (d?.kind === "one_liner") return <OneLinerBody d={d} categ
         +ory={card.category} />;                                        
      18 +  if (card.card_type === "what_to_watch") return <WhatToWatchBo
         +dy card={card} />;                                             
      19 +  if (card.card_type === "results")                            
      20 +    return <p className="t-small text-ink-2">Numbers are being 
         +extracted and cross-checked — open the filing meanwhile.</p>;  
      21 +  return null;                                                 
      22 +}                                                              
      23 +                                                               
      24 +export function CardView({ card, ...shell }: { card: Card } & O
         +mit<ComponentProps<typeof CardShell>, "card" | "children">) {  
      25    const d = card.detail;
      26    if (card.card_type === "inline_chip" && d?.kind === "chip") {
      13 -    return <InlineChip symbol={card.symbol} d={d} />;          
      27 +    return (                                                   
      28 +      <div className="bg-surface px-4 py-3">                   
      29 +        <InlineChip symbol={card.symbol} d={d} />              
      30 +      </div>                                                   
      31 +    );                                                         
      32    }
      15 -  let body = null;                                             
      16 -  if (d?.kind === "results") body = <ResultsBody card={card} d=
         -{d} />;                                                        
      17 -  else if (d?.kind === "management_change") body = <ManagementB
         -ody d={d} />;                                                  
      18 -  else if (d?.kind === "price_volume") body = <PriceVolumeBody 
         -d={d} />;                                                      
      19 -  else if (d?.kind === "one_liner") body = <OneLinerBody d={d} 
         -category={card.category} />;                                   
      20 -  else if (card.card_type === "results")                       
      21 -    body = <p className="text-xs text-muted-foreground">Numbers
         - are being extracted and cross-checked — open the filing meanwh
         -ile.</p>;                                                      
     … 7 more lines (ctrl+o to expand)
  ⎿  Updated web/components/cards/ManagementChangeCard.tsx (+9 -9)
      11        target="_blank"
      12        rel="noopener noreferrer"
      13        title={c.quote ? `“${c.quote}”` : undefined}
      14 -      className="ml-1 whitespace-nowrap text-[11px] text-amber-
         -700 underline-offset-2 hover:underline dark:text-amber-300"    
      14 +      className="ml-1 whitespace-nowrap text-[12px] text-warn u
         +nderline-offset-2 hover:underline"                             
      15      >
      16        web · unverified{kind ? ` · ${kind}` : ""} ↗
      17      </a>
     ...
      24  }
      25  
      26  export function ManagementBody({ d }: { d: ManagementDetail }) 
          {
      27 -  if (d.people.length === 0) return <p className="text-xs text-
         -muted-foreground">No profile found in the filing.</p>;         
      27 +  if (d.people.length === 0) return <p className="text-xs text-
         +ink-2">No profile found in the filing.</p>;                    
      28    return (
      29 -    <div className="space-y-4">                                
      29 +    <div className="space-y-4 t-small">                        
      30        {d.people.map((p) => (
      31 -        <section key={p.name} className="text-sm">             
      32 -          <p className="font-medium">                          
      33 -            {p.name} <span className="font-normal text-muted-fo
         -reground">— {p.role}, {p.change.replace("_", "-")}</span>      
      31 +        <section key={p.name} className="t-small">             
      32 +          <p className="text-[15px] font-medium">              
      33 +            {p.name} <span className="font-normal text-ink-2">—
         + {p.role}, {p.change.replace("_", "-")}</span>                 
      34            </p>
      35            {p.insider !== null && (
      36              <p className="text-xs">
      37                {p.insider ? "Insider" : "Outside hire"}
      38 -              {p.insider_reason && <span className="text-muted-
         -foreground"> · {p.insider_reason}</span>}                      
      38 +              {p.insider_reason && <span className="text-ink-2"
         +> · {p.insider_reason}</span>}                                 
      39              </p>
      40            )}
      41            {p.tenure_years && (
     ...
      64              </ul>
      65            )}
      66            {p.qualifications.length > 0 && (
      67 -            <ul className="mt-1 space-y-0.5 text-xs text-muted-
         -foreground">                                                   
      67 +            <ul className="mt-1 space-y-0.5 text-xs text-ink-2"
         +>                                                              
      68                {p.qualifications.map((q, i) => (
      69                  <li key={i}>
      70                    {q.text}
     … 8 more lines (ctrl+o to expand)
  ⎿  Created web/components/cards/WhatToWatchCard.tsx (+19 -0)
       1 +// "What to watch": a results board meeting is announced — the 
         +promises the results will test live in the dossier.            
       2 +import Link from "next/link";                                  
       3 +import { ChevronRight } from "lucide-react";                   
       4 +import type { Card } from "@/lib/types";                       
       5 +                                                               
       6 +export function WhatToWatchBody({ card }: { card: Card }) {    
       7 +  return (                                                     
       8 +    <div className="t-small space-y-2 text-ink-2">             
       9 +      <p>The board meeting is announced; results aren&apos;t ou
         +t yet. FINN scores them against management&apos;s own guidance 
         +once they land.</p>                                            
      10 +      <Link                                                    
      11 +        href={`/research/${encodeURIComponent(card.symbol)}#led
         +ger`}                                                          
      12 +        onClick={(e) => e.stopPropagation()}                   
      13 +        className="inline-flex h-9 items-center gap-1 font-medi
         +um text-ink"                                                   
      14 +      >                                                        
      15 +        Promises these results will test <ChevronRight classNam
         +e="size-4" />                                                  
      16 +      </Link>                                                  
      17 +    </div>                                                     
      18 +  );                                                           
      19 +}                                                              
  ⎿  Updated web/components/cards/index.ts (+4 -2)
      1 -export { CardView } from "./CardView";                          
      1 +export { CardView, CardBody } from "./CardView";                
      2  export { CardShell } from "./CardShell";
      3  export { ResultsBody } from "./ResultsCard";
      4  export { ManagementBody } from "./ManagementChangeCard";
     ...
       6  export { OneLinerBody } from "./OneLinerCard";
       7  export { InlineChip } from "./InlineChip";
       8  export { FigureValue } from "./FigureValue";
       9 -export { ImpactTag, SourceChip, Timeline, VerificationBadge } f
         -rom "./primitives";                                            
       9 +export { ClaimText } from "./ClaimLink";                       
      10 +export { CitationBlock, FigureProvenance, ClaimProvenance } fro
         +m "./Provenance";                                              
      11 +export { ImpactTag, SourceChip, Timeline, VerificationBadge, VE
         +RIFICATION } from "./primitives";                              

⏺ Card components typecheck. Now the Brief screen itself: data orchestration,
  header, window chips, season strip, swipe rows, sheets and states.

  Searched for 1 pattern, called ccd_turn (ctrl+o to expand)

⏺ Bash(mkdir -p ~/Documents/finn/web/components/brief && cd
      ~/Documents/finn/web/components/brief && cat > useBrief.ts
      <<'EOF'
      "use cli…)
  ⎿  Created web/components/brief/useBrief.ts (+171 -0)
        1 +"use client";                                                 
        2 +// Brief data, fastest source first (DECISIONS: Phase 4 first 
          +paint):                                                       
        3 +//   1. this phone's last Brief for the same holdings + rules 
          ++ window (localStorage) — instant;                            
        4 +//   2. first visit on the demo portfolio: the edge-cached dem
          +o Brief (Vercel serves it while Render wakes);                
        5 +//   3. nothing within 1.5 s: the saved showcase day, clearly 
          +labelled, with a "Live Brief ready" pill later;               
        6 +//   4. always: POST /api/brief with holdings + rules + queued
          + swipes; keep the last good copy on failure.                  
        7 +import { useCallback, useEffect, useMemo, useRef, useState } f
          +rom "react";                                                  
        8 +import { api, FetchError } from "@/lib/client";               
        9 +import {                                                      
       10 +  FALLBACK,                                                   
       11 +  holdingsSignature,                                          
       12 +  isDemoPortfolio,                                            
       13 +  read,                                                       
       14 +  settleFeedback,                                             
       15 +  useStored,                                                  
       16 +  write,                                                      
       17 +  type CachedBrief,                                           
       18 +  type LocalHolding,                                          
       19 +  type Visit,                                                 
       20 +  type WindowKey,                                             
       21 +} from "@/lib/store";                                         
       22 +import type { BriefRequest, BriefResponse, FeedbackAction, Wei
          +ghtRule } from "@/lib/types";                                 
       23 +                                                              
       24 +export type Source = "cache" | "edge" | "fallback" | "live" | 
          +"showcase";                                                   
       25 +                                                              
       26 +export type BriefState = {                                    
       27 +  data: BriefResponse | null;                                 
       28 +  source: Source | null;                                      
       29 +  refreshing: boolean;                                        
       30 +  slow: boolean;                                              
       31 +  error: FetchError | null;                                   
       32 +  liveReady: boolean;                                         
       33 +  fetchedAt: string | null;                                   
       34 +};                                                            
       35 +                                                              
       36 +export function useBrief(opts: {                              
       37 +  window: WindowKey;                                          
       38 +  customSince: string | null;                                 
       39 +  visit: Visit | null;                                        
       40 +  showcase: boolean;                                          
     … 131 more lines (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='useBrief.ts'…)
  ⎿  done
  ⎿  Updated web/components/brief/useBrief.ts (+0 -5)
      93        fetchedAt: usable?.at ?? s.fetchedAt,
      94      }));
      95  
      96 -    const haveData = () => !!usable || state.data !== null;    
      96      if (!usable && isDemoPortfolio(holdings) && rules.length ==
          = 0 && pending.length === 0 && reqWindow !== "since") {
      97        const w = reqWindow === "all" ? "7d" : reqWindow;
      98        api
     ...
      162        setState((s) => ({ ...s, data: liveRef.current, source: 
           "live", liveReady: false, fetchedAt: new Date().toISOString() 
           }));
      163    }, []);
      164    const refresh = useCallback(() => setNonce((n) => n + 1), []
           );
      166 -  void haveDataPlaceholder;                                   
      165    return { ...state, since, reqWindow, refresh, showLive };
      166  }
      169 -                                                              
      170 -// (kept for lint: no-op reference)                           
      171 -const haveDataPlaceholder = null;                             

⏺ Bash(cat > SwipeRow.tsx <<'EOF'
      "use client";…)
  ⎿  ok
  ⎿  Created web/components/brief/SwipeRow.tsx (+88 -0)
       1 +"use client";                                                  
       2 +// Swipe right = Reviewed, left = Not useful. Commits only past
         + 40% of the row; shorter drags spring back.                    
       3 +// A haptic tick marks the threshold (navigator.vibrate: Androi
         +d; iOS has no web haptics). Vertical scroll wins               
       4 +// ties (direction lock + touch-action: pan-y). The reveal is n
         +eutral; past the threshold its label inverts.                  
       5 +import { useRef, useState, type ReactNode } from "react";      
       6 +import { animate, m, useMotionValue, useMotionValueEvent, useRe
         +ducedMotion } from "framer-motion";                            
       7 +import { Check, ThumbsDown } from "lucide-react";              
       8 +                                                               
       9 +export type SwipeDir = "right" | "left";                       
      10 +const THRESHOLD = 0.4;                                         
      11 +                                                               
      12 +export function SwipeRow({                                     
      13 +  children,                                                    
      14 +  onCommit,                                                    
      15 +  draggedRef,                                                  
      16 +}: {                                                           
      17 +  children: ReactNode;                                         
      18 +  onCommit: (dir: SwipeDir) => void;                           
      19 +  draggedRef: React.MutableRefObject<boolean>;                 
      20 +}) {                                                           
      21 +  const ref = useRef<HTMLDivElement>(null);                    
      22 +  const x = useMotionValue(0);                                 
      23 +  const reduce = useReducedMotion();                           
      24 +  const [side, setSide] = useState<0 | 1 | -1>(0);             
      25 +  const [armed, setArmed] = useState<SwipeDir | null>(null);   
      26 +  const armedRef = useRef<SwipeDir | null>(null);              
      27 +                                                               
      28 +  useMotionValueEvent(x, "change", (v) => {                    
      29 +    const s = v > 4 ? 1 : v < -4 ? -1 : 0;                     
      30 +    setSide((p) => (p === s ? p : s));                         
      31 +    const w = ref.current?.offsetWidth ?? 375;                 
      32 +    const a: SwipeDir | null = v > w * THRESHOLD ? "right" : v 
         +< -w * THRESHOLD ? "left" : null;                              
      33 +    if (a !== armedRef.current) {                              
      34 +      armedRef.current = a;                                    
      35 +      setArmed(a);                                             
      36 +      if (a) {                                                 
      37 +        try {                                                  
      38 +          navigator.vibrate?.(10);                             
      39 +        } catch {}                                             
      40 +      }                                                        
     … 48 more lines (ctrl+o to expand)
  ⎿  Created web/components/brief/sheets.tsx (+268 -0)
        1 +"use client";                                                 
        2 +// Brief sheets: Why #N, Not-useful scope, est. time saved, hi
          +dden drawer, season scoreboard, custom window.                
        3 +import { useState } from "react";                             
        4 +import Link from "next/link";                                 
        5 +import { ArrowUpRight, ChevronDown, ChevronRight } from "lucid
          +e-react";                                                     
        6 +import { Sheet } from "@/components/shell/Sheet";             
        7 +import { FigureValue, VERIFICATION } from "@/components/cards"
          +;                                                             
        8 +import { CATEGORY_LABEL, CATEGORY_PLURAL, istDay, istWhen, rea
          +dTime } from "@/lib/format";                                  
        9 +import type { BriefCounts, BriefResponse, Card, ScoreBreakdown
          +, SeasonStrip } from "@/lib/types";                           
       10 +                                                              
       11 +const FACTORS: { key: keyof ScoreBreakdown; label: string; wha
          +t: string }[] = [                                             
       12 +  { key: "category_weight", label: "Category", what: "How much
          + this kind of filing usually matters, after your feedback" }, 
       13 +  { key: "position_weight", label: "Position", what: "Grows wi
          +th the holding's share of your portfolio" },                  
       14 +  { key: "relevance", label: "Relevance", what: "Impact on the
          + business; drivers you watch" },                              
       15 +  { key: "novelty", label: "Novelty", what: "New information b
          +eats repeat filings" },                                       
       16 +  { key: "surprise", label: "Surprise", what: "Deviation from 
          +the stock's own trend" },                                     
       17 +];                                                            
       18 +                                                              
       19 +export function WhySheet({ card, rank, onClose }: { card: Card
          + | null; rank: number; onClose: () => void }) {               
       20 +  const s = card?.score;                                      
       21 +  return (                                                    
       22 +    <Sheet open={!!card} onClose={onClose} eyebrow={`Why is th
          +is #${rank}?`} title={card ? `${card.symbol} · ${CATEGORY_LABE
          +L[card.category] ?? card.category}` : ""}>                    
       23 +      {s && (                                                 
       24 +        <div>                                                 
       25 +          <p className="t-small text-ink-2">Ranked by importan
          +ce, not time. Each factor is a plain multiplier, computed on t
          +he server.</p>                                                
       26 +          <ul className="mt-3 divide-y divide-rule border-y bo
          +rder-rule">                                                   
       27 +            {FACTORS.map((f) => (                             
       28 +              <li key={f.key} className="flex items-baseline g
          +ap-3 py-2.5">                                                 
       29 +                <div className="min-w-0 flex-1">              
       30 +                  <p className="text-[15px]">{f.label}</p>    
       31 +                  <p className="t-small text-ink-3">{f.what}</
          +p>                                                            
       32 +                </div>                                        
       33 +                <span className="t-figure">×{(s[f.key] as numb
          +er).toFixed(2)}</span>                                        
       34 +              </li>                                           
       35 +            ))}                                               
       36 +            <li className="flex items-baseline gap-3 py-2.5"> 
       37 +              <p className="min-w-0 flex-1 text-[15px] font-se
          +mibold">Score</p>                                             
       38 +              <span className="t-figure font-semibold">{s.tota
          +l.toFixed(2)}</span>                                          
       39 +            </li>                                             
       40 +          </ul>                                               
     … 228 more lines (ctrl+o to expand)

⏺ Bash(cat > BriefScreen.tsx <<'EOF'
      "use client";…)
  ⎿  components/brief/sheets.tsx(164,35): error TS18048: 'n' is possibly 'u
     ndefined'.
     components/brief/useBrief.ts(97,17): error TS2367: This comparison app
     … +2 lines (ctrl+o to expand)
  ⎿  Created web/components/brief/stale.ts (+21 -0)
       1 +// Is the filings feed behind? Checks run every 30 min, 08:30–2
         +2:00 IST on weekdays (DECISIONS: filing checks).               
       2 +// Stale = the last successful check is more than 2 h older tha
         +n the most recent slot that should have run.                   
       3 +export function lastExpectedCheck(now = new Date()): Date {    
       4 +  const ist = new Date(now.getTime() + 5.5 * 3600 * 1000); // s
         +hift so UTC getters read IST                                   
       5 +  for (let back = 0; back < 8; back++) {                       
       6 +    const d = new Date(Date.UTC(ist.getUTCFullYear(), ist.getUT
         +CMonth(), ist.getUTCDate() - back));                           
       7 +    const dow = d.getUTCDay();                                 
       8 +    if (dow === 0 || dow === 6) continue;                      
       9 +    const open = d.getTime() + 8.5 * 3600 * 1000;              
      10 +    const close = d.getTime() + 22 * 3600 * 1000;              
      11 +    const t = back === 0 ? Math.min(ist.getTime(), close) : clo
         +se;                                                            
      12 +    if (t < open) continue;                                    
      13 +    return new Date(t - 5.5 * 3600 * 1000);                    
      14 +  }                                                            
      15 +  return now;                                                  
      16 +}                                                              
      17 +                                                               
      18 +export function isStale(dataAsOf: string | null, now = new Date
         +()): boolean {                                                 
      19 +  if (!dataAsOf) return true;                                  
      20 +  return lastExpectedCheck(now).getTime() - Date.parse(dataAsOf
         +) > 2 * 3600 * 1000;                                           
      21 +}                                                              
  ⎿  … 1 more file changed

⏺ Bash(sed -i '' 's/      const w = reqWindow === "all" ? "7d" : reqWindow;/
       const w = reqWindow;/' components/brief/useBrief.ts && sed -i ''
      's/{items.length < n…)
  ⎿  96:    if (!usable && isDemoPortfolio(holdings) && rules.length === 0
     && pending.length === 0 && reqWindow !== "since") {
  ⎿  Updated web/components/brief/sheets.tsx (+1 -1)
      161                        </a>
      162                      </li>
      163                    ))}
      164 -                  {items.length < n && <li className="t-small 
          -px-2 py-1 text-ink-3">Showing the newest {items.length}.</li>}
      164 +                  {items.length < (n ?? 0) && <li className="t
          +-small px-2 py-1 text-ink-3">Showing the newest {items.length}
          +.</li>}                                                       
      165                  </ul>
      166                )}
      167              </li>
  ⎿  Updated web/components/brief/useBrief.ts (+1 -1)
       94      }));
       95  
       96      if (!usable && isDemoPortfolio(holdings) && rules.length =
           == 0 && pending.length === 0 && reqWindow !== "since") {
       97 -      const w = reqWindow === "all" ? "7d" : reqWindow;       
       97 +      const w = reqWindow;                                    
       98        api
       99          .demoBrief(w, ctrl.signal)
      100          .then((resp) => {

⏺ Brief screen typechecks. Wiring the routes (an app group with the shell,
  /brief, and moving /e/[id] and /connect into it), then I'll look at it in the
  browser.

⏺ Bash(mkdir -p "app/(app)/brief" && git mv app/e "app/(app)/e" && git mv
      app/connect "app/(app)/connect" && cat > "app/(app)/layout.tsx" <<'EOF'
      import { AppShell } f…)
  ⎿  app:
     (app)
     api
     … +13 lines (ctrl+o to expand)
  ⎿  Created web/app/(app)/brief/page.tsx (+8 -0)
      1 +import type { Metadata } from "next";                           
      2 +import { BriefScreen } from "@/components/brief/BriefScreen";   
      3 +                                                                
      4 +export const metadata: Metadata = { title: "Brief" };           
      5 +                                                                
      6 +export default function BriefPage() {                           
      7 +  return <BriefScreen />;                                       
      8 +}                                                               
  ⎿  Created web/app/(app)/connect/page.tsx (+159 -0)
        1 +"use client";                                                 
        2 +// Connect Telegram: uploads symbols + weights only (opt-in se
          +rver copy), then hands over a one-time t.me link.             
        3 +// The subscriber secret stays in this browser and is the only
          + way to change or delete the server copy here.                
        4 +import { useState, useSyncExternalStore } from "react";       
        5 +                                                              
        6 +const DEMO =                                                  
        7 +  "HAL 6\nEICHERMOT 6\nGRASIM 5\nTATAPOWER 5\nALKEM 5\nKALYANK
          +JIL 5\nCOCHINSHIP 5\nTITAGARH 4\nIDEA 3\n" +                  
        8 +  "RELIANCE 8\nHDFCBANK 8\nBAJFINANCE 6\nINFY 7\nITC 6\nDIVISL
          +AB 5\nTATASTEEL 5\nJUBLFOOD 5\nDIXON 6";                      
        9 +const SECRET_KEY = "finn.telegram.secret";                    
       10 +                                                              
       11 +type Link = { deep_link: string; expires_at: string; uploaded:
          + { symbol: string; weight_pct: number | null }[] };           
       12 +                                                              
       13 +function parse(text: string) {                                
       14 +  return text                                                 
       15 +    .split(/[\n,]+/)                                          
       16 +    .map((l) => l.trim())                                     
       17 +    .filter(Boolean)                                          
       18 +    .map((l) => {                                             
       19 +      const [sym, w] = l.split(/[\s:=]+/);                    
       20 +      const weight = w ? Number(w.replace("%", "")) : NaN;    
       21 +      return { symbol: sym.toUpperCase(), weight_pct: Number.i
          +sFinite(weight) && weight > 0 ? weight : null };              
       22 +    });                                                       
       23 +}                                                             
       24 +                                                              
       25 +function readSecret(): string | null {                        
       26 +  try {                                                       
       27 +    return localStorage.getItem(SECRET_KEY);                  
       28 +  } catch {                                                   
       29 +    return null;                                              
       30 +  }                                                           
       31 +}                                                             
       32 +                                                              
       33 +function subscribeStorage(cb: () => void) {                   
       34 +  window.addEventListener("storage", cb);                     
       35 +  return () => window.removeEventListener("storage", cb);     
       36 +}                                                             
       37 +                                                              
       38 +export default function Connect() {                           
       39 +  const [text, setText] = useState(DEMO);                     
       40 +  const [link, setLink] = useState<Link | null>(null);        
     … 119 more lines (ctrl+o to expand)
  ⎿  Created web/app/(app)/e/[id]/loading.tsx (+14 -0)
       1 +export default function Loading() {                            
       2 +  return (                                                     
       3 +    <main className="mx-auto flex w-full max-w-md flex-1 flex-c
         +ol gap-4 px-4 py-6">                                           
       4 +      <p className="text-lg font-semibold tracking-tight">FINN<
         +/p>                                                            
       5 +      <div className="animate-pulse rounded-2xl border p-4">   
       6 +        <div className="h-3 w-24 rounded bg-muted" />          
       7 +        <div className="mt-3 h-4 w-3/4 rounded bg-muted" />    
       8 +        <div className="mt-2 h-3 w-1/2 rounded bg-muted" />    
       9 +        <div className="mt-4 h-20 rounded bg-muted" />         
      10 +      </div>                                                   
      11 +      <p className="text-xs text-muted-foreground">Loading… (th
         +e free-tier API can take up to ~50 s to wake)</p>              
      12 +    </main>                                                    
      13 +  );                                                           
      14 +}                                                              
  ⎿  Created web/app/(app)/e/[id]/page.tsx (+54 -0)
       1 +// One card, opened directly (Telegram "Open in FINN"). Server-
         +rendered from the API; never a blank error.                    
       2 +import type { Metadata } from "next";                          
       3 +import Link from "next/link";                                  
       4 +import { CardView } from "@/components/cards";                 
       5 +import { apiFetch } from "@/lib/api";                          
       6 +import type { Card } from "@/lib/types";                       
       7 +                                                               
       8 +export const metadata: Metadata = { title: "FINN · card" };    
       9 +                                                               
      10 +async function load(id: string): Promise<{ card?: Card; error?:
         + string }> {                                                   
      11 +  try {                                                        
      12 +    const r = await apiFetch(`/events/${encodeURIComponent(id)}
         +/card`);                                                       
      13 +    if (r.status === 404) return { error: "This event isn't in 
         +FINN any more (it may have been re-threaded)." };              
      14 +    if (!r.ok) return { error: `The API answered ${r.status}.` 
         +};                                                             
      15 +    return { card: (await r.json()) as Card };                 
      16 +  } catch (e) {                                                
      17 +    const timedOut = e instanceof Error && e.name === "TimeoutE
         +rror";                                                         
      18 +    return { error: timedOut ? "The API is still waking up — re
         +fresh in a few seconds." : "The API is unreachable right now." 
         +};                                                             
      19 +  }                                                            
      20 +}                                                              
      21 +                                                               
      22 +export default async function EventPage(props: PageProps<"/e/[i
         +d]">) {                                                        
      23 +  const { id: raw } = await props.params;                      
      24 +  let id = raw;                                                
      25 +  try {                                                        
      26 +    id = decodeURIComponent(raw);                              
      27 +  } catch {                                                    
      28 +    // already decoded                                         
      29 +  }                                                            
      30 +  const { card, error } = await load(id);                      
      31 +  return (                                                     
      32 +    <main className="mx-auto flex w-full max-w-md flex-1 flex-c
         +ol gap-4 px-4 py-6">                                           
      33 +      <header className="flex items-center justify-between">   
      34 +        <Link href="/" className="text-lg font-semibold trackin
         +g-tight">                                                      
      35 +          FINN                                                 
      36 +        </Link>                                                
      37 +        <Link href="/connect" className="text-xs text-muted-for
         +eground underline-offset-4 hover:underline">                   
      38 +          Telegram alerts                                      
      39 +        </Link>                                                
      40 +      </header>                                                
     … 14 more lines (ctrl+o to expand)
  ⎿  Created web/app/(app)/layout.tsx (+5 -0)
      1 +import { AppShell } from "@/components/shell/AppShell";         
      2 +                                                                
      3 +export default function AppLayout({ children }: LayoutProps<"/">
        +) {                                                             
      4 +  return <AppShell>{children}</AppShell>;                       
      5 +}                                                               
  ⎿  … 9 more files changed

  Ran 2 shell commands (ctrl+o to expand)

⏺ Bash(git checkout -- web/app/api/hello/route.ts && ls web/app/api)
  ⎿  [...path]
     brief
     hello
  ⎿  Created web/app/api/hello/route.ts (+25 -0)
  ⎿  (a git step in this command can move the working tree, so these may be
     its changes, not edits) (ctrl+o to expand)

⏺ Bash(cd ~/Documents/finn/web && mkdir -p components/portfolio
      components/rules components/research && for pair in
      "portfolio/PortfolioScreen" "rules/…)
  ⎿  .next/dev/types/validator.ts(58,39): error TS2307: Cannot find module
     '../../../app/connect/page.js' or its corresponding type declarations.
     .next/dev/types/validator.ts(66,69): error TS2344: Type '__InvalidPara
     … +13 lines (ctrl+o to expand)
  ⎿  Created web/components/portfolio/PortfolioScreen.tsx (+4 -0)
      1 +"use client";                                                   
      2 +export function PortfolioScreen() {                             
      3 +  return <div className="px-4 py-6 t-body text-ink-2">Loading…</
        +div>;                                                           
      4 +}                                                               
  ⎿  Created web/components/research/ResearchHome.tsx (+4 -0)
      1 +"use client";                                                   
      2 +export function ResearchHome() {                                
      3 +  return <div className="px-4 py-6 t-body text-ink-2">Loading…</
        +div>;                                                           
      4 +}                                                               
  ⎿  Created web/components/rules/RulesScreen.tsx (+4 -0)
      1 +"use client";                                                   
      2 +export function RulesScreen() {                                 
      3 +  return <div className="px-4 py-6 t-body text-ink-2">Loading…</
        +div>;                                                           
      4 +}                                                               

⏺ Starting the dev server against the deployed API to look at the Brief.

⏺ Bash(cd ~/Documents/finn && python3 - <<'EOF'
      import json…)
  ⎿        "runtimeArgs": [
             "-c",
     "cd web && API_BASE_URL=https://finn-api-4ejm.onrender.com npm run dev
     … +6 lines (ctrl+o to expand)
  ⎿  Updated .claude/launch.json (+17 -2)
       4      {
       5        "name": "api",
       6        "runtimeExecutable": "bash",
       7 -      "runtimeArgs": ["-c", "cd backend && ../.venv/bin/uvicorn
         - api.main:app --port 8000"],                                   
       7 +      "runtimeArgs": [                                         
       8 +        "-c",                                                  
       9 +        "cd backend && ../.venv/bin/uvicorn api.main:app --port
         + 8000"                                                         
      10 +      ],                                                       
      11        "port": 8000
      12      },
      13      {
      14        "name": "web",
      15        "runtimeExecutable": "bash",
      13 -      "runtimeArgs": ["-c", "cd web && API_BASE_URL=http://127.
         -0.0.1:8000 npm run dev -- --port 3000"],                       
      16 +      "runtimeArgs": [                                         
      17 +        "-c",                                                  
      18 +        "cd web && API_BASE_URL=http://127.0.0.1:8000 npm run d
         +ev -- --port 3000"                                             
      19 +      ],                                                       
      20        "port": 3000
      21 +    },                                                         
      22 +    {                                                          
      23 +      "name": "web-live-api",                                  
      24 +      "runtimeExecutable": "bash",                             
      25 +      "runtimeArgs": [                                         
      26 +        "-c",                                                  
      27 +        "cd web && API_BASE_URL=https://finn-api-4ejm.onrender.
         +com npm run dev -- --port 3001"                                
      28 +      ],                                                       
      29 +      "port": 3001                                             
      30      }
      31    ]
      32  }

  Called Claude_Browser 2 times (ctrl+o to expand)

⏺ The Brief renders with live data. Checking the dev-overlay issue and the
  console before going further.

  Called Claude_Browser 2 times, ran 2 shell commands (ctrl+o to expand)

⏺ Found the freshness bug: data_as_of uses the oldest check across all tracked
  symbols, including two test tickers, so the Brief wrongly flags filings as
  possibly stale. I'm scoping it to the requested holdings now. · summary

⏺ Bash(python3 - <<'EOF'
      p='finn/cards/brief.py'…)
  ⎿  finn/cards/brief.py:95:def data_as_of(conn, symbols: list[str] | None
     = None) -> datetime | None:
     finn/cards/brief.py:152:        rules=rules, data_as_of=data_as_of(con
     … +3 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/cards/brief.py (+13 -3)
       92      ]  # fmt: skip
       93  
       94  
       95 -def data_as_of(conn) -> datetime | None:                      
       95 +def data_as_of(conn, symbols: list[str] | None = None) -> date
          +time | None:                                                  
       96 +    """Freshness of the filings feed for these holdings: the o
          +ldest last-successful NSE check among them.                   
       97 +    Symbols FINN doesn't track yet have no row; if none do, th
          +e latest check of any symbol is used."""                      
       98 +    if symbols:                                               
       99 +        r = conn.execute(                                     
      100 +            "select min(last_success_at) as t from public.sour
          +ce_status "                                                   
      101 +            "where source = 'nse_announcements' and scope = an
          +y(%s)",                                                       
      102 +            (symbols,),                                       
      103 +        ).fetchone()                                          
      104 +        if r and r["t"]:                                      
      105 +            return r["t"]                                     
      106      r = conn.execute(
       97 -        "select min(last_success_at) as t from public.source_s
          -tatus where source = 'nse_announcements'"                     
      107 +        "select max(last_success_at) as t from public.source_s
          +tatus where source = 'nse_announcements'"                     
      108      ).fetchone()
      109      return r["t"] if r else None
      110  
     ...
      149          cards=cards, hidden=hidden, hidden_total=len(hidden_ro
           ws), hidden_items=hidden_items(hidden_rows),
      150          counts=brief_counts(cards, len(hidden_rows), since),
      151          season=season_strip(conn, symbols, now_utc()),
      142 -        rules=rules, data_as_of=data_as_of(conn), since=since,
          - window=window,                                               
      152 +        rules=rules, data_as_of=data_as_of(conn, symbols), sin
          +ce=since, window=window,                                      
      153      )  # fmt: skip
      154  
      155  

⏺ Tests still pass. Now testing the Brief interactions in the browser: expand,
  swipe past and short of 40 %, undo, and the sheets.  ⎿  Error: [navigate] navigated to http://localhost:3001/brief


     Tab Context:
     - Executed on tabId: seed
     - Available tabs:
       • tabId seed: "Brief · FINN" ("http://localhost:3001/brief")
     - Viewport: emulating 375x812 (you set this; reset it with preset "desktop"
     when you finish testing; the app also clears it when your turn ends or the
     pane's width changes)
     [computer:wait] waited 3s

     … +8 lines (ctrl+o to expand)

  Called Claude_Browser 3 times (ctrl+o to expand)

⏺ The synthetic drag didn't commit, probably because the tool sends only a start
  and an end point. Simulating a stepped pointer drag in the page to test the
  gesture itself.

  Called Claude_Browser (ctrl+o to expand)

⏺ The drag never started: framer-motion's domAnimation bundle excludes drag,
  which needs domMax. Switching.

⏺ Bash(cd ~/Documents/finn/web && sed -i '' 's/import {
      LazyMotion, domAnimation } from "framer-motion";/import { LazyMotion,
      domMax } from "framer-mot…)
  ⎿  5:import { LazyMotion, domMax } from "framer-motion";
     12:    <LazyMotion features={domMax} strict>
  ⎿  Updated web/components/shell/AppShell.tsx (+2 -2)
       2  // Phone-width column + bottom dock (Ask bar above the tab bar,
           thumb zone) + undo toast.
       3  // On desktop every app route renders in a centred 430 px colum
          n; only "/" shows the QR landing.
       4  import type { ReactNode } from "react";
       5 -import { LazyMotion, domAnimation } from "framer-motion";      
       5 +import { LazyMotion, domMax } from "framer-motion";            
       6  import { AskBar } from "./AskBar";
       7  import { TabBar } from "./TabBar";
       8  import { ToastHost } from "./Toast";
       9  
      10  export function AppShell({ children }: { children: ReactNode })
           {
      11    return (
      12 -    <LazyMotion features={domAnimation} strict>                
      12 +    <LazyMotion features={domMax} strict>                      
      13        <div className="mx-auto flex min-h-dvh w-full max-w-[430p
          x] flex-col bg-paper pb-[calc(112px+env(safe-area-inset-bottom)
          )] min-[431px]:border-x min-[431px]:border-rule">
      14          {children}
      15        </div>

  Called Claude_Browser 3 times (ctrl+o to expand)

⏺ The browser pane is hidden, so requestAnimationFrame is throttled and
  framer-motion lags behind synthetic events. Retrying with slower steps.

  Called Claude_Browser (ctrl+o to expand)

⏺ Gesture tracking works, but the commit never fires in a hidden pane because
  the fly-out animation doesn't finish there. I'm switching to a timer alongside
  the animation, then I'll test the commit and undo flow. · summary

⏺ Bash(python3 - <<'EOF'
      p='components/brief/SwipeRow.tsx'…)
  ⎿  ok
  ⎿  Updated web/components/brief/SwipeRow.tsx (+3 -3)
      72            const dir = armedRef.current;
      73            setTimeout(() => (draggedRef.current = false), 50);
      74            if (dir) {
      75 -            animate(x, dir === "right" ? w * 1.05 : -w * 1.05, 
         -{ duration: reduce ? 0 : 0.16, ease: "easeIn" }).then(() =>    
      76 -              onCommit(dir),                                   
      77 -            );                                                 
      75 +            // Commit on a timer, not on the animation's end: a
         + throttled tab must never lose a swipe.                        
      76 +            animate(x, dir === "right" ? w * 1.05 : -w * 1.05, 
         +{ duration: reduce ? 0 : 0.16, ease: "easeIn" });              
      77 +            setTimeout(() => onCommit(dir), reduce ? 0 : 140); 
      78            } else {
      79              animate(x, 0, reduce ? { duration: 0 } : { type: "s
          pring", stiffness: 520, damping: 38 });
      80            }

  Called Claude_Browser 2 times (ctrl+o to expand)

⏺ The review, toast and undo flow works; the DOM check only looked broken
  because the exit animation stalls in the hidden pane. I'm testing the Not
  useful path next. · summary

  Called Claude_Browser (ctrl+o to expand)

⏺ The whole Not-useful loop works: the swipe queued after the 5 s undo window,
  the server applied it and returned a ×0.8 rule, and the queue cleared. Quick
  check of the sheets.

  Called Claude_Browser (ctrl+o to expand)

⏺ Brief interactions and sheets now work end to end, with a reported holding
  showing a clear note instead of "n/m" and every tab populated before the first
  push. Next I'm writing the Portfolio and Rules tabs. · summary

⏺ Bash(python3 - <<'EOF'
      p='components/brief/sheets.tsx'…)
  ⎿  9:import { effectiveWeights } from "@/lib/holdings";
     130:      holdings: effectiveWeights(holdings).map((h) => ({ symbol: h
     .symbol, weight_pct: h.weight_pct })) as BriefRequest["holdings"],
  ⎿  Updated web/components/brief/sheets.tsx (+5 -1)
      210                        )}
      211                      </span>
      212                    </td>
      213 -                  {r.status === "reported" && r.verification !
          -== "mismatch" ? (                                             
      213 +                  {r.status === "reported" && !r.verification 
          +? (                                                           
      214 +                    <td colSpan={3} className="py-2 text-right
          + text-ink-3">                                                 
      215 +                      Numbers being checked                   
      216 +                    </td>                                     
      217 +                  ) : r.status === "reported" && r.verificatio
          +n !== "mismatch" ? (                                          
      218                      <>
      219                        <td className="py-2 text-right">{r.reven
           ue_yoy ? <FigureValue f={r.revenue_yoy} signed /> : <span clas
           sName="text-ink-3">n/m</span>}</td>
      220                        <td className="py-2 text-right">{r.pat_y
           oy ? <FigureValue f={r.pat_yoy} signed /> : <span className="t
           ext-ink-3">n/m</span>}</td>
  ⎿  Updated web/components/brief/useBrief.ts (+3 -1)
       6  //   4. always: POST /api/brief with holdings + rules + queued 
          swipes; keep the last good copy on failure.
       7  import { useCallback, useEffect, useMemo, useRef, useState } fr
          om "react";
       8  import { api, FetchError } from "@/lib/client";
       9 +import { effectiveWeights } from "@/lib/holdings";             
      10  import {
      11    FALLBACK,
      12    holdingsSignature,
     ...
      126  
      127      const sent = pending;
      128      const req: BriefRequest = {
      128 -      holdings: holdings.map((h) => ({ symbol: h.symbol, weigh
          -t_pct: h.weight_pct })) as BriefRequest["holdings"],          
      129 +      // Symbols + weights only: quantities never leave the ph
          +one.                                                          
      130 +      holdings: effectiveWeights(holdings).map((h) => ({ symbo
          +l: h.symbol, weight_pct: h.weight_pct })) as BriefRequest["hol
          +dings"],                                                      
      131        window: reqWindow,
      132        since: reqWindow === "since" ? since : null,
      133        rules,
  ⎿  Created web/lib/holdings.ts (+47 -0)
       1 +// Paste/CSV import (PRODUCT §7): "SYMBOL 6%" is a weight, "SYM
         +BOL 120" a share quantity. Stored in the browser.              
       2 +// Until prices are wired (Friday's /portfolio), quantity-only 
         +holdings share the weight the others leave, equally.           
       3 +import type { LocalHolding } from "@/lib/store";               
       4 +                                                               
       5 +export type ParseResult = { holdings: LocalHolding[]; unknown: 
         +string[]; errors: string[] };                                  
       6 +                                                               
       7 +export function parseHoldings(text: string, known: Set<string> 
         +| null): ParseResult {                                         
       8 +  const out = new Map<string, LocalHolding>();                 
       9 +  const unknown: string[] = [];                                
      10 +  const errors: string[] = [];                                 
      11 +  const now = new Date().toISOString();                        
      12 +  for (const raw of text.split(/\r?\n|;/)) {                   
      13 +    const line = raw.trim();                                   
      14 +    if (!line || /^symbol\b/i.test(line)) continue; // blank or
         + CSV header                                                    
      15 +    const parts = line.split(/[\s,:=\t]+/).filter(Boolean);    
      16 +    const sym = parts[0]?.toUpperCase().replace(/^NSE:/, "");  
      17 +    if (!sym || !/^[A-Z0-9&_-]{1,20}$/.test(sym)) {            
      18 +      errors.push(line);                                       
      19 +      continue;                                                
      20 +    }                                                          
      21 +    if (known && !known.has(sym)) unknown.push(sym);           
      22 +    const v = parts[1];                                        
      23 +    let weight: number | null = null;                          
      24 +    let qty: number | null = null;                             
      25 +    if (v) {                                                   
      26 +      const n = Number(v.replace(/[%,]/g, ""));                
      27 +      if (!Number.isFinite(n) || n <= 0) {                     
      28 +        errors.push(line);                                     
      29 +        continue;                                              
      30 +      }                                                        
      31 +      if (v.includes("%") || (parts[2] ?? "").startsWith("%")) 
         +weight = n;                                                    
      32 +      else qty = n;                                            
      33 +    }                                                          
      34 +    out.set(sym, { symbol: sym, weight_pct: weight, quantity: q
         +ty, added_at: now });                                          
      35 +  }                                                            
      36 +  return { holdings: [...out.values()], unknown, errors };     
      37 +}                                                              
      38 +                                                               
      39 +/** Weights to send with /brief. Given weights are kept; holdin
         +gs without one share what's left equally. */                   
      40 +export function effectiveWeights(h: LocalHolding[]): LocalHoldi
         +ng[] {                                                         
     … 7 more lines (ctrl+o to expand)

⏺ Bash(mkdir -p components/telegram && cat >
      components/telegram/TelegramConnect.tsx <<'EOF'
      "use client";…)
  ⎿  ok
  ⎿  Updated web/app/(app)/connect/page.tsx (+11 -154)
        1 -"use client";                                                 
        2 -// Connect Telegram: uploads symbols + weights only (opt-in se
          -rver copy), then hands over a one-time t.me link.             
        3 -// The subscriber secret stays in this browser and is the only
          - way to change or delete the server copy here.                
        4 -import { useState, useSyncExternalStore } from "react";       
        1 +import type { Metadata } from "next";                         
        2 +import { TelegramConnect } from "@/components/telegram/Telegra
          +mConnect";                                                    
        3  
        6 -const DEMO =                                                  
        7 -  "HAL 6\nEICHERMOT 6\nGRASIM 5\nTATAPOWER 5\nALKEM 5\nKALYANK
          -JIL 5\nCOCHINSHIP 5\nTITAGARH 4\nIDEA 3\n" +                  
        8 -  "RELIANCE 8\nHDFCBANK 8\nBAJFINANCE 6\nINFY 7\nITC 6\nDIVISL
          -AB 5\nTATASTEEL 5\nJUBLFOOD 5\nDIXON 6";                      
        9 -const SECRET_KEY = "finn.telegram.secret";                    
       10 -                                                              
       11 -type Link = { deep_link: string; expires_at: string; uploaded:
          - { symbol: string; weight_pct: number | null }[] };           
       12 -                                                              
       13 -function parse(text: string) {                                
       14 -  return text                                                 
       15 -    .split(/[\n,]+/)                                          
       16 -    .map((l) => l.trim())                                     
       17 -    .filter(Boolean)                                          
       18 -    .map((l) => {                                             
       19 -      const [sym, w] = l.split(/[\s:=]+/);                    
       20 -      const weight = w ? Number(w.replace("%", "")) : NaN;    
       21 -      return { symbol: sym.toUpperCase(), weight_pct: Number.i
          -sFinite(weight) && weight > 0 ? weight : null };              
       22 -    });                                                       
       23 -}                                                             
       24 -                                                              
       25 -function readSecret(): string | null {                        
       26 -  try {                                                       
       27 -    return localStorage.getItem(SECRET_KEY);                  
       28 -  } catch {                                                   
       29 -    return null;                                              
       30 -  }                                                           
       31 -}                                                             
       32 -                                                              
       33 -function subscribeStorage(cb: () => void) {                   
       34 -  window.addEventListener("storage", cb);                     
       35 -  return () => window.removeEventListener("storage", cb);     
       36 -}                                                             
       37 -                                                              
       38 -export default function Connect() {                           
     … 130 more lines (ctrl+o to expand)
  ⎿  Updated web/components/rules/RulesScreen.tsx (+113 -1)
        1  "use client";
        2 +// Rules: every feedback adjustment is visible with Reset (PRO
          +DUCT §5), Telegram connect, and the alert rules.              
        3 +import { useEffect } from "react";                            
        4 +import { TelegramConnect } from "@/components/telegram/Telegra
          +mConnect";                                                    
        5 +import { setAskContext } from "@/components/shell/ui-store";  
        6 +import { CATEGORY_LABEL, CATEGORY_PLURAL, istDay } from "@/lib
          +/format";                                                     
        7 +import { FALLBACK, resetRule, useStored } from "@/lib/store"; 
        8 +import type { FeedbackAction, WeightRule } from "@/lib/types";
        9 +                                                              
       10 +function describe(r: WeightRule): string {                    
       11 +  const cat = r.category ? (CATEGORY_PLURAL[r.category] ?? (CA
          +TEGORY_LABEL[r.category] ?? r.category).toLowerCase()) : "";  
       12 +  const verb = r.multiplier < 1 ? "Fewer" : "More";           
       13 +  switch (r.scope) {                                          
       14 +    case "stock":                                             
       15 +      return `${verb} filings from ${r.symbol}`;              
       16 +    case "category":                                          
       17 +      return `${verb} ${cat}, all stocks`;                    
       18 +    case "stock_category":                                    
       19 +      return `${verb} ${r.symbol} ${cat}`;                    
       20 +    case "event":                                             
       21 +      return `One card hidden (${r.event_id?.split(":").slice(
          +0, 2).join(" · ")})`;                                         
       22 +  }                                                           
       23 +}                                                             
       24 +                                                              
       25 +const ALERT_RULES: [string, string][] = [                     
       26 +  ["Price move", "±4% close to close, adjusted for dividends, 
          +bonuses and splits"],                                         
       27 +  ["Volume", "2× the 20-day average"],                        
       28 +  ["Volatility-aware", "On — a move must also be unusual for t
          +hat stock (z ≥ 2)"],                                          
       29 +  ["Sector-relative", "On — the stock's own part of the move"]
          +,                                                             
       30 +  ["Push categories", "Results, M&A, management change, litiga
          +tion, credit rating, pledging, price moves"],                 
       31 +  ["Budget", "5 messages a day; the rest wait for your next Br
          +ief"],                                                        
       32 +  ["Quiet hours", "22:00–07:00 IST; only M&A, a CEO/MD exit or
          + a rating downgrade break through"],                          
       33 +  ["Snooze", "Per stock, 1 day or 1 week — from the alert's Sn
          +ooze button in Telegram"],                                    
       34 +];                                                            
       35 +                                                              
       36  export function RulesScreen() {
        3 -  return <div className="px-4 py-6 t-body text-ink-2">Loading…
          -</div>;                                                       
       37 +  const rules = useStored<WeightRule[]>("rules", FALLBACK.rule
          +s);                                                           
       38 +  const pending = useStored<FeedbackAction[]>("pending", FALLB
          +ACK.pending);                                                 
       39 +  useEffect(() => {                                           
     … 77 more lines (ctrl+o to expand)
  ⎿  Created web/components/telegram/TelegramConnect.tsx (+126 -0)
        1 +"use client";                                                 
        2 +// Connect Telegram: uploads symbols + weights only (opt-in se
          +rver copy), then hands over a one-time t.me link.             
        3 +// The subscriber secret stays in this browser and is the only
          + way to change or delete the server copy here.                
        4 +import { useState, useSyncExternalStore } from "react";       
        5 +import { ArrowUpRight, Send } from "lucide-react";            
        6 +import { effectiveWeights } from "@/lib/holdings";            
        7 +import { FALLBACK, useStored, type LocalHolding } from "@/lib/
          +store";                                                       
        8 +                                                              
        9 +const SECRET_KEY = "finn.telegram.secret";                    
       10 +type Link = { deep_link: string; expires_at: string; uploaded:
          + { symbol: string; weight_pct: number | null }[] };           
       11 +                                                              
       12 +function readSecret(): string | null {                        
       13 +  try {                                                       
       14 +    return localStorage.getItem(SECRET_KEY);                  
       15 +  } catch {                                                   
       16 +    return null;                                              
       17 +  }                                                           
       18 +}                                                             
       19 +function subscribeStorage(cb: () => void) {                   
       20 +  window.addEventListener("storage", cb);                     
       21 +  return () => window.removeEventListener("storage", cb);     
       22 +}                                                             
       23 +                                                              
       24 +export function TelegramConnect() {                           
       25 +  const holdings = useStored<LocalHolding[]>("holdings", FALLB
          +ACK.holdings);                                                
       26 +  const [link, setLink] = useState<Link | null>(null);        
       27 +  const [busy, setBusy] = useState(false);                    
       28 +  const [error, setError] = useState<string | null>(null);    
       29 +  const stored = useSyncExternalStore(subscribeStorage, () => 
          +Boolean(readSecret()), () => false);                          
       30 +  const [override, setConnected] = useState<boolean | null>(nu
          +ll);                                                          
       31 +  const connected = override ?? stored;                       
       32 +                                                              
       33 +  async function connect() {                                  
       34 +    setBusy(true);                                            
       35 +    setError(null);                                           
       36 +    try {                                                     
       37 +      const r = await fetch("/api/telegram/link", {           
       38 +        method: "POST",                                       
       39 +        headers: { "content-type": "application/json" },      
       40 +        body: JSON.stringify({                                
     … 86 more lines (ctrl+o to expand)

⏺ Bash(cat > components/portfolio/PortfolioScreen.tsx <<'EOF'
      "use client";…)
  ⎿    Type 'string' is not assignable to type 'never'.
       Type 'string' is not assignable to type 'never'.
  ⎿  Updated web/components/portfolio/PortfolioScreen.tsx (+201 -1)
        1  "use client";
        2 +// Portfolio: holdings with weight and their latest event from
          + the Brief; paste/CSV import (stored on the phone).           
        3 +// Prices, sparklines, the calendar and the scoreboard arrive 
          +with /portfolio (Friday); the season scoreboard is            
        4 +// already one tap away in the Brief.                         
        5 +import { useEffect, useMemo, useState } from "react";         
        6 +import Link from "next/link";                                 
        7 +import { ChevronRight } from "lucide-react";                  
        8 +import { useBrief } from "@/components/brief/useBrief";       
        9 +import { Sheet } from "@/components/shell/Sheet";             
       10 +import { Notice, Skeleton } from "@/components/shell/StateView
          +";                                                            
       11 +import { setAskContext } from "@/components/shell/ui-store";  
       12 +import { Dot, IMPACT } from "@/components/ui/signal";         
       13 +import { api } from "@/lib/client";                           
       14 +import { CATEGORY_LABEL, displayHeadline, istWhen } from "@/li
          +b/format";                                                    
       15 +import { effectiveWeights, parseHoldings } from "@/lib/holding
          +s";                                                           
       16 +import { FALLBACK, isDemoPortfolio, read, useStored, write, ty
          +pe LocalHolding } from "@/lib/store";                         
       17 +import type { Card } from "@/lib/types";                      
       18 +                                                              
       19 +function latestAt(c: Card): string {                          
       20 +  return [...c.timeline.map((t) => t.at)].sort().at(-1) ?? c.a
          +s_of;                                                         
       21 +}                                                             
       22 +                                                              
       23  export function PortfolioScreen() {
        3 -  return <div className="px-4 py-6 t-body text-ink-2">Loading…
          -</div>;                                                       
       24 +  const holdings = useStored<LocalHolding[]>("holdings", FALLB
          +ACK.holdings);                                                
       25 +  const [enabled, setEnabled] = useState(false);              
       26 +  useEffect(() => setEnabled(true), []);                      
       27 +  const b = useBrief({ window: "7d", customSince: null, visit:
          + null, showcase: false, enabled });                           
       28 +  const [editing, setEditing] = useState(false);              
       29 +  const demo = isDemoPortfolio(holdings);                     
       30 +  const weights = useMemo(() => effectiveWeights(holdings), [h
          +oldings]);                                                    
       31 +                                                              
       32 +  const latest = useMemo(() => {                              
       33 +    const m = new Map<string, Card>();                        
       34 +    for (const c of b.data?.cards ?? []) {                    
       35 +      if (c.card_type === "inline_chip") continue;            
       36 +      const cur = m.get(c.symbol);                            
       37 +      if (!cur || latestAt(c) > latestAt(cur)) m.set(c.symbol,
          + c);                                                          
       38 +    }                                                         
       39 +    return m;                                                 
     … 165 more lines (ctrl+o to expand)
  ⎿  Updated web/components/research/ResearchHome.tsx (+1 -1)
      1  "use client";
      2  export function ResearchHome() {
      3 -  return <div className="px-4 py-6 t-body text-ink-2">Loading…</
        -div>;                                                           
      3 +  return <div className="px-4 py-6 t-body text-ink-2">Research</
        +div>;                                                           
      4  }

⏺ Portfolio and Rules are in place. Since an empty Research tab can't ship, I'm
  building Research and the Promise Ledger before the first push rather than
  shipping a stub.

  Called ccd_turn (ctrl+o to expand)

⏺ Bash(cat > lib/symbols.ts <<'EOF'
      "use client";…)
  ⎿  ok
  ⎿  Updated web/components/research/ResearchHome.tsx (+160 -1)
        1  "use client";
        2 +import { useEffect, useMemo, useRef, useState } from "react"; 
        3 +import Link from "next/link";                                 
        4 +import { useRouter } from "next/navigation";                  
        5 +import { ChevronRight, Search, X } from "lucide-react";       
        6 +import { setAskContext } from "@/components/shell/ui-store";  
        7 +import { DEMO_TICKERS } from "@/lib/demo";                    
        8 +import { FALLBACK, useStored, write, type LocalHolding } from 
          +"@/lib/store";                                                
        9 +import { companyName, searchSymbols, useSymbols } from "@/lib/
          +symbols";                                                     
       10 +                                                              
       11  export function ResearchHome() {
        3 -  return <div className="px-4 py-6 t-body text-ink-2">Research
          -</div>;                                                       
       12 +  const list = useSymbols();                                  
       13 +  const router = useRouter();                                 
       14 +  const [q, setQ] = useState("");                             
       15 +  const [active, setActive] = useState(0);                    
       16 +  const recent = useStored<string[]>("recent", FALLBACK.recent
          +);                                                            
       17 +  const holdings = useStored<LocalHolding[]>("holdings", FALLB
          +ACK.holdings);                                                
       18 +  const input = useRef<HTMLInputElement>(null);               
       19 +  const hits = useMemo(() => (list ? searchSymbols(list, q) : 
          +[]), [list, q]);                                              
       20 +  const names = useMemo(() => new Map(list ?? []), [list]);   
       21 +                                                              
       22 +  const open = (sym: string) => {                             
       23 +    write("recent", [sym, ...recent.filter((s) => s !== sym)].
          +slice(0, 6));                                                 
       24 +    router.push(`/research/${encodeURIComponent(sym)}`);      
       25 +  };                                                          
       26 +                                                              
       27 +  useEffect(() => {                                           
       28 +    setAskContext({                                           
       29 +      placeholder: "Ask about any company…",                  
       30 +      chips: [                                                
       31 +        { label: "Did Bajaj Finance keep its promises?", run: 
          +() => open("BAJFINANCE") },                                   
       32 +        { label: "What do analysts keep asking Infosys?", run:
          + () => router.push("/research/INFY#analysts") },              
       33 +        { label: "Research a company I hold", run: () => input
          +.current?.focus() },                                          
       34 +      ],                                                      
       35 +    });                                                       
       36 +    return () => setAskContext(null);                         
       37 +    // eslint-disable-next-line react-hooks/exhaustive-deps   
       38 +  }, []);                                                     
       39 +                                                              
     … 124 more lines (ctrl+o to expand)
  ⎿  Created web/lib/symbols.ts (+58 -0)
       1 +"use client";                                                  
       2 +// NSE equity list for autocomplete: the committed static copy 
         +(instant, CDN), refreshed from the API once a day.             
       3 +import { useEffect, useState } from "react";                   
       4 +import { api } from "@/lib/client";                            
       5 +import { read, write } from "@/lib/store";                     
       6 +                                                               
       7 +type Cached = { at: string; list: [string, string][] };        
       8 +const DAY = 24 * 3600 * 1000;                                  
       9 +                                                               
      10 +export function useSymbols(): [string, string][] | null {      
      11 +  const [list, setList] = useState<[string, string][] | null>(n
         +ull);                                                          
      12 +  useEffect(() => {                                            
      13 +    let cancelled = false;                                     
      14 +    const cached = read<Cached | null>("symbols", null);       
      15 +    if (cached) setList(cached.list);                          
      16 +    const fresh = cached && Date.now() - Date.parse(cached.at) 
         +< DAY;                                                         
      17 +    if (!cached)                                               
      18 +      api                                                      
      19 +        .staticSymbols()                                       
      20 +        .then((r) => !cancelled && setList((cur) => cur ?? r.sy
         +mbols))                                                        
      21 +        .catch(() => {});                                      
      22 +    if (!fresh)                                                
      23 +      api                                                      
      24 +        .symbols()                                             
      25 +        .then((r) => {                                         
      26 +          if (cancelled || !r.symbols?.length) return;         
      27 +          write<Cached>("symbols", { at: new Date().toISOString
         +(), list: r.symbols });                                        
      28 +          setList(r.symbols);                                  
      29 +        })                                                     
      30 +        .catch(() => {});                                      
      31 +    return () => {                                             
      32 +      cancelled = true;                                        
      33 +    };                                                         
      34 +  }, []);                                                      
      35 +  return list;                                                 
      36 +}                                                              
      37 +                                                               
      38 +export function searchSymbols(list: [string, string][], q: stri
         +ng, limit = 8): [string, string][] {                           
      39 +  const Q = q.trim().toUpperCase();                            
      40 +  if (!Q) return [];                                           
     … 18 more lines (ctrl+o to expand)

⏺ Now the dossier page: data and polling hook, build confirmation and progress,
  sections that each render their own status, and the Promise Ledger.

⏺ Bash(cd ~/Documents/finn/web/components/research && cat >
      useDossier.ts <<'EOF'
      "use client";…)
  ⎿  ok
  ⎿  Created web/components/research/mockBuild.ts (+57 -0)
       1 +// Dev-only scripted build (?mock=build): exercises BuildProgre
         +ss without calling the API or spending quota.                  
       2 +import type { DossierJob, JobStep } from "@/lib/types";        
       3 +                                                               
       4 +const STEPS: [string, string][] = [                            
       5 +  ["discover", "Finding documents"],                           
       6 +  ["documents", "Reading documents"],                          
       7 +  ["extract", "Extracting guidance"],                          
       8 +  ["compute", "Computing figures"],                            
       9 +  ["ledger", "Scoring promises"],                              
      10 +  ["judge", "Judging qualitative promises"],                   
      11 +  ["reduce", "Writing the summary"],                           
      12 +  ["publish", "Publishing"],                                   
      13 +];                                                             
      14 +                                                               
      15 +export function mockJobSequence(symbol: string, emit: (j: Dossi
         +erJob) => void): () => void {                                  
      16 +  const now = () => new Date().toISOString();                  
      17 +  const resume = new Date(Date.now() + 3 * 3600 * 1000).toISOSt
         +ring();                                                        
      18 +  const frames: { status: DossierJob["status"]; upto: number; w
         +aiting?: boolean; msg: string; read: number; g: number; q?: num
         +ber }[] = [                                                    
      19 +    { status: "queued", upto: -1, msg: "Queued", read: 0, g: 0,
         + q: 1 },                                                       
      20 +    { status: "running", upto: 0, msg: "Found 8 transcripts, 1 
         +annual report, 3 decks", read: 0, g: 0 },                      
      21 +    { status: "running", upto: 1, msg: "Reading 2 of 8 transcri
         +pts", read: 2, g: 6 },                                         
      22 +    { status: "running", upto: 2, msg: "Reading 6 of 8 transcri
         +pts · 21 guidance statements found", read: 6, g: 21 },         
      23 +    { status: "running", upto: 4, msg: "Scoring promises agains
         +t delivered figures", read: 8, g: 29 },                        
      24 +    { status: "waiting_quota", upto: 4, waiting: true, msg: "Wa
         +iting for model quota", read: 8, g: 29 },                      
      25 +  ];                                                           
      26 +  let i = 0;                                                   
      27 +  const step = () => {                                         
      28 +    const f = frames[i];                                       
      29 +    const steps: JobStep[] = STEPS.map(([key, label], k) => ({ 
      30 +      key,                                                     
      31 +      label,                                                   
      32 +      detail: null,                                            
      33 +      status: k <= f.upto ? "done" : k === f.upto + 1 ? (f.wait
         +ing ? "waiting" : f.status === "running" ? "running" : "pending
         +") : "pending",                                                
      34 +    }));                                                       
      35 +    emit({                                                     
      36 +      id: 999,                                                 
      37 +      symbol,                                                  
      38 +      status: f.status,                                        
      39 +      stage: STEPS[Math.max(0, f.upto + 1)]?.[0] ?? null,      
      40 +      message: f.msg,                                          
     … 17 more lines (ctrl+o to expand)
  ⎿  Created web/components/research/useDossier.ts (+118 -0)
        1 +"use client";                                                 
        2 +// One dossier: GET it, poll an active build (every 3 s; every
          + 60 s while parked for model quota), refetch when a           
        3 +// section is published (dossier_version changes). If the API 
          +can't be reached, the 4 demo tickers fall back to             
        4 +// their saved fixtures (labelled). Never starts a build by it
          +self — the user confirms first.                               
        5 +import { useCallback, useEffect, useRef, useState } from "reac
          +t";                                                           
        6 +import { api, FetchError } from "@/lib/client";               
        7 +import { DEMO_TICKERS } from "@/lib/demo";                    
        8 +import type { DossierJob, DossierResponse } from "@/lib/types"
          +;                                                             
        9 +import { mockJobSequence } from "./mockBuild";                
       10 +                                                              
       11 +export type DossierState = {                                  
       12 +  resp: DossierResponse | null;                               
       13 +  status: "loading" | "ready" | "error" | "notfound";         
       14 +  error: FetchError | null;                                   
       15 +  source: "live" | "fixture" | "mock";                        
       16 +  slow: boolean;                                              
       17 +  building: boolean;                                          
       18 +  buildError: string | null;                                  
       19 +};                                                            
       20 +                                                              
       21 +const ACTIVE = new Set<DossierJob["status"]>(["queued", "runni
          +ng", "waiting_quota"]);                                       
       22 +export const isActive = (j: DossierJob | null | undefined) => 
          +!!j && ACTIVE.has(j.status);                                  
       23 +                                                              
       24 +export function useDossier(symbol: string, mock: boolean) {   
       25 +  const [s, setS] = useState<DossierState>({ resp: null, statu
          +s: "loading", error: null, source: "live", slow: false, buildi
          +ng: false, buildError: null });                               
       26 +  const version = useRef<number>(-1);                         
       27 +  const [tick, setTick] = useState(0);                        
       28 +                                                              
       29 +  const load = useCallback(async () => {                      
       30 +    const slow = setTimeout(() => setS((p) => ({ ...p, slow: t
          +rue })), 4000);                                               
       31 +    try {                                                     
       32 +      if (mock) {                                             
       33 +        const fx = await api.fixture((DEMO_TICKERS as readonly
          + string[]).includes(symbol) ? symbol : "INFY");               
       34 +        version.current = 0;                                  
       35 +        setS((p) => ({ ...p, resp: { ...fx, symbol, job: null 
          +}, status: "ready", source: "mock", slow: false }));          
       36 +        return;                                               
       37 +      }                                                       
       38 +      const resp = await api.dossier(symbol);                 
       39 +      version.current = resp.dossier_version;                 
       40 +      setS((p) => ({ ...p, resp, status: "ready", error: null,
          + source: "live", slow: false }));                             
     … 78 more lines (ctrl+o to expand)

⏺ Bash(cat > BuildProgress.tsx <<'EOF'
      "use client";…)
  ⎿  ok
  ⎿  Created web/components/research/BuildProgress.tsx (+66 -0)
       1 +"use client";                                                  
       2 +// Build progress for a dossier job: steps, live message, count
         +ers, queue position — and, when the strong models'             
       3 +// daily quota is used up, a plain explanation plus a pointer t
         +o the sections that are already readable.                      
       4 +import { Check, Clock, Loader2, X } from "lucide-react";       
       5 +import type { DossierJob } from "@/lib/types";                 
       6 +import { istDay, istTime, isTodayIST } from "@/lib/format";    
       7 +                                                               
       8 +const when = (iso: string) => `${isTodayIST(iso) ? "" : istDay(
         +iso) + " "}${istTime(iso)} IST`;                               
       9 +                                                               
      10 +export function BuildProgress({ job, readyCount }: { job: Dossi
         +erJob; readyCount: number }) {                                 
      11 +  const waiting = job.status === "waiting_quota" || job.steps.s
         +ome((s) => s.status === "waiting");                            
      12 +  const c = job.counters;                                      
      13 +  return (                                                     
      14 +    <section className="mx-4 mt-3 rounded-xl border border-rule
         + bg-surface p-4" aria-live="polite">                           
      15 +      <div className="flex items-start gap-3">                 
      16 +        <div className="min-w-0 flex-1">                       
      17 +          <p className="t-micro text-ink-3">                   
      18 +            {job.status === "queued" ? "Queued" : waiting ? "Pa
         +used for model quota" : "Building dossier"}                    
      19 +          </p>                                                 
      20 +          <p className="t-headline mt-1">                      
      21 +            {job.status === "queued"                           
      22 +              ? job.queue_position && job.queue_position > 1   
      23 +                ? `${job.queue_position - 1} ahead of you`     
      24 +                : "Starting in a moment"                       
      25 +              : job.message}                                   
      26 +          </p>                                                 
      27 +          {c.transcripts_total > 0 && (                        
      28 +            <p className="t-small mt-0.5 text-ink-2">          
      29 +              {c.transcripts_read} of {c.transcripts_total} tra
         +nscripts read · {c.guidance_found} guidance statements found   
      30 +            </p>                                               
      31 +          )}                                                   
      32 +        </div>                                                 
      33 +      </div>                                                   
      34 +      {waiting && (                                            
      35 +        <div className="t-small mt-3 rounded-lg bg-warn-bg p-3 
         +text-ink">                                                     
      36 +          <p className="font-medium text-warn">FINN&apos;s AI q
         +uota for today is used up.</p>                                 
      37 +          <p className="mt-1 text-ink-2">                      
      38 +            The steps that need the stronger model — judging qu
         +alitative promises and writing the summary — resume            
      39 +            {job.resume_after ? ` after ${when(job.resume_after
         +)}` : " after 13:30 IST"}, automatically. Numbers, the         
      40 +            numeric Promise Ledger and every other section {rea
         +dyCount > 0 ? `are ready below (${readyCount}).` : "appear belo
         +w as they finish."}                                            
     … 26 more lines (ctrl+o to expand)
  ⎿  Created web/components/research/sections.tsx (+325 -0)
        1 +"use client";                                                 
        2 +// Dossier sections. Each renders its own status (SectionMeta)
          +: ready / partial / building / unavailable.                   
        3 +// "Coming soon" sections (red flags, exchange data: building 
          ++ not_built_yet) show a quiet line, never an error.           
        4 +import type { ReactNode } from "react";                       
        5 +import { ArrowUpRight, Eye, EyeOff } from "lucide-react";     
        6 +import { ClaimText, FigureValue } from "@/components/cards";  
        7 +import { Sparkline } from "@/components/cards/Sparkline";     
        8 +import { figureText, istDay, istTime } from "@/lib/format";   
        9 +import { FALLBACK, read, useStored, write } from "@/lib/store"
          +;                                                             
       10 +import type { Dossier, Figure, SectionMeta, Series } from "@/l
          +ib/types";                                                    
       11 +                                                              
       12 +const REASON: Record<string, string> = {                      
       13 +  not_built_yet: "Coming soon.",                              
       14 +  no_screener_page: "screener.in has no page for this company,
          + so FINN can't build this section.",                          
       15 +  no_transcripts: "No earnings-call transcripts were found for
          + this company, so there's nothing to score.",                 
       16 +  few_transcripts: "Too few call transcripts to compare across
          + calls.",                                                     
       17 +  scanned_documents: "The documents are scanned images FINN ca
          +n't read yet.",                                               
       18 +  no_annual_report: "No annual report was found.",            
       19 +  not_meaningful_for_lenders: "Not meaningful for lenders.",  
       20 +  llm_unavailable: "The model was unavailable; FINN retries on
          + the next build.",                                            
       21 +  nse_pending: "Fetching exchange data… (about 1–2 minutes)", 
       22 +  nse_unavailable: "Available after tonight's refresh.",      
       23 +  not_found_in_sources: "Not found in sources.",              
       24 +  source_unreachable: "The source couldn't be reached; FINN re
          +tries tonight.",                                              
       25 +};                                                            
       26 +                                                              
       27 +export function metaLine(meta: SectionMeta): string | null {  
       28 +  if (meta.reason === "llm_quota")                            
       29 +    return `Waiting for the model quota — resumes ${meta.resum
          +e_after ? `after ${istTime(meta.resume_after)} IST` : "after 1
          +3:30 IST"}.`;                                                 
       30 +  if (meta.status === "building" && meta.reason === "not_built
          +_yet") return "Coming soon.";                                 
       31 +  return meta.note ?? (meta.reason ? (REASON[meta.reason] ?? n
          +ull) : null);                                                 
       32 +}                                                             
       33 +                                                              
       34 +export function SectionFrame({                                
       35 +  id,                                                         
       36 +  title,                                                      
       37 +  meta,                                                       
       38 +  children,                                                   
       39 +  aside,                                                      
       40 +}: {                                                          
     … 285 more lines (ctrl+o to expand)

⏺ Bash(mkdir -p ~/Documents/finn/web/components/ledger && cd
      ~/Documents/finn/web/components/ledger && cat > Ledger.tsx
      <<'EOF'
      "use cl…)
  ⎿  ok
  ⎿  Created web/components/ledger/Ledger.tsx (+298 -0)
        1 +"use client";                                                 
        2 +// ⭐ The Promise Ledger: what management said vs what they de
          +livered. Code decides numeric verdicts; the model             
        3 +// only judges qualitative promises and must cite both calls. 
          +Every verdict and number opens its provenance.                
        4 +import { useMemo, useState } from "react";                    
        5 +import { ChevronRight } from "lucide-react";                  
        6 +import { Sheet } from "@/components/shell/Sheet";             
        7 +import { FigureValue } from "@/components/cards";             
        8 +import { CitationBlock, ClaimProvenance, FigureProvenance } fr
          +om "@/components/cards/Provenance";                           
        9 +import { TONE_BG, TONE_TEXT, VERDICT, VerdictGlyph, type Verdi
          +ct } from "@/components/ui/signal";                           
       10 +import { SectionFrame } from "@/components/research/sections";
       11 +import { istDayYear } from "@/lib/format";                    
       12 +import type { Dossier, MgmtPromise } from "@/lib/types";      
       13 +                                                              
       14 +type Filter = "scored" | "due" | "not_yet_due" | "cant_score" 
          +| "all";                                                      
       15 +const SCORED: Verdict[] = ["missed", "goalposts_moved", "quiet
          +ly_dropped", "kept"];                                         
       16 +const ORDER: Record<Verdict, number> = { missed: 0, goalposts_
          +moved: 1, quietly_dropped: 2, kept: 3, not_yet_due: 4, cant_sc
          +ore: 5 };                                                     
       17 +                                                              
       18 +const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice
          +(1);                                                          
       19 +                                                              
       20 +function beat(p: MgmtPromise) {                               
       21 +  return p.verdict === "kept" && /\bbeat\b/.test(p.verdict_rea
          +son?.text ?? "");                                             
       22 +}                                                             
       23 +                                                              
       24 +export function LedgerSection({ d, focus }: { d: Dossier; focu
          +s?: string | null }) {                                        
       25 +  const L = d.ledger;                                         
       26 +  const cred = L.credibility;                                 
       27 +  const [filter, setFilter] = useState<Filter>("scored");     
       28 +  const [open, setOpen] = useState<MgmtPromise | null>(null); 
       29 +  const [credOpen, setCredOpen] = useState(false);            
       30 +  const c = L.counts;                                         
       31 +  const scoredN = c.kept + c.missed + c.goalposts_moved + c.qu
          +ietly_dropped;                                                
       32 +  const dueNext = useMemo(                                    
       33 +    () => L.promises.filter((p) => p.verdict === "not_yet_due"
          + && L.next_test && p.period?.label === L.next_test.label),    
       34 +    [L],                                                      
       35 +  );                                                          
       36 +  const list = useMemo(() => {                                
       37 +    let ps = L.promises;                                      
       38 +    if (filter === "scored") ps = ps.filter((p) => SCORED.incl
          +udes(p.verdict));                                             
       39 +    else if (filter === "due") ps = dueNext;                  
       40 +    else if (filter === "not_yet_due") ps = ps.filter((p) => p
          +.verdict === "not_yet_due");                                  
     … 258 more lines (ctrl+o to expand)

⏺ Bash(cd ~/Documents/finn/web && sed -i '' 's/{s ===
      p.scored_target \&\& <span className="text-ink-3"> ·
      scored<\/span>}/{p.scored_target \&\& s.doc_…)
  ⎿  1
  ⎿  Created web/app/(app)/research/[symbol]/loading.tsx (+10 -0)
       1 +import { Skeleton } from "@/components/shell/StateView";       
       2 +                                                               
       3 +export default function Loading() {                            
       4 +  return (                                                     
       5 +    <div className="pt-14">                                    
       6 +      <div className="mx-4 mb-4 h-6 w-40 animate-pulse rounded 
         +bg-surface-2" />                                               
       7 +      <Skeleton rows={4} label="Loading dossier" />            
       8 +    </div>                                                     
       9 +  );                                                           
      10 +}                                                              
  ⎿  Created web/app/(app)/research/[symbol]/page.tsx (+12 -0)
       1 +import type { Metadata } from "next";                          
       2 +import { DossierScreen } from "@/components/research/DossierScr
         +een";                                                          
       3 +                                                               
       4 +export async function generateMetadata(props: PageProps<"/resea
         +rch/[symbol]">): Promise<Metadata> {                           
       5 +  const { symbol } = await props.params;                       
       6 +  return { title: decodeURIComponent(symbol).toUpperCase() };  
       7 +}                                                              
       8 +                                                               
       9 +export default async function DossierPage(props: PageProps<"/re
         +search/[symbol]">) {                                           
      10 +  const { symbol } = await props.params;                       
      11 +  return <DossierScreen symbol={decodeURIComponent(symbol).toUp
         +perCase()} />;                                                 
      12 +}                                                              
  ⎿  Updated web/components/ledger/Ledger.tsx (+1 -1)
      273                        {s.period_text ? <span className="text-i
           nk-3"> ({s.period_text})</span> : null}
      274                      </span>
      275                    )}
      276 -                  {s === p.scored_target && <span className="t
          -ext-ink-3"> · scored</span>}                                  
      276 +                  {p.scored_target && s.doc_id === p.scored_ta
          +rget.doc_id && s.made_on === p.scored_target.made_on && p.stat
          +ements.length > 1 && <span className="text-ink-3"> · scored</s
          +pan>}                                                         
      277                  </p>
      278                  <CitationBlock c={s.quote} />
      279                  {s.speaker && <p className="t-small -mt-1 pb-2
            text-ink-3">— {s.speaker}</p>}
  ⎿  Created web/components/research/DossierScreen.tsx (+186 -0)
        1 +"use client";                                                 
        2 +import { useEffect, useMemo, useState } from "react";         
        3 +import Link from "next/link";                                 
        4 +import { ChevronLeft } from "lucide-react";                   
        5 +import { LedgerSection } from "@/components/ledger/Ledger";   
        6 +import { ErrorState, Notice, Skeleton } from "@/components/she
          +ll/StateView";                                                
        7 +import { setAskContext } from "@/components/shell/ui-store";  
        8 +import { FIXTURE_DATE } from "@/lib/demo";                    
        9 +import { istDay, istTime } from "@/lib/format";               
       10 +import { companyName } from "@/lib/symbols";                  
       11 +import type { Dossier } from "@/lib/types";                   
       12 +import { BuildProgress } from "./BuildProgress";              
       13 +import {                                                      
       14 +  AnalystsSectionView,                                        
       15 +  BullBearSectionView,                                        
       16 +  DriversSectionView,                                         
       17 +  ExchangeSectionView,                                        
       18 +  RedFlagsSectionView,                                        
       19 +  SeriesSectionView,                                          
       20 +  SnapshotSection,                                            
       21 +  SourcesSection,                                             
       22 +  TrajectorySection,                                          
       23 +} from "./sections";                                          
       24 +import { isActive, useDossier } from "./useDossier";          
       25 +                                                              
       26 +const TABS: [string, string][] = [                            
       27 +  ["snapshot", "Snapshot"],                                   
       28 +  ["trajectory", "Trajectory"],                               
       29 +  ["ledger", "Ledger"],                                       
       30 +  ["cash", "Cash"],                                           
       31 +  ["balance-sheet", "Balance sheet"],                         
       32 +  ["analysts", "Analysts"],                                   
       33 +  ["red-flags", "Red flags"],                                 
       34 +  ["bull-bear", "Bull vs bear"],                              
       35 +  ["drivers", "Drivers"],                                     
       36 +  ["exchange", "Exchange"],                                   
       37 +  ["sources", "Sources"],                                     
       38 +];                                                            
       39 +                                                              
       40 +const TEMPLATE = { bank: "Bank", nbfc: "NBFC", standard: null 
          +} as const;                                                   
     … 146 more lines (ctrl+o to expand)

  Called Claude_Browser 3 times (ctrl+o to expand)
⏺ The dossier request succeeds; fixing a Next 16 prerender rule (the tab bar's
  usePathname needs a Suspense boundary on dynamic routes), then checking the
  dossier and ledger render.

⏺ Bash(python3 - <<'EOF'
      p='components/shell/AppShell.tsx'…)
  ⎿  Updated web/components/shell/AppShell.tsx (+5 -3)
       1  "use client";
       2  // Phone-width column + bottom dock (Ask bar above the tab bar,
           thumb zone) + undo toast.
       3  // On desktop every app route renders in a centred 430 px colum
          n; only "/" shows the QR landing.
       4 -import type { ReactNode } from "react";                        
       4 +import { Suspense, type ReactNode } from "react";              
       5  import { LazyMotion, domMax } from "framer-motion";
       6  import { AskBar } from "./AskBar";
       7 -import { TabBar } from "./TabBar";                             
       7 +import { TabBar, TabBarStatic } from "./TabBar";               
       8  import { ToastHost } from "./Toast";
       9  
      10  export function AppShell({ children }: { children: ReactNode })
           {
     ...
      16        <div className="fixed inset-x-0 bottom-0 z-30">
      17          <div className="mx-auto w-full max-w-[430px] bg-paper/9
          5 pb-[env(safe-area-inset-bottom)] backdrop-blur-sm min-[431px]
          :border-x min-[431px]:border-rule">
      18            <AskBar />
      19 -          <TabBar />                                           
      19 +          <Suspense fallback={<TabBarStatic />}>               
      20 +            <TabBar />                                         
      21 +          </Suspense>                                          
      22          </div>
      23        </div>
      24        <ToastHost />
  ⎿  Updated web/components/shell/TabBar.tsx (+9 -1)
      11  ];
      12  
      13  export function TabBar() {
      14 -  const path = usePathname() ?? "/";                           
      14 +  return <Bar path={usePathname() ?? "/"} />;                  
      15 +}                                                              
      16 +                                                               
      17 +/** Prerendered fallback (no active tab) while the pathname str
         +eams in. */                                                    
      18 +export function TabBarStatic() {                               
      19 +  return <Bar path="" />;                                      
      20 +}                                                              
      21 +                                                               
      22 +function Bar({ path }: { path: string }) {                     
      23    return (
      24      <nav aria-label="Main" className="grid grid-cols-4 border-t
           border-rule bg-paper">
      25        {TABS.map(({ href, label, Icon, match }) => {

  Called Claude_Browser (ctrl+o to expand)

⏺ The ledger renders correctly except for one change: delivered figures should
  appear as printed, so the franchise count reads 119.3 million rather than
  11.93 Cr. I'm adding an as-printed mode to the tappable figure. · summary

⏺ Bash(python3 - <<'EOF'
      p='components/cards/FigureValue.tsx'…)
  ⎿  components/cards/FigureValue.tsx:12:  printed = false,
     components/cards/FigureValue.tsx:17:  /** Show the value exactly as th
     e source printed it (ledger: "119.3 million", "7.54 %"). */
     … +5 lines (ctrl+o to expand)
  ⎿  Updated web/components/cards/FigureValue.tsx (+4 -1)
       9  export function FigureValue({
      10    f,
      11    signed = false,
      12 +  printed = false,                                             
      13    className = "",
      14  }: {
      15    f: Figure | null | undefined;
      16    signed?: boolean;
      17 +  /** Show the value exactly as the source printed it (ledger: 
         +"119.3 million", "7.54 %"). */                                 
      18 +  printed?: boolean;                                           
      19    className?: string;
      20  }) {
      21    const [open, setOpen] = useState(false);
      22    if (!f) return <span className="text-ink-3">—</span>;
      23    const unverified = f.status !== "verified";
      21 -  const text = figureText(f, { signed });                      
      24 +  const text = printed && f.raw ? f.raw.replace(/\s+%/, "%") : 
         +figureText(f, { signed });                                     
      25    return (
      26      <>
      27        <button
  ⎿  Updated web/components/ledger/Ledger.tsx (+1 -1)
      213            {p.delivered && (
      214              <span className="t-small mt-1 block">
      215                <span className="text-ink-3">Delivered </span>
      216 -              <FigureValue f={p.delivered} className="font-med
          -ium" />                                                       
      216 +              <FigureValue f={p.delivered} printed className="
          +font-medium" />                                               
      217              </span>
      218            )}
      219            {p.dropped_note && <span className="t-small mt-1 blo
           ck text-ink-2">{p.dropped_note}</span>}

  Called Claude_Browser (ctrl+o to expand)
  ⎿  Error: javascript_tool failed: TypeError: Cannot read properties of 
     undefined (reading 'click')
         at <anonymous>:4:9

  Called Claude_Browser 4 times (ctrl+o to expand)

⏺ Provenance now works end to end, from the verdict through both quotes and
  their pages to the "Open p.5" PDF links. I'm fixing 2.33 % showing as 2.3 %,
  then running a production build before the first push. · summary

⏺ Bash(python3 - <<'EOF'
      p='lib/format.ts'…)
  ⎿       |
            ^^^^^^^^^^ Cannot call impure function
       30 |         />
     … +21 lines (ctrl+o to expand)
  ⎿  Updated web/lib/format.ts (+2 -1)
       5  const inr1 = new Intl.NumberFormat("en-IN", { minimumFractionDi
          gits: 1, maximumFractionDigits: 1 });
       6  const inr2 = new Intl.NumberFormat("en-IN", { minimumFractionDi
          gits: 2, maximumFractionDigits: 2 });
       7  const upTo2 = new Intl.NumberFormat("en-IN", { maximumFractionD
          igits: 2 });
       8 +const pct = new Intl.NumberFormat("en-IN", { minimumFractionDig
         +its: 1, maximumFractionDigits: 2 });                           
       9  
      10  const minus = (s: string) => s.replace("-", "−");
      11  
     ...
      34      case "INR_CR":
      35        return opts.signed ? `${v >= 0 ? "▲" : "▼"}${moneyCr(Math
          .abs(v))}` : moneyCr(v);
      36      case "PCT":
      36 -      return opts.signed ? signed(v) : `${minus(inr1.format(v))
         -}%`;                                                           
      37 +      return opts.signed ? signed(v) : `${minus(pct.format(v))}
         +%`;                                                            
      38      case "BPS":
      39        return signed(v, 0, " bps");
      40      case "X":

  Ran 1 shell command (ctrl+o to expand)

⏺ Lint is flagging React Compiler purity issues; I'm fixing the real ones
  (render-time component definitions, impure Date.now(), an unescaped
  apostrophe, and a location.href navigation) and adding targeted, documented
  disables for the mount-time localStorage syncs. · summary

⏺ Bash(python3 - <<'EOF'
      import re…)
  ⎿    89:5  warning  Unused eslint-disable directive (no problems were rep
     orted from 'react-hooks/set-state-in-effect')
       0 errors and 1 warning potentially fixable with the `--fix` option.
       0 errors and 1 warning potentially fixable with the `--fix` option.
  ⎿  Updated web/components/brief/BriefScreen.tsx (+2 -0)
      28      // On "/" at desktop widths the landing shows instead; don'
          t fetch for a hidden Brief.
      29      if (gateDesktop && window.matchMedia("(min-width: 1024px)")
          .matches) return;
      30      const v = startVisit();
      31 +    // Visits live in localStorage (an external store) and can 
         +only be read after hydration.                                  
      32 +    // eslint-disable-next-line react-hooks/set-state-in-effect
      33      setVisit(v);
      34      if (!v.previous) setWindow("7d");
      35      setEnabled(true);
  ⎿  Updated web/components/brief/sheets.tsx (+1 -3)
      113              <dd className="t-figure text-[13px]">{readTime(cou
           nts.read_seconds)}</dd>
      114            </dl>
      115            <p className="rounded-xl bg-surface-2 p-3 font-mono 
           text-[12px] leading-[18px]">{counts.formula}</p>
      116 -          <p className="t-small text-ink-3">An estimate, not a
          - measurement — it assumes you'd otherwise open each filing.</p
          ->                                                             
      116 +          <p className="t-small text-ink-3">An estimate, not a
          + measurement — it assumes you&apos;d otherwise open each filin
          +g.</p>                                                        
      117          </div>
      118        )}
      119      </Sheet>
     ...
      237  }
      238  
      239  export function CustomWindowSheet({ open, onClose, onPick }: {
            open: boolean; onClose: () => void; onPick: (iso: string) => 
           void }) {
      240 -  const today = open ? new Intl.DateTimeFormat("en-CA", { time
          -Zone: "Asia/Kolkata" }).format(Date.now()) : "";              
      240    const [d, setD] = useState("");
      241    return (
      242      <Sheet
     ...
      261        <input
      262          id="since-date"
      263          type="date"
      265 -        max={today}                                           
      264          value={d}
      265          onChange={(e) => setD(e.target.value)}
      266          className="mt-1 h-12 w-full rounded-xl border border-r
           ule bg-paper px-3 text-[16px]"
  ⎿  Updated web/components/brief/useBrief.ts (+3 -0)
      72      liveRef.current = null;
      73  
      74      if (opts.showcase) {
      75 +      // eslint-disable-next-line react-hooks/set-state-in-effe
         +ct -- marks the request in flight                              
      76        setState((s) => ({ ...s, refreshing: true, error: null, l
          iveReady: false }));
      77        api
      78          .showcase()
     ...
      85  
      86      const cached = read<CachedBrief | null>(cacheKey, null);
      87      const usable = cached && cached.sig === sig ? cached : null
          ;
      88 +    // Paint the cached Brief from localStorage at once, flagge
         +d as refreshing (DECISIONS: first paint).                      
      89 +    // eslint-disable-next-line react-hooks/set-state-in-effect
      90      setState((s) => ({
      91        data: usable?.resp ?? (s.source === "showcase" ? null : s
          .data),
      92        source: usable ? "cache" : s.source === "showcase" ? null
           : s.source,
  ⎿  Updated web/components/portfolio/PortfolioScreen.tsx (+7 -4)
       4  // already one tap away in the Brief.
       5  import { useEffect, useMemo, useState } from "react";
       6  import Link from "next/link";
       7 +import { useRouter } from "next/navigation";                   
       8  import { ChevronRight } from "lucide-react";
       9  import { useBrief } from "@/components/brief/useBrief";
      10  import { Sheet } from "@/components/shell/Sheet";
     ...
      14  import { api } from "@/lib/client";
      15  import { CATEGORY_LABEL, displayHeadline, istWhen } from "@/lib
          /format";
      16  import { effectiveWeights, parseHoldings } from "@/lib/holdings
          ";
      16 -import { FALLBACK, isDemoPortfolio, read, useStored, write, typ
         -e LocalHolding } from "@/lib/store";                           
      17 +import { FALLBACK, isDemoPortfolio, read, useHydrated, useStore
         +d, write, type LocalHolding } from "@/lib/store";              
      18  import type { Card } from "@/lib/types";
      19  
      20  function latestAt(c: Card): string {
     ...
      23  
      24  export function PortfolioScreen() {
      25    const holdings = useStored<LocalHolding[]>("holdings", FALLBA
          CK.holdings);
      25 -  const [enabled, setEnabled] = useState(false);               
      26 -  useEffect(() => setEnabled(true), []);                       
      26 +  const enabled = useHydrated();                               
      27 +  const router = useRouter();                                  
      28    const b = useBrief({ window: "7d", customSince: null, visit: 
          null, showcase: false, enabled });
      29    const [editing, setEditing] = useState(false);
      30    const demo = isDemoPortfolio(holdings);
     ...
      47      setAskContext({
      48        placeholder: "Ask about your holdings…",
      49        chips: [
      49 -        ...(top ? [{ label: `Research ${top}, your largest hold
         -ing`, run: () => (window.location.href = `/research/${top}`) }]
         - : []),                                                        
      50 +        ...(top ? [{ label: `Research ${top}, your largest hold
         +ing`, run: () => router.push(`/research/${top}`) }] : []),     
      51          { label: "Which holdings had news this week?", run: () 
          => document.getElementById("holdings")?.scrollIntoView({ behavi
          or: "smooth" }) },
      52          { label: "Change my holdings", run: () => setEditing(tr
          ue) },
      53        ],
     ...
      142    const [known, setKnown] = useState<Set<string> | null>(null)
           ;
      143    useEffect(() => {
      144      if (!open) return;
      145 +    // Opening the sheet seeds the editor from the stored hold
          +ings (an external store) — once per open.                     
      146 +    // eslint-disable-next-line react-hooks/set-state-in-effec
          +t                                                             
      147      setText(
      148        demo
     … 1 more lines (ctrl+o to expand)
  ⎿  Updated web/components/research/DossierScreen.tsx (+2 -0)
      50    const [focus, setFocus] = useState<string | null>(null);
      51    useEffect(() => {
      52      const q = new URLSearchParams(window.location.search);
      53 +    // Query flags are read after hydration so the route stays 
         +prerenderable.                                                 
      54 +    // eslint-disable-next-line react-hooks/set-state-in-effect
      55      if (process.env.NODE_ENV !== "production" && q.get("mock") 
          === "build") setMock(true);
      56      setFocus(q.get("focus"));
      57    }, []);
  ⎿  … 5 more files changed
  ⎿  You've hit your 5-hour limit · resets 6:50pm (Asia/Calcutta)
     /upgrade or /usage-credits to finish what you’re working on.

❯ token limit reset, continue working                                           

⏺ Picking up where I left off: lint is down to one warning. Fixing it, then
  running the production build.

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(sed -n 87,90p components/brief/useBrief.ts && sed -i ''
      '89{/eslint-disable-next-line react-hooks\/set-state-in-effect/d;}'
      components/brief/useBrief.ts && npm…)
  ⎿      const usable = cached && cached.sig === sig ? cached : null;
         // Paint the cached Brief from localStorage at once, flagged as re
     freshing (DECISIONS: first paint).
     … +43 lines (ctrl+o to expand)
  ⎿  Updated web/components/brief/useBrief.ts (+0 -1)
      86      const cached = read<CachedBrief | null>(cacheKey, null);
      87      const usable = cached && cached.sig === sig ? cached : null
          ;
      88      // Paint the cached Brief from localStorage at once, flagge
          d as refreshing (DECISIONS: first paint).
      89 -    // eslint-disable-next-line react-hooks/set-state-in-effect
      89      setState((s) => ({
      90        data: usable?.resp ?? (s.source === "showcase" ? null : s
          .data),
      91        source: usable ? "cache" : s.source === "showcase" ? null
           : s.source,

⏺ Bash(sed -i '' 's/  const now = new Date().toISOString();/  const now = "";
      \/\/ stamped on save (no clock reads during prerender)/' lib/holdings.ts
      && sed -i '' 's/…)
  ⎿  175:            write("holdings", parsed.holdings.map((h) => ({ ...h,
     added_at: at })));
       Finished TypeScript in 1348ms ...
     … +29 lines (ctrl+o to expand)
  ⎿  Updated web/components/portfolio/PortfolioScreen.tsx (+2 -1)
      171            type="button"
      172            disabled={!ok}
      173            onClick={() => {
      174 -            write("holdings", parsed.holdings);               
      174 +            const at = new Date().toISOString();              
      175 +            write("holdings", parsed.holdings.map((h) => ({ ..
          +.h, added_at: at })));                                        
      176              for (const k of ["since", "24h", "3d", "7d", "cust
           om"]) write(`brief.${k}`, null);
      177              onClose();
      178            }}
  ⎿  Updated web/lib/holdings.ts (+1 -1)
       8    const out = new Map<string, LocalHolding>();
       9    const unknown: string[] = [];
      10    const errors: string[] = [];
      11 -  const now = new Date().toISOString();                        
      11 +  const now = ""; // stamped on save (no clock reads during pre
         +render)                                                        
      12    for (const raw of text.split(/\r?\n|;/)) {
      13      const line = raw.trim();
      14      if (!line || /^symbol\b/i.test(line)) continue; // blank or
           CSV header

⏺ Build passes and every route prerenders (static or partial). Restyling the
  single-card /e/[id] page (Telegram's "Open in FINN") to the new shell, then
  committing and pushing.

⏺ Bash(python3 - <<'EOF'
      p='app/(app)/e/[id]/page.tsx'…)
  ⎿  M  .claude/launch.json
     M  backend/finn/cards/brief.py
     A  web/app/(app)/brief/page.tsx
     … +47 lines (ctrl+o to expand)
  ⎿  Updated web/app/(app)/e/[id]/loading.tsx (+6 -10)
  ⎿  Updated web/app/(app)/e/[id]/page.tsx (+13 -14)
  ⎿  (a git step in this command can move the working tree, so these may be
     its changes, not edits) (ctrl+o to expand)

  Ran 1 shell command (ctrl+o to expand)

⏺ Splitting this into focused commits: backend freshness fix, then the design
  system and cards, then the screens.

  Ran 1 shell command (ctrl+o to expand)

⏺ Pushed. Waiting on both deploys: Render for the freshness fix, Vercel for the
  web app.

  Ran 2 shell commands (ctrl+o to expand)

⏺ The deploy is live with no frame-blocking headers, so the landing iframe will
  load, and the demo Brief is served from Vercel's edge. I'm checking the
  deployed site in the browser next. · summary
  ⎿  Error: actions[0] (resize_window) failed: No preview is open. Use 
     `preview_start` or `navigate` with {"url": "https://…"} to open a browser 
     tab at a URL, or `preview_start` with {"name": "…"} to start a dev server 
     from .claude/launch.json. (0 completed, 3 remaining)

  Called Claude_Browser (ctrl+o to expand)

⏺ The landing renders with the live phone preview on the deployed site, so the
  iframe works. The preview's freshness line shows a warning, so I'm zooming in.

  Called Claude_Browser 2 times (ctrl+o to expand)
⏺ The edge-cached demo Brief arrived in 55 ms. The follow-up live POST failed
  after about 2 s, so checking it directly.

  Ran 2 shell commands (ctrl+o to expand)

⏺ Results cards average about 60 KB each and the live Brief is 1 MB, too heavy
  for a phone and for localStorage. Measuring where the weight sits.

  Called Claude_Browser, ran 1 shell command (ctrl+o to expand)

⏺ A direct fetch works (brotli-compressed, 2.4 s), so the iframe failure is
  client-side. Reproducing on /brief directly.

  Called Claude_Browser 2 times (ctrl+o to expand)

⏺ Works on /brief directly: the edge copy in 159 ms, the live Brief in 2.3 s,
  cached afterwards. Re-checking the landing iframe.

  Called Claude_Browser 2 times (ctrl+o to expand)

⏺ The second load succeeded, and the first failure was transient. I'm capping
  localStorage to the current window's Brief next, since a live 7-day Brief runs
  about 1 MB uncompressed. · summary

⏺ Bash(cd ~/Documents/finn/web && python3 - <<'EOF'
      p='lib/store.ts'…)
  ⎿  Updated web/components/brief/useBrief.ts (+2 -2)
       8  import { api, FetchError } from "@/lib/client";
       9  import { effectiveWeights } from "@/lib/holdings";
      10  import {
      11 +  cacheBrief,                                                  
      12    FALLBACK,
      13    holdingsSignature,
      14    isDemoPortfolio,
      15    read,
      16    settleFeedback,
      17    useStored,
      17 -  write,                                                       
      18    type CachedBrief,
      19    type LocalHolding,
      20    type Visit,
     ...
      141          if (cancelled) return;
      142          liveRef.current = resp;
      143          const at = new Date().toISOString();
      144 -        write<CachedBrief>(cacheKey, { resp, at, sig: holdings
          -Signature(holdings, resp.rules) });                           
      144 +        cacheBrief(cacheKey, { resp, at, sig: holdingsSignatur
          +e(holdings, resp.rules) });                                   
      145          if (sent.length) settleFeedback(resp.rules, sent.map((
           p) => p.at).sort().at(-1) ?? null);
      146          setState((s) =>
      147            s.source === "fallback"
  ⎿  Updated web/lib/store.ts (+6 -0)
      140    );
      141  }
      142  
      143 +/** Cache one Brief at a time (a 7-day Brief is ~1 MB uncompre
          +ssed; localStorage holds ~5 MB). */                           
      144 +export function cacheBrief(key: string, value: CachedBrief) { 
      145 +  for (const k of ["since", "24h", "3d", "7d", "custom"]) if (
          +`brief.${k}` !== key) write(`brief.${k}`, null);              
      146 +  write(key, value);                                          
      147 +}                                                             
      148 +                                                              
      149  // --- Visits ("Since your last visit") ----------------------
           -----------------------------------------------
      150  
      151  const SESSION_GAP_MS = 30 * 60 * 1000;

⏺ Next, the 3-step first-run tour: swipe to triage, tap a number for its source,
  research any ticker.

  Called Claude_Browser (ctrl+o to expand)

⏺ Bash(cat > components/shell/Tour.tsx <<'EOF'
      "use client";…)
  ⎿  Updated web/components/brief/BriefScreen.tsx (+4 -0)
       5  import { Check, ChevronRight, Info, RotateCcw, Send, ThumbsDown
           } from "lucide-react";
       6  import { CardView } from "@/components/cards";
       7  import { ErrorState, Notice, Skeleton } from "@/components/shel
          l/StateView";
       8 +import { Tour } from "@/components/shell/Tour";                
       9  import { setAskContext, showToast } from "@/components/shell/ui
          -store";
      10  import { SHOWCASE_LABEL } from "@/lib/demo";
      11  import { CATEGORY_LABEL, CATEGORY_PLURAL, displayHeadline, isTo
          dayIST, istClock, istDay, istTime, readTime } from "@/lib/forma
          t";
     ...
      24    const [window_, setWindow] = useState<WindowKey>("since");
      25    const [customSince, setCustomSince] = useState<string | null>
          (null);
      26    const showcase = useStored<boolean>("showcase", FALLBACK.show
          case);
      27 +  const tourDone = useStored<boolean>("tour", FALLBACK.tour);  
      28 +  const [tourOpen, setTourOpen] = useState(true);              
      29  
      30    useEffect(() => {
      31      // On "/" at desktop widths the landing shows instead; don'
          t fetch for a hidden Brief.
     ...
      300          )}
      301        </main>
      302  
      303 +      {data && visible.length > 0 && !tourDone && tourOpen && 
          +<Tour onDone={() => setTourOpen(false)} />}                   
      304        <WhySheet card={why?.card ?? null} rank={why?.rank ?? 1}
            onClose={() => setWhy(null)} />
      305        <ScopeSheet card={scopeFor} onChoose={chooseScope} />
      306        <TimeSavedSheet open={sheet === "time"} counts={data?.co
           unts ?? null} onClose={() => setSheet(null)} />
  ⎿  Created web/components/shell/Tour.tsx (+115 -0)
        1 +"use client";                                                 
        2 +// First-run tour: 3 skippable steps, shown once (localStorage
          +). A spotlight over the real element, not a slideshow.        
        3 +import { useEffect, useLayoutEffect, useState } from "react"; 
        4 +import { createPortal } from "react-dom";                     
        5 +import { write } from "@/lib/store";                          
        6 +                                                              
        7 +type Step = { selector: string; title: string; body: string };
        8 +const STEPS: Step[] = [                                       
        9 +  {                                                           
       10 +    selector: '[data-tour="top-card"]',                       
       11 +    title: "Swipe to triage",                                 
       12 +    body: "Right = reviewed. Left = not useful — FINN shows le
          +ss of it. Undo for 5 seconds. Tap a card to open it.",        
       13 +  },                                                          
       14 +  {                                                           
       15 +    selector: '[data-tour="top-card"] [data-figure]',         
       16 +    title: "Tap a number for its source",                     
       17 +    body: "Every figure opens its filing, page and the exact q
          +uote. If FINN couldn't verify it, it says so.",               
       18 +  },                                                          
       19 +  {                                                           
       20 +    selector: '[data-tour="research-tab"]',                   
       21 +    title: "Research any NSE ticker",                         
       22 +    body: "A dossier from transcripts, annual reports and fili
          +ngs — with a Promise Ledger of what management said vs did.", 
       23 +  },                                                          
       24 +];                                                            
       25 +                                                              
       26 +export function Tour({ onDone }: { onDone: () => void }) {    
       27 +  const [i, setI] = useState(0);                              
       28 +  const [rect, setRect] = useState<DOMRect | null>(null);     
       29 +  const step = STEPS[i];                                      
       30 +                                                              
       31 +  useLayoutEffect(() => {                                     
       32 +    const el = document.querySelector(step.selector) as HTMLEl
          +ement | null;                                                 
       33 +    if (!el) return;                                          
       34 +    const r0 = el.getBoundingClientRect();                    
       35 +    if (r0.top < 60 || r0.bottom > window.innerHeight - 140) e
          +l.scrollIntoView({ block: "center" });                        
       36 +    const measure = () => setRect(el.getBoundingClientRect());
       37 +    measure();                                                
       38 +    window.addEventListener("resize", measure);               
       39 +    window.addEventListener("scroll", measure, true);         
       40 +    return () => {                                            
     … 75 more lines (ctrl+o to expand)
  ⎿  Error: actions[0] (navigate) failed: navigation to http://localhost:3001 
     was denied or failed (0 completed, 4 remaining)

  Called Claude_Browser 2 times (ctrl+o to expand)

⏺ The spotlight drifted because the layout shifted after it measured.
  Re-measuring continuously while the tour is open.

⏺ Bash(python3 - <<'EOF'
      p='components/shell/Tour.tsx'…)
  ⎿  ok
  ⎿  Updated web/components/shell/Tour.tsx (+2 -0)
      35      if (r0.top < 60 || r0.bottom > window.innerHeight - 140) el
          .scrollIntoView({ block: "center" });
      36      const measure = () => setRect(el.getBoundingClientRect());
      37      measure();
      38 +    const iv = setInterval(measure, 250); // content above can 
         +still be settling (header, season strip)                       
      39      window.addEventListener("resize", measure);
      40      window.addEventListener("scroll", measure, true);
      41      return () => {
      42 +      clearInterval(iv);                                       
      43        window.removeEventListener("resize", measure);
      44        window.removeEventListener("scroll", measure, true);
      45      };

  Called Claude_Browser 2 times (ctrl+o to expand)

⏺ The spotlight held onto a stale element after the live data replaced the list.
  Re-querying the target on each measure.

⏺ Bash(python3 - <<'EOF'
      p='components/shell/Tour.tsx'…)
  ⎿  ok
  ⎿  Updated web/components/shell/Tour.tsx (+4 -1)
      33      if (!el) return;
      34      const r0 = el.getBoundingClientRect();
      35      if (r0.top < 60 || r0.bottom > window.innerHeight - 140) el
          .scrollIntoView({ block: "center" });
      36 -    const measure = () => setRect(el.getBoundingClientRect()); 
      36 +    const measure = () => {                                    
      37 +      const cur = document.querySelector(step.selector) as HTML
         +Element | null; // the list may re-render                      
      38 +      if (cur) setRect(cur.getBoundingClientRect());           
      39 +    };                                                         
      40      measure();
      41      const iv = setInterval(measure, 250); // content above can 
          still be settling (header, season strip)
      42      window.addEventListener("resize", measure);

  Called Claude_Browser (ctrl+o to expand)

⏺ Bash(sed -i '' 's/className="pointer-events-none absolute rounded-xl
      transition-all duration-200"/className="pointer-events-none absolute
      rounded-xl"/' components/sh…)
  ⎿  1
  ⎿  Updated web/components/shell/Tour.tsx (+1 -1)
      66        {rect ? (
      67          <div
      68            aria-hidden
      69 -          className="pointer-events-none absolute rounded-xl tr
         -ansition-all duration-200"                                     
      69 +          className="pointer-events-none absolute rounded-xl"  
      70            style={{
      71              left: Math.max(4, rect.left - pad),
      72              top: rect.top - pad,

  Called Claude_Browser 2 times (ctrl+o to expand)

⏺ The tour spotlight lines up on all three steps, and finishing it is
  remembered. Committing, then on to the drivers-only build mode.

  Called ccd_turn, ran 3 shell commands (ctrl+o to expand)

⏺ I'm building a drivers-only mode as a foreground CLI run, so the live Render
  worker stays untouched and the run can check quota headroom itself. Next I'll
  look at how the router counts today's calls. · summary

  Ran 3 shell commands (ctrl+o to expand)

⏺ Bash(cat > db/migrations/0005_drivers.sql <<'EOF'
      -- Suggested drivers per holding from a drivers-only build (Flash-Lite MAP
      + code; no strong model).…)
  ⎿  78:create table if not exists public.dossiers (
     79-  symbol          text primary key,
     80-  schema_version  integer not null,
     … +19 lines (ctrl+o to expand)
  ⎿  Created backend/db/migrations/0005_drivers.sql (+9 -0)
      1 +-- Suggested drivers per holding from a drivers-only build (Flas
        +h-Lite MAP + code; no strong model).                            
      2 +-- Read by GET /research/drivers; a full dossier's own drivers s
        +ection supersedes it.                                           
      3 +create table if not exists public.drivers (                     
      4 +  symbol      text primary key,                                 
      5 +  section     jsonb not null,                                   
      6 +  calls_read  int not null default 0,                           
      7 +  built_at    timestamptz not null default now()                
      8 +);                                                              
      9 +alter table public.drivers enable row level security;           
  ⎿  Created backend/finn/research/drivers_only.py (+129 -0)
        1 +"""Drivers-only builds for portfolio holdings (DECISIONS: "Wha
          +t you're watching" drivers without strong calls).             
        2 +                                                              
        3 +Drivers are pure code over MAP output (insights.drivers via bu
          +ild.apply_ledger), so a holding's suggested drivers           
        4 +need only the Flash-Lite MAP of its latest calls. This module 
          +runs discover → latest 3 transcripts → MAP → code,            
        5 +stores the drivers section in `drivers`, and never publishes a
          + dossier — Research still shows the normal build              
        6 +flow for that ticker, which then reuses the cached MAP output.
        7 +                                                              
        8 +The strong tier is unreachable here: `CheapOnly` raises if any
          +thing asks for it. Before a run the caller checks             
        9 +today's Flash-Lite count (failed attempts included) and caps t
          +he run so evaluators keep their share.                        
       10 +"""                                                           
       11 +                                                              
       12 +from __future__ import annotations                            
       13 +                                                              
       14 +import logging                                                
       15 +from dataclasses import dataclass                             
       16 +                                                              
       17 +from psycopg.types.json import Jsonb                          
       18 +                                                              
       19 +from finn.calendar import now_utc                             
       20 +from finn.llm import LLMUnavailable                           
       21 +from finn.models.research import DriversSection               
       22 +                                                              
       23 +log = logging.getLogger("finn.research.drivers")              
       24 +                                                              
       25 +TRANSCRIPTS = 3  # latest calls per holding — enough for "ment
          +ioned in 3+ places" without reading all 8                     
       26 +FLASH_LITE_RPD = 500  # free-tier daily requests (product owne
          +r's AI Studio dashboard, 11 Nov 2026)                         
       27 +RUN_CAP = 50  # Flash-Lite calls one drivers run may spend (pr
          +oduct owner, 11 Nov)                                          
       28 +MIN_HEADROOM = 150  # Flash-Lite calls that must stay free for
          + evaluators and the push side after the run                   
       29 +                                                              
       30 +                                                              
       31 +class StrongTierBlocked(RuntimeError):                        
       32 +    pass                                                      
       33 +                                                              
       34 +                                                              
       35 +class CheapOnly:                                              
       36 +    """Router wrapper for drivers-only builds: cheap tier only
          +, and at most `budget` uncached calls."""                     
       37 +                                                              
       38 +    def __init__(self, inner, budget: int):                   
       39 +        self.inner, self.budget, self.spent = inner, budget, 0
       40 +        self.stats = inner.stats                              
     … 89 more lines (ctrl+o to expand)

⏺ Bash(sed -i '' "s/dossier->'drivers' as drivers from
      public.dossiers/payload->'drivers' as drivers from public.dossiers/;
      s/raise LLMUnavailable(\"drivers run budget…)
  ⎿  ......
        [100%]
     6 passed in 0.28s
  ⎿  Updated backend/finn/research/drivers_only.py (+2 -2)
      43          if tier != "cheap":
      44              raise StrongTierBlocked(f"drivers-only builds never
           call the {tier} tier ({req.purpose})")
      45          if self.spent >= self.budget:
      46 -            raise LLMUnavailable("drivers run budget used", kin
         -d="budget")                                                    
      46 +            raise LLMUnavailable("drivers run budget used", kin
         +d="quota")                                                     
      47          before = self.inner.stats.calls
      48          res = self.inner.run(tier, req)
      49          self.spent += self.inner.stats.calls - before
     ...
      121      for r in conn.execute("select symbol, section from public.
           drivers where symbol = any(%s)", (symbols,)).fetchall():
      122          out[r["symbol"]] = r["section"]
      123      rows = conn.execute(
      124 -        "select symbol, dossier->'drivers' as drivers from pub
          -lic.dossiers where symbol = any(%s)", (symbols,)              
      124 +        "select symbol, payload->'drivers' as drivers from pub
          +lic.dossiers where symbol = any(%s)", (symbols,)              
      125      ).fetchall()
      126      for r in rows:
      127          if r["drivers"] and (r["drivers"].get("items") or out[
           r["symbol"]] is None):
  ⎿  Updated backend/jobs/research.py (+41 -0)
       4  python -m jobs.research drain [--max 20] [--minutes 40]        
                       # run queued builds here (a worker)
       5  python -m jobs.research export --symbols INFY,BAJFINANCE --out 
          ../web/public/fixtures   # frontend fixtures
       6  python -m jobs.research resume                                 
                       # re-queue builds parked for quota
       7 +python -m jobs.research drivers [--symbols HAL,ITC] [--dry-run]
         +             # drivers only (Flash-Lite, no strong)            
       8  
       9  Builds normally run on Render's worker thread; `drain` lets the
           nightly Actions run (7 GB RAM, same Supabase
      10  queue) take work too. Both claim with SKIP LOCKED, so they neve
          r build the same job twice.
     ...
      35      d.add_argument("--max", type=int, default=20)
      36      d.add_argument("--minutes", type=float, default=40)
      37      sub.add_parser("resume", help="Re-queue builds parked for m
          odel quota now (e.g. after adding a model)")
      38 +    dv = sub.add_parser("drivers", help="Suggested drivers for 
         +holdings: Flash-Lite MAP + code, never the strong tier")       
      39 +    dv.add_argument("--symbols", default="", help="Default: dem
         +o portfolio holdings without drivers yet")                     
      40 +    dv.add_argument("--dry-run", action="store_true")          
      41      x = sub.add_parser("export")
      42      x.add_argument("--symbols", default="INFY,BAJFINANCE")
      43      x.add_argument("--out", default=str(Path(__file__).resolve(
          ).parents[2] / "web" / "public" / "fixtures"))
     ...
      58                  "where status = 'waiting_quota' returning id, s
          ymbol"
      59              ).fetchall()
      60              print("re-queued:", ", ".join(f"{r['symbol']} (#{r[
          'id']})" for r in rows) or "none")
      61 +        elif args.cmd == "drivers":                            
      62 +            run_drivers(conn, args.symbols, args.dry_run)      
      63          elif args.cmd == "export":
      64              out = Path(args.out)
      65              out.mkdir(parents=True, exist_ok=True)
     ...
       75                  print(f"{sym}: wrote {out / f'dossier_{sym}.js
           on'}")
       76  
       77  
       78 +def run_drivers(conn, symbols_arg: str, dry_run: bool) -> None
          +:                                                             
       79 +    from finn.llm import PostgresLLMLog, Router               
       80 +    from finn.llm.gemini import DEFAULT_CHEAP                 
       81 +    from finn.portfolio import DEMO_WEIGHTS                   
       82 +    from finn.research import drivers_only as dv              
       83 +                                                              
       84 +    model = os.environ.get("GEMINI_MODEL_CHEAP") or DEFAULT_CH
          +EAP                                                           
       85 +    used = dv.flash_lite_used_today(conn, model)              
       86 +    budget = dv.plan_budget(used)                             
       87 +    print(f"{model}: {used} calls today (incl. failed) · headr
          +oom {dv.headroom(used)} · this run may spend {budget}")       
       88 +    if budget == 0:                                           
       89 +        print(f"skipped: fewer than {dv.MIN_HEADROOM} calls wo
          +uld stay free after a {dv.RUN_CAP}-call run")                 
       90 +        return                                                
     … 24 more lines (ctrl+o to expand)
  ⎿  Created backend/tests/test_drivers_only.py (+50 -0)
       1 +"""Drivers-only builds never touch the strong tier and respect 
         +the run budget / headroom rule."""                             
       2 +                                                               
       3 +import pytest                                                  
       4 +                                                               
       5 +from finn.research import drivers_only as dv                   
       6 +                                                               
       7 +                                                               
       8 +class FakeStats:                                               
       9 +    calls = 0                                                  
      10 +                                                               
      11 +                                                               
      12 +class FakeRouter:                                              
      13 +    def __init__(self):                                        
      14 +        self.stats = FakeStats()                               
      15 +        self.tiers = []                                        
      16 +                                                               
      17 +    def run(self, tier, req):                                  
      18 +        self.tiers.append(tier)                                
      19 +        self.stats.calls += 1                                  
      20 +        return "ok"                                            
      21 +                                                               
      22 +                                                               
      23 +class Req:                                                     
      24 +    purpose = "research.judge.v1"                              
      25 +                                                               
      26 +                                                               
      27 +def test_strong_tier_is_blocked():                             
      28 +    inner = FakeRouter()                                       
      29 +    r = dv.CheapOnly(inner, budget=5)                          
      30 +    with pytest.raises(dv.StrongTierBlocked):                  
      31 +        r.run("strong", Req())                                 
      32 +    assert inner.tiers == []                                   
      33 +    r.run("cheap", Req())                                      
      34 +    assert inner.tiers == ["cheap"] and r.spent == 1           
      35 +                                                               
      36 +                                                               
      37 +def test_budget_stops_further_calls():                         
      38 +    from finn.llm import LLMUnavailable                        
      39 +                                                               
      40 +    r = dv.CheapOnly(FakeRouter(), budget=2)                   
     … 10 more lines (ctrl+o to expand)

⏺ Strong-tier blocking, the run budget and the headroom rule are tested. Adding
  GET /research/drivers, passing query strings through the web proxy, then
  applying the migration.

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='api/research.py'…)  ⎿  19:from fastapi import APIRouter, HTTPException, Query
       applied  0003_push.sql
       applied  0004_research.sql
     … +4 lines (ctrl+o to expand)
  ⎿  Updated backend/api/research.py (+10 -0)
      66          return {"symbols": _securities(conn)["rows"]}
      67  
      68  
      69 +@router.get("/drivers")                                        
      70 +def drivers(symbols: str = Query(..., description="Comma-separa
         +ted NSE symbols (at most 40)")):                               
      71 +    """Suggested drivers per holding (Portfolio's "What you're 
         +watching"); null where none are built yet."""                  
      72 +    from finn.research.drivers_only import load_many           
      73 +                                                               
      74 +    syms = sorted({s.strip().upper() for s in symbols.split(","
         +) if s.strip()})[:40]                                          
      75 +    with connect() as conn:                                    
      76 +        return {"drivers": load_many(conn, syms)}              
      77 +                                                               
      78 +                                                               
      79  @router.get("/jobs/{job_id}")
      80  def job(job_id: int):
      81      with connect() as conn:
  ⎿  Updated web/app/api/[...path]/route.ts (+2 -1)
      13    ["DELETE", /^subscriptions\/me$/],
      14    // Research (Phase 3): builds run in the background on the AP
          I, so every call here returns quickly.
      15    ["GET", /^research\/symbols$/],
      16 +  ["GET", /^research\/drivers$/],                              
      17    ["GET", /^research\/jobs\/\d+$/],
      18    ["GET", /^research\/[A-Za-z0-9&_-]{1,20}$/],
      19    ["POST", /^research\/[A-Za-z0-9&_-]{1,20}\/build$/],
     ...
      32    const auth = req.headers.get("authorization");
      33    if (auth) headers.authorization = auth;
      34    try {
      34 -    const r = await fetch(`${base}/${joined}`, {               
      35 +    const r = await fetch(`${base}/${joined}${new URL(req.url).
         +search}`, {                                                    
      36        method: req.method,
      37        headers,
      38        body: req.method === "GET" || req.method === "DELETE" ? u
          ndefined : await req.text(),

⏺ Passing every query string through would let a browser send ?force=true to the
  build endpoint and spend strong quota, which the proxy has blocked until now.
  Limiting it to the drivers route.

⏺ Bash(python3 - <<'EOF'
      p='app/api/[...path]/route.ts'…)
  ⎿  14:  // Research (Phase 3): builds run in the background on the API, s
     o every call here returns quickly.
     15:  ["GET", /^research\/symbols$/],
     … +13 lines (ctrl+o to expand)
  ⎿  Updated web/app/api/[...path]/route.ts (+3 -1)
      32    const auth = req.headers.get("authorization");
      33    if (auth) headers.authorization = auth;
      34    try {
      35 -    const r = await fetch(`${base}/${joined}${new URL(req.url).
         -search}`, {                                                    
      35 +    // Query strings pass only where a route needs one (never e
         +.g. ?force=true on /build: that spends quota).                 
      36 +    const search = /^research\/drivers$/.test(path.join("/")) ?
         + new URL(req.url).search : "";                                 
      37 +    const r = await fetch(`${base}/${joined}${search}`, {      
      38        method: req.method,
      39        headers,
      40        body: req.method === "GET" || req.method === "DELETE" ? u
          ndefined : await req.text(),

⏺ 95 Flash-Lite calls used today, so a 50-call run leaves 355 free (above the
  150 floor). Running the drivers build for the 15 holdings without drivers in
  the background (no strong calls possible).

  Ran 2 shell commands (ctrl+o to expand)
  ⎿  2 actions not run · auto mode's check had no usable answer

⏺ The background command hit a transient permission-check failure. I'll retry it
  shortly; meanwhile, wiring "What you're watching" into Portfolio.

⏺ Update(web/lib/client.ts)
  ⎿  Added 4 lines
      52      call<DossierJob & { dossier_version: number }>(`/api/resear
          ch/jobs/${id}`, { signal }, 20_000),
      53    fixture: (sym: string) => call<DossierResponse>(`/fixtures/do
          ssier_${sym}.json`, { cache: "default" }),
      54    symbols: () => call<{ symbols: [string, string][] }>("/api/re
          search/symbols", {}, 58_000),
      55 +  drivers: (symbols: string[]) =>                              
      56 +    call<{ drivers: Record<string, DriversSection | null> }>(  
      57 +      `/api/research/drivers?symbols=${encodeURIComponent(symbo
         +ls.join(","))}`,                                               
      58 +    ),                                                         
      59    staticSymbols: () => call<{ at: string; symbols: [string, str
          ing][] }>("/nse-symbols.json", { cache: "default" }),
      60  };

⏺ Update(web/lib/client.ts)
  ⎿  Added 1 line, removed 1 line
      1  "use client";
      2  // Browser → Vercel proxy (/api/*) → Render. Render's free tier 
         can take ~50 s to wake: callers show progress,
      3  // never a blank screen, and keep the last good data (CLAUDE.md 
         rule 7).
      4 -import type { BriefRequest, BriefResponse, DossierJob, DossierRe
        -sponse } from "@/lib/types";                                    
      4 +import type { BriefRequest, BriefResponse, DossierJob, DossierRe
        +sponse, DriversSection } from "@/lib/types";                    
      5  
      6  export class FetchError extends Error {
      7    constructor(

⏺ Now the watching section in Portfolio.

⏺ Update(web/components/portfolio/PortfolioScreen.tsx)
  ⎿  Added 2 lines, removed 7 lines
      125            Holdings entered as share quantities split the remai
           ning weight equally until prices are wired in.
      126          </p>
      127        )}
      128 -      <section className="mt-8 px-4">                         
      129 -        <h2 className="t-micro text-ink-3">What you&apos;re wa
          -tching</h2>                                                   
      130 -        <p className="t-small mt-1 text-ink-2">               
      131 -          FINN suggests 2–3 drivers per holding from the compa
          -ny&apos;s own calls (margins, growth, asset quality…). Drivers
          - appear after                                                 
      132 -          research — open a holding in Research to see its sug
          -gestions.                                                     
      133 -        </p>                                                  
      134 -      </section>                                              
      128 +      <Watching symbols={rows.map((r) => r.symbol)} />        
      129 +                                                              
      130        <ImportSheet open={editing} onClose={() => setEditing(fa
           lse)} current={holdings} demo={demo} />
      131      </div>
      132    );

⏺ Update(web/components/portfolio/PortfolioScreen.tsx)
  ⎿  Added 69 lines
      132    );
      133  }
      134  
      135 +// "What you're watching": 2–3 drivers per holding suggested f
          +rom the company's own calls (counted in code);                
      136 +// one tap confirms. Confirmed drivers stay on this phone.    
      137 +function Watching({ symbols }: { symbols: string[] }) {       
      138 +  const [drivers, setDrivers] = useState<Record<string, Driver
          +sSection | null> | null>(null);                               
      139 +  const [failed, setFailed] = useState(false);                
      140 +  const confirmed = useStored<Record<string, string[]>>("drive
          +rs", FALLBACK.drivers);                                       
      141 +  const key = symbols.join(",");                              
      142 +  useEffect(() => {                                           
      143 +    let cancelled = false;                                    
      144 +    api                                                       
      145 +      .drivers(key.split(","))                                
      146 +      .then((r) => !cancelled && setDrivers(r.drivers))       
      147 +      .catch(() => !cancelled && setFailed(true));            
      148 +    return () => {                                            
      149 +      cancelled = true;                                       
      150 +    };                                                        
      151 +  }, [key]);                                                  
      152 +  const toggle = (sym: string, id: string) => {               
      153 +    const cur = read<Record<string, string[]>>("drivers", FALL
          +BACK.drivers);                                                
      154 +    const list = cur[sym] ?? [];                              
      155 +    write("drivers", { ...cur, [sym]: list.includes(id) ? list
          +.filter((i) => i !== id) : [...list, id] });                  
      156 +  };                                                          
      157 +  const withItems = symbols.filter((s) => drivers?.[s]?.items.
          +length);                                                      
      158 +  const without = symbols.filter((s) => !drivers?.[s]?.items.l
          +ength);                                                       
      159 +  return (                                                    
      160 +    <section className="mt-8" id="watching">                  
      161 +      <h2 className="t-micro px-4 text-ink-3">What you&apos;re
          + watching</h2>                                                
      162 +      <p className="t-small mt-1 px-4 text-ink-2">            
      163 +        Suggested from each company&apos;s own calls — what ma
          +nagement guides on and analysts ask about most. Tap to watch. 
      164 +      </p>                                                    
      165 +      {!drivers && !failed && <Skeleton rows={2} label="Loadin
          +g drivers" />}                                                
      166 +      {failed && <p className="t-small px-4 pt-2 text-ink-3">C
          +ouldn&apos;t load drivers right now.</p>}                     
      167 +      {drivers && (                                           
      168 +        <ul className="mt-2 divide-y divide-rule border-y bord
          +er-rule bg-surface">                                          
      169 +          {withItems.map((s) => (                             
      170 +            <li key={s} className="px-4 py-3">                
      171 +              <p className="text-[15px] font-semibold">{s}</p>
      172 +              <div className="mt-1.5 flex flex-wrap gap-2">   
      173 +                {drivers[s]!.items.map((d) => {               
      174 +                  const on = (confirmed[s] ?? []).includes(d.i
          +d);                                                           
      175 +                  return (                                    
      176 +                    <button                                   
      177 +                      key={d.id}                              
      178 +                      type="button"                           
      179 +                      aria-pressed={on}                       
      180 +                      title={d.description}                   
      181 +                      onClick={() => toggle(s, d.id)}         
      182 +                      className={`hit h-8 rounded-full border 
          +px-3 text-[13px] ${on ? "border-ink bg-ink font-medium text-pa
          +per" : "border-rule text-ink-2"}`}                            
      183 +                    >                                         
      184 +                      {on ? "✓ " : ""}                        
      185 +                      {d.label}                               
      186 +                    </button>                                 
      187 +                  );                                          
      188 +                })}                                           
      189 +              </div>                                          
      190 +            </li>                                             
      191 +          ))}                                                 
      192 +          {without.length > 0 && (                            
      193 +            <li className="t-small px-4 py-3 text-ink-3">     
      194 +              {without.join(", ")}: drivers appear after resea
          +rch                                                           
      195 +              {without.some((s) => drivers[s]?.meta.reason ===
          + "no_transcripts") ? " (some publish no call transcripts)" : "
          +"}.                                                           
      196 +            </li>                                             
      197 +          )}                                                  
      198 +        </ul>                                                 
      199 +      )}                                                      
      200 +    </section>                                                
      201 +  );                                                          
      202 +}                                                             
      203 +                                                              
      204  function ImportSheet({ open, onClose, current, demo }: { open:
            boolean; onClose: () => void; current: LocalHolding[]; demo: 
           boolean }) {
      205    const [text, setText] = useState("");
      206    const [known, setKnown] = useState<Set<string> | null>(null)
           ;

⏺ Update(web/components/portfolio/PortfolioScreen.tsx)
  ⎿  Added 1 line, removed 1 line
      15  import { CATEGORY_LABEL, displayHeadline, istWhen } from "@/lib
          /format";
      16  import { effectiveWeights, parseHoldings } from "@/lib/holdings
          ";
      17  import { FALLBACK, isDemoPortfolio, read, useHydrated, useStore
          d, write, type LocalHolding } from "@/lib/store";
      18 -import type { Card } from "@/lib/types";                       
      18 +import type { Card, DriversSection } from "@/lib/types";       
      19  
      20  function latestAt(c: Card): string {
      21    return [...c.timeline.map((t) => t.at)].sort().at(-1) ?? c.as
          _of;

⏺ Retrying the drivers run now.

  Ran 2 shell commands (ctrl+o to expand)

⏺ Everything passes (337 backend tests, web typecheck and lint). Writing the
  DECISIONS entries while the drivers run works.

⏺ Bash(cd ~/Documents/finn && cat >> docs/DECISIONS.md <<'EOF'…)
  ⎿  - **Fallback:** if the API can't be reached, the 4 demo tickers fall b
     ack to their fixtures, labelled "Saved copy from 11 Nov 2026".
     - **Section states:** building + `not_built_yet` (red flags, exchange
     … +7 lines (ctrl+o to expand)
  ⎿  Updated docs/DECISIONS.md (+78 -0)
      444  - **Ingest**:
      445    - A Gemini content refusal (`promptFeedback.blockReason`) is
            recorded as "model refused" and not retried every 30 minutes.
      446    - JSON written to Postgres drops NUL characters. One filing'
           s NUL made every run's tagging step fail.
      447 +                                                              
      448 +## 2026-11-12 · Phase 4 frontend: plan amendments (product own
          +er)                                                           
      449 +- **Approved with amendments, 11 Nov evening:**               
      450 +  1. Push and verify the deployed site after the Brief and aft
          +er the Ledger, not only at the end.                           
      451 +  2. No empty tabs: Portfolio lists the holdings with their la
          +test Brief event; Rules has Connect Telegram and Reset; the Br
          +ief has a visible "Connect Telegram" entry.                   
      452 +  3. Drivers queue: read today's Flash-Lite count from `llm_ca
          +lls` first (failed attempts count), cap a run at 50 calls, and
          + skip it if fewer than 150 would stay free afterwards.        
      453 +  4. Strong models were out of quota until 13:30 IST: BuildPro
          +gress explains that and shows the ready sections meanwhile; a 
          +first-time build asks for one-tap confirmation.               
      454 +  5. Verify the landing iframe on the deployed site (no X-Fram
          +e-Options conflict).                                          
      455 +  6. Screenshots: 375 px light and dark for Brief, Research, L
          +edger and the provenance sheet; 1280 px for the landing only; 
          +the time saved goes into loading, error and stale states.     
      456 +- **Deviation:** the first push came after Research and the Le
          +dger rather than after the Brief, because amendment 2 ruled ou
          +t shipping an empty Research tab.                             
      457 +                                                              
      458 +## 2026-11-12 · Visual direction                              
      459 +- **Decision:** a printed financial page, not a dashboard.    
      460 +  - Ink on warm paper (`#F7F6F2` / `#0F0F0E`), hairline rules 
          +between full-bleed rows, no shadows, gradients or decorative c
          +olour.                                                        
      461 +  - Newsreader (serif) for what you read: titles, headlines, c
          +laims and quotes. Geist for what you scan. Tabular numerals ev
          +erywhere.                                                     
      462 +  - Colour only for signal: impact, verdicts, verification and
          + warnings. Moves stay ink, with ▲/▼.                          
      463 +  - Dark mode follows `prefers-color-scheme` through a media-q
          +uery variant, so there's no script and no flash.              
      464 +- **Symbols:** the spec's ✅ ❌ ↘ ↗ 🔇 / 🟢🔴🟡⚪ states are d
          +rawn as monochrome glyphs in signal colour (✓ ✕ ↘ ↗, a muted-s
          +peaker icon, a 6 px dot plus a word), not system emoji. Same s
          +tates; renders the same on every phone.                       
      465 +- **Headlines lead with meaning:** a results card's serif head
          +line is its code-written line ("Revenue +46.7% YoY; margin −10
          +4 bps"). A management card names the person and role from the 
          +filing. Other cards use the exchange subject without its "Cate
          +gory:" prefix, with the so-what underneath.                   
      466 +- **Tappable numbers:** a dotted underline (amber when unverif
          +ied). Every number opens a sheet with its document, page, verb
          +atim quote and `url#page=N`; computed figures show their formu
          +la and inputs. Ledger delivered figures show as printed ("119.
          +3 million", "7.54%").                                         
      467 +                                                              
      468 +## 2026-11-12 · First paint < 1 s while Render may be asleep  
      469 +- **Decision:** the app shell is prerendered static HTML on Ve
          +rcel's edge, and nothing on the critical path waits for Render
          +. Brief data comes in this order:                             
      470 +  1. This phone's last Brief for the same holdings, rules and 
          +window (localStorage, one Brief kept at a time: a 7-day Brief 
          +is about 1 MB uncompressed).                                  
      471 +  2. On a first visit with the demo portfolio: `GET /api/brief
          +/demo`, a route handler that replies with `Vercel-CDN-Cache-Co
          +ntrol: max-age=300, stale-while-revalidate=86400`. Only succes
          +sful answers are cached. Measured on the deployed site: `MISS`
          + then `HIT`, 55–160 ms from the edge.                         
      472 +  3. Nothing within 1.5 s: the saved showcase day, under a ban
          +ner. When live data lands, a "Show live" pill appears; content
          + never swaps under your thumb.                                
      473 +  4. Always: `POST /api/brief` with holdings, rules and queued
          + swipes. On failure the last copy stays, with "couldn't refres
          +h · retry".                                                   
      474 +- **Stale:** the feed is flagged when its last success is more
          + than 2 h older than the most recent 30-minute check slot that
          + should have run (08:30–22:00 IST, weekdays).                 
      475 +- **Freshness fix:** `data_as_of` now means the oldest NSE che
          +ck among the *requested* holdings. Before, two one-off test ti
          +ckers made every Brief look a day behind.                     
      476 +- **Alternatives:** a server-rendered Brief inside `use cache`
          + (a cold Render at build time stalls or fails the build); a sk
          +eleton until Render answers (fails the "populated in < 1 s" ba
          +r on a cold start).                                           
      477 +                                                              
      478 +## 2026-11-12 · Brief contract, est. time saved, season strip,
          + feedback                                                     
      479 +- **Contract:** `BriefRequest` / `BriefResponse` are Pydantic 
          +models exported to `types.ts`. The response adds:             
      480 +  - `hidden_items` (the newest 300; every one still opens its 
          +PDF);                                                         
      481 +  - `counts`;                                                 
      482 +  - `season`;                                                 
      483 +  - `rules`;                                                  
     … 41 more lines (ctrl+o to expand)

⏺ Now the screenshot pass, starting with the Brief at 375 px, light then dark.

  Called Claude_Browser (ctrl+o to expand)

⏺ Dark mode reads well. The Showcase toggle is off but its knob sits on the
  right in both themes. Inspecting it.

  Called Claude_Browser (ctrl+o to expand)

⏺ Bash(cd ~/Documents/finn/web && python3 - <<'EOF'
      p='components/brief/BriefScreen.tsx'…)
  ⎿  ok
  ⎿  Updated web/components/brief/BriefScreen.tsx (+1 -1)
      333            onClick={() => write("showcase", !showcase)}
      334            className={`relative h-6 w-10 rounded-full transitio
           n-colors ${showcase ? "bg-ink" : "bg-rule"}`}
      335          >
      336 -          <span className={`absolute top-0.5 size-5 rounded-fu
          -ll bg-surface shadow-sm transition-transform ${showcase ? "tra
          -nslate-x-[18px]" : "translate-x-0.5"}`} />                    
      336 +          <span className={`absolute left-0 top-0.5 size-5 rou
          +nded-full transition-transform ${showcase ? "translate-x-[18px
          +] bg-paper" : "translate-x-0.5 bg-ink-3"}`} />                
      337          </button>
      338        </label>
      339      </div>

  Called Claude_Browser (ctrl+o to expand)

⏺ The switch reads as off now. Toggling the showcase replay on to check that
  state.

  Called Claude_Browser (ctrl+o to expand)

⏺ The replay header is right, but the card list is empty. Inspecting the DOM.

  Called Claude_Browser (ctrl+o to expand)

⏺ The cards are there; the screenshot just beat the render. Re-shooting.

  Called Claude_Browser (ctrl+o to expand)

⏺ Showcase replay renders as designed, including RELIANCE's honest "Couldn't
  verify". Next, the error and stale states: I'll make the API unreachable in
  the page and age the cached data.

  Called Claude_Browser (ctrl+o to expand)

⏺ Background shell command didn't finish before the previous session ended
❯ continue                                                                      

⏺ The drivers run was cut off when the previous session ended. Checking what it
  finished before re-running it.

  Ran 1 shell command (ctrl+o to expand)

⏺ Only RELIANCE was saved, with 0 calls read and a quota stop, so the router
  refused the MAP call. Finding out why before re-running.

  Ran 1 shell command (ctrl+o to expand)

⏺ Gemini gave 503 "high demand" on all five tries, a transient outage rather
  than quota, so I'm fixing the mislabeled llm_quota and making the run stop on
  a busy model before re-running. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(sed -i '' 's/"note": "Drivers resume after the quota reset" if quota else
      "The model was busy; FINN retries on the next run",/"note": "Drivers
      resume after the…)
  ⎿  6 passed in 0.20s
  ⎿  Updated backend/finn/research/drivers_only.py (+1 -1)
      105          quota = stop_kind == "quota"
      106          d.drivers.meta = d.drivers.meta.model_copy(update={
      107              "status": "building" if quota else "unavailable", 
           "reason": "llm_quota" if quota else "llm_unavailable",
      108 -            "note": "Drivers resume after the quota reset" if 
          -quota else "The model was busy; FINN retries on the next run",
      108 +            "note": "Drivers resume after the quota reset" if 
          +quota else "Model busy; retried next run",                    
      109          })  # fmt: skip
      110      return DriversResult(symbol, d.drivers, len(calls), stoppe
           d)
      111  

  Ran 1 shell command (ctrl+o to expand)

⏺ While that runs: checking error and stale states with a second dev server
  whose API address is unreachable.

⏺ Bash(cd ~/Documents/finn && python3 - <<'EOF'
      import json…)
  ⎿  ok
  ⎿  Updated .claude/launch.json (+9 -0)
      27          "cd web && API_BASE_URL=https://finn-api-4ejm.onrender.
          com npm run dev -- --port 3001"
      28        ],
      29        "port": 3001
      30 +    },                                                         
      31 +    {                                                          
      32 +      "name": "web-no-api",                                    
      33 +      "runtimeExecutable": "bash",                             
      34 +      "runtimeArgs": [                                         
      35 +        "-c",                                                  
      36 +        "cd web && API_BASE_URL=http://127.0.0.1:9 npm run dev 
         +-- --port 3002"                                                
      37 +      ],                                                       
      38 +      "port": 3002                                             
      39      }
      40    ]
      41  }
  ⎿  Error: The dev server exited during startup (code 1). Fix the error in the 
     output below, then start the server again.

     Output:
     shell-init: error retrieving current directory: getcwd: cannot access 
     parent directories: Operation not permitted
     chdir: error retrieving current directory: getcwd: cannot access parent 
     directories: Operation not permitted

     > web@0.1.0 dev
     > next dev --port 3002

     ▲ Next.js 16.4.5 (Turbopack)
     … +13 lines (ctrl+o to expand)

⏺ Only one Next dev server can run per folder, so I'm swapping servers for this
  check.

  Called Claude_Browser 2 times, ran 1 shell command (ctrl+o to expand)
  ⎿  Error: [resize_window] Viewport set to 375x812 (mobile) on this tab (scaled
     down to fit if larger than the pane). Reset it with preset "desktop" as 
     soon as you finish testing; the desktop app also clears a size you set when
     your turn ends or the pane's width changes, so set it again if you still 
     need it. If the user wants to keep a phone or tablet size after your turn, 
     they can pick Mobile or Tablet in the pane's Viewport menu; a custom size 
     you simply set again next turn. Color scheme emulation set to light on this
     tab; it survives reloads until you set the other value or the pane 
     re-syncs the tab to the app theme.


     Tab Context:
     - Executed on tabId: seed
     - Available tabs:
       • tabId seed: "http://localhost:3003/" ("http://localhost:3003/")
     - Viewport: emulating 375x812 (you set this; reset it with preset "desktop"
     when you finish testing; the app also clears it when your turn ends or the
     pane's width changes)

     actions[1] (navigate) failed: navigation to http://localhost:3003 was 
     denied or failed (1 completed, 3 remaining)
  ⎿  Error: [computer:wait] waited 5s


     Tab Context:
     - Executed on tabId: seed
     - Available tabs:
       • tabId seed: "http://localhost:3003/brief" 
     ("http://localhost:3003/brief")
     - Viewport: emulating 375x812 (you set this; reset it with preset "desktop"
     when you finish testing; the app also clears it when your turn ends or the
     pane's width changes)

     actions[1] (navigate) failed: navigation to http://localhost:3003 was 
     denied or failed (1 completed, 3 remaining)
  ⎿  Error: [computer:wait] waited 8s


     Tab Context:
     - Executed on tabId: seed
     - Available tabs:
       • tabId seed: "http://localhost:3003/brief" 
     ("http://localhost:3003/brief")
     - Viewport: emulating 375x812 (you set this; reset it with preset "desktop"
     when you finish testing; the app also clears it when your turn ends or the
     pane's width changes)

     actions[1] (javascript_tool:javascript_exec) failed: javascript_tool 
     failed: SecurityError: Failed to read the 'localStorage' property from 
     'Window': Access is denied for this document. (1 completed, 2 remaining)

  Called Claude_Browser (ctrl+o to expand)

⏺ Still on the error-state check: the server actually listens on 3002, not the
  3003 the tool reported. Pointing the browser there.

  Called Claude_Browser (ctrl+o to expand)

⏺ Without an API, the Brief falls back to the saved showcase day within 1.5 s as
  designed, but the title still says "Last 7 days" and the banner keeps saying
  "while live data loads…" after the live request failed. I'm fixing both of
  those next. · summary

⏺ Bash(cd ~/Documents/finn/web && python3 - <<'EOF'
      p='components/brief/BriefScreen.tsx'…)
  ⎿  176:              ? `FINN's server isn't answering — showing the saved
      showcase day (${SHOWCASE_LABEL}). Retrying shortly.`
  ⎿  Updated web/components/brief/BriefScreen.tsx (+8 -2)
      129    const sinceIso = b.since;
      130    const title = showcase
      131      ? "Showcase replay"
      132 +    : b.source === "fallback"                                 
      133 +      ? "Saved showcase day"                                  
      134      : window_ === "since" && sinceIso
      135        ? "Since your last visit"
      136        : window_ === "custom" && customSince
     ...
      140            : window_ === "3d"
      141              ? "Last 3 days"
      142              : "Last 7 days";
      141 -  const sinceLabel = showcase && data?.showcase ? SHOWCASE_LAB
          -EL : window_ === "since" && sinceIso ? (isTodayIST(sinceIso) ?
          - istClock(sinceIso) : `${istDay(sinceIso)}, ${istClock(sinceIs
          -o)}`) : null;                                                 
      143 +  const sinceLabel = (showcase || b.source === "fallback") && 
          +data?.showcase ? SHOWCASE_LABEL : window_ === "since" && since
          +Iso ? (isTodayIST(sinceIso) ? istClock(sinceIso) : `${istDay(s
          +inceIso)}, ${istClock(sinceIso)}`) : null;                    
      144    const n = visible.length;
      145    const stale = data && !showcase && b.source !== "fallback" ?
            isStale(data.data_as_of) : false;
      146  
     ...
      170              ) : undefined
      171            }
      172          >
      171 -          {b.liveReady ? "Your live Brief is ready." : `Showin
          -g the saved showcase day (${SHOWCASE_LABEL}) while live data l
          -oads…`}                                                       
      173 +          {b.liveReady                                        
      174 +            ? "Your live Brief is ready."                     
      175 +            : b.error                                         
      176 +              ? `FINN's server isn't answering — showing the s
          +aved showcase day (${SHOWCASE_LABEL}). Retrying shortly.`     
      177 +              : `Showing the saved showcase day (${SHOWCASE_LA
          +BEL}) while live data loads…`}                                
      178          </Notice>
      179        )}
      180  

⏺ The banner promises a retry, so adding one: up to 3 automatic retries 20 s
  apart while the server is waking.

⏺ Bash(python3 - <<'EOF'
      p='components/brief/useBrief.ts'…)
  ⎿  Updated web/components/brief/useBrief.ts (+9 -1)
      55      fetchedAt: null,
      56    });
      57    const liveRef = useRef<BriefResponse | null>(null);
      58 +  const retries = useRef(0);                                   
      59  
      60    const since =
      61      opts.window === "since" ? (opts.visit?.previous ?? null) : 
          opts.window === "custom" ? opts.customSince : null;
     ...
      141        .then((resp) => {
      142          if (cancelled) return;
      143          liveRef.current = resp;
      144 +        retries.current = 0;                                  
      145          const at = new Date().toISOString();
      146          cacheBrief(cacheKey, { resp, at, sig: holdingsSignatur
           e(holdings, resp.rules) });
      147          if (sent.length) settleFeedback(resp.rules, sent.map((
           p) => p.at).sort().at(-1) ?? null);
     ...
      153        })
      154        .catch((e) => {
      155          if (cancelled || (e instanceof DOMException && e.name 
           === "AbortError")) return;
      154 -        setState((s) => ({ ...s, refreshing: false, slow: fals
          -e, error: e instanceof FetchError ? e : new FetchError(0, Stri
          -ng(e)) }));                                                   
      156 +        const err = e instanceof FetchError ? e : new FetchErr
          +or(0, String(e));                                             
      157 +        setState((s) => ({ ...s, refreshing: false, slow: fals
          +e, error: err }));                                            
      158 +        // Render's free tier may still be waking: retry a few
          + times on its own (20 s apart).                               
      159 +        if (err.waking && retries.current < 3) {              
      160 +          retries.current += 1;                               
      161 +          timers.push(setTimeout(() => !cancelled && setNonce(
          +(n) => n + 1), 20_000));                                      
      162 +        }                                                     
      163        });
      164      return () => {
      165        cancelled = true;

⏺ Next, the stale state: seeding an old cached Brief so the screen shows the
  stale copy with "couldn't refresh".

  Called Claude_Browser 2 times (ctrl+o to expand)

⏺ The stale state shows the last copy with its "couldn't refresh" warning. Next
  I'll test Research without an API: a demo ticker should fall back to its saved
  fixture, and another ticker should show an error. · summary

  Called Claude_Browser (ctrl+o to expand)

⏺ Both work: the saved copy is labelled for BAJFINANCE, and HAL gets a clear
  error with Try again. Now the scripted build (dev-only mock) to check the
  paused-for-quota state.

  Called Claude_Browser 2 times (ctrl+o to expand)

⏺ The quota pause reads clearly and points at the 8 ready sections. Switching
  back to the live-API server for the remaining screenshots.

  Called Claude_Browser 3 times (ctrl+o to expand)
⏺ Research home is good in both themes. Testing autocomplete, then the Ledger
  and provenance sheet in dark.

  Called Claude_Browser 2 times (ctrl+o to expand)

⏺ Autocomplete works on the real NSE list (Tata Motors' post-demerger symbols).
  Now the Ledger and its provenance sheet in dark.

  Called Claude_Browser (ctrl+o to expand)

⏺ The dossier is taking longer than usual. Checking the request.

  Called Claude_Browser, ran 1 shell command (ctrl+o to expand)

⏺ Render isn't answering at all (60 s timeouts). Checking whether it's waking or
  down.

  Ran 1 shell command (ctrl+o to expand)

⏺ Background command "Re-run drivers-only builds for holdings" completed (exit
code 0)

  Ran 1 shell command (ctrl+o to expand)

⏺ Drivers HAL and EICHERMOT are built, RELIANCE is partial, and ITC has no
  transcripts; the run halted on Gemini Flash-Lite 503 errors. Render is
  unresponsive while Vercel and the internet work, so I'm retrying it. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ Render's status page says all systems operational, so it's our service.
  Checking whether the connection even opens.

  Ran 1 shell command (ctrl+o to expand)

⏺ TCP connections to Render's IPs time out from this machine. Testing through
  Vercel to tell a local network problem from a down service.

  Ran 1 shell command (ctrl+o to expand)

⏺ The API responds fine through Vercel in 1.8 s, and render.com is unreachable
  from this machine, though the deployed app is unaffected. For local dev I'll
  point the server at Vercel's proxy instead. · summary

⏺ Bash(cd ~/Documents/finn && python3 - <<'EOF'
      import json…)
  ⎿  ok
  ⎿  Updated .claude/launch.json (+10 -1)
      24        "runtimeExecutable": "bash",
      25        "runtimeArgs": [
      26          "-c",
      27 -        "cd web && API_BASE_URL=https://finn-api-4ejm.onrender.
         -com npm run dev -- --port 3001"                                
      27 +        "cd web && API_BASE_URL=${FINN_API:-https://finn-api-4e
         +jm.onrender.com} npm run dev -- --port 3001"                   
      28        ],
      29        "port": 3001
      30      },
     ...
      36          "cd web && API_BASE_URL=http://127.0.0.1:9 npm run dev 
          -- --port 3002"
      37        ],
      38        "port": 3002
      39 +    },                                                         
      40 +    {                                                          
      41 +      "name": "web-via-vercel",                                
      42 +      "runtimeExecutable": "bash",                             
      43 +      "runtimeArgs": [                                         
      44 +        "-c",                                                  
      45 +        "cd web && API_BASE_URL=https://finn-tau-red.vercel.app
         +/api npm run dev -- --port 3001"                               
      46 +      ],                                                       
      47 +      "port": 3001                                             
      48      }
      49    ]
      50  }

  Called Claude_Browser 5 times (ctrl+o to expand)

⏺ Rendered now; the delay was dev-mode compilation. Taking the Ledger and
  provenance screenshots.

  Called Claude_Browser (ctrl+o to expand)

⏺ Two copy fixes from the Ledger: a "goalposts moved" verdict isn't decided from
  a delivered figure, and "1 decks" needs singular. Then I'll re-take the light
  sheet, which was captured mid-animation.

⏺ Bash(cd ~/Documents/finn/web && python3 - <<'EOF'
      p='components/ledger/Ledger.tsx'…)
  ⎿  1
  ⎿  Updated web/components/ledger/Ledger.tsx (+8 -2)
      120            </div>
      121          )}
      122          <p className="t-small mt-2 text-ink-3">
      123 -          {L.calls_read} calls{L.decks_read ? ` · ${L.decks_re
          -ad} decks` : ""} read                                         
      123 +          {L.calls_read} calls{L.decks_read ? ` · ${L.decks_re
          +ad} deck${L.decks_read === 1 ? "" : "s"}` : ""} read          
      124            {cred ? ` · ${cred.numeric_n} decided in code · ${cr
           ed.qualitative_n} judged by model` : ""}
      125          </p>
      126        </div>
     ...
      251            </p>
      252            <p className="t-small mt-0.5 text-ink-3">
      253              {p.verdict_by === "code"
      254 -              ? "Decided in code from the target and the deliv
          -ered figure."                                                 
      254 +              ? p.verdict === "goalposts_moved"               
      255 +                ? "Decided in code: a later call revised the t
          +arget unfavourably — that is the verdict even if the new targe
          +t is met."                                                    
      256 +                : p.verdict === "quietly_dropped"             
      257 +                  ? "Decided in code: no delivered figure, and
          + later calls don't mention it."                               
      258 +                  : p.verdict === "not_yet_due" || p.verdict =
          +== "cant_score"                                               
      259 +                    ? "Status set in code; it doesn't count to
          +ward credibility."                                            
      260 +                    : "Decided in code from the target and the
          + delivered figure."                                           
      261                : `Judged by ${p.verdict_model ?? "the model"} —
            it must quote a later call, which is checked.`}
      262            </p>
      263            {p.verdict_reason && (

  Called Claude_Browser (ctrl+o to expand)

⏺ The light provenance sheet reads cleanly. Re-taking it in dark.

  Called Claude_Browser (ctrl+o to expand)

⏺ The dark sheet looks washed out. Checking the computed colours.

  Called Claude_Browser 2 times (ctrl+o to expand)

⏺ The dark sheet is fine; the earlier shot was a mid-switch artifact. Committing
  the drivers work, the state fixes and the docs, then pushing.

  Ran 2 shell commands (ctrl+o to expand)

⏺ Pushed. Waiting for both deploys, checked through Vercel since this machine
  can't reach Render directly: the new drivers route has to answer.

  Ran 1 shell command (ctrl+o to expand)

⏺ Both deploys are live, with the new drivers route serving HAL and EICHERMOT
  through Vercel's proxy. I'm retrying the drivers run for the remaining
  holdings. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ While that runs: measuring first paint on the deployed Brief at phone size,
  with a cleared cache and then a warm one.

  Called Claude_Browser (ctrl+o to expand)

⏺ The first demo load on a cold edge took 4.1 s because each deploy empties
  Vercel's regional cache, so the first visitor pays Render's latency. I'm
  measuring a warm reload and then tightening the fallback. · summary

  Called Claude_Browser 2 times (ctrl+o to expand)
⏺ Paint timing isn't recorded in this pane, so I'm adding a performance.mark at
  first card render, along with a fallback that shows the showcase day after 0.9
  s and swaps in live data if it arrives first. · summary

⏺ Bash(cd ~/Documents/finn/web && python3 - <<'EOF'
      p='components/brief/useBrief.ts'…)
  ⎿  138:        }, 900),
  ⎿  Updated web/components/brief/BriefScreen.tsx (+5 -0)
      51    const dragged = useRef(false);
      52  
      53    const cards = data?.cards ?? [];
      54 +  useEffect(() => {                                            
      55 +    // For first-paint measurement (DECISIONS: first paint): wh
         +en cards first appear, and from which source.                  
      56 +    if (data && typeof performance !== "undefined" && !performa
         +nce.getEntriesByName("finn:brief-cards").length)               
      57 +      performance.mark("finn:brief-cards", { detail: b.source }
         +);                                                             
      58 +  }, [data, b.source]);                                        
      59    const visible = cards.filter((c) => c.card_type !== "inline_c
          hip" && !marks[c.id]);
      60    const chips = cards.filter((c) => c.card_type === "inline_chi
          p" && !marks[c.id]);
      61    const reviewedToday = useMemo(
  ⎿  Updated web/components/brief/useBrief.ts (+16 -3)
      56    });
      57    const liveRef = useRef<BriefResponse | null>(null);
      58    const retries = useRef(0);
      59 +  // Until the user touches or scrolls, a fallback can be repla
         +ced in place; after that, offer a pill instead.                
      60 +  const interacted = useRef(false);                            
      61 +  useEffect(() => {                                            
      62 +    const mark = () => (interacted.current = true);            
      63 +    window.addEventListener("pointerdown", mark, { once: true, 
         +passive: true });                                              
      64 +    window.addEventListener("scroll", mark, { once: true, passi
         +ve: true });                                                   
      65 +    return () => {                                             
      66 +      window.removeEventListener("pointerdown", mark);         
      67 +      window.removeEventListener("scroll", mark);              
      68 +    };                                                         
      69 +  }, []);                                                      
      70  
      71    const since =
      72      opts.window === "since" ? (opts.visit?.previous ?? null) : 
          opts.window === "custom" ? opts.customSince : null;
     ...
      114          .demoBrief(w, ctrl.signal)
      115          .then((resp) => {
      116            if (cancelled || liveRef.current) return;
      106 -          setState((s) => ({ ...s, data: resp, source: "edge",
          - liveReady: false }));                                        
      117 +          setState((s) =>                                     
      118 +            s.source === "fallback" && interacted.current ? s 
          +: { ...s, data: resp, source: "edge", liveReady: false },     
      119 +          );                                                  
      120          })
      121          .catch(() => {});
      122      }
     ...
      135                .catch(() => {});
      136              return s;
      137            });
      125 -        }, 1500),                                             
      138 +        }, 900),                                              
      139        );
      140      }
      141      timers.push(setTimeout(() => !cancelled && setState((s) =>
            ({ ...s, slow: s.refreshing })), 4000));
     ...
      159          cacheBrief(cacheKey, { resp, at, sig: holdingsSignatur
           e(holdings, resp.rules) });
      160          if (sent.length) settleFeedback(resp.rules, sent.map((
           p) => p.at).sort().at(-1) ?? null);
      161          setState((s) =>
      149 -          s.source === "fallback"                             
      162 +          s.source === "fallback" && interacted.current       
     … 3 more lines (ctrl+o to expand)

⏺ Bash(cd ~/Documents/finn && python3 - <<'EOF'
      p='docs/DECISIONS.md'…)
  ⎿  0936c0f First paint: showcase fallback at 0.9 s, replaced in place unt
     il the first touch; perf mark when cards appear
  ⎿  Updated docs/DECISIONS.md (+2 -1)
      469  - **Decision:** the app shell is prerendered static HTML on Ve
           rcel's edge, and nothing on the critical path waits for Render
           . Brief data comes in this order:
      470    1. This phone's last Brief for the same holdings, rules and 
           window (localStorage, one Brief kept at a time: a 7-day Brief 
           is about 1 MB uncompressed).
      471    2. On a first visit with the demo portfolio: `GET /api/brief
           /demo`, a route handler that replies with `Vercel-CDN-Cache-Co
           ntrol: max-age=300, stale-while-revalidate=86400`. Only succes
           sful answers are cached. Measured on the deployed site: `MISS`
            then `HIT`, 55–160 ms from the edge.
      472 -  3. Nothing within 1.5 s: the saved showcase day, under a ban
          -ner. When live data lands, a "Show live" pill appears; content
          - never swaps under your thumb.                                
      472 +  3. Nothing within 0.9 s: the saved showcase day, under a ban
          +ner. Live data replaces it in place if it lands before the fir
          +st touch or scroll; after that a "Show live" pill appears, so 
          +content never swaps under your thumb.                         
      473 +     - Why a fallback at all: Vercel's edge cache is per regio
          +n and is emptied by every deploy, so the first visitor in a re
          +gion after a deploy waits for Render. Measured: 4.1 s cold vs 
          +~0.1 s warm.                                                  
      474    4. Always: `POST /api/brief` with holdings, rules and queued
            swipes. On failure the last copy stays, with "couldn't refres
           h · retry".
      475  - **Stale:** the feed is flagged when its last success is more
            than 2 h older than the most recent 30-minute check slot that
            should have run (08:30–22:00 IST, weekdays).
      476  - **Freshness fix:** `data_as_of` now means the oldest NSE che
           ck among the *requested* holdings. Before, two one-off test ti
           ckers made every Brief look a day behind.

⏺ While Vercel deploys, adding the Phase 4 section to PLAN.md.

⏺ Bash(python3 - <<'EOF'
      p='docs/PLAN.md'…)
  ⎿  156:## Phase 4 — frontend (11–12 Nov 2026)
  ⎿  Updated docs/PLAN.md (+23 -0)
      153  - [ ] Summary refresh reuse: nightly/forced rebuilds re-run RE
           DUCE whenever any fact changes (market cap moves daily); reuse
            the stored summary unless the document set or ledger verdicts
            changed
      154  - [x] Frontend fixtures: validated INFY, BAJFINANCE, POLYCAB d
           ossiers in `web/public/fixtures/` (`python -m jobs.research ex
           port`; built locally against Supabase — rebuild on Render once
            §7 is set)
      155  
      156 +## Phase 4 — frontend (11–12 Nov 2026)                        
      157 +                                                              
      158 +Plan approved 11 Nov with six amendments (DECISIONS: "Phase 4 
          +frontend: plan amendments").                                  
      159 +                                                              
      160 +- [x] Brief contract: `BriefRequest`/`BriefResponse`, hidden i
          +tems, header counts + est. time saved, season strip, feedback 
          +in → rules out — `f7c253c`; freshness scoped to the requested 
          +holdings — `c5f3e95`                                          
      161 +- [x] Showcase replay frozen as a ranked Brief (`jobs.snapshot
          + --brief 2026-10-30` → `web/public/showcase/brief.json`) — `f7
          +c253c`                                                        
      162 +- [x] Design system, shell (tab bar, Ask bar, sheet, undo toas
          +t, states), provenance sheet, restyled cards — `ea9c512`      
      163 +- [x] Brief: cache-first, window chips, season strip + scorebo
          +ard, swipe 40% + scope + 5 s undo, Reviewed today, hidden draw
          +er, Why #N, caught-up, Connect Telegram entry — `76061bc`     
      164 +- [x] Research: NSE autocomplete, dossier sections with their 
          +own status, one-tap build confirmation, BuildProgress with the
          + quota pause, fixture fallback — `76061bc`                    
      165 +- [x] Promise Ledger: tally, % only from n ≥ 5, filters, origi
          +nal → revised, provenance on every verdict and number — `76061
          +bc`, copy fixes `3e5114d`                                     
      166 +- [x] Portfolio (holdings + latest Brief event + paste/CSV imp
          +ort) and Rules (adjustments with Reset, Telegram connect, aler
          +t rules) — `76061bc`                                          
      167 +- [x] QR landing with live phone iframe (no X-Frame-Options; v
          +erified on the deployed site), 3-step tour — `76061bc`, `f42e8
          +68`                                                           
      168 +- [x] Drivers-only builds (Flash-Lite only, 50-call cap, 150 h
          +eadroom) + `GET /research/drivers` + "What you're watching" — 
          +`536fa91`                                                     
      169 +- [x] Loading / error / stale states checked with an unreachab
          +le API; auto-retry while waking; first-paint fallback at 0.9 s
          + — `3e5114d`, `0936c0f`                                       
      170 +- [ ] **Drivers for the rest of the holdings.** First runs got
          + HAL and EICHERMOT (plus RELIANCE partly) before Gemini Flash-
          +Lite returned 503 "high demand". Re-run `python -m jobs.resear
          +ch drivers`: it skips holdings that already have drivers and c
          +hecks headroom itself. ITC publishes no transcripts on screene
          +r.                                                            
      171 +- [ ] Confirmed drivers → ×1.5 Level-1 boost in `/brief` (toda
          +y `brief()` never passes drivers to `score()`); needs an event
          +→driver match rule                                            
      172 +- [ ] `POST /portfolio`: last close, day change, 1-month spark
          +line, status dot (rule in DECISIONS), upcoming calendar; Portf
          +olio scoreboard                                               
      173 +- [ ] Rules editing (thresholds, categories, budget, quiet hou
          +rs, snoozes) synced via `PUT /subscriptions/me` when Telegram 
          +is connected; push rule changes to a connected Telegram copy  
      174 +- [ ] PWA: manifest, icons, offline cache of the latest Brief 
          +(web push stays below the cut)                                
      175 +- [ ] Wire `/ask` when Friday's backend lands: `setAskContext`
          + chips → `POST /research/{sym}/ask` → answer sheet; enable fre
          +e text                                                        
      176 +- [ ] Real-phone checks the browser pane can't do: iOS swipe v
          +s scroll, haptics on Android, first paint on 4G               
      177 +- [ ] Brief payload: a 7-day Brief is ~1 MB uncompressed (resu
          +lts figures carry full provenance trees); brotli makes the tra
          +nsfer small, but consider trimming duplicated `inputs` server-
          +side                                                          
      178 +                                                              
      179  ## Phase 5
      180  
      181  - [ ] **Held-out classification eval (~20 filings, never used 
           for tuning).** The current 60-filing set is a *dev* set: the r
           ules were written from the same Aug–Nov 2026 filings, so its s
           core is optimistic.

⏺ Measuring first paint on the new deploy once it's live.

  Ran 1 shell command (ctrl+o to expand)

⏺ The deploy check is still running after 10 minutes. Checking Vercel's
  deployment status on GitHub directly.

  Ran 2 shell commands (ctrl+o to expand)

⏺ Vercel reports 0936c0f deployed successfully; my check script was grepping the
  wrong chunk paths. Stopping it and measuring in the browser.

⏺ Stop Task
  ⎿  Error: Task bw57cqw6m is not running (status: completed)

  Called Claude_Browser (ctrl+o to expand)

⏺ Background command "Wait until the new build is live on Vercel" completed
(exit code 0)

⏺ Cached visits paint cards in 438 ms, while a cold first visit took 1.8 s
  because the showcase file waited on a 0.9 s timer. I'm prefetching it at load,
  and the first navigation hit a Vercel 403 checkpoint that cleared on its own,
  probably from my scripted traffic. · summary

⏺ Bash(cd ~/Documents/finn/web && python3 - <<'EOF'
      p='components/brief/useBrief.ts'…)
  ⎿  8781c2b Prefetch the saved showcase day at load so the cold-edge fallb
     ack paints at ~0.9 s; PLAN: Phase 4 items
  ⎿  Updated web/components/brief/useBrief.ts (+5 -10)
      121          .catch(() => {});
      122      }
      123      if (!usable) {
      124 +      // Fetch the saved day at once (static, on the CDN) so t
          +he fallback costs no extra round trip at 0.9 s.               
      125 +      const fallback = api.showcase().catch(() => null);      
      126        timers.push(
      127          setTimeout(() => {
      128            if (cancelled || liveRef.current) return;
      127 -          setState((s) => {                                   
      128 -            if (s.data) return s;                             
      129 -            api                                               
      130 -              .showcase()                                     
      131 -              .then((resp) => {                               
      132 -                if (cancelled || liveRef.current) return;     
      133 -                setState((s2) => (s2.data ? s2 : { ...s2, data
          -: resp, source: "fallback" }));                               
      134 -              })                                              
      135 -              .catch(() => {});                               
      136 -            return s;                                         
      129 +          fallback.then((resp) => {                           
      130 +            if (!resp || cancelled || liveRef.current) return;
      131 +            setState((s2) => (s2.data ? s2 : { ...s2, data: re
          +sp, source: "fallback" }));                                   
      132            });
      133          }, 900),
      134        );

  Called Claude_Browser, ran 1 shell command (ctrl+o to expand)

⏺ The fallback paints at 1.35 s, while the saved day was ready at 0.44 s but
  waited on a 0.9 s timer that starts after hydration. I'm cutting that wait to
  0.4 s so cards appear under 1 s either way. · summary

⏺ Bash(sed -i '' 's/        }, 900),/        }, 400),/; s/so the fallback costs
      no extra round trip at 0.9 s./so the fallback costs no extra round trip
      (shown after 0.…)
  ⎿  1
     fd544c4 First paint: show the prefetched saved day 0.4 s after hydrati
     on when the edge is cold
  ⎿  Updated docs/DECISIONS.md (+1 -1)
      469  - **Decision:** the app shell is prerendered static HTML on Ve
           rcel's edge, and nothing on the critical path waits for Render
           . Brief data comes in this order:
      470    1. This phone's last Brief for the same holdings, rules and 
           window (localStorage, one Brief kept at a time: a 7-day Brief 
           is about 1 MB uncompressed).
      471    2. On a first visit with the demo portfolio: `GET /api/brief
           /demo`, a route handler that replies with `Vercel-CDN-Cache-Co
           ntrol: max-age=300, stale-while-revalidate=86400`. Only succes
           sful answers are cached. Measured on the deployed site: `MISS`
            then `HIT`, 55–160 ms from the edge.
      472 -  3. Nothing within 0.9 s: the saved showcase day, under a ban
          -ner. Live data replaces it in place if it lands before the fir
          -st touch or scroll; after that a "Show live" pill appears, so 
          -content never swaps under your thumb.                         
      472 +  3. Nothing within 0.4 s of hydration: the saved showcase day
          + (prefetched at load), under a banner. Live data replaces it i
          +n place if it lands before the first touch or scroll; after th
          +at a "Show live" pill appears, so content never swaps under yo
          +ur thumb.                                                     
      473       - Why a fallback at all: Vercel's edge cache is per regio
           n and is emptied by every deploy, so the first visitor in a re
           gion after a deploy waits for Render. Measured: 4.1 s cold vs 
           ~0.1 s warm.
      474    4. Always: `POST /api/brief` with holdings, rules and queued
            swipes. On failure the last copy stays, with "couldn't refres
           h · retry".
      475  - **Stale:** the feed is flagged when its last success is more
            than 2 h older than the most recent 30-minute check slot that
            should have run (08:30–22:00 IST, weekdays).
  ⎿  Updated web/components/brief/useBrief.ts (+2 -2)
      121          .catch(() => {});
      122      }
      123      if (!usable) {
      124 -      // Fetch the saved day at once (static, on the CDN) so t
          -he fallback costs no extra round trip at 0.9 s.               
      124 +      // Fetch the saved day at once (static, on the CDN) so t
          +he fallback costs no extra round trip (shown after 0.4 s; a wa
          +rm edge answers in ~0.15 s).                                  
      125        const fallback = api.showcase().catch(() => null);
      126        timers.push(
      127          setTimeout(() => {
     ...
      130              if (!resp || cancelled || liveRef.current) return;
      131              setState((s2) => (s2.data ? s2 : { ...s2, data: re
           sp, source: "fallback" }));
      132            });
      133 -        }, 900),                                              
      133 +        }, 400),                                              
      134        );
      135      }
      136      timers.push(setTimeout(() => !cancelled && setState((s) =>
            ({ ...s, slow: s.refreshing })), 4000));

  Ran 2 shell commands (ctrl+o to expand)

⏺ Background command "Wait for the Vercel deployment" completed (exit code 0)

  Called Claude_Browser (ctrl+o to expand)

⏺ The first visit on a cold edge shows cards at 0.81 s, which are then replaced
  by the live Brief, while repeat visits load from cache in 0.44 s. I'm checking
  the 1280 px landing page on the deployed site last. · summary

  Called Claude_Browser (ctrl+o to expand)

⏺ The landing works on the deployed site. One tweak: on shorter laptop screens
  the 812 px phone frame overflows, so I'm capping its height to the viewport.

⏺ Bash(sed -i '' 's/className="relative h-\[812px\] w-\[390px\]
      rounded-\[54px\]/className="relative h-[min(812px,calc(100dvh-110px))]
      min-h-[560px] w-[390px] rounded-…)
  ⎿  1
     8b6aba2 Landing: phone frame fits laptop-height viewports
  ⎿  Updated web/components/landing/Landing.tsx (+1 -1)
      47          </div>
      48        </section>
      49        <section aria-label="Live preview" className="shrink-0">
      50 -        <div className="relative h-[812px] w-[390px] rounded-[5
         -4px] border border-rule bg-ink p-3 shadow-[0_30px_80px_-30px_rg
         -ba(0,0,0,0.35)]">                                              
      50 +        <div className="relative h-[min(812px,calc(100dvh-110px
         +))] min-h-[560px] w-[390px] rounded-[54px] border border-rule b
         +g-ink p-3 shadow-[0_30px_80px_-30px_rgba(0,0,0,0.35)]">        
      51            <div className="absolute left-1/2 top-5 z-10 h-[26px]
           w-[110px] -translate-x-1/2 rounded-full bg-ink" aria-hidden />
      52            <iframe
      53              src="/brief"

⏺ Checking how the second drivers run went.

  Ran 1 shell command (ctrl+o to expand)

⏺ Drivers now exist for 13 of 18 holdings (IDEA is presumably still running).
  Confirming in the call log that the drivers runs made no strong-model calls.

  Ran 1 shell command (ctrl+o to expand)

⏺ No strong-model calls were made; the 73 drivers-mode calls all went to
  Flash-Lite, with 168 of 500 used today. I'm changing the in-run budget to
  count failed 503 retries as well, since it only counted successful calls
  before. · summary

⏺ Bash(python3 - <<'EOF'
      p='finn/research/drivers_only.py'…)
  ⎿  E501 Line too long (123 > 120)
        --> jobs/research.py:99:121
         |
     … +11 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/research/drivers_only.py (+9 -5)
      33  
      34  
      35  class CheapOnly:
      36 -    """Router wrapper for drivers-only builds: cheap tier only,
         - and at most `budget` uncached calls."""                       
      36 +    """Router wrapper for drivers-only builds: cheap tier only,
         + and at most `budget` model attempts. Attempts are             
      37 +    counted from the call log when `used` is given (failed atte
         +mpts count against quota), else from router stats."""          
      38  
      38 -    def __init__(self, inner, budget: int):                    
      39 +    def __init__(self, inner, budget: int, used=None):         
      40          self.inner, self.budget, self.spent = inner, budget, 0
      41          self.stats = inner.stats
      42 +        self._used = used                                      
      43 +        self._start = used() if used else 0                    
      44  
      45      def run(self, tier, req):
      46          if tier != "cheap":
     ...
      48          if self.spent >= self.budget:
      49              raise LLMUnavailable("drivers run budget used", kin
          d="quota")
      50          before = self.inner.stats.calls
      48 -        res = self.inner.run(tier, req)                        
      49 -        self.spent += self.inner.stats.calls - before          
      50 -        return res                                             
      51 +        try:                                                   
      52 +            return self.inner.run(tier, req)                   
      53 +        finally:                                               
      54 +            self.spent = (self._used() - self._start) if self._
         +used else self.spent + self.inner.stats.calls - before         
      55  
      56  
      57  @dataclass
  ⎿  Updated backend/jobs/research.py (+3 -1)
       96      print("symbols:", ", ".join(syms) or "none")
       97      if dry_run or not syms:
       98          return
       99 -    router = dv.CheapOnly(Router.default(PostgresLLMLog(conn))
          -, budget)                                                     
       99 +    router = dv.CheapOnly(                                    
      100 +        Router.default(PostgresLLMLog(conn)), budget, used=lam
          +bda: dv.flash_lite_used_today(conn, model)                    
      101 +    )                                                         
      102      for sym in syms:
      103          r = dv.build_drivers(conn, sym, router)
      104          dv.save(conn, r)
  ⎿  Updated backend/tests/test_drivers_only.py (+21 -0)
      48  def test_plan_budget_keeps_150_free(used, budget):
      49      # 500/day free: a 50-call run is allowed only if ≥150 stay 
          free afterwards (used ≤ 300).
      50      assert dv.plan_budget(used) == budget
      51 +                                                               
      52 +                                                               
      53 +def test_failed_attempts_count_against_the_budget():           
      54 +    from finn.llm import LLMUnavailable                        
      55 +                                                               
      56 +    log = {"n": 0}                                             
      57 +                                                               
      58 +    class Failing(FakeRouter):                                 
      59 +        def run(self, tier, req):                              
      60 +            log["n"] += 5  # five logged attempts, all failed  
      61 +            raise LLMUnavailable("busy")                       
      62 +                                                               
      63 +    r = dv.CheapOnly(Failing(), budget=8, used=lambda: log["n"]
         +)                                                              
      64 +    with pytest.raises(LLMUnavailable):                        
      65 +        r.run("cheap", Req())                                  
      66 +    assert r.spent == 5                                        
      67 +    with pytest.raises(LLMUnavailable):                        
      68 +        r.run("cheap", Req())                                  
      69 +    assert r.spent == 10                                       
      70 +    with pytest.raises(LLMUnavailable, match="budget"):        
      71 +        r.run("cheap", Req())                                  
  Ran 1 shell command (ctrl+o to expand)

⏺ Background command "Re-run drivers for the remaining holdings" completed (exit
code 0)

  Ran 1 shell command (ctrl+o to expand)

⏺ Drivers are live for 16 of 18 holdings; ITC has no transcripts on screener,
  and IDEA's (plus two of RELIANCE's) overflow the existing 16K output limit.
  Next I'll update PLAN and check Portfolio on the deployed site. · summary

⏺ Bash(python3 - <<'EOF'
      p='docs/PLAN.md'…)
  ⎿  de96be4 PLAN: drivers served for 16 of 18 holdings; MAP truncation fol
     low-up
  ⎿  Updated docs/PLAN.md (+2 -1)
      167  - [x] QR landing with live phone iframe (no X-Frame-Options; v
           erified on the deployed site), 3-step tour — `76061bc`, `f42e8
           68`
      168  - [x] Drivers-only builds (Flash-Lite only, 50-call cap, 150 h
           eadroom) + `GET /research/drivers` + "What you're watching" — 
           `536fa91`
      169  - [x] Loading / error / stale states checked with an unreachab
           le API; auto-retry while waking; first-paint fallback at 0.9 s
            — `3e5114d`, `0936c0f`
      170 -- [ ] **Drivers for the rest of the holdings.** First runs got
          - HAL and EICHERMOT (plus RELIANCE partly) before Gemini Flash-
          -Lite returned 503 "high demand". Re-run `python -m jobs.resear
          -ch drivers`: it skips holdings that already have drivers and c
          -hecks headroom itself. ITC publishes no transcripts on screene
          -r.                                                            
      170 +- [x] Drivers for the holdings: 16 of 18 served (3 drivers eac
          +h; RELIANCE 1). 0 strong calls; 73 Flash-Lite attempts across 
          +three runs (36 were Gemini 503 retries); budget now counts fai
          +led attempts — `536fa91`, `62d8029`                           
      171 +- [ ] MAP output truncates at 16K tokens on very long transcri
          +pts (IDEA, 2 of 3 RELIANCE calls): split the transcript or rai
          +se the output cap for MAP. ITC publishes no transcripts on scr
          +eener (stays "drivers appear after research").                
      172  - [ ] Confirmed drivers → ×1.5 Level-1 boost in `/brief` (toda
           y `brief()` never passes drivers to `score()`); needs an event
           →driver match rule
      173  - [ ] `POST /portfolio`: last close, day change, 1-month spark
           line, status dot (rule in DECISIONS), upcoming calendar; Portf
           olio scoreboard
      174  - [ ] Rules editing (thresholds, categories, budget, quiet hou
           rs, snoozes) synced via `PUT /subscriptions/me` when Telegram 
           is connected; push rule changes to a connected Telegram copy

  Called Claude_Browser, ccd_turn 3 times (ctrl+o to expand)

⏺ Phase 4 is live at https://finn-tau-red.vercel.app with all P0 screens; P1 is
  partly done (see "Moved to Friday"). The visual direction is exactly as
  approved. Backend tests pass (338), and the web app typechecks, lints and
  builds with every route prerendered. I haven't tried it on a real phone, so
  iOS swipe-versus-scroll, Android haptics and 4G load speed are still
  unchecked.

  What's on the deployed site
  - Brief:
    - Header shows the window, counts, "est. N min saved" (tap ⓘ for the
      formula) and the data time.
    - Window chips, the Q2 FY27 strip with a per-holding scoreboard, ranked
      cards of every type, and "Why #N".
    - Swipe commits past 40% and springs back otherwise. "Not useful" asks for a
      scope, then gives a 5-second undo; the weight change happens in Python
      only after the undo window.
    - Also: Reviewed today, the hidden drawer (every filing opens), the
      caught-up state, a Connect Telegram entry, and the 3-step tour.
  - Research: autocomplete over all 2,645 NSE companies. Each dossier section
    shows its own status; red flags and exchange data say "Coming soon". A
    first-time build needs a one-tap confirm, and the progress view says plainly
    when the AI quota is paused and which sections are already readable. I
    tested that progress view with a scripted job and started no real builds.
  - Promise Ledger: "4 of 6 kept · 5 not yet due · next test: FY27 results",
    with the % only from 5 promises up. Revised targets show the old one struck
    through. Every verdict and number opens both quotes with "Open p.N" links to
    the PDF page.
  - Landing: desktop shows a live phone preview plus a QR code. No
    X-Frame-Options header is set, and I confirmed the preview loads on the
    deployed site.
  - Portfolio: holdings with their latest event, paste/CSV import, and "What
    you're watching" with one-tap confirm.
  - Rules: your adjustments with Reset, Telegram connect using the DECISIONS
    privacy wording, and the current alert rules.

  Speed and failure states (measured on the deployed site)
  - Repeat visit: cards appear at 0.44 s from the phone's cache.
  - First visit after a deploy: cards appear at 0.81 s. Every deploy empties
    Vercel's cache, so the live Brief took 3.9 s; the saved 30 Oct day shows
    under a clear label in the meantime and is swapped for the live one if you
    haven't touched the screen yet.
  - With the API unreachable: the saved day shows under a banner and the app
    retries on its own. Old data is flagged "filings may be behind". The 4 ready
    companies show labelled saved copies; any other ticker shows an error with
    Try again.

  Drivers: live for 16 of 18 holdings, with zero strong-model calls. The run
  counts today's Flash-Lite usage first, failed attempts included, and caps
  itself at 50 calls only if 150 stay free.
  - ITC publishes no call transcripts on screener.
  - IDEA's transcripts are too long for the extraction model's output limit, and
    the same hit 2 of RELIANCE's 3 calls, so RELIANCE has only one driver.
    Fixing that is in PLAN.md.

  Changes from the plan, and things to know
  - The first push came after Research and the Ledger rather than right after
    the Brief, because amendment 2 ruled out shipping an empty Research tab.
  - I fixed a backend bug: two one-off test tickers made every Brief claim
    filings were a day behind.
  - This machine can't currently reach Render at all; render.com itself also
    times out from here. Through Vercel the API works normally. So I confirmed
    the backend deploy by its new endpoint answering through Vercel, not with
    the usual /version check.
  - One deployed page load briefly hit a Vercel "Security Checkpoint", probably
    triggered by my scripted traffic. If an evaluator ever sees it, it's
    Vercel's bot protection setting in the dashboard.

  Moved to Friday (in PLAN.md): the ranking boost for confirmed drivers,
  prices/sparklines/calendar on Portfolio, editable alert rules, the
  installable-app basics, and wiring Ask. All choices are recorded in
  DECISIONS.md.

❯ Bug found on my phone (Android Chrome): on a results card, tapping a figure → 
  provenance sheet → "Open" opens the raw XBRL XML on                           
  nsearchives.nseindia.com, a wall of XML tags. An investor can't read that.    
  Every "Open" link in the app must land on a human-readable document, at the   
  right page where possible.                                                    
                                                                                
  Order for the primary "Open" link on a figure:                                
  1. Results figures: the results PDF filed on the exchange (the                
  outcome/financial-results announcement in that event's thread), at the page   
  with the results table (url#page=N). Find the page in code by searching the   
  PDF text for the statement's line items ("Revenue from operations", "Total    
  income", …), matching consolidated vs standalone. This runs where NSE is      
  reachable (GitHub Actions), never on Render.                                  
  2. If no results PDF or no page is found: NSE's iXBRL (HTML) view of the same 
  filing. integrated-filing-results returns an ixbrl link next to xbrl          
  (DATA_SOURCES.md f).                                                          
  3. Raw XBRL XML: only a small secondary "Raw XBRL (machine-readable)" link,   
  kept for auditability.                                                        
  4. Screener cross-check: link to the screener company page's quarterly        
  section.                                                                      
                                                                                
  Provenance sheet:                                                             
  - Group input sources by document: one row per document with one Open button, 
  and the figures / XBRL element names it supplied listed underneath. Today     
  the same XBRL file appears once per input.                                    
  - Figures never wrap mid-value ("₹159 Cr" broke across two lines): nowrap on  
  figures, let the label column wrap.                                           
  - The button label says what opens and shows the page number: "Results PDF ·  
  p.3", "iXBRL view", "Raw XBRL". Mobile PDF viewers often ignore #page, so the 
  page number must be visible.                                                  
                                                                                
  Also:                                                                         
  - Audit every Open/source link in the app (results, management, price/volume  
  explanation, one-liners, chips, hidden drawer, ledger statements and deck     
  figures, screener). List where each points now and fix any that land on an    
  unreadable file.                                                              
  - Store whatever new URLs and pages are needed (migration if required), and   
  backfill existing results cards through a dispatched GitHub Actions run,      
  since Render can't reach NSE. Give me the run id.                             
  - Tests for the link-choice order and the page finder, using a saved PDF      
  fixture.                                                                      
  - Deploy, then on the deployed site at 375 px open figures on 3 different     
  results cards and confirm each Open lands on a readable PDF page with the     
  number on that page. Screenshot them.                                         
  - Don't spend strong-model calls. Record it in DECISIONS.md and tick it in    
  PLAN.md.                                                                      
                                                                                
  I'm away, so don't ask questions unless something needs a dashboard click or  
  can't be undone. End with a short summary: what each link type opens now, and 
  the commit hashes.                                                            

⏺ Starting with how results figures get their citations, where the results PDF
  and iXBRL links live, and how I can dispatch an Actions run from here.

  Listed 1 directory, called ccd_turn (ctrl+o to expand)

⏺ No gh CLI here. Checking which credentials exist locally (key names only) and
  how results citations are built.

  Ran 1 shell command (ctrl+o to expand)

⏺ The backfill workflow will also trigger on pushes to a request file, since git
  pushes authenticate through the keychain and I'd rather not extract that
  token. Next I'm working on the results code. · summary

  Ran 2 shell commands (ctrl+o to expand)

⏺ Results figures are cited directly from the XBRL XML at compute.py:110, but
  NSE's ixbrl link isn't stored anywhere. I'm checking the results_filings
  columns and how cards are rebuilt next. · summary

  Ran 3 shell commands (ctrl+o to expand)

⏺ NSE's ixbrl link is an HTML page and the integrated filing list has no PDF, so
  the results PDF must come from the event thread's outcome announcement. Next
  I'm auditing every stored link across cards, filings and dossiers by kind,
  host and file type. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ The audit found 1,239 results figures and 22 impact reasons that open raw XBRL
  XML, which is the bug you hit, plus 45 board-meeting filings with only an
  XBRL link. I'm checking what the stored board-meeting rows contain next. 
  · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ Board-meeting filings keep NSE's ixbrl HTML link in raw, so those 45 can open
  a readable page without migration. Next I'm moving on to the results card
  builder, where the PDF page lookup and link rewrite will go. · summary

  Searched for 2 patterns, ran 1 shell command (ctrl+o to expand)

⏺ I'm adding a scoring page finder and a pure link-rewrite module next to the
  existing find_statement, both testable offline, and then I'll read the fetch
  step that backfills the ixbrl links. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ The citation design is settled: three optional fields, plus a small table for
  the results PDF pages and ixbrl_url on results_filings. I'm writing the
  backend now. · summary

  Called ccd_turn, ran 1 shell command (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/models/common.py'…)
  ⎿  ok
  ⎿  Created backend/db/migrations/0006_readable_links.sql (+17 -0)
       1 +-- Human-readable links for results figures (DECISIONS: readabl
         +e Open links).                                                 
       2 +-- NSE's integrated-filing list gives an iXBRL (HTML) view next
         + to each raw XBRL instance.                                    
       3 +alter table public.results_filings add column if not exists ixb
         +rl_url text;                                                   
       4 +                                                               
       5 +-- The page of a results PDF that holds the statement for a bas
         +is, found in code from the PDF text (Actions only:             
       6 +-- NSE archives are blocked from Render). page null = looked, n
         +ot found (note says why).                                      
       7 +create table if not exists public.results_pdf_pages (          
       8 +  filing_id      text        not null,                         
       9 +  basis          text        not null check (basis in ('consoli
         +dated', 'standalone')),                                        
      10 +  url            text        not null,                         
      11 +  page           int,                                          
      12 +  value_on_page  boolean     not null default false,           
      13 +  note           text,                                         
      14 +  checked_at     timestamptz not null default now(),           
      15 +  primary key (filing_id, basis)                               
      16 +);                                                             
      17 +alter table public.results_pdf_pages enable row level security;
  ⎿  Updated backend/finn/models/common.py (+10 -1)
      51      """Where a number or claim came from. Every Figure/Claim th
          at is not `not_found` carries one."""
      52  
      53      source_type: SourceType
      54 -    url: str = Field(min_length=1, description="Direct link to 
         -the document (exchange PDF, XBRL, etc.)")                      
      54 +    url: str = Field(                                          
      55 +        min_length=1,                                          
      56 +        description="The human-readable document to open (resul
         +ts PDF, iXBRL view, filing PDF, page); `source_type` "         
      57 +        "says where the value was read, which may be a machine 
         +format kept in `raw_url`",                                     
      58 +    )                                                          
      59 +    doc_kind: Literal["results_pdf", "pdf", "ixbrl", "raw_xbrl"
         +, "screener", "web", "zip"] | None = Field(                    
      60 +        None, description="What `url` opens — drives the Open b
         +utton's label ('Results PDF · p.3', 'iXBRL view')"             
      61 +    )                                                          
      62 +    raw_url: str | None = Field(None, description="Machine-read
         +able original (raw XBRL), offered as a secondary link")        
      63 +    check_url: str | None = Field(None, description="Independen
         +t cross-check, e.g. screener's quarterly table")               
      64      title: str | None = Field(None, description="Human title, e
          .g. 'Q2 FY27 earnings call transcript'")
      65      exchange: Literal["NSE", "BSE"] | None = None
      66      page: int | None = Field(None, ge=1, description="1-based P
          DF page")

⏺ Now the page finder and link rewriting, as pure functions in
  finn/extraction/results/links.py.

⏺ Write(backend/finn/extraction/results/links.py)
  ⎿  Wrote 197 lines to backend/finn/extraction/results/links.py
      1 """Human-readable links for results figures (DECISIONS: readable 
        Open links).
      2 
      3 Results numbers are *read* from NSE's XBRL instances, but an XBRL
         file is a wall of tags. A figure's Open link
      4 therefore points, in this order, to:
      5   1. the results PDF filed on the exchange (the outcome announcem
        ent in the card's event thread), at the page
      6      holding the statement for the figure's basis — found here in
         code from the PDF text;
     … +191 lines (ctrl+o to expand)

⏺ Next I'm applying the same readable-first rule to every filing link, so the
  PDF attachment comes first, then NSE's iXBRL page, then raw XBRL marked as
  such, and invalid - links get dropped. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(head -20 finn/citations.py | grep -n "import" ; python3 - <<'EOF'
      import re…)
  ⎿  7:from __future__ import annotations
     9:import io
     10:import logging
     … +26 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/cards/brief.py (+3 -2)
      20      "id, key, symbol, category, title, period, started_at, upda
          ted_at, timeline, figures, impact, impact_reason, "
      21      "driver_ids, so_what, detail, detail_at, refreshed_at"
      22  )
      23 -FILING_COLS = "id, exchange, symbol, filed_at, subject, attachm
         -ent_url, xbrl_url, fetched_at"                                 
      23 +FILING_COLS = "id, exchange, symbol, filed_at, subject, attachm
         +ent_url, xbrl_url, raw->>'ixbrl' as ixbrl_url, fetched_at"     
      24  
      25  
      26  def load_events(conn, symbols: list[str], since: datetime | Non
          e, limit: int = 400) -> list[dict]:
     ...
      63  def hidden_filings(conn, symbols: list[str], since: datetime | 
          None, until: datetime | None = None) -> list[dict]:
      64      """Hidden drawer: routine filings (grouped by hidden_reason
          ), investor meetings and unclassified, newest first."""
      65      q = (
      66 -        f"select id, symbol, subject, filed_at, coalesce(attach
         -ment_url, xbrl_url) as url, {HIDDEN_GROUP} as grp "            
      66 +        "select id, symbol, subject, filed_at, coalesce(nullif(
         +nullif(attachment_url, '-'), ''), raw->>'ixbrl', "             
      67 +        f"xbrl_url) as url, {HIDDEN_GROUP} as grp "            
      68          "from public.filings where symbol = any(%s) and duplica
          te_of is null "
      69          "and category in ('routine', 'investor_meetings', 'uncl
          assified')"
      70      )
  ⎿  Updated backend/finn/cards/build.py (+5 -3)
       8  
       9  from datetime import UTC, datetime
      10  
      11 +from finn.citations import filing_doc                          
      12  from finn.models import Card, Citation, Figure, ScoreBreakdown
      13  
      14  CARD_TYPE = {
     ...
      54  
      55  
      56  def _citation(f: dict) -> Citation | None:
      56 -    url = f.get("attachment_url") or f.get("xbrl_url")         
      57 -    if not url:                                                
      57 +    doc = filing_doc(f)                                        
      58 +    if not doc:                                                
      59          return None
      60 +    url, kind, raw = doc                                       
      61      return Citation(
      60 -        source_type="exchange_filing", url=url, title=(f.get("s
         -ubject") or "")[:120] or None,                                 
      62 +        source_type="exchange_filing", url=url, doc_kind=kind, 
         +raw_url=raw, title=(f.get("subject") or "")[:120] or None,     
      63          exchange=f.get("exchange") or "NSE", published_at=f.get
          ("filed_at"),
      64          retrieved_at=f.get("fetched_at") or f.get("filed_at") o
          r datetime.now(UTC),
      65      )  # fmt: skip
  ⎿  Updated backend/finn/citations.py (+21 -0)
      60          if quote_in_text(quote, p):
      61              return i
      62      return None
      63 +                                                               
      64 +                                                               
      65 +def filing_doc(f: dict) -> tuple[str, str, str | None] | None: 
      66 +    """(url, doc_kind, raw_url) for an exchange filing, most re
         +adable first: the attached PDF, else NSE's iXBRL               
      67 +    (HTML) view, else the raw XBRL labelled as machine-readable
         +. None when the filing has no usable link                      
      68 +    (NSE sometimes sends '-')."""                              
      69 +    att = (f.get("attachment_url") or "").strip()              
      70 +    xbrl = (f.get("xbrl_url") or "").strip() or None           
      71 +    if att and att != "-" and att.startswith("http"):          
      72 +        low = att.lower().split("?")[0]                        
      73 +        kind = "zip" if low.endswith(".zip") else "raw_xbrl" if
         + low.endswith(".xml") else "pdf"                               
      74 +        if kind != "raw_xbrl":                                 
      75 +            return att, kind, None                             
      76 +        xbrl = xbrl or att                                     
      77 +    raw = f.get("raw") if isinstance(f.get("raw"), dict) else {
         +}                                                              
      78 +    ix = (f.get("ixbrl_url") or raw.get("ixbrl") or "").strip()
      79 +    if ix.startswith("http") and ix.lower().endswith(".html"): 
      80 +        return ix, "ixbrl", xbrl                               
      81 +    if xbrl and xbrl.startswith("http"):                       
      82 +        return xbrl, "raw_xbrl", xbrl                          
      83 +    return None                                                
  ⎿  Updated backend/finn/ranking/impact.py (+4 -2)
      100      quote = (d.get("quote") or "").strip()
      101      found = quote_in_text(quote, source_text)
      102      page = page_of(quote, pages) if found and pages else None
      103 -    url = filing.get("attachment_url") or filing.get("xbrl_url
          -")                                                            
      104 -    cite = Citation(source_type="exchange_filing", url=url, ti
          -tle=filing["subject"][:120], exchange="NSE",                  
      103 +    doc = filing_doc(filing)                                  
      104 +    url, kind, raw = doc if doc else (None, None, None)       
      105 +    cite = Citation(source_type="exchange_filing", url=url, do
          +c_kind=kind, raw_url=raw, title=filing["subject"][:120],      
      106 +                    exchange="NSE",                           
      107                      page=page, quote=quote[:300] if found else
            None, published_at=filing["filed_at"],
      108                      retrieved_at=now) if url else None  # fmt:
            skip
      109      impact = d.get("impact") if d.get("impact") in ("positive"
           , "negative", "mixed", "neutral") else None
  ⎿  Updated backend/finn/store.py (+2 -1)
      475  
      476  def filing_rows(conn, ids: list[str]) -> dict[str, dict]:
      477      rows = conn.execute(
      478 -        "select id, symbol, filed_at, exchange_category, subje
          -ct, attachment_url, xbrl_url, stage from public.filings "     
      478 +        "select id, symbol, filed_at, exchange_category, subje
          +ct, attachment_url, xbrl_url, raw->>'ixbrl' as ixbrl_url, "   
      479 +        "stage from public.filings "                          
      480          "where id = any(%s)",
      481          (ids,),
      482      ).fetchall()

⏺ Bash(sed -i '' 's/^from finn.citations import page_of, pdf_text,
      quote_in_text$/from finn.citations import filing_doc, page_of, pdf_text,
      quote_in_text/' finn/rankin…)
  ⎿  E501 Line too long (121 > 120)
       --> finn/cards/brief.py:23:121
        |
     … +40 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/cards/brief.py (+3 -1)
      20      "id, key, symbol, category, title, period, started_at, upda
          ted_at, timeline, figures, impact, impact_reason, "
      21      "driver_ids, so_what, detail, detail_at, refreshed_at"
      22  )
      23 -FILING_COLS = "id, exchange, symbol, filed_at, subject, attachm
         -ent_url, xbrl_url, raw->>'ixbrl' as ixbrl_url, fetched_at"     
      23 +FILING_COLS = (                                                
      24 +    "id, exchange, symbol, filed_at, subject, attachment_url, x
         +brl_url, raw->>'ixbrl' as ixbrl_url, fetched_at"               
      25 +)                                                              
      26  
      27  
      28  def load_events(conn, symbols: list[str], since: datetime | Non
          e, limit: int = 400) -> list[dict]:
  ⎿  Updated backend/finn/extraction/results/links.py (+3 -1)
      174          "check_url": screener_quarters_url(symbol, detail.basi
           s),
      175      }
      176      lines = [
      177 -        ln.model_copy(update={k: _figure(getattr(ln, k), **kw)
          - for k in ("current", "previous", "year_ago", "qoq", "yoy")}) 
      177 +        ln.model_copy(                                        
      178 +            update={k: _figure(getattr(ln, k), **kw) for k in 
          +("current", "previous", "year_ago", "qoq", "yoy")}            
      179 +        )                                                     
      180          for ln in detail.lines
      181      ]
      182      out = detail.model_copy(update={"lines": lines})
  ⎿  Updated backend/finn/ranking/impact.py (+1 -1)
      14  from dataclasses import dataclass
      15  from datetime import UTC, datetime
      16  
      17 -from finn.citations import page_of, pdf_text, quote_in_text    
      17 +from finn.citations import filing_doc, page_of, pdf_text, quote
         +_in_text                                                       
      18  from finn.llm import LLMRequest, LLMUnavailable, Router
      19  from finn.models import Citation, Claim, Figure, OneLinerDetail
      20  from finn.numbers import parse_money

  Ran 1 shell command (ctrl+o to expand)
⏺ Bash(python3 - <<'EOF'
      def edit(p, a, b):…)
  ⎿  skip finn/extraction/results/links.py
     23:FILING_COLS = (
     24-    "id, exchange, symbol, filed_at, subject, attachment_url, xbrl_
     … +4 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/cards/build.py (+2 -1)
      59          return None
      60      url, kind, raw = doc
      61      return Citation(
      62 -        source_type="exchange_filing", url=url, doc_kind=kind, 
         -raw_url=raw, title=(f.get("subject") or "")[:120] or None,     
      62 +        source_type="exchange_filing", url=url, doc_kind=kind, 
         +raw_url=raw,                                                   
      63 +        title=(f.get("subject") or "")[:120] or None,          
      64          exchange=f.get("exchange") or "NSE", published_at=f.get
          ("filed_at"),
      65          retrieved_at=f.get("fetched_at") or f.get("filed_at") o
          r datetime.now(UTC),
      66      )  # fmt: skip
  ⎿  Updated backend/finn/extraction/results/links.py (+2 -1)
      35  ]
      36  _LINE_RE = [re.compile(p, re.I) for p in LINE_ITEMS]
      37  _NUM = re.compile(r"\(?-?\d[\d,]*\.?\d*\)?")
      38 -HEAD_CHARS = 900  # the statement's title sits at the top of it
         -s page                                                         
      38 +HEAD_CHARS = 900                                               
      39 +FIGURE_FIELDS = ("current", "previous", "year_ago", "qoq", "yoy
         +")  # the statement's title sits at the top of its page        
      40  
      41  
      42  @dataclass
  ⎿  Updated backend/finn/store.py (+2 -2)
      475  
      476  def filing_rows(conn, ids: list[str]) -> dict[str, dict]:
      477      rows = conn.execute(
      478 -        "select id, symbol, filed_at, exchange_category, subje
          -ct, attachment_url, xbrl_url, raw->>'ixbrl' as ixbrl_url, "   
      479 -        "stage from public.filings "                          
      478 +        "select id, symbol, filed_at, exchange_category, subje
          +ct, attachment_url, xbrl_url, "                               
      479 +        "raw->>'ixbrl' as ixbrl_url, stage from public.filings
          + "                                                            
      480          "where id = any(%s)",
      481          (ids,),
      482      ).fetchall()

  Ran 1 shell command (ctrl+o to expand)

⏺ Still on the backend link rewrite: tidying a formatting slip in the new links
  module, then wiring the PDF page finder into the results pipeline.

⏺ Bash(python3 - <<'EOF'
      p='finn/extraction/results/links.py'…)
  ⎿  _LINE_RE = [re.compile(p, re.I) for p in LINE_ITEMS]
     _NUM = re.compile(r"\(?-?\d[\d,]*\.?\d*\)?")
     HEAD_CHARS = 900  # the statement's title sits at the top of its page
     FIGURE_FIELDS = ("current", "previous", "year_ago", "qoq", "yoy")
  ⎿  Updated backend/finn/extraction/results/links.py (+3 -8)
      35  ]
      36  _LINE_RE = [re.compile(p, re.I) for p in LINE_ITEMS]
      37  _NUM = re.compile(r"\(?-?\d[\d,]*\.?\d*\)?")
      38 -HEAD_CHARS = 900                                               
      39 -FIGURE_FIELDS = ("current", "previous", "year_ago", "qoq", "yoy
         -")  # the statement's title sits at the top of its page        
      38 +HEAD_CHARS = 900  # the statement's title sits at the top of it
         +s page                                                         
      39 +FIGURE_FIELDS = ("current", "previous", "year_ago", "qoq", "yoy
         +")                                                             
      40  
      41  
      42  @dataclass
     ...
      174          "ixbrl": ixbrl,
      175          "check_url": screener_quarters_url(symbol, detail.basi
           s),
      176      }
      177 -    lines = [                                                 
      178 -        ln.model_copy(                                        
      179 -            update={k: _figure(getattr(ln, k), **kw) for k in 
          -("current", "previous", "year_ago", "qoq", "yoy")}            
      180 -        )                                                     
      181 -        for ln in detail.lines                                
      182 -    ]                                                         
      177 +    lines = [ln.model_copy(update={k: _figure(getattr(ln, k), 
          +**kw) for k in FIGURE_FIELDS}) for ln in detail.lines]        
      178      out = detail.model_copy(update={"lines": lines})
      179      if impact_reason is not None:
      180          impact_reason = impact_reason.model_copy(

⏺ Now NSE refs carry ixbrl, store helpers read and write PDF pages, and the
  pipeline finds the page and rewrites links on build, with a --relink mode for
  the backfill.

⏺ Bash(python3 - <<'EOF'
      def edit(p, a, b):…)
  ⎿  finn/extraction/results/xbrl.py:93:    ixbrl_url: str | None = None  #
      NSE's human-readable (HTML) view of the same instance
     finn/sources/nse.py:367:                ixbrl_url=ix if (ix := (r.get(
     "ixbrl") or "").strip()).lower().endswith(".html") else None,
  ⎿  Updated backend/finn/extraction/results/xbrl.py (+1 -0)
      90      xbrl_url: str
      91      broadcast_at: datetime | None
      92      raw: dict
      93 +    ixbrl_url: str | None = None  # NSE's human-readable (HTML)
         + view of the same instance                                     
  ⎿  Updated backend/finn/sources/nse.py (+1 -0)
      364                  xbrl_url=url,
      365                  broadcast_at=parse_ist(stamp, "%d-%b-%Y %H:%M:
           %S") if stamp else None,
      366                  raw=r,
      367 +                ixbrl_url=ix if (ix := (r.get("ixbrl") or "").
          +strip()).lower().endswith(".html") else None,                 
      368              )
      369          )
      370      return out
  ⎿  Updated backend/finn/store.py (+53 -4)
      324  def upsert_results_filing(conn, ref, parsed: dict, xml_gz: byt
           es | None) -> None:
      325      conn.execute(
      326          "insert into public.results_filings (symbol, period_en
           d, basis, type_sub, audited, xbrl_url, broadcast_at, "
      327 -        "facts, xml_gz) values (%s,%s,%s,%s,%s,%s,%s,%s,%s) on
          - conflict (symbol, period_end, basis, xbrl_url) do "          
      327 +        "facts, xml_gz, ixbrl_url) values (%s,%s,%s,%s,%s,%s,%
          +s,%s,%s,%s) "                                                 
      328 +        "on conflict (symbol, period_end, basis, xbrl_url) do 
          +"                                                             
      329          "update set facts = excluded.facts, type_sub = exclude
           d.type_sub, broadcast_at = excluded.broadcast_at, "
      329 -        "xml_gz = coalesce(excluded.xml_gz, results_filings.xm
          -l_gz), fetched_at = now()",                                   
      330 +        "xml_gz = coalesce(excluded.xml_gz, results_filings.xm
          +l_gz), "                                                      
      331 +        "ixbrl_url = coalesce(excluded.ixbrl_url, results_fili
          +ngs.ixbrl_url), fetched_at = now()",                          
      332          (ref.symbol, ref.period_end, ref.basis, ref.type_sub, 
           ref.audited, ref.xbrl_url, ref.broadcast_at,
      331 -         Jsonb(parsed), xml_gz),                              
      333 +         Jsonb(parsed), xml_gz, getattr(ref, "ixbrl_url", None
          +)),                                                           
      334      )  # fmt: skip
      335  
      336  
      337  def results_filings(conn, symbol: str) -> list[dict]:
      338      """Stored XBRL instances for a symbol (no raw XML), newest
            version first within a quarter/basis."""
      339      return conn.execute(
      338 -        "select symbol, period_end, basis, type_sub, audited, 
          -xbrl_url, broadcast_at, facts, fetched_at "                   
      340 +        "select symbol, period_end, basis, type_sub, audited, 
          +xbrl_url, ixbrl_url, broadcast_at, facts, fetched_at "        
      341          "from public.results_filings where symbol = %s order b
           y period_end desc, basis, "
      342          "(type_sub = 'Revised') desc, broadcast_at desc nulls 
           last",
      343          (symbol,),
     ...
      374      return r["ind"] if r else None
      375  
      376  
      377 +def set_ixbrl_urls(conn, refs) -> int:                        
      378 +    """NSE's iXBRL (HTML) view for instances already stored (b
          +ackfill; the instance itself never changes)."""               
      379 +    n = 0                                                     
      380 +    for r in refs:                                            
      381 +        if r.ixbrl_url:                                       
      382 +            n += conn.execute(                                
      383 +                "update public.results_filings set ixbrl_url =
          + %s where xbrl_url = %s and ixbrl_url is distinct from %s",   
      384 +                (r.ixbrl_url, r.xbrl_url, r.ixbrl_url),       
      385 +            ).rowcount                                        
      386 +    return n                                                  
      387 +                                                              
      388 +                                                              
      389 +def ixbrl_map(conn, symbol: str) -> dict[str, str]:           
     … 37 more lines (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/ingest/pipeline.py'…)
  ⎿  347:def recent_results_events(conn, symbols: list[str], days: int) ->
     list[dict]:
     348-    """Results events with an outcome filing, updated in the last
     … +23 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/ingest/pipeline.py (+78 -2)
      266              run.fail("results_fetch", sym, err)
      267              continue
      268          have = store.stored_xbrl_urls(run.conn, sym)
      269 +        stats["ixbrl_linked"] = stats.get("ixbrl_linked", 0) +
          + store.set_ixbrl_urls(run.conn, refs)                         
      270          for q in sorted(need):
      271              mine = [r for r in refs if r.period_end == q]
      272              if not mine:
     ...
      318      return None, None
      319  
      320  
      321 +def _results_doc(run: Run, s: NSESession | None, outcome_ids: 
          +list[str], basis: str, revenue_cr: float | None,              
      322 +                 stats: dict):  # fmt: skip                   
      323 +    """The results PDF and the page with this basis's statemen
          +t (cached in results_pdf_pages). Looking a page up            
      324 +    needs the PDF, so only a run with an NSE session (Actions)
          + can find new pages; others reuse stored ones."""             
      325 +    from finn.citations import pdf_text                       
      326 +    from finn.extraction.results.links import ResultsDoc, find
          +_results_page                                                 
      327 +                                                              
      328 +    pdfs = store.outcome_pdfs(run.conn, outcome_ids)          
      329 +    if not pdfs:                                              
      330 +        return None                                           
      331 +    known = store.results_pdf_pages(run.conn, [p["id"] for p i
          +n pdfs], basis)                                               
      332 +    for p in pdfs:                                            
      333 +        k = known.get(p["id"])                                
      334 +        if k and k["page"]:                                   
      335 +            return ResultsDoc(k["url"], k["page"])            
      336 +    if s is None:                                             
      337 +        return None                                           
      338 +    for p in pdfs:                                            
      339 +        if p["id"] in known:                                  
      340 +            continue  # looked before, no statement page in it
      341 +        raw = fetch_capped(s, p["attachment_url"], max_bytes=M
          +AX_PDF_BYTES, deadline_s=60)                                  
      342 +        if not raw or not raw.startswith(b"%PDF"):            
      343 +            store.save_results_pdf_page(run.conn, p["id"], bas
          +is, p["attachment_url"], None, False, "not a PDF")            
      344 +            continue                                          
      345 +        _, pages = pdf_text(raw, max_pages=40)                
      346 +        m = find_results_page(pages, basis, revenue_cr) if any
          +(t.strip() for t in pages) else None                          
      347 +        note = None if m else ("no text layer (scanned)" if no
          +t any(t.strip() for t in pages) else "no statement page")     
      348 +        store.save_results_pdf_page(run.conn, p["id"], basis, 
          +p["attachment_url"], m.page if m else None,                   
      349 +                                    bool(m and m.value_on_page
          +), note)  # fmt: skip                                         
      350 +        stats["pdf_pages_found" if m else "pdf_pages_missing"]
          + = stats.get("pdf_pages_found" if m else                      
     … 59 more lines (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      p='finn/store.py'…)
  ⎿  E501 Line too long (121 > 120)
        --> finn/store.py:392:121
         |
     … +11 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/store.py (+10 -1)
      347  def recent_results_events(conn, symbols: list[str], days: int)
            -> list[dict]:
      348      """Results events with an outcome filing, updated in the l
           ast `days` days."""
      349      return conn.execute(
      350 -        "select id, symbol, period, timeline, detail, updated_
          -at from public.events where category = 'results' "            
      350 +        "select id, symbol, period, timeline, detail, impact_r
          +eason, updated_at from public.events "                        
      351 +        "where category = 'results' "                         
      352          "and symbol = any(%s) and updated_at > now() - make_in
           terval(days => %s) "
      353          "and exists (select 1 from jsonb_array_elements(timeli
           ne) t where t->>'stage' = 'outcome') "
      354          "order by updated_at desc",
     ...
      366      )  # fmt: skip
      367  
      368  
      369 +def update_event_links(conn, event_id: str, detail: dict, impa
          +ct_reason: dict | None) -> None:                              
      370 +    """Same numbers, new links (results relink): detail_at is 
          +left alone so freshness stamps don't move."""                 
      371 +    conn.execute(                                             
      372 +        "update public.events set detail = %s, impact_reason =
          + %s where id = %s",                                           
      373 +        (Jsonb(detail), Jsonb(impact_reason) if impact_reason 
          +is not None else None, event_id),                             
      374 +    )                                                         
      375 +                                                              
      376 +                                                              
      377  def symbol_industry(conn, symbol: str) -> str | None:
      378      r = conn.execute(
      379          "select raw->>'smIndustry' as ind from public.filings 
           where symbol = %s and raw ? 'smIndustry' "
  ⎿  Updated backend/jobs/results.py (+6 -1)
      1  """Results cards: fetch XBRL (current, previous, year-ago quarte
         r) for recent results events, then build and
      2  cross-check each card. Also run at the end of check_filings / in
         gest_daily.
      3  
      4 -python -m jobs.results [--symbols X,Y] [--days 45] [--no-fetch] 
        -[--rebuild]                                                     
      4 +python -m jobs.results [--symbols X,Y] [--days 45] [--no-fetch] 
        +[--rebuild] [--relink]                                          
      5    --no-fetch: build from stored XBRL only · --rebuild: also rebu
         ild final (cross-checked) cards
      6 +  --relink: only rewrite stored cards' links (results PDF page →
        + iXBRL → raw XBRL); no number changes                           
      7  """
      8  
      9  from __future__ import annotations
     ...
      23      ap.add_argument("--days", type=int, default=45, help="resul
          ts events updated in the last N days")
      24      ap.add_argument("--no-fetch", action="store_true", help="sk
          ip NSE (local dev / Render): stored XBRL only")
      25      ap.add_argument("--rebuild", action="store_true", help="reb
          uild final cards too (after a method change)")
      26 +    ap.add_argument("--relink", action="store_true", help="rewr
         +ite stored cards' links only")                                 
      27      args = ap.parse_args()
      28      logging.basicConfig(level=logging.INFO, format="%(asctime)s
           %(levelname)s %(name)s: %(message)s")
      29  
     ...
      31          symbols = tracked_symbols(args.symbols or None, conn)
      32          run.stats["symbols"] = symbols
      33          s = None if args.no_fetch else nse.session()
      34 +        if args.relink:                                        
      35 +            run.step("results_relink", p.step_results_relink, s
         +ymbols, args.days, s)                                          
      36 +            return                                             
      37          if s is not None:
      38              run.step("results_fetch", p.step_results_fetch, s, 
          symbols, args.days)
      39          run.step("results_build", p.step_results_build, symbols
          , args.days, s=s, rebuild=args.rebuild)

⏺ Bash(python3 - <<'EOF'
      p='finn/store.py'…)
  ⎿  clean
       applied  0005_drivers.sql
       APPLIED  0006_readable_links.sql
  ⎿  Updated backend/finn/store.py (+2 -1)
      389      for r in refs:
      390          if r.ixbrl_url:
      391              n += conn.execute(
      392 -                "update public.results_filings set ixbrl_url =
          - %s where xbrl_url = %s and ixbrl_url is distinct from %s",   
      392 +                "update public.results_filings set ixbrl_url =
          + %s "                                                         
      393 +                "where xbrl_url = %s and ixbrl_url is distinct
          + from %s",                                                    
      394                  (r.ixbrl_url, r.xbrl_url, r.ixbrl_url),
      395              ).rowcount
      396      return n

⏺ Migration applied. For the tests I need a real results PDF as a fixture.
  Checking whether NSE archives are reachable from this machine and which
  outcome PDFs are small enough to commit.

  Ran 1 shell command (ctrl+o to expand)

⏺ Several results PDFs run 18–25 MB, over the pipeline's 12 MB download cap, so
  their pages would never be found; results PDFs get a 32 MB cap on Actions. I'm
  trying the 1.1 MB HDFCBANK results PDF from this machine for the fixture. 
  · summary

  Ran 2 shell commands (ctrl+o to expand)

⏺ NSE archives are reachable from here. Running the page finder on all three
  against their cards' real revenue figures.

  Ran 1 shell command (ctrl+o to expand)

⏺ The finder picks consolidated pages with the card's revenue printed on them
  (HDFCBANK p.9, TRENT p.10, DIXON p.11). Spot-checking the page headings to
  confirm basis.

  Ran 1 shell command (ctrl+o to expand)

⏺ Consolidated and standalone headings confirm the basis for DIXON and TRENT,
  and HDFCBANK's OCR'd PDF still matched on value. I'm building small fixture
  PDFs from the relevant pages and writing the tests next. · summary

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(S=/private/tmp/claude-501/-Users-<user>-Documents-finn/d3ff930d-14ee-
      4948-8047-75d6a884e9ed/scratchpad && rm -f
      tests/fixtures/results_pdf/*.pdf && ../.venv…)
  ⎿  tests/fixtures/results_pdf/dixon_q2fy27_p5_p11.pdf 910962
     tests/fixtures/results_pdf/hdfcbank_q2fy27_p2_p9.pdf 92693
     tests/fixtures/results_pdf/trent_q2fy27_p3_p10.pdf 147009
  ⎿  4 files changed (binary, mode only or too large to show)

⏺ Keeping the HDFCBANK (93 KB) and TRENT (147 KB) fixtures and dropping DIXON's
  910 KB scan. Writing the tests.

⏺ Bash(rm tests/fixtures/results_pdf/dixon_q2fy27_p5_p11.pdf && cat >
      tests/test_readable_links.py <<'EOF'
      """Readable Open links: results PDF page finder, link-choice…)
  ⎿  ........
        [100%]
     8 passed in 0.23s
  ⎿  Created backend/tests/test_readable_links.py (+118 -0)
        1 +"""Readable Open links: results PDF page finder, link-choice o
          +rder, filing links (DECISIONS: readable links).               
        2 +                                                              
        3 +Fixtures are two pages cut from real Q2 FY27 results PDFs on N
          +SE archives (page 1 = standalone statement,                   
        4 +page 2 = consolidated): TRENT (text layer) and HDFCBANK (OCR'd
          + scan: zeros read as 'O' in places).                          
        5 +"""                                                           
        6 +                                                              
        7 +from datetime import UTC, date, datetime                      
        8 +from pathlib import Path                                      
        9 +                                                              
       10 +import pytest                                                 
       11 +                                                              
       12 +from finn.citations import filing_doc, pdf_text               
       13 +from finn.extraction.results.links import (                   
       14 +    ResultsDoc,                                               
       15 +    apply_links,                                              
       16 +    find_results_page,                                        
       17 +    readable,                                                 
       18 +    screener_quarters_url,                                    
       19 +    value_printed,                                            
       20 +)                                                             
       21 +from finn.models import Citation, Claim, Figure, Period, Resul
          +tsDetail, ResultsLine                                         
       22 +                                                              
       23 +FX = Path(__file__).parent / "fixtures" / "results_pdf"       
       24 +NOW = datetime(2026, 11, 12, tzinfo=UTC)                      
       25 +                                                              
       26 +                                                              
       27 +def pages(name: str) -> list[str]:                            
       28 +    _, p = pdf_text((FX / name).read_bytes(), max_pages=10)   
       29 +    return p                                                  
       30 +                                                              
       31 +                                                              
       32 +@pytest.mark.parametrize(                                     
       33 +    "fixture,revenue_cr",                                     
       34 +    [("trent_q2fy27_p3_p10.pdf", 5873.14), ("hdfcbank_q2fy27_p
          +2_p9.pdf", 95131.63)],                                        
       35 +)                                                             
       36 +def test_page_finder_matches_basis_and_finds_the_number(fixtur
          +e, revenue_cr):                                               
       37 +    p = pages(fixture)                                        
       38 +    cons = find_results_page(p, "consolidated", revenue_cr)   
       39 +    assert cons is not None and cons.page == 2 and cons.value_
          +on_page                                                       
       40 +    stand = find_results_page(p, "standalone")                
     … 78 more lines (ctrl+o to expand)
  ⎿  … 1 more file changed

⏺ All 8 pass. Raising the download cap for results PDFs and running the full
  suite.

⏺ Bash(python3 - <<'EOF'
      p='finn/ingest/pipeline.py'…)
  ⎿  31:RESULTS_PDF_BYTES = 32 * 1024 * 1024  # board outcomes bundle scann
     ed auditor reports: 18–25 MB is common
     342:        raw = fetch_capped(s, p["attachment_url"], max_bytes=RESUL
     … +2 lines (ctrl+o to expand)
  ⎿  Updated backend/finn/ingest/pipeline.py (+2 -1)
      28  INCREMENTAL_DAYS = 15  # calendar days ≈ 10 sessions
      29  MAX_PDF_BYTES = 12 * 1024 * 1024
      30  MAX_XBRL_BYTES = 8 * 1024 * 1024
      31 +RESULTS_PDF_BYTES = 32 * 1024 * 1024  # board outcomes bundle s
         +canned auditor reports: 18–25 MB is common                     
      32  
      33  
      34  @dataclass
     ...
      339      for p in pdfs:
      340          if p["id"] in known:
      341              continue  # looked before, no statement page in it
      341 -        raw = fetch_capped(s, p["attachment_url"], max_bytes=M
          -AX_PDF_BYTES, deadline_s=60)                                  
      342 +        raw = fetch_capped(s, p["attachment_url"], max_bytes=R
          +ESULTS_PDF_BYTES, deadline_s=120)                             
      343          if not raw or not raw.startswith(b"%PDF"):
      344              store.save_results_pdf_page(run.conn, p["id"], bas
           is, p["attachment_url"], None, False, "not a PDF")
      345              continue

⏺ Backend tests pass (346). Now the backfill workflow, triggered by
  workflow_dispatch or by pushing a request file. Relink covers every symbol
  with results cards when no symbols are given.

⏺ Bash(cd ~/Documents/finn && python3 - <<'EOF'
      p='backend/jobs/results.py'…)
  ⎿  ok
  ⎿  Created .github/workflows/backfill.yml (+58 -0)
       1 +# One-off backfills that need NSE (blocked from Render). Trigge
         +red by workflow_dispatch, or by committing a                   
       2 +# request file under backend/data/backfills/ (so a backfill can
         + be started without an API token; the file says                
       3 +# what was asked and why). Shares the ingest concurrency group 
         +so it never overlaps a scheduled run.                          
       4 +name: backfill                                                 
       5 +                                                               
       6 +on:                                                            
       7 +  workflow_dispatch:                                           
       8 +    inputs:                                                    
       9 +      job:                                                     
      10 +        description: "results-relink: rewrite results cards' Op
         +en links (results PDF page → iXBRL → raw XBRL)"                
      11 +        required: true                                         
      12 +        default: results-relink                                
      13 +        type: choice                                           
      14 +        options: [results-relink]                              
      15 +      days:                                                    
      16 +        description: "Results events updated in the last N days
         +"                                                              
      17 +        required: false                                        
      18 +        default: "400"                                         
      19 +  push:                                                        
      20 +    branches: [main]                                           
      21 +    paths: ["backend/data/backfills/*.request"]                
      22 +                                                               
      23 +permissions:                                                   
      24 +  contents: read                                               
      25 +                                                               
      26 +concurrency:                                                   
      27 +  group: ingest                                                
      28 +  cancel-in-progress: false                                    
      29 +                                                               
      30 +jobs:                                                          
      31 +  backfill:                                                    
      32 +    runs-on: ubuntu-latest                                     
      33 +    timeout-minutes: 45                                        
      34 +    defaults:                                                  
      35 +      run:                                                     
      36 +        working-directory: backend                             
      37 +    env:                                                       
      38 +      DATABASE_URL: ${{ secrets.DATABASE_URL }}                
      39 +      FINN_CACHE_DIR: ${{ github.workspace }}/backend/.cache   
      40 +      PYTHONUNBUFFERED: "1"                                    
     … 18 more lines (ctrl+o to expand)
  ⎿  Created backend/data/backfills/2026-11-12-results-links.request (+3 
     -0)
      1 +Rewrite every stored results card's Open links: results PDF page
        + (found in code) -> NSE iXBRL view -> raw XBRL                  
      2 +as a secondary link. No number changes, no model calls. Product 
        +owner's bug report, 12 Nov 2026:                                
      3 +a figure's Open landed on raw XBRL XML on a phone.              
  ⎿  Updated backend/jobs/results.py (+4 -0)
      32          run.stats["symbols"] = symbols
      33          s = None if args.no_fetch else nse.session()
      34          if args.relink:
      35 +            if not args.symbols:  # every symbol with a results
         + card, not only the tracked portfolio                          
      36 +                rows = conn.execute("select distinct symbol fro
         +m public.events where category = 'results'").fetchall()        
      37 +                symbols = sorted({r["symbol"] for r in rows} | 
         +set(symbols))                                                  
      38 +                run.stats["symbols"] = symbols                 
      39              run.step("results_relink", p.step_results_relink, s
          ymbols, args.days, s)
      40              return
      41          if s is not None:

⏺ Before triggering the Actions run, a read-only dry run of the relink logic on
  two cards (it caches the PDF page it finds but doesn't save the cards).

  Ran 1 shell command (ctrl+o to expand)

⏺ DIXON now resolves to the results PDF at p.11, and the HDFCBANK error was in
  my print line rather than the code. Next I'm moving on to the frontend:
  regenerated types, Open labels, and grouped sources. · summary

  Called ccd_turn (ctrl+o to expand)
⏺ Bash(cd ~/Documents/finn/web && npm run gen:schema >/dev/null
      2>&1 && npm run gen:types 2>&1 | tail -1 && grep -n
      "doc_kind\|raw_url\|check_url" lib/…)
  ⎿  wrote lib/types.ts
     108:  check_url: string | null;
     112:  doc_kind: ("results_pdf" | "pdf" | "ixbrl" | "raw_xbrl" | "scree
     … +22 lines (ctrl+o to expand)
  ⎿  Updated web/lib/schema.json (+52 -1)
      957        "additionalProperties": false,
      958        "description": "Where a number or claim came from. Every
            Figure/Claim that is not `not_found` carries one.",
      959        "properties": {
      960 +        "check_url": {                                        
      961 +          "anyOf": [                                          
      962 +            {                                                 
      963 +              "type": "string"                                
      964 +            },                                                
      965 +            {                                                 
      966 +              "type": "null"                                  
      967 +            }                                                 
      968 +          ],                                                  
      969 +          "default": null,                                    
      970 +          "description": "Independent cross-check, e.g. screen
          +er's quarterly table",                                        
      971 +          "title": "Check Url"                                
      972 +        },                                                    
      973 +        "doc_kind": {                                         
      974 +          "anyOf": [                                          
      975 +            {                                                 
      976 +              "enum": [                                       
      977 +                "results_pdf",                                
      978 +                "pdf",                                        
      979 +                "ixbrl",                                      
      980 +                "raw_xbrl",                                   
      981 +                "screener",                                   
      982 +                "web",                                        
      983 +                "zip"                                         
      984 +              ],                                              
      985 +              "type": "string"                                
      986 +            },                                                
      987 +            {                                                 
      988 +              "type": "null"                                  
      989 +            }                                                 
      990 +          ],                                                  
      991 +          "default": null,                                    
      992 +          "description": "What `url` opens \u2014 drives the O
          +pen button's label ('Results PDF \u00b7 p.3', 'iXBRL view')", 
      993 +          "title": "Doc Kind"                                 
      994 +        },                                                    
      995          "exchange": {
      996            "anyOf": [
     … 37 more lines (ctrl+o to expand)
  ⎿  Updated web/lib/types.ts (+13 -1)
      102   * Where a number or claim came from. Every Figure/Claim that 
           is not `not_found` carries one.
      103   */
      104  export interface Citation {
      105 +  /**                                                         
      106 +   * Independent cross-check, e.g. screener's quarterly table 
      107 +   */                                                         
      108 +  check_url: string | null;                                   
      109 +  /**                                                         
      110 +   * What `url` opens — drives the Open button's label ('Resul
          +ts PDF · p.3', 'iXBRL view')                                  
      111 +   */                                                         
      112 +  doc_kind: ("results_pdf" | "pdf" | "ixbrl" | "raw_xbrl" | "s
          +creener" | "web" | "zip") | null;                             
      113    exchange: ("NSE" | "BSE") | null;
      114    /**
      115     * Machine locator when there is no page, e.g. 'in-capmkt:Pr
           ofitBeforeTax@OneD' or 'screener:quarters/Net Profit/Sep 2026'
     ...
      127     * Verbatim snippet supporting the value/claim
      128     */
      129    quote: string | null;
      130 +  /**                                                         
      131 +   * Machine-readable original (raw XBRL), offered as a second
          +ary link                                                      
      132 +   */                                                         
      133 +  raw_url: string | null;                                     
      134    /**
      135     * When FINN fetched it (UTC) — drives freshness stamps
      136     */
     ...
      141     */
      142    title: string | null;
      143    /**
      132 -   * Direct link to the document (exchange PDF, XBRL, etc.)   
      144 +   * The human-readable document to open (results PDF, iXBRL v
          +iew, filing PDF, page); `source_type` says where the value was
          + read, which may be a machine format kept in `raw_url`        
      145     */
      146    url: string;
      147  }

⏺ Bash(python3 - <<'EOF'
      p='lib/format.ts'…)
  ⎿  Updated web/lib/format.ts (+68 -3)
      141    return { headline: cleaned, sub: null };
      142  }
      143  
      144 +// --- Source links: every Open lands on a human-readable docu
          +ment (DECISIONS: readable Open links) -----------             
      145 +                                                              
      146 +type DocKind = NonNullable<Citation["doc_kind"]>;             
      147  const PDF_TYPES = new Set(["exchange_filing", "concall_transcr
           ipt", "investor_presentation", "annual_report"]);
      148 +const SCREENER_SECTION: Record<string, string> = {            
      149 +  quarters: "Quarters",                                       
      150 +  "profit-loss": "Profit & loss",                             
      151 +  "balance-sheet": "Balance sheet",                           
      152 +  "cash-flow": "Cash flows",                                  
      153 +  ratios: "Ratios",                                           
      154 +  shareholding: "Shareholding",                               
      155 +  "top-ratios": "Key ratios",                                 
      156 +  schedules: "Cash flows",                                    
      157 +};                                                            
      158 +                                                              
      159 +/** What a citation's url opens. Stored cards from before the 
          +change carry no doc_kind: infer it. */                        
      160 +export function docKind(c: Citation): DocKind {               
      161 +  if (c.doc_kind) return c.doc_kind;                          
      162 +  const u = c.url.toLowerCase().split("?")[0];                
      163 +  if (u.endsWith(".xml")) return "raw_xbrl";                  
      164 +  if (u.endsWith(".zip")) return "zip";                       
      165 +  if (u.includes("/ixbrl/") || u.endsWith(".html")) return c.s
          +ource_type === "web_profile" ? "web" : "ixbrl";               
      166 +  if (c.source_type === "screener_table") return "screener";  
      167 +  if (u.endsWith(".pdf") || PDF_TYPES.has(c.source_type) || u.
          +includes("annpdfopen")) return "pdf";                         
      168 +  return "web";                                               
      169 +}                                                             
      170 +                                                              
      171 +function screenerSection(c: Citation): string | null {        
      172 +  const m = /^screener:([a-z-]+)/.exec(c.locator ?? "");      
      173 +  return m ? m[1] : null;                                     
      174 +}                                                             
      175 +                                                              
      176  export function sourceHref(c: Citation): string {
      146 -  return c.page && PDF_TYPES.has(c.source_type) ? `${c.url}#pa
          -ge=${c.page}` : c.url;                                        
      177 +  const kind = docKind(c);                                    
      178 +  if (kind === "screener") {                                  
      179 +    const sec = screenerSection(c);                           
     … 46 more lines (ctrl+o to expand)

⏺ I'm building the provenance sheet next: one row per document, each with an
  Open button, the supplied figures beneath, and the screener cross-check. 
  · summary

⏺ Write(web/components/cards/Provenance.tsx)
  ⎿  Added 94 lines, removed 29 lines
       1  "use client";
       2  // The provenance drawer: every number and claim opens its docu
          ment, page and verbatim quote (PRODUCT §8, rule 3).
       3 +// Open always lands on something a person can read (results PD
         +F page, iXBRL view, filing PDF); a machine-readable            
       4 +// original (raw XBRL) is offered only as a small secondary lin
         +k (DECISIONS: readable Open links).                            
       5 +import type { ReactNode } from "react";                        
       6  import { ArrowUpRight } from "lucide-react";
       7  import type { Citation, Claim, Figure } from "@/lib/types";
       5 -import { figureText, ist, sourceHref, sourceLabel } from "@/lib
         -/format";                                                      
       8 +import { figureText, ist, openLabel, sourceHref, sourceLabel } 
         +from "@/lib/format";                                           
       9  
      10  const STATUS: Record<string, { text: string; cls: string }> = {
      11    verified: { text: "Verified in source", cls: "text-pos" },
     ...
      13    not_found: { text: "Not found in sources", cls: "text-warn" }
          ,
      14  };
      15  
      13 -export function CitationBlock({ c, label }: { c: Citation; labe
         -l?: string }) {                                                
      16 +function OpenButton({ c }: { c: Citation }) {                  
      17    return (
      18 +    <a                                                         
      19 +      href={sourceHref(c)}                                     
      20 +      target="_blank"                                          
      21 +      rel="noopener noreferrer"                                
      22 +      className="t-small inline-flex h-9 shrink-0 items-center 
         +gap-1 whitespace-nowrap rounded-full border border-rule px-3 fo
         +nt-medium"                                                     
      23 +    >                                                          
      24 +      {openLabel(c)} <ArrowUpRight className="size-3.5" />     
      25 +    </a>                                                       
      26 +  );                                                           
      27 +}                                                              
      28 +                                                               
      29 +function RawLink({ c }: { c: Citation }) {                     
      30 +  if (!c.raw_url || c.raw_url === c.url) return null;          
      31 +  return (                                                     
      32 +    <a href={c.raw_url} target="_blank" rel="noopener noreferre
         +r" className="t-small mt-1 inline-block text-ink-3 underline un
         +derline-offset-4">                                             
      33 +      Raw XBRL (machine-readable)                              
      34 +    </a>                                                       
      35 +  );                                                           
      36 +}                                                              
      37 +                                                               
      38 +export function CitationBlock({ c, label, children }: { c: Cita
         +tion; label?: string; children?: ReactNode }) {                
      39 +  const meta = [sourceLabel(c), c.published_at ? ist(c.publishe
         +d_at, false) : null].filter(Boolean).join(" · ");              
      40 +  return (                                                     
      41      <div className="border-t border-rule py-3 first:border-t-0"
          >
      42        <div className="flex items-start justify-between gap-3">
      43          <div className="min-w-0">
      44            {label && <p className="t-micro text-ink-3">{label}</
          p>}
      45            <p className="t-small font-medium">{c.title ?? source
          Label(c)}</p>
      20 -          <p className="t-small text-ink-3">                   
      21 -            {[sourceLabel(c), c.published_at ? ist(c.published_
         -at, false) : null].filter(Boolean).join(" · ")}                
      22 -          </p>                                                 
      46 +          <p className="t-small text-ink-3">{meta}</p>         
      47          </div>
      24 -        <a                                                     
      25 -          href={sourceHref(c)}                                 
      26 -          target="_blank"                                      
      27 -          rel="noopener noreferrer"                            
      28 -          className="t-small inline-flex h-9 shrink-0 items-cen
         -ter gap-1 rounded-full border border-rule px-3 font-medium"    
      29 -        >                                                      
      30 -          {c.page ? `Open p.${c.page}` : "Open"} <ArrowUpRight 
         -className="size-3.5" />                                        
      31 -        </a>                                                   
      48 +        <OpenButton c={c} />                                   
      49        </div>
      50        {c.quote && (
      51          <blockquote className="mt-2 border-l-2 border-ink-3/40 
          pl-3 font-serif text-[16px] leading-[23px] text-ink">
      52            “{c.quote}”
      53          </blockquote>
      54        )}
      38 -      {c.locator && !c.quote && <p className="mt-1 break-all fo
         -nt-mono text-[11px] text-ink-3">{c.locator}</p>}               
      55 +      {children}                                               
      56 +      {c.locator && !c.quote && !children && <p className="mt-1
         + break-all font-mono text-[11px] text-ink-3">{c.locator}</p>}  
      57 +      <RawLink c={c} />                                        
      58      </div>
      59    );
      60  }
      61  
      62 +type Supplied = { label: string; period: string | null; value: 
         +string; locator: string | null };                              
      63 +type Doc = { c: Citation; items: Supplied[] };                 
      64 +                                                               
      65 +/** Every sourced figure behind `f` (itself and its inputs, rec
         +ursively), grouped by the document it came from. */            
      66 +function sourceDocs(f: Figure): Doc[] {                        
      67 +  const docs = new Map<string, Doc>();                         
      68 +  const visit = (x: Figure) => {                               
      69 +    if (x.citation) {                                          
      70 +      const key = `${sourceHref(x.citation)}|${x.citation.quote
         + ?? ""}`;                                                      
      71 +      let d = docs.get(key);                                   
      72 +      if (!d) docs.set(key, (d = { c: x.citation, items: [] }))
         +;                                                              
      73 +      const item = { label: x.label, period: x.period?.label ??
         + null, value: figureText(x), locator: x.citation.locator };    
      74 +      if (!d.items.some((i) => i.label === item.label && i.peri
         +od === item.period)) d.items.push(item);                       
      75 +    }                                                          
      76 +    x.inputs.forEach(visit);                                   
      77 +  };                                                           
      78 +  visit(f);                                                    
      79 +  return [...docs.values()];                                   
      80 +}                                                              
      81 +                                                               
      82 +function checkUrl(f: Figure): string | null {                  
      83 +  if (f.citation?.check_url) return f.citation.check_url;      
      84 +  for (const i of f.inputs) {                                  
      85 +    const u = checkUrl(i);                                     
      86 +    if (u) return u;                                           
      87 +  }                                                            
      88 +  return null;                                                 
      89 +}                                                              
      90 +                                                               
      91  export function FigureProvenance({ f }: { f: Figure }) {
      92    const st = STATUS[f.status] ?? STATUS.unverified;
      93 +  const docs = sourceDocs(f);                                  
      94 +  const check = checkUrl(f);                                   
      95    return (
      96      <div>
      97        <p className="t-small text-ink-2">
     ...
       99          {(f.period || f.basis) && " · "}
      100          <span className={st.cls}>{st.text}</span>
      101        </p>
       52 -      <p className="t-figure-lg mt-1">{figureText(f)}</p>     
       53 -      {f.raw && (                                             
      102 +      <p className="t-figure-lg mt-1 whitespace-nowrap">{figur
          +eText(f)}</p>                                                 
      103 +      {f.raw && f.citation?.source_type !== "xbrl" && (       
      104          <p className="t-small mt-1 text-ink-3">
      105            As printed: {f.raw} {f.raw_unit && !f.raw.toLowerCas
           e().includes(f.raw_unit) ? f.raw_unit : ""}
      106          </p>
     ...
      113            {f.inputs.length > 0 && (
      114              <ul className="mt-2 space-y-1">
      115                {f.inputs.map((i, n) => (
       66 -                <li key={n} className="t-small flex justify-be
          -tween gap-3">                                                 
       67 -                  <span className="text-ink-2">               
      116 +                <li key={n} className="t-small flex items-base
          +line justify-between gap-3">                                  
      117 +                  <span className="min-w-0 text-ink-2">       
      118                      {i.label}
      119                      {i.period ? ` · ${i.period.label}` : ""}
      120                    </span>
       71 -                  <span className="t-figure text-[13px]">{figu
          -reText(i)}</span>                                             
      121 +                  <span className="t-figure shrink-0 whitespac
          +e-nowrap text-[13px]">{figureText(i)}</span>                  
      122                  </li>
      123                ))}
      124              </ul>
      125            )}
      126          </div>
      127        )}
       78 -      {f.citation && (                                        
      128 +      {docs.length > 0 && (                                   
      129          <div className="mt-3">
       80 -          <CitationBlock c={f.citation} label="Source" />     
       81 -        </div>                                                
       82 -      )}                                                      
       83 -      {!f.citation && f.inputs.some((i) => i.citation) && (   
       84 -        <div className="mt-3">                                
       85 -          <p className="t-micro text-ink-3">Input sources</p> 
       86 -          {dedupe(f.inputs.map((i) => i.citation).filter((c): 
          -c is Citation => !!c)).map((c, i) => (                        
       87 -            <CitationBlock key={i} c={c} />                   
      130 +          <p className="t-micro text-ink-3">{docs.length === 1
          + ? "Source" : `Sources · ${docs.length} documents`}</p>       
      131 +          {docs.map((d, i) => (                               
      132 +            <CitationBlock key={i} c={d.c}>                   
      133 +              {(d.items.length > 1 || f.inputs.length > 0) && 
          +(                                                             
      134 +                <ul className="mt-2 space-y-1">               
      135 +                  {d.items.map((it, n) => (                   
      136 +                    <li key={n} className="t-small flex items-
          +baseline justify-between gap-3">                              
      137 +                      <span className="min-w-0 text-ink-2">   
      138 +                        {it.label}                            
      139 +                        {it.period ? ` · ${it.period}` : ""}  
      140 +                        {it.locator && <span className="block 
          +break-all font-mono text-[11px] text-ink-3">{it.locator}</span
          +>}                                                            
      141 +                      </span>                                 
      142 +                      <span className="t-figure shrink-0 white
          +space-nowrap text-[13px]">{it.value}</span>                   
      143 +                    </li>                                     
      144 +                  ))}                                         
      145 +                </ul>                                         
      146 +              )}                                              
      147 +            </CitationBlock>                                  
      148            ))}
      149          </div>
      150        )}
      151 +      {check && (                                             
      152 +        <a href={check} target="_blank" rel="noopener noreferr
          +er" className="t-small mt-3 inline-flex items-center gap-1 tex
          +t-ink-2 underline underline-offset-4">                        
      153 +          Cross-check: screener.in quarterly table <ArrowUpRig
          +ht className="size-3.5" />                                    
      154 +        </a>                                                  
      155 +      )}                                                      
      156      </div>
      157    );
      158  }
     ...
      175  function dedupe(cs: Citation[]): Citation[] {
      176    const seen = new Set<string>();
      177    return cs.filter((c) => {
      113 -    const k = `${c.url}#${c.page ?? ""}#${c.locator ?? ""}#${c
          -.quote ?? ""}`;                                               
      178 +    const k = `${sourceHref(c)}#${c.locator ?? ""}#${c.quote ?
          +? ""}`;                                                       
      179      if (seen.has(k)) return false;
      180      seen.add(k);
      181      return true;

⏺ Bash(sed -i '' 's/className={`hit tabular-nums underline
      decoration-dotted/className={`hit whitespace-nowrap tabular-nums underline
      decoration-dotted/' components/ca…)
  ⎿  1
     components/research/sections.tsx:297:            <a href={s.url} targe
     t="_blank" rel="noopener noreferrer" className="flex items-center gap-
     … +13 lines (ctrl+o to expand)
  ⎿  Updated web/components/cards/FigureValue.tsx (+1 -1)
      31            e.stopPropagation();
      32            setOpen(true);
      33          }}
      34 -        className={`hit tabular-nums underline decoration-dotte
         -d decoration-1 underline-offset-[5px] ${                       
      34 +        className={`hit whitespace-nowrap tabular-nums underlin
         +e decoration-dotted decoration-1 underline-offset-[5px] ${     
      35            unverified ? "decoration-warn" : "decoration-ink-3/70
          "
      36          } ${className}`}
      37          aria-label={`${f.label}: ${text}${unverified ? " (unver
          ified)" : ""} — show source`}

⏺ Other spots still use the raw c.url: management roles, chips and price-move
  explanations. Switching them to the readable href, then checking the
  price/volume and chip citations in the backend.

⏺ Bash(sed -i '' 's|href={r.citation.url}
      target="_blank"|href={sourceHref(r.citation)} target="_blank"|'
      components/cards/ManagementChangeCard.tsx && sed -i '' 's|<a…)
  ⎿  // Inline chip for dividends and bonus/splits, e.g. "₹8 dividend · rec
     ord 21 Nov".
     import type { ChipDetail } from "@/lib/types";
     … +16 lines (ctrl+o to expand)
  ⎿  Updated web/components/cards/InlineChip.tsx (+1 -1)
       9      </span>
      10    );
      11    return d.citation ? (
      12 -    <a href={d.citation.url} target="_blank" rel="noopener nore
         -ferrer" className="underline decoration-ink-3/40 underline-offs
         -et-4">                                                         
      12 +    <a href={sourceHref(d.citation)} target="_blank" rel="noope
         +ner noreferrer" className="underline decoration-ink-3/40 underl
         +ine-offset-4">                                                 
      13        {body}
      14      </a>
      15    ) : (
  ⎿  Updated web/components/cards/ManagementChangeCard.tsx (+1 -1)
      47              <ul className="mt-1 space-y-0.5 text-xs">
      48                {p.prior_roles.map((r, i) => (
      49                  <li key={i}>
      50 -                  <a href={r.citation.url} target="_blank" rel=
         -"noopener noreferrer" className="hover:underline">             
      50 +                  <a href={sourceHref(r.citation)} target="_bla
         +nk" rel="noopener noreferrer" className="hover:underline">     
      51                      {r.role ? `${r.role}, ` : ""}
      52                      {r.company}
      53                      {r.period_citation ? "" : years(r.start_yea
          r, r.end_year)}
  ⎿  Updated web/components/cards/PriceVolumeAlertCard.tsx (+1 -1)
      38              <li key={i} className={e.kind === "none" ? "font-me
          dium text-warn" : ""}>
      39                {e.citation ? (
      40                  <a
      41 -                  href={e.citation.url}                        
      41 +                  href={sourceHref(e.citation)}                
      42                    target="_blank"
      43                    rel="noopener noreferrer"
      44                    onClick={(ev) => ev.stopPropagation()}

⏺ Bash(cd ~/Documents/finn/web && python3 - <<'EOF'
      for f in ["InlineChip","ManagementChangeCard","PriceVolumeAlertCard"]:…)
  ⎿  finn/signals/run.py:25:    url = f"https://finance.yahoo.com/quote/{si
     g.symbol}.NS/history"
     finn/signals/run.py:28:                            citation=Citation(s
     … +16 lines (ctrl+o to expand)
  ⎿  Updated web/components/cards/InlineChip.tsx (+1 -0)
      1  // Inline chip for dividends and bonus/splits, e.g. "₹8 dividend
          · record 21 Nov".
      2 +import { sourceHref } from "@/lib/format";                      
      3  import type { ChipDetail } from "@/lib/types";
      4  
      5  export function InlineChip({ symbol, d }: { symbol: string; d: C
         hipDetail }) {
  ⎿  Updated web/components/cards/ManagementChangeCard.tsx (+1 -0)
      1  // Management change: the incoming person's mini-CV — filing fir
         st. Every web fact says "web · unverified",
      2  // names its kind of source (profile, bio page, prior employer, 
         news) and links to the snippet's URL.
      3 +import { sourceHref } from "@/lib/format";                      
      4  import type { Citation, ManagementDetail } from "@/lib/types";
      5  import { FigureValue } from "./FigureValue";
      6  
  ⎿  Updated web/components/cards/PriceVolumeAlertCard.tsx (+1 -0)
      1  // Price/volume alert: the move, volume, z-score, and the explan
         ation chain (filing → deal → sector → none).
      2 +import { sourceHref } from "@/lib/format";                      
      3  import type { PriceVolumeDetail } from "@/lib/types";
      4  import { FigureValue } from "./FigureValue";
      5  

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(python3 - <<'EOF'
      def edit(p,a,b):…)
  ⎿  346 passed, 1 warning in 1.45s
  ⎿  Updated backend/finn/cards/chips.py (+3 -1)
       4  
       5  from datetime import UTC, date, datetime, timedelta
       6  
       7 +from finn.citations import filing_doc                          
       8  from finn.models import ChipDetail, Citation, Figure
       9  
      10  
     ...
      19      a = min(cands, key=lambda a: a["ex_date"])
      20      rec = a.get("record_date")
      21      when = f"record {rec:%d %b}" if rec else f"ex {a['ex_date']
          :%d %b}"
      21 -    url = (filing or {}).get("attachment_url") or f"https://www
         -.nseindia.com/get-quotes/equity?symbol={event['symbol']}"      
      22 +    doc = filing_doc(filing) if filing else None               
      23 +    url = doc[0] if doc else f"https://www.nseindia.com/get-quo
         +tes/equity?symbol={event['symbol']}"                           
      24      cite = Citation(source_type="exchange_filing", url=url, tit
          le=f"NSE corporate action: {a['subject'][:80]}",
      25                      exchange="NSE", locator=f"nse:corporate-act
          ions/{event['symbol']}/{a['ex_date']}",
      26                      retrieved_at=a.get("fetched_at") or datetim
          e.now(UTC))  # fmt: skip
  ⎿  Updated backend/finn/signals/price_volume.py (+3 -1)
      17  from datetime import date, datetime, time, timedelta
      18  
      19  from finn.calendar import IST
      20 +from finn.citations import filing_doc                          
      21  from finn.models import AlertSettings
      22  
      23  VOL_WINDOW, Z_WINDOW = 20, 60
     ...
      239          lab = (labels or {}).get(f["category"], f["category"].
           replace("_", " ").capitalize())
      240          when = f["filed_at"].astimezone(IST).strftime("%d %b %
           H:%M")
      241          subj = re.sub(SUBJECT_BOILERPLATE, "", f["subject"], f
           lags=re.I).strip(" .'\"") or f["subject"]
      241 -        out.append(Explanation("filing", f"{lab} filed {when} 
          -IST: {subj[:90]}", f.get("attachment_url"), f))               
      242 +        doc = filing_doc(f)  # readable-first: PDF, else iXBRL
          + view; never '-'                                              
      243 +        out.append(Explanation("filing", f"{lab} filed {when} 
          +IST: {subj[:90]}", doc[0] if doc else None, f))               
      244          break
      245      if deals:
      246          d = max(deals, key=lambda d: d["value_cr"])

⏺ Render's strict Pydantic models would reject cards that gain doc_kind before
  Render deploys, so Render has to go out before the backfill. I can't reach
  Render directly, so I'm adding a read-only /version route to the web proxy's
  allow-list to check its deploy through Vercel. · summary

⏺ Bash(cd ~/Documents/finn/web && python3 - <<'EOF'
      p='app/api/[...path]/route.ts'…)
  ⎿  ✓ Generating static pages using 7 workers (13/13) in 225ms
  ⎿  Updated web/app/api/[...path]/route.ts (+1 -0)
       5  export const maxDuration = 60;
       6  
       7  const ALLOWED: [string, RegExp][] = [
       8 +  ["GET", /^version$/], // deploy checks (Render's commit), rea
         +d-only                                                         
       9    ["POST", /^brief$/],
      10    ["GET", /^events\/[^/]+\/card$/],
      11    ["POST", /^telegram\/link$/],
  ⎿  Updated web/components/brief/sheets.tsx (+4 -1)
      155                          <span className="w-24 shrink-0 font-se
           mibold">{i.symbol}</span>
      156                          <span className="min-w-0 flex-1 text-i
           nk-2">
      157                            <span className="line-clamp-2">{i.su
           bject}</span>
      158 -                          <span className="text-ink-3">{istWhe
          -n(i.filed_at)}</span>                                         
      158 +                          <span className="text-ink-3">       
      159 +                            {istWhen(i.filed_at)}             
      160 +                            {i.url?.includes("/ixbrl/") ? " · 
          +iXBRL view" : i.url?.toLowerCase().endsWith(".xml") ? " · raw 
          +XBRL" : ""}                                                   
      161 +                          </span>                             
      162                          </span>
      163                          <ArrowUpRight className="mt-0.5 size-3
           .5 shrink-0 text-ink-3" />
      164                        </a>

⏺ Build passes. Committing in focused pieces and pushing, without the backfill
  trigger yet.

  Ran 1 shell command (ctrl+o to expand)

⏺ Pushed. Waiting for Vercel to deploy and for Render to serve 74f383f (checked
  through the proxy).

  Ran 1 shell command (ctrl+o to expand)

⏺ Render serves 74f383f. Quick check that the live Brief still loads, then
  triggering the backfill.

  Ran 1 shell command (ctrl+o to expand)

⏺ Backfill run 43106362843 is in progress. I'll wait on it in the background and
  write DECISIONS and PLAN meanwhile.

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(cat >> docs/DECISIONS.md <<'EOF'…)
  ⎿  docs/PLAN.md:1
     docs/DECISIONS.md:1
  ⎿  Updated docs/DECISIONS.md (+32 -0)
      523  - **Fallback:** if the API can't be reached, the 4 demo ticker
           s fall back to their fixtures, labelled "Saved copy from 11 No
           v 2026".
      524  - **Section states:** building + `not_built_yet` (red flags, e
           xchange data) renders a quiet "Coming soon"; `llm_quota` shows
            when it resumes; other reasons are explained in plain words.
      525  - **Ask (until Friday):** the bar is always visible. Its 3 con
           text suggestions per screen jump to the section, ledger filter
            or card that answers them. Free text says it arrives with the
            next release. `lib/ask`-style wiring is one place: `component
           s/shell/ui-store.ts` `setAskContext`.
      526 +                                                              
      527 +## 2026-11-12 · Readable Open links (product owner's bug: a fi
          +gure opened raw XBRL XML on a phone)                          
      528 +- **Context:** results figures are read from NSE's XBRL instan
          +ces, and their citation pointed at the `.xml`. On Android Chro
          +me, Open showed a wall of tags. An audit of every stored link 
          +(cards, filings, dossiers) found the same problem in three mor
          +e places:                                                     
      529 +  - 22 results impact reasons;                                
      530 +  - 45 board-meeting filings with only a prior-intimation XBRL
          + link, shown as source chips on results, what-to-watch and one
          +-liner cards, and in the hidden drawer;                       
      531 +  - one KMP `.zip` attachment, and 3 one-liner chips pointing 
          +at `-`.                                                       
      532 +                                                              
      533 +  Filing PDFs, BSE transcripts and decks, Yahoo price history 
          +and web profiles were already readable.                       
      534 +- **Decision: a figure's Open goes to a human-readable documen
          +t, in this order:**                                           
      535 +  1. **Results PDF**, the outcome announcement in the card's o
          +wn event thread, at the page with the statement for the card's
          + basis, as `url#page=N`. The page is found in code (`finn/extr
          +action/results/links.py`):                                    
      536 +     - a candidate page prints ≥ 3 statement line items;      
      537 +     - it scores for naming its basis in the heading, and lose
          +s for naming only the other basis;                            
      538 +     - it scores most when the card's revenue (or a lender's i
          +nterest line) is printed on it in crore, lakh or million.     
      539 +                                                              
      540 +     Previous- and year-ago-quarter figures open the same PDF 
          +page, titled "… · Q1 FY27 column". Pages are cached in `result
          +s_pdf_pages` (migration 0006). Results PDFs may be up to 32 MB
          +: board outcomes bundle scanned auditor reports, and 18–25 MB 
          +is common.                                                    
      541 +  2. **NSE's iXBRL (HTML) view** of the same instance, when th
          +ere's no results PDF or no statement page. It's stored on `res
          +ults_filings.ixbrl_url` from the integrated-filing list.      
      542 +  3. **Raw XBRL** only as a small secondary "Raw XBRL (machine
          +-readable)" link (`Citation.raw_url`), kept for auditability. 
      543 +  4. **Screener cross-check** (`Citation.check_url`): the comp
          +any page's `#quarters` section. Every screener citation also l
          +ands on its own section (`#profit-loss`, `#cash-flow`, …) from
          + its locator.                                                 
      544 +- **Filing links everywhere** (`finn.citations.filing_doc`): t
          +he attached PDF, else NSE's iXBRL view (board-meeting rows kee
          +p it in `raw`), else raw XBRL labelled as such. `-` and empty 
          +links are dropped. ZIPs are labelled "ZIP file".              
      545 +- **Contract:** `Citation.url` now means "the human-readable d
          +ocument to open". `source_type` still says where the value was
          + read (`xbrl`), and the XBRL element stays in `locator`. Added
          + `doc_kind`, `raw_url` and `check_url`, all optional, so store
          +d data stays valid.                                           
      546 +- **Provenance sheet:**                                       
      547 +  - one row per document, with one Open button and the figures
          + and XBRL elements it supplied listed underneath (previously t
          +he same XBRL file appeared once per input);                   
      548 +  - the button says what opens and shows the page ("Results PD
          +F · p.3", "iXBRL view", "Raw XBRL"), because mobile PDF viewer
          +s often ignore `#page`;                                       
      549 +  - figures never wrap mid-value; the label column wraps.     
      550 +- **Where it runs:** the page finder needs the PDF, and NSE ar
          +chives are blocked from Render, so new pages are found by the 
          +results job on GitHub Actions. Render and local runs reuse sto
          +red pages.                                                    
      551 +  - Existing cards were relinked by `python -m jobs.results --
          +relink`: same numbers, new links, `detail_at` unchanged. It ra
          +n through the new `backfill.yml` workflow, which starts from `
          +workflow_dispatch` or a committed request file under `backend/
          +data/backfills/` (no API token on this machine).              
      552 +- **Order of deploys:** Render had to serve the new contract b
          +efore any card carried `doc_kind`, because the API's models fo
          +rbid unknown fields. That was checked through the proxy's new 
          +`GET /api/version`, and the backfill was triggered afterwards.
      553 +- **No model calls:** page finding and relinking are code only
          +.                                                             
      554 +- **Alternatives:**                                           
      555 +  - Render the XBRL as an HTML table ourselves: rejected, beca
          +use a reader should see the company's own document.           
      556 +  - Link only the iXBRL view: rejected; it's readable, but it 
          +isn't the statement as the company printed it.                
      557 +  - Leave XBRL and label it: rejected; it's still unreadable o
          +n a phone.                                                    
  ⎿  Updated docs/PLAN.md (+1 -0)
      174  - [ ] Rules editing (thresholds, categories, budget, quiet hou
           rs, snoozes) synced via `PUT /subscriptions/me` when Telegram 
           is connected; push rule changes to a connected Telegram copy
      175  - [ ] PWA: manifest, icons, offline cache of the latest Brief 
           (web push stays below the cut)
      176  - [ ] Wire `/ask` when Friday's backend lands: `setAskContext`
            chips → `POST /research/{sym}/ask` → answer sheet; enable fre
           e text
      177 +- [x] **Readable Open links** (bug from the product owner's ph
          +one): results figures open the results PDF at the statement pa
          +ge → iXBRL view → raw XBRL as a secondary link; filing links r
          +eadable-first everywhere; provenance grouped by document with 
          +page-numbered buttons; figures nowrap — `c59a247`, `41d6096`, 
          +backfill workflow `74f383f`, relink run 43106362843 (`5b87c57`
          +)                                                             
      178  - [ ] Real-phone checks the browser pane can't do: iOS swipe v
           s scroll, haptics on Android, first paint on 4G
      179  - [ ] Brief payload: a 7-day Brief is ~1 MB uncompressed (resu
           lts figures carry full provenance trees); brotli makes the tra
           nsfer small, but consider trimming duplicated `inputs` server-
           side
      180  

⏺ Waiting for the backfill run to finish.

  Ran 1 shell command (ctrl+o to expand)

⏺ Still running (downloading and reading the results PDFs on Actions). I'll pick
  up when it completes.

  Ran 1 shell command (ctrl+o to expand)

⏺ The backfill is still running: 24 of 90 XBRL instances already have their
  iXBRL link, and the two PDF pages from my dry run are cached. I'll be notified
  when the run completes, then verify three results cards on the deployed site
  at 375 px.

⏺ Background command "Wait for the backfill Actions run to finish" completed
(exit code 0)

  Ran 1 shell command (ctrl+o to expand)

⏺ The backfill run succeeded, relinking 15 cards and giving all 90 XBRL
  instances their iXBRL link, and the statement page turned up in all 15 results
  PDFs. I'm re-running the link audit to see what's still outstanding. 
  · summary

  Ran 1 shell command (ctrl+o to expand)
⏺ All 1,239 results figures and 22 impact reasons now open their PDFs, and the
  board-meeting chips open NSE's iXBRL pages. I'm checking the deployed site at
  375 px next. · summary

  Called ccd_turn, Claude_Browser 2 times (ctrl+o to expand)

⏺ Opening the PAT figure on the DIVISLAB card.

  Called Claude_Browser 2 times (ctrl+o to expand)

⏺ The sheet shows "Results PDF · p.7" as the primary Open, raw XBRL as a small
  secondary link, and the screener #quarters cross-check. Opening that link in
  the browser.

  Called Claude_Browser (ctrl+o to expand)

⏺ The browser pane can't show the NSE PDFs since they download instead, so I'll
  render each linked page to an image and highlight the number to confirm it's
  there. I'm collecting the other two cards' links from the deployed sheet
  first. · summary

  Called Claude_Browser (ctrl+o to expand)

⏺ Each Open lands on a page-numbered results PDF. Now rendering each linked page
  and searching it for that card's exact PAT value (in crore, lakh or million).

  Ran 1 shell command (ctrl+o to expand)

⏺ The PAT value appears on every linked page, in different units: DIVISLAB 1127
  (₹ crore) on p.7, COCHINSHIP 5377.08 (₹ lakh, about ₹53.77 Cr) on p.10, and
  JUBLFOOD 1,115.88 (₹ million, about ₹111.59 Cr) on p.11. I'm opening one
  render to check it's readable. · summary

  Read 1 file (ctrl+o to expand)

⏺ Three linked pages confirm the figure: COCHINSHIP's statement shows 5377.08 (₹
  lakh) on PDF page 10. I'm tightening the number matcher's decimal tolerance
  next, since it wrongly flagged JUBLFOOD's 111.46 against ₹111.59 Cr. · summary

⏺ Bash(python3 - <<'EOF'
      p='finn/extraction/results/links.py'…)
  ⎿  346 passed, 1 warning in 1.62s
  ⎿  Updated backend/finn/extraction/results/links.py (+8 -5)
      46      score: int
      47  
      48  
      49 -def _numbers(text: str) -> list[float]:                        
      49 +def _numbers(text: str) -> list[tuple[float, int]]:            
      50 +    """(value, decimals printed) for every number on the page."
         +""                                                             
      51      out = []
      52      for tok in _NUM.findall(text):
      53          t = tok.strip("()").replace(",", "")
      54          if not t or t in ("-", "."):
      55              continue
      56          try:
      56 -            out.append(abs(float(t)))                          
      57 +            out.append((abs(float(t)), len(t.split(".")[1]) if 
         +"." in t else 0))                                              
      58          except ValueError:
      59              continue
      60      return out
      61  
      62  
      63  def value_printed(text: str, value_cr: float | None) -> bool:
      63 -    """Is a ₹ crore value printed on the page in crore, lakh or
         - million (within the printed rounding)?"""                     
      64 +    """Is a ₹ crore value printed on the page in crore, lakh or
         + million? A printed number matches within half a               
      65 +    unit of its own last digit (or 0.05% for rounding of large 
         +values) — 111.46 is not 111.59."""                             
      66      if value_cr is None or value_cr == 0:
      67          return False
      68      targets = [abs(value_cr), abs(value_cr) * 100, abs(value_cr
          ) * 10]  # crore, lakh, million
      67 -    for n in _numbers(text):                                   
      69 +    for n, dec in _numbers(text):                              
      70 +        tol = 0.5 * 10 ** (-dec)                               
      71          for t in targets:
      69 -            if t >= 1 and abs(n - t) <= max(0.51, t * 0.0005): 
      72 +            if t >= 1 and abs(n - t) <= max(tol, t * 0.0005):  
      73                  return True
      74      return False
      75  
  ⎿  Updated backend/tests/test_readable_links.py (+2 -0)
      50      assert value_printed("Revenue from operations 49,24,400.00"
          , 49244.0)  # lakh
      51      assert value_printed("Revenue from operations 492,440", 492
          44.0)  # million
      52      assert not value_printed("Revenue from operations 12,345", 
          49244.0)
      53 +    assert value_printed("Profit for the period 1,115.88", 111.
         +5883)  # ₹ million                                             
      54 +    assert not value_printed("Other line 111.46", 111.5883)  # 
         +printed precision: not the same number                         
      55  
      56  
      57  XBRL = "https://nsearchives.nseindia.com/corporate/xbrl/INTEGRA
          TED_FILING_INDAS_1_WEB.xml"

⏺ Tests still pass with the tighter matcher. Adding the viewer-page note to the
  sheet.

⏺ Bash(cd ~/Documents/finn/web && python3 - <<'EOF'
      p='components/cards/Provenance.tsx'…)
  ⎿  ✓ Generating static pages using 7 workers (13/13) in 223ms
  ⎿  Updated web/components/cards/Provenance.tsx (+3 -0)
      52            “{c.quote}”
      53          </blockquote>
      54        )}
      55 +      {c.page && (c.doc_kind === "results_pdf" || c.doc_kind ==
         += "pdf") && (                                                  
      56 +        <p className="t-small mt-1 text-ink-3">Page {c.page} as
         + your PDF viewer counts it; the document may print its own page
         + numbers.</p>                                                  
      57 +      )}                                                       
      58        {children}
      59        {c.locator && !c.quote && !children && <p className="mt-1
           break-all font-mono text-[11px] text-ink-3">{c.locator}</p>}
      60        <RawLink c={c} />
  ⎿  Updated web/lib/format.ts (+1 -1)
      217        return `${c.exchange ?? "NSE"} filing${page}`;
      218      }
      219      case "xbrl":
      220 -      return docKind(c) === "results_pdf" ? `Results PDF${page
          -}` : docKind(c) === "ixbrl" ? "NSE iXBRL" : "NSE XBRL";       
      220 +      return docKind(c) === "results_pdf" ? "Results PDF · fig
          +ures read from NSE XBRL" : docKind(c) === "ixbrl" ? "NSE iXBRL
          +" : "NSE XBRL";                                               
      221      case "screener_table":
      222        return "screener.in";
      223      case "concall_transcript":

  Ran 1 shell command (ctrl+o to expand)

⏺ Re-rendering the three highlighted pages with the tighter matcher while Vercel
  deploys.

  Ran 1 shell command (ctrl+o to expand)

⏺ Waiting for Vercel to deploy 4b604bb, then screenshotting the three sheets.

  Called Claude_Browser, ran 1 shell command (ctrl+o to expand)

⏺ COCHINSHIP (p.10) and JUBLFOOD (p.11) sheets are clean. Re-taking DIVISLAB,
  which was caught mid-animation, using a computed figure (EBITDA margin) to
  show the grouped sources.

  Called Claude_Browser (ctrl+o to expand)

⏺ Grouping now works: the results PDF (p.7) shows as one row with its five
  XBRL-tagged figures listed beneath, and no value wraps. I'm sending the
  evidence next: three sheets from the deployed site and the three linked PDF
  pages with the number boxed. · summary

  Called Claude_Browser (ctrl+o to expand)

  Called ccd_turn (ctrl+o to expand)

⏺ The raw-XBRL bug is fixed and deployed. A results figure's Open now lands on
  the company's results PDF at the page with the statement, and existing cards
  were updated by GitHub Actions run 43106362843: 15 cards relinked, the page
  found in all 15 results PDFs, and NSE's HTML view linked for all 90 XBRL
  filings. No model calls were used. 346 backend tests pass, including new ones
  for the link order and the page finder, run on two real results PDFs saved as
  fixtures.

  Checked on the deployed site at 375 px. On three results cards I opened PAT
  and confirmed the number is on the page the link names:

  ┌────────────┬────────────────────┬───────────────────────────────────┐
  │    Card    │     Open says      │        Number on that page        │
  ├────────────┼────────────────────┼───────────────────────────────────┤
  │ DIVISLAB   │ Results PDF · p.7  │ 1127 (₹ crore)                    │
  ├────────────┼────────────────────┼───────────────────────────────────┤
  │ COCHINSHIP │ Results PDF · p.10 │ 5377.08 (₹ lakh = ₹53.77 Cr)      │
  ├────────────┼────────────────────┼───────────────────────────────────┤
  │ JUBLFOOD   │ Results PDF · p.11 │ 1,115.88 (₹ million = ₹111.59 Cr) │
  └────────────┴────────────────────┴───────────────────────────────────┘

  I sent the sheet screenshots and those PDF pages with the number boxed. The
  in-app browser can't display NSE's PDFs (NSE serves them as downloads), so I
  rendered the same pages from the same PDFs. I haven't tried it on a real
  phone.

  What each link type opens now
  - Results figures:
    - The results PDF from that card's own announcement, at the statement page
      for its consolidated/standalone basis. The page is found in code from the
      PDF text and checked against the card's revenue. Previous-quarter and
      year-ago figures open the same page, labelled "Q1 FY27 column".
    - If there's no PDF or no page: NSE's iXBRL (HTML) view.
    - Raw XBRL appears only as a small "Raw XBRL (machine-readable)" link.
    - A "Cross-check: screener.in quarterly table" link goes to screener's
      quarterly section.
  - Results impact reasons: same as results figures.
  - Board-meeting intimations (45 filings that only had an XBRL file) and the
    hidden drawer: NSE's iXBRL page.
  - Other filings, one-liners, management cards, price-move explanations, chips:
    the filing PDF. A ZIP attachment is labelled "ZIP file", and broken "-"
    links are dropped.
  - Promise Ledger statements and deck figures: BSE-hosted PDF at the page.
    These were already readable.
  - Screener links: now land on their own section (quarters, profit & loss, cash
    flows…).
  - Price-move day prices: the Yahoo history page.

  Provenance sheet. One row per document with one Open button, and the figures
  and XBRL element names it supplied listed underneath. The button says what
  opens and the page ("Results PDF · p.7", "iXBRL view", "Raw XBRL"). Figures no
  longer wrap mid-value.

  Things to know
  - The page number on the button is the PDF viewer's page. Some documents print
    their own numbers: COCHINSHIP's p.10 is footed "Page 14", so the sheet now
    says the number is your viewer's page.
  - Render had to run the new code before the backfill. Its data models reject
    fields they don't know, so relinking first would have broken every results
    card. I confirmed Render's version through the site before triggering the
    run, and added /api/version to the site proxy so that check works from
    anywhere.
  - There's no GitHub token on this machine, so the new backfill workflow starts
    either from the Actions "Run workflow" button or by committing a request
    file. I used the request file (5b87c57).
  - Results PDFs can now be up to 32 MB. Board outcomes of 18–25 MB were being
    skipped before.
  - The decision is recorded in DECISIONS.md and ticked in PLAN.md.

  Commits: c59a247 (backend links, page finder, migration, tests) · 41d6096
  (provenance sheet) · 74f383f (backfill workflow) · 5b87c57 (backfill request)
  · 4b604bb (tighter number matching, viewer-page note, docs).

❯ /export docs/ai-logs/phase-0-setup.md                                         
  ⎿  Conversation exported to:
     ~/Documents/finn/docs/ai-logs/phase-0-setup.md