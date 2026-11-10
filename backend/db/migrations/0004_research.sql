-- 0004_research: research dossiers (Phase 3). Render's disk is wiped on restart, so every cache lives here.
-- Applied by `python -m jobs.migrate`. RLS on, no policies (the anon key reads nothing).

-- Documents FINN has seen (transcripts, annual reports). A URL is downloaded once; its bytes' sha256 is the key
-- for the extracted text, so the same PDF under two URLs is extracted once.
create table if not exists public.research_documents (
  url           text primary key,
  symbol        text not null,
  kind          text not null check (kind in ('transcript', 'annual_report', 'investor_presentation')),
  title         text,
  period_label  text,                       -- e.g. 'Q2 FY27' (computed in code)
  call_date     date,
  sha256        text,                       -- of the PDF bytes; null until downloaded
  pages         integer,
  status        text not null default 'new' -- new | extracting | read | scanned | too_large | failed | not_pdf
                check (status in ('new', 'extracting', 'read', 'scanned', 'too_large', 'failed', 'not_pdf')),
  status_note   text,
  bytes         integer,
  fetched_at    timestamptz,
  created_at    timestamptz not null default now()
);
create index if not exists research_documents_symbol on public.research_documents (symbol, kind, call_date desc);
create index if not exists research_documents_sha on public.research_documents (sha256);

-- Extracted page text, gzip-compressed JSON array of strings (one per page). Never the PDF itself.
create table if not exists public.research_doc_text (
  sha256        text primary key,
  pages_gz      bytea not null,
  page_count    integer not null,
  chars         integer not null,
  extractor     text not null,              -- e.g. 'pymupdf-1.26'
  created_at    timestamptz not null default now(),
  last_used_at  timestamptz not null default now()
);

-- Validated model extractions per document (after Pydantic + citation checks), so a ledger never flips between
-- builds and a Groq/Gemini fallback answer is reused. Key: (document hash, extractor, prompt version).
create table if not exists public.research_extractions (
  sha256          text not null,
  extractor       text not null,            -- e.g. 'map_transcript', 'annual_report_sections'
  prompt_version  text not null,            -- e.g. 'v1'
  model           text not null,
  payload         jsonb not null,
  stats           jsonb not null default '{}',  -- quotes checked/dropped/re-anchored, tokens
  created_at      timestamptz not null default now(),
  primary key (sha256, extractor, prompt_version)
);

-- Build jobs: the queue for Render's worker thread and the nightly GitHub Actions worker.
create table if not exists public.research_jobs (
  id             bigint generated always as identity primary key,
  symbol         text not null,
  status         text not null default 'queued'
                 check (status in ('queued', 'running', 'waiting_quota', 'done', 'partial', 'failed')),
  reason         text not null default 'requested'
                 check (reason in ('requested', 'nightly', 'new_document', 'prewarm', 'resume')),
  priority       integer not null default 10,   -- lower runs first (requested 10, nightly 50)
  stage          text,
  progress       jsonb not null default '{}',   -- steps, counters, message (DossierJob)
  stats          jsonb not null default '{}',   -- calls, cache hits, tokens, est cost, models
  worker         text,                          -- 'render:<pid>' | 'actions:<run id>'
  attempts       integer not null default 0,
  error          text,
  resume_after   timestamptz,
  queued_at      timestamptz not null default now(),
  started_at     timestamptz,
  heartbeat_at   timestamptz,
  finished_at    timestamptz,
  updated_at     timestamptz not null default now()
);
-- One active build per ticker; other tickers queue.
create unique index if not exists research_jobs_one_active on public.research_jobs (symbol)
  where status in ('queued', 'running', 'waiting_quota');
create index if not exists research_jobs_queue on public.research_jobs (status, priority, queued_at);
create index if not exists research_jobs_symbol on public.research_jobs (symbol, id desc);

-- The last good dossier per ticker (rule 7: serve it with its freshness when a rebuild fails).
create table if not exists public.dossiers (
  symbol          text primary key,
  schema_version  integer not null,
  version         integer not null default 1,   -- increments on every publish (clients refetch on change)
  payload         jsonb not null,
  doc_set_hash    text,                          -- documents + pipeline version that produced it
  synthesis_hash  text,                          -- inputs of the strong calls (no strong calls when unchanged)
  status          text not null default 'partial' check (status in ('complete', 'partial')),
  built_at        timestamptz not null,
  last_opened_at  timestamptz,
  updated_at      timestamptz not null default now()
);

-- On-demand build requests per IST day (daily cap protects the push side's model quota).
create table if not exists public.research_requests (
  id         bigint generated always as identity primary key,
  symbol     text not null,
  ist_date   date not null,
  kind       text not null default 'build' check (kind in ('build', 'ask')),
  created_at timestamptz not null default now()
);
create index if not exists research_requests_day on public.research_requests (ist_date, kind);

alter table public.research_documents   enable row level security;
alter table public.research_doc_text    enable row level security;
alter table public.research_extractions enable row level security;
alter table public.research_jobs        enable row level security;
alter table public.dossiers             enable row level security;
alter table public.research_requests    enable row level security;
