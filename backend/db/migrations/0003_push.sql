-- 0003_push: Phase 2 — results XBRL store, card details, Telegram subscriptions, feedback rules, alerts,
-- price/volume signals. RLS on with no policies (as 0002): the anon key reads nothing.

-- XBRL results instances, fetched by GitHub Actions (NSE blocks Render) so the API and local dev can read them.
create table if not exists public.results_filings (
  symbol        text        not null,
  period_end    date        not null,
  basis         text        not null check (basis in ('consolidated', 'standalone')),
  type_sub      text,                          -- Original | Revised
  audited       text,
  xbrl_url      text        not null,
  broadcast_at  timestamptz,
  facts         jsonb       not null,           -- parsed top-level facts (₹, OneD/FourD contexts) + meta
  xml_gz        bytea,                          -- raw instance, gzip (provenance; ~10–100 KB)
  fetched_at    timestamptz not null default now(),
  primary key (symbol, period_end, basis, xbrl_url)
);
create index if not exists results_filings_symbol on public.results_filings (symbol, period_end desc);

alter table public.events add column if not exists so_what text;
alter table public.events add column if not exists detail jsonb;          -- Event.detail (card-type payload)
alter table public.events add column if not exists detail_at timestamptz; -- when detail was last built
alter table public.events add column if not exists impact_tier text;      -- code | model | failed (Level 0)

-- Opt-in server copy for push: symbols + weights only (DECISIONS: holdings). Deleted by /stop or the web.
create table if not exists public.push_subscriptions (
  id           bigint generated always as identity primary key,
  chat_id      bigint      not null unique,
  holdings     jsonb       not null,           -- [{symbol, weight_pct}]
  settings     jsonb       not null default '{}', -- AlertSettings
  secret_hash  text,                           -- sha256 of the browser's subscriber secret (null for bare /start)
  source       text        not null,           -- link | demo
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create table if not exists public.telegram_link_tokens (
  token_hash   text primary key,               -- sha256 of the deep-link token
  holdings     jsonb       not null,
  settings     jsonb       not null default '{}',
  secret_hash  text        not null,
  expires_at   timestamptz not null,
  used_at      timestamptz,
  created_at   timestamptz not null default now()
);

create table if not exists public.feedback_rules (
  subscription_id  bigint not null references public.push_subscriptions (id) on delete cascade,
  rule_id          text   not null,
  rule             jsonb  not null,           -- WeightRule
  updated_at       timestamptz not null default now(),
  primary key (subscription_id, rule_id)
);

create table if not exists public.snoozes (
  subscription_id  bigint not null references public.push_subscriptions (id) on delete cascade,
  symbol           text   not null,
  until            timestamptz not null,
  primary key (subscription_id, symbol)
);

-- One row per (subscription, event): reruns never resend. Statuses as the Alert contract.
create table if not exists public.alerts (
  id               bigint generated always as identity primary key,
  subscription_id  bigint not null references public.push_subscriptions (id) on delete cascade,
  event_id         text   not null,
  symbol           text   not null,
  trigger          text   not null,            -- filing | price_move | volume_spike | test
  severity         text   not null,            -- critical | normal
  status           text   not null,            -- queued | sent | batched | held_quiet_hours | over_budget | suppressed | failed
  status_reason    text,
  title            text   not null,
  body             text   not null,
  score            jsonb,                       -- ScoreBreakdown at decision time
  batch_id         text,
  telegram_message_id bigint,
  created_at       timestamptz not null default now(),
  sent_at          timestamptz,
  unique (subscription_id, event_id)
);
create index if not exists alerts_sub_sent on public.alerts (subscription_id, sent_at desc);

create table if not exists public.price_signals (
  symbol          text not null,
  date            date not null,               -- IST trading day
  move_pct        double precision,            -- adjusted close-to-close (mechanical ex-date part removed)
  raw_move_pct    double precision,
  mechanical_pct  double precision,
  z_score         double precision,
  volume_ratio    double precision,
  sector_index    text,
  sector_move_pct double precision,
  day_label       text,
  detail          jsonb not null,              -- PriceVolumeDetail
  computed_at     timestamptz not null default now(),
  primary key (symbol, date)
);

alter table public.results_filings       enable row level security;
alter table public.push_subscriptions    enable row level security;
alter table public.telegram_link_tokens  enable row level security;
alter table public.feedback_rules        enable row level security;
alter table public.snoozes               enable row level security;
alter table public.alerts                enable row level security;
alter table public.price_signals         enable row level security;
