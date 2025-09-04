export type SmartMoneyItem = {
  address: string;
  status?: string;
  dex_swaps_90d?: number;
  unique_protocols_90d?: number;
  last_activity_at?: string | null;
  total_gas_spent_eth?: number | null;
  sharpe_ratio?: number | null;
  win_rate?: number | null;
  volume_90d_usd?: number | null;
  coverage_pct?: number | null;
  priced_trades_count?: number | null;
};

export type SmartMoneyResponse = {
  items: SmartMoneyItem[];
  count: number;
  limit: number;
};

