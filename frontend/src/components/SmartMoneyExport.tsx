"use client";

import { SmartMoneyItem } from "../../types/smartMoney";

function toCSV(items: SmartMoneyItem[]): string {
  const headers = [
    'address','ens','dex_swaps_90d','unique_protocols_90d','last_activity_at','sharpe_ratio','win_rate','pnl_usd_90d','coverage_pct','priced_trades_count'
  ];
  const rows = items.map((r: any) => [
    r.address,
    r.ens || '',
    r.dex_swaps_90d ?? '',
    r.unique_protocols_90d ?? '',
    r.last_activity_at ?? '',
    r.sharpe_ratio ?? '',
    r.win_rate ?? '',
    r.pnl_usd_90d ?? '',
    r.coverage_pct ?? '',
    r.priced_trades_count ?? '',
  ]);
  const lines = [headers.join(','), ...rows.map(r => r.join(','))];
  return lines.join('\n');
}

export default function SmartMoneyExport({ items }: { items: SmartMoneyItem[] }) {
  function download() {
    const csv = toCSV(items);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `smart_money_${new Date().toISOString().slice(0,19)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <button onClick={download} className="border rounded px-3 py-1 text-sm hover:bg-gray-50" title="Export current rows to CSV">
      Export CSV
    </button>
  );
}

