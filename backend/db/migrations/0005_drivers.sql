-- Suggested drivers per holding from a drivers-only build (Flash-Lite MAP + code; no strong model).
-- Read by GET /research/drivers; a full dossier's own drivers section supersedes it.
create table if not exists public.drivers (
  symbol      text primary key,
  section     jsonb not null,
  calls_read  int not null default 0,
  built_at    timestamptz not null default now()
);
alter table public.drivers enable row level security;
