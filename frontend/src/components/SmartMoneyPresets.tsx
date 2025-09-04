"use client";

function link(params: Record<string, string | number | boolean>) {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => sp.set(k, String(v)));
  return `/smart-money?${sp.toString()}`;
}

export default function SmartMoneyPresets() {
  return (
    <div className="flex items-center gap-2 text-xs">
      <a
        href={link({ sort: 'sharpe', priced_only: 1, min_coverage: 80, min_priced_trades: 10 })}
        className="px-2 py-1 border rounded hover:bg-gray-50"
        title="High confidence: priced-only, coverage≥80%, trades≥10"
      >
        Conservative
      </a>
      <a
        href={link({ sort: 'sharpe', priced_only: 1, min_coverage: 60, min_priced_trades: 5 })}
        className="px-2 py-1 border rounded bg-gray-100 hover:bg-gray-50"
        title="Balanced: priced-only, coverage≥60%, trades≥5"
      >
        Standard
      </a>
      <a
        href={link({ sort: 'sharpe', priced_only: 1, min_coverage: 40, min_priced_trades: 3 })}
        className="px-2 py-1 border rounded hover:bg-gray-50"
        title="Exploratory: priced-only, coverage≥40%, trades≥3"
      >
        Exploratory
      </a>
      <a
        href={link({ sort: 'activity', priced_only: 0 })}
        className="px-2 py-1 border rounded hover:bg-gray-50"
        title="No risk metrics; rank by activity"
      >
        Activity Only
      </a>
    </div>
  );
}

