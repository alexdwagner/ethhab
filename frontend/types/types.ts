export interface Whale {
  address: string;
  display_name: string;      // Smart display name (ENS or truncated address)
  description?: string;      // Context description ("Ethereum Co-Founder", "CEX Hot Wallet")
  name: string;              // Legacy field for compatibility
  ens?: string;              // ENS domain if available
  entity_type: string;
  category: string;
  balance_eth: number;
  balance_usd: number;
  composite_score: number;
  total_trades: number;
  avg_roi_percent: number;
  win_rate_percent: number;
  sharpe_ratio?: number;     // Risk-adjusted returns
  total_volume_usd?: number; // Annual trading volume
  last_activity?: string;    // Last transaction timestamp
  portfolio_value_usd?: number; // Total portfolio value
}

export interface TableSort {
  column: keyof Whale | 'rank';
  direction: 'asc' | 'desc';
}

export interface TablePagination {
  page: number;
  pageSize: number;
  total: number;
}

export interface Stats {
  total_whales: number;
  whales_with_roi: number;
  avg_roi_score: number;
}

export interface ApiResponse {
  whales: Whale[];
  count: number;
  generated_at: string;
}

export interface WhaleDisplayInfo {
  display_name: string;
  description: string;
  isAddress: boolean;
}