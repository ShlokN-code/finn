-- Human-readable links for results figures (DECISIONS: readable Open links).
-- NSE's integrated-filing list gives an iXBRL (HTML) view next to each raw XBRL instance.
alter table public.results_filings add column if not exists ixbrl_url text;

-- The page of a results PDF that holds the statement for a basis, found in code from the PDF text (Actions only:
-- NSE archives are blocked from Render). page null = looked, not found (note says why).
create table if not exists public.results_pdf_pages (
  filing_id      text        not null,
  basis          text        not null check (basis in ('consolidated', 'standalone')),
  url            text        not null,
  page           int,
  value_on_page  boolean     not null default false,
  note           text,
  checked_at     timestamptz not null default now(),
  primary key (filing_id, basis)
);
alter table public.results_pdf_pages enable row level security;
