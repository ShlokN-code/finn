-- Ask (Phase 5): cached answers per (symbol, normalised question, dossier version), and a per-visitor daily count.

create table if not exists public.ask_answers (
  symbol           text        not null,
  qnorm            text        not null,      -- lower-cased words of the question, punctuation dropped
  dossier_version  integer     not null,      -- dossiers.version: a rebuilt dossier asks again
  payload          jsonb       not null,      -- AskAnswer
  model            text,
  created_at       timestamptz not null default now(),
  hits             integer     not null default 0,
  primary key (symbol, qnorm, dossier_version)
);

-- visitor = sha256(salt + client IP + IST date), truncated: it can't be reversed or linked across days.
create table if not exists public.ask_usage (
  visitor   text    not null,
  ist_date  date    not null,
  n         integer not null default 0,
  primary key (visitor, ist_date)
);

alter table public.ask_answers enable row level security;
alter table public.ask_usage   enable row level security;
