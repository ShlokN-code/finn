-- 0002_ingest: tables for Phase 1 ingestion (prices, filings, events, actions, deals, freshness, LLM log).
-- Applied by `python -m jobs.migrate`. Every table has RLS on with no policies (anon key reads nothing);
-- jobs and the API connect as the postgres role via the pooler and bypass RLS.

create table if not exists public.securities (
  symbol      text primary key,             -- NSE symbol (canonical key)
  isin        text,
  name        text,
  industry    text,
  series      text,
  bse_code    text,
  updated_at  timestamptz not null default now()
);

create table if not exists public.prices_daily (
  symbol      text        not null,
  date        date        not null,           -- IST trading day
  open        double precision,
  high        double precision,
  low         double precision,
  close       double precision,               -- split/bonus-adjusted (Yahoo Close)
  adj_close   double precision,               -- also dividend-adjusted (Yahoo Adj Close) → use for returns
  volume      bigint,                         -- split/bonus-adjusted
  source      text        not null default 'yahoo',
  fetched_at  timestamptz not null default now(),
  primary key (symbol, date)
);

create table if not exists public.filings (
  id                   text primary key,      -- '<exchange>:<exchange_id>'
  exchange             text not null check (exchange in ('NSE', 'BSE')),
  exchange_id          text not null,
  symbol               text not null,
  isin                 text,
  bse_code             text,
  filed_at             timestamptz not null,
  exchange_category    text not null,
  subject              text not null,
  attachment_url       text,
  attachment_size      text,
  xbrl_url             text,
  category             text,
  category_source      text check (category_source in ('exchange', 'rule', 'model')),
  category_model       text,
  category_confidence  double precision,
  classify_tier        text,                   -- exchange | rule | model | failed (null = not yet run)
  classify_note        text,                   -- rule name / model reason / failure reason
  stage                text,
  hidden_reason        text,
  duplicate_of         text,
  event_id             text,
  raw                  jsonb not null,
  fetched_at           timestamptz not null default now(),
  unique (exchange, exchange_id)
);
create index if not exists filings_symbol_filed_at on public.filings (symbol, filed_at desc);
create index if not exists filings_filed_at on public.filings (filed_at desc);
create index if not exists filings_event on public.filings (event_id);

create table if not exists public.events (
  id            text primary key,
  key           text not null unique,
  symbol        text not null,
  category      text not null,
  title         text not null,
  period        jsonb,
  started_at    timestamptz not null,
  updated_at    timestamptz not null,
  timeline      jsonb not null default '[]',
  figures       jsonb not null default '[]',
  impact        text,
  impact_reason jsonb,
  driver_ids    jsonb not null default '[]',
  refreshed_at  timestamptz not null default now()
);
create index if not exists events_symbol_updated on public.events (symbol, updated_at desc);
create index if not exists events_updated on public.events (updated_at desc);

create table if not exists public.corporate_actions (
  symbol            text not null,
  ex_date           date not null,
  subject           text not null,
  record_date       date,
  kind              text not null,            -- dividend | bonus | split | rights | buyback | demerger | other
  ratio_new         double precision,         -- bonus a:b → new=a, held=b; split FV x→y → new=x/y, held=1
  ratio_held        double precision,
  amount_per_share  double precision,         -- ₹ per share (dividends)
  face_value        text,
  raw               jsonb not null,
  fetched_at        timestamptz not null default now(),
  primary key (symbol, ex_date, subject)
);

create table if not exists public.deals (
  id          text primary key,               -- hash of the row (NSE gives no id)
  date        date not null,
  symbol      text not null,
  kind        text not null check (kind in ('bulk', 'block')),
  client      text not null,
  side        text not null,
  quantity    bigint not null,
  price       double precision not null,      -- ₹ per share
  value_cr    double precision not null,      -- quantity × price, computed in code, ₹ crore
  remarks     text,
  raw         jsonb not null,
  fetched_at  timestamptz not null default now()
);
create index if not exists deals_symbol_date on public.deals (symbol, date desc);

create table if not exists public.market_holidays (
  date         date primary key,
  description  text,
  source       text not null,
  fetched_at   timestamptz not null default now()
);

-- Freshness / last-good bookkeeping per source and scope (symbol or 'all'). Drives "data as of" stamps.
create table if not exists public.source_status (
  source           text not null,             -- e.g. nse_announcements, yahoo_prices
  scope            text not null,             -- symbol or 'all'
  last_attempt_at  timestamptz not null,
  last_success_at  timestamptz,
  last_error       text,
  rows             integer,
  primary key (source, scope)
);

create table if not exists public.ingest_runs (
  id           bigint generated always as identity primary key,
  job          text not null,
  started_at   timestamptz not null default now(),
  finished_at  timestamptz,
  status       text not null default 'running', -- running | ok | partial | failed | skipped
  stats        jsonb not null default '{}',     -- counts, classification tier split, timings
  failures     jsonb not null default '[]',
  trigger      text                             -- schedule | workflow_dispatch | local
);

-- LLM calls: cache (by content hash) and token/cost log in one table.
create table if not exists public.llm_calls (
  id            bigint generated always as identity primary key,
  content_hash  text not null,
  provider      text not null,
  model         text not null,
  tier          text not null,                  -- cheap | strong
  purpose       text not null,                  -- e.g. classify_filing
  request       jsonb not null,                 -- prompt text (PDF bytes replaced by their hash)
  response      jsonb,
  ok            boolean not null,
  error         text,
  tokens_in     integer,
  tokens_out    integer,
  est_cost_usd  double precision,
  latency_ms    integer,
  created_at    timestamptz not null default now()
);
create unique index if not exists llm_calls_cache on public.llm_calls (content_hash) where ok;
create index if not exists llm_calls_provider_day on public.llm_calls (provider, created_at desc);

create table if not exists public.snapshots (
  id            bigint generated always as identity primary key,
  label         text not null,
  trading_date  date not null,
  created_at    timestamptz not null default now(),
  payload       jsonb not null,
  unique (label)
);

alter table public.securities        enable row level security;
alter table public.prices_daily      enable row level security;
alter table public.filings           enable row level security;
alter table public.events            enable row level security;
alter table public.corporate_actions enable row level security;
alter table public.deals             enable row level security;
alter table public.market_holidays   enable row level security;
alter table public.source_status     enable row level security;
alter table public.ingest_runs       enable row level security;
alter table public.llm_calls         enable row level security;
alter table public.snapshots         enable row level security;
