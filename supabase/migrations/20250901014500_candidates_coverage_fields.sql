-- D-019.5 Add coverage fields to smart_money_candidates
alter table if exists public.smart_money_candidates
  add column if not exists priced_trades_count integer default 0;

alter table if exists public.smart_money_candidates
  add column if not exists coverage_pct numeric(5,2) default 0;

alter table if exists public.smart_money_candidates
  add column if not exists last_priced_at timestamptz;

