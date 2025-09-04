-- ENS cache table for reverse resolution results
create table if not exists public.ens_cache (
  address text primary key,
  ens text,
  last_resolved timestamptz not null default now()
);

create index if not exists idx_ens_cache_last on public.ens_cache (last_resolved desc);

