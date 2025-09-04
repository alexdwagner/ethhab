import SmartMoneyTable from "@/components/SmartMoneyTable";
import SmartMoneyFilters from "@/components/SmartMoneyFilters";
import SmartMoneyPresets from "@/components/SmartMoneyPresets";
import SmartMoneyExport from "@/components/SmartMoneyExport";
import { getHealth, getSmartMoney } from "@/lib/backend";
import { adaptSmartMoneyItem } from "@/lib/adapters";

export const dynamic = "force-dynamic"; // ensure fresh data on each request

export default async function SmartMoneyPage({ searchParams }: { searchParams?: Record<string, string | string[]> }) {
  const sp = Object.fromEntries(
    Object.entries(searchParams || {}).map(([k, v]) => [k, Array.isArray(v) ? v[0] : v])
  ) as Record<string, string>;
  const sort = (sp.sort as any) || 'sharpe';
  const priced_only = sp.priced_only !== undefined
    ? ['1','true','yes','on'].includes((sp.priced_only || '').toLowerCase())
    : true;
  const min_coverage = sp.min_coverage ? Number(sp.min_coverage) : 60;
  const min_trades = sp.min_priced_trades ? Number(sp.min_priced_trades) : 5;

  const res = await getSmartMoney({
    limit: 50,
    // Include candidates by default to increase useful results; gates constrain quality
    sort: sort as any,
    priced_only,
    min_coverage,
    min_priced_trades: min_trades,
  });
  const items = (res.items || []).map(adaptSmartMoneyItem);
  const debug = searchParams?.debug === '1' || process.env.NODE_ENV !== 'production';
  const health = debug ? await getHealth().catch(() => null) : null;

  return (
    <main className="mx-auto max-w-6xl p-6 space-y-4">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold">Smart Money Leaderboard</h1>
          <p className="text-sm text-gray-600">
            Ranked by Sharpe (90d) with coverage gates by default. Adjust filters below.
          </p>
          <div className="mt-1 text-xs text-gray-500">
            Gates: {priced_only ? 'priced_only' : 'all'}{priced_only ? `, cov≥${min_coverage}%` : ''}{priced_only ? `, trades≥${min_trades}` : ''}; sort: {sort}
          </div>
          <div className="mt-2">
            <SmartMoneyPresets />
          </div>
        </div>
        <SmartMoneyFilters
          defaultSort={sort}
          defaultPricedOnly={priced_only}
          defaultMinCoverage={min_coverage}
          defaultMinTrades={min_trades}
        />
      </div>
      <div className="flex items-center justify-between text-sm">
        <div>
          {items.length < 10 && (
            <a
              href="/smart-money?sort=sharpe&priced_only=1&min_coverage=40&min_priced_trades=3"
              className="text-blue-600 hover:underline"
              title="Loosen filters to see more results"
            >
              Too few results? Loosen filters
            </a>
          )}
          {items.length > 100 && (
            <a
              href="/smart-money?sort=sharpe&priced_only=1&min_coverage=80&min_priced_trades=10"
              className="text-blue-600 hover:underline"
              title="Tighten filters to reduce noise"
            >
              Too many results? Tighten filters
            </a>
          )}
        </div>
        <SmartMoneyExport items={items} />
      </div>
      <SmartMoneyTable items={items} />
      {debug && (
        <div className="text-xs text-gray-500 border-t pt-3">
          <div>Items: {items.length}</div>
          <div>Backend: {process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8080'}</div>
          <div>Rendered at: {new Date().toLocaleString()}</div>
          {res && (res as any).fallback_sort && (
            <div className="text-amber-600">Fallback: activity sort (risk metrics unavailable)</div>
          )}
          {health && (
            <div className="mt-1">
              <div>Status: {health.status}</div>
              {typeof health.whale_count !== 'undefined' && (
                <div>Whales in DB: {health.whale_count}</div>
              )}
              {health.response_time_ms && (
                <div>Backend RT: {health.response_time_ms} ms</div>
              )}
            </div>
          )}
        </div>
      )}
    </main>
  );
}
