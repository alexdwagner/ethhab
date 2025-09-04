-- D-019.1 Pricing Schema
-- Tables: tx_receipts_cache, priced_trades

-- Cache of raw transaction receipts to avoid re-fetching from RPC/APIs
create table if not exists public.tx_receipts_cache (
  tx_hash text primary key,
  block_number bigint,
  block_ts timestamptz not null,
  status smallint not null, -- 1 = success, 0 = fail
  from_address text,
  to_address text,
  logs_json jsonb not null,
  fetched_at timestamptz not null default now()
);

create index if not exists idx_tx_receipts_block_ts_desc on public.tx_receipts_cache (block_ts desc);
create index if not exists idx_tx_receipts_fetched_at_desc on public.tx_receipts_cache (fetched_at desc);

-- Normalized per-tx priced trade for a wallet
create table if not exists public.priced_trades (
  id bigserial primary key,
  address text not null, -- trader EOA
  tx_hash text not null unique,
  router text not null,
  block_number bigint,
  block_ts timestamptz not null,
  side text not null check (side in ('buy','sell','route')),
  token_in text null,
  token_in_decimals smallint null,
  token_out text null,
  token_out_decimals smallint null,
  amt_in numeric(38, 18) null,
  amt_out numeric(38, 18) null,
  usd_in numeric(38, 10) not null default 0,
  usd_out numeric(38, 10) not null default 0,
  fees_usd numeric(38, 10) null,
  slippage_bps numeric(12, 4) null,
  pricing_method text not null default 'stable_leg',
  pricing_confidence numeric(5, 2) not null default 1.00,
  created_at timestamptz not null default now()
);

create index if not exists idx_priced_trades_address_block_ts on public.priced_trades (address, block_ts desc);
create index if not exists idx_priced_trades_router on public.priced_trades (router);
create unique index if not exists uq_priced_trades_tx_hash on public.priced_trades (tx_hash);

