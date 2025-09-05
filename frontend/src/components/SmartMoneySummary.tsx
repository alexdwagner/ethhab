export default function SmartMoneySummary({
  watchlistCount,
  recentActive24h,
  avgSwaps90d,
  generatedAt,
}: {
  watchlistCount: number;
  recentActive24h: number;
  avgSwaps90d: number;
  generatedAt: string;
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
      <div className="border rounded p-3 bg-white">
        <div className="text-xs text-gray-500">Watchlist (qualified)</div>
        <div className="text-2xl font-semibold text-blue-700">{watchlistCount}</div>
      </div>
      <div className="border rounded p-3 bg-white">
        <div className="text-xs text-gray-500">Active in last 24h</div>
        <div className="text-2xl font-semibold text-green-700">{recentActive24h}</div>
      </div>
      <div className="border rounded p-3 bg-white">
        <div className="text-xs text-gray-500">Avg Swaps (watchlist, 90d)</div>
        <div className="text-2xl font-semibold text-purple-700">{avgSwaps90d}</div>
      </div>
      <div className="md:col-span-3 text-xs text-gray-500">Updated: {new Date(generatedAt).toLocaleString()}</div>
    </div>
  );
}

