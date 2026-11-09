-- 0001_hello: skeleton table proving web -> API -> DB.
-- Run once in Supabase Dashboard -> SQL Editor.
create table if not exists public.hello (
  id          bigint generated always as identity primary key,
  message     text        not null,
  created_at  timestamptz not null default now()
);

-- RLS on with no policies: the public anon key (PostgREST) cannot read this table.
-- The API connects as the postgres role via the pooler and is unaffected.
alter table public.hello enable row level security;

insert into public.hello (message)
select 'Namaste from Supabase — FINN skeleton is wired end to end'
where not exists (select 1 from public.hello);
