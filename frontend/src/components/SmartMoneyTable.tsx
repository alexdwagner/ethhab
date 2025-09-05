"use client";

import { useMemo, useState } from "react";
import { SmartMoneyItem } from "../../types/smartMoney";

type Props = {
  items: SmartMoneyItem[];
};

type SortKey = keyof Pick<
  SmartMoneyItem,
  "address" | "dex_swaps_90d" | "unique_protocols_90d" | "sharpe_ratio" | "last_activity_at"
>;

type SortDir = "asc" | "desc";

function fmtDate(iso?: string | null) {
  if (!iso) return "-";
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

function etherscanLink(addr: string) {
  return `https://etherscan.io/address/${addr}`;
}

export default function SmartMoneyTable({ items }: Props) {
  // Sorting
  const [sortKey, setSortKey] = useState<SortKey>("sharpe_ratio");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  // Pagination
  const [pageSize, setPageSize] = useState<number>(25);
  const [page, setPage] = useState<number>(1);

  const sorted = useMemo(() => {
    const data = [...items];
    const dir = sortDir === "asc" ? 1 : -1;
    data.sort((a, b) => {
      const va = (a as any)[sortKey];
      const vb = (b as any)[sortKey];
      // For last_activity_at, compare dates
      if (sortKey === "last_activity_at") {
        const da = va ? new Date(va).getTime() : 0;
        const db = vb ? new Date(vb).getTime() : 0;
        return (da - db) * dir;
      }
      // Numbers first
      const na = typeof va === "number" ? va : Number(va ?? 0);
      const nb = typeof vb === "number" ? vb : Number(vb ?? 0);
      return (na - nb) * dir;
    });
    return data;
  }, [items, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const start = (currentPage - 1) * pageSize;
  const end = start + pageSize;
  const pageItems = sorted.slice(start, end);

  function setSort(next: SortKey) {
    if (sortKey === next) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(next);
      setSortDir("desc");
    }
    setPage(1);
  }

  function SortHeader({ label, k, align = "left" }: { label: string; k: SortKey; align?: "left" | "right" }) {
    const active = sortKey === k;
    const arrow = !active ? "↕" : sortDir === "asc" ? "↑" : "↓";
    const alignClass = align === "right" ? "text-right" : "text-left";
    return (
      <th
        className={`px-3 py-2 font-medium text-gray-600 cursor-pointer hover:bg-gray-100 ${alignClass}`}
        onClick={() => setSort(k)}
      >
        {label} <span className="text-gray-400">{arrow}</span>
      </th>
    );
  }

  return (
    <div className="border rounded-md">
      <div className="flex items-center justify-between px-3 py-2">
        <div className="text-sm text-gray-600">{items.length} entries</div>
        <div className="flex items-center gap-2 text-sm">
          <span>Rows:</span>
          <select
            className="border rounded px-2 py-1"
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(1);
            }}
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <SortHeader label="ENS / Address" k="address" />
              <th className="px-3 py-2 font-medium text-gray-600 text-right" title="Number of DEX swaps seen in 90d">Swaps (90d)</th>
              <th className="px-3 py-2 font-medium text-gray-600 text-right" title="Unique DEX protocols touched in 90d">Protocols</th>
              <th className="px-3 py-2 font-medium text-gray-600 text-right" title="Risk-adjusted performance from priced trades (90d)">Sharpe</th>
              <th className="px-3 py-2 font-medium text-gray-600 text-right" title="Most recent activity timestamp">Last Active</th>
              <th className="px-3 py-2 text-right font-medium text-gray-600">Signals</th>
              <th className="px-3 py-2 text-right font-medium text-gray-600">Actions</th>
            </tr>
          </thead>
          <tbody>
            {pageItems.length === 0 ? (
              <tr>
                <td className="px-3 py-6 text-center text-gray-500" colSpan={5}>
                  No data yet. Try seeding and running discovery.
                </td>
              </tr>
            ) : (
              pageItems.map((row) => (
                <tr key={row.address} className="border-t">
                  <td className="px-3 py-2 text-xs md:text-sm">
                    <div className="flex flex-col">
                      {(row as any)?.ens ? (
                        <span className="font-mono">{(row as any).ens}</span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                      <a
                        href={etherscanLink(row.address)}
                        target="_blank"
                        rel="noreferrer"
                        className="font-mono text-[11px] text-blue-600 hover:underline"
                      >
                        {row.address.slice(0, 10)}...{row.address.slice(-6)}
                      </a>
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right">{row.dex_swaps_90d ?? "-"}</td>
                  <td className="px-3 py-2 text-right">{row.unique_protocols_90d ?? "-"}</td>
                  <td className="px-3 py-2 text-right">
                    {row.sharpe_ratio != null ? row.sharpe_ratio.toFixed(2) : "-"}
                  </td>
                  <td className="px-3 py-2 text-right" title={row.last_activity_at || ''}>{fmtDate(row.last_activity_at)}</td>
                  <td className="px-3 py-2 text-right text-[11px]">
                    <span className={`inline-block px-2 py-0.5 rounded ${((row as any).coverage_pct ?? 0) >= 80 ? 'bg-green-50 text-green-700' : 'bg-gray-50 text-gray-500'}`}
                      title="Coverage: priced trades share in 90d"
                    >
                      {(row as any).coverage_pct != null ? `Cov ${(row as any).coverage_pct}%` : 'Cov —'}
                    </span>
                    {' '}
                    <span className={`inline-block px-2 py-0.5 rounded ${((row as any).unique_protocols_90d ?? 0) >= 3 ? 'bg-blue-50 text-blue-700' : 'bg-gray-50 text-gray-500'}`}
                      title="Unique DEX protocols touched in 90d"
                    >
                      Proto {(row as any).unique_protocols_90d ?? '—'}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      onClick={() => navigator.clipboard.writeText(row.address)}
                      className="border rounded px-2 py-1 text-xs hover:bg-gray-50"
                      title="Copy address"
                    >
                      Copy
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between px-3 py-2 border-t text-sm">
        <div>
          Showing {start + 1}-{Math.min(end, sorted.length)} of {sorted.length}
        </div>
        <div className="flex items-center gap-2">
          <button
            className="border rounded px-2 py-1 disabled:opacity-50"
            disabled={currentPage === 1}
            onClick={() => setPage(1)}
          >
            First
          </button>
          <button
            className="border rounded px-2 py-1 disabled:opacity-50"
            disabled={currentPage === 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Prev
          </button>
          <span>
            Page {currentPage} / {totalPages}
          </span>
          <button
            className="border rounded px-2 py-1 disabled:opacity-50"
            disabled={currentPage === totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            Next
          </button>
          <button
            className="border rounded px-2 py-1 disabled:opacity-50"
            disabled={currentPage === totalPages}
            onClick={() => setPage(totalPages)}
          >
            Last
          </button>
        </div>
      </div>
    </div>
  );
}
