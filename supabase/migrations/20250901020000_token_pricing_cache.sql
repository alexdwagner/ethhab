-- D-019.1b Token metadata and price cache

create table if not exists public.token_metadata (
  address text primary key,
  symbol text,
  decimals smallint not null,
  coingecko_id text
);

create table if not exists public.token_prices (
  address text not null,
  ts_bucket timestamptz not null, -- e.g., hour bucket
  usd numeric(38,10) not null,
  source text not null default 'coingecko',
  fetched_at timestamptz not null default now(),
  primary key (address, ts_bucket)
);

create index if not exists idx_token_prices_ts on public.token_prices (ts_bucket desc);

