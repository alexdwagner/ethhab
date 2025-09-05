"use client";

import { useState } from "react";

type Props = {
  defaultSort: string;
  defaultPricedOnly: boolean;
  defaultMinCoverage: number;
  defaultMinTrades: number;
  defaultWatchlist?: boolean;
};

export default function SmartMoneyFilters({ defaultSort, defaultPricedOnly, defaultMinCoverage, defaultMinTrades, defaultWatchlist }: Props) {
  const [sort, setSort] = useState<string>(defaultSort || 'sharpe');
  const [pricedOnly, setPricedOnly] = useState<boolean>(defaultPricedOnly ?? true);
  const [minCoverage, setMinCoverage] = useState<number>(defaultMinCoverage ?? 60);
  const [minTrades, setMinTrades] = useState<number>(defaultMinTrades ?? 5);
  const [watchlistOnly, setWatchlistOnly] = useState<boolean>(!!defaultWatchlist);

  function apply() {
    const params = new URLSearchParams();
    params.set('sort', sort);
    params.set('priced_only', pricedOnly ? '1' : '0');
    params.set('min_coverage', String(minCoverage));
    params.set('min_priced_trades', String(minTrades));
    if (watchlistOnly) params.set('watchlist', '1');
    window.location.href = `/smart-money?${params.toString()}`;
  }

  function loosen() {
    const params = new URLSearchParams();
    params.set('sort', 'activity');
    params.set('priced_only', '0');
    window.location.href = `/smart-money?${params.toString()}`;
  }

  return (
    <div className="flex items-center gap-3 text-sm">
      <label className="flex items-center gap-1">
        <span className="text-gray-600">Sort</span>
        <select className="border rounded px-2 py-1" value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="sharpe">Sharpe (90d)</option>
          <option value="pnl">PnL (90d)</option>
          <option value="activity">Activity</option>
          <option value="win_rate">Win Rate</option>
          <option value="last_activity">Last Active</option>
        </select>
      </label>
      <label className="flex items-center gap-2" title="Only include rows with priced trades; enables Sharpe/PnL sorting">
        <input type="checkbox" checked={pricedOnly} onChange={(e) => setPricedOnly(e.target.checked)} />
        <span className="text-gray-600">Priced only</span>
      </label>
      <label className="flex items-center gap-2" title="Limit to qualified watchlist entries">
        <input type="checkbox" checked={watchlistOnly} onChange={(e) => setWatchlistOnly(e.target.checked)} />
        <span className="text-gray-600">Watchlist only</span>
      </label>
      <label className="flex items-center gap-1">
        <span className="text-gray-600" title="Priced trades share over total swaps in 90d">Min coverage</span>
        <input
          type="number"
          min={0}
          max={100}
          className="w-16 border rounded px-2 py-1"
          value={minCoverage}
          onChange={(e) => setMinCoverage(Number(e.target.value))}
          disabled={!pricedOnly}
        />
        <span className="text-gray-600">%</span>
      </label>
      <label className="flex items-center gap-1">
        <span className="text-gray-600" title="Minimum number of priced trades in 90d">Min trades</span>
        <input
          type="number"
          min={0}
          className="w-16 border rounded px-2 py-1"
          value={minTrades}
          onChange={(e) => setMinTrades(Number(e.target.value))}
          disabled={!pricedOnly}
        />
      </label>
      <button onClick={apply} className="border rounded px-3 py-1 bg-blue-600 text-white hover:bg-blue-700">Apply</button>
      <button onClick={loosen} className="border rounded px-3 py-1 text-blue-600 hover:bg-blue-50">Loosen Filters</button>
    </div>
  );
}
