-- D-020 Trader Metrics (rolling aggregates)
-- Stores 90d (and optional other windows) metrics per trader

create table if not exists public.trader_metrics (
  address text not null,
  metrics_window text not null default '90d', -- e.g., '90d', '30d', '7d'
  priced_trades_count integer not null default 0,
  coverage_pct numeric(5,2) default 0,
  pnl_usd_90d numeric(38,10) default 0,
  win_rate numeric(6,4) default 0,
  sharpe_90d numeric(10,4) default 0,
  max_drawdown_usd numeric(38,10) default 0,
  updated_at timestamptz not null default now(),
  primary key (address, metrics_window)
);

create index if not exists idx_trader_metrics_updated on public.trader_metrics (updated_at desc);
