#!/usr/bin/env python3
"""
Smart Money CLI
Utilities to support D-018 (Behavior-Based Smart Money Discovery):
- Seed routers/CEX from JSON or inline flags
- Run discovery batch (time-boxed)
- Inspect funnel stats, watchlist, and per-address activity
"""

import argparse
import json
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import config
from src.services.smart_money_discovery import smart_money_discovery
from src.services.ens_service import ens_service
from src.data.smart_money_repository import smart_money_repository
from src.services.pricing_service import pricing_service
from src.services.metrics_service import metrics_service
from src.services.smart_money_discovery import smart_money_discovery


def require_repo():
    if not smart_money_repository:
        print("❌ Database not available (Supabase client not initialized)")
        sys.exit(1)


def require_service():
    if not smart_money_discovery:
        print("❌ Discovery service not available (check configuration)")
        sys.exit(1)


def cmd_seed(args: argparse.Namespace):
    """Seed DEX routers and CEX addresses from JSON files or flags"""
    require_repo()

    routers_file = Path(args.routers or "sample_dex_routers.json")
    cex_file = Path(args.cex or "sample_cex_addresses.json")

    added_routers = 0
    added_cex = 0

    if routers_file.exists():
        data = json.loads(routers_file.read_text())
        for row in data:
            ok = smart_money_repository.add_dex_router(
                address=row.get("address", ""),
                name=row.get("name", row.get("label", "Router")),
                version=row.get("version"),
            )
            if ok:
                added_routers += 1

    if cex_file.exists():
        data = json.loads(cex_file.read_text())
        for row in data:
            ok = smart_money_repository.add_cex_address(
                address=row.get("address", ""),
                exchange_name=row.get("exchange_name", row.get("label", "CEX")),
                address_type=row.get("address_type", "hot_wallet"),
            )
            if ok:
                added_cex += 1

    # Optional single additions via flags
    if args.add_router:
        addr, name = args.add_router.split(":", 1)
        if smart_money_repository.add_dex_router(addr, name):
            added_routers += 1
    if args.add_cex:
        addr, name = args.add_cex.split(":", 1)
        if smart_money_repository.add_cex_address(addr, name):
            added_cex += 1

    print(f"✅ Seed complete: routers={added_routers}, cex={added_cex}")


def cmd_discover(args: argparse.Namespace):
    """Run a bounded discovery batch"""
    require_service()
    # Allow offline mode which skips network calls and relies on DB
    if not config.ETHERSCAN_API_KEY and not args.offline:
        print("❌ ETHERSCAN_API_KEY not configured (.env). Use --offline to run without network.")
        sys.exit(1)

    limit = args.limit
    hours = args.hours
    print(
        f"🚀 Running Smart Money Discovery (limit={limit}, hours_back={hours}, routers={args.max_routers}, "
        f"budget={args.time_budget}s, offline={args.offline})"
    )
    results = smart_money_discovery.discover_smart_money_batch(
        max_candidates=limit,
        hours_back=hours,
        max_routers=args.max_routers,
        time_budget_sec=args.time_budget,
        offline=args.offline,
    )
    print(f"\n✅ Discovery finished. Qualified: {len(results)}")


def cmd_funnel(_args: argparse.Namespace):
    """Show candidate funnel stats"""
    require_repo()
    stats = smart_money_repository.get_candidate_funnel_stats()
    print("📊 Funnel Stats")
    print("-" * 20)
    print(f"Total candidates:   {stats.get('total_candidates', 0)}")
    print(f"Scored traders:     {stats.get('scored_traders', 0)}")
    print(f"Watchlist traders:  {stats.get('watchlist_traders', 0)}")
    print(f"Conversion rate:    {stats.get('conversion_rate', 0):.1f}%")


def cmd_watchlist(args: argparse.Namespace):
    """List watchlist entries (optionally gated by sharpe)"""
    require_repo()
    entries = smart_money_repository.get_smart_money_watchlist(
        min_sharpe=args.min_sharpe, limit=args.limit
    )
    if not entries:
        print("ℹ️  No watchlist entries found (yet)")
        return
    for row in entries:
        addr = row.get("address", "")
        sharpe = row.get("sharpe_ratio")
        swaps = row.get("dex_swaps_90d")
        print(f"• {addr[:10]}...  sharpe={sharpe}  swaps90d={swaps}")


def cmd_activity_show(args: argparse.Namespace):
    """Show activity metrics for a single address"""
    require_service()
    metrics = smart_money_discovery.get_activity_metrics(args.address.lower())
    if not metrics:
        print("❌ No metrics found")
        return
    print(json.dumps(metrics, indent=2, default=str))


def cmd_backfill(args: argparse.Namespace):
    """Backfill interactions for addresses and re-qualify them"""
    require_service()
    from src.data.smart_money_repository import smart_money_repository as repo
    if not repo:
        print("❌ Repository not available")
        return

    addresses: list[str] = []
    if args.address:
        addresses = [args.address.lower()]
    else:
        # Use recent traders as a source pool
        hours = max(24, min(args.hours, 24 * 30))
        pool = repo.get_recent_traders(hours_back=hours, limit=max(args.top, 50))
        addresses = pool[: args.top]

    if not addresses:
        print("ℹ️  No addresses to backfill")
        return

    print(f"🏗️  Backfilling {len(addresses)} addresses for {args.days} days (tx_limit={args.tx_limit}, budget={args.time_budget}s, timeout={args.timeout}s)...")
    total_logged = 0
    qualified = 0
    for i, addr in enumerate(addresses, 1):
        if i % 25 == 0:
            print(f"   {i}/{len(addresses)} processed...")
        logged = smart_money_discovery.backfill_address_interactions(
            addr,
            days=args.days,
            max_tx=args.tx_limit,
            time_budget_sec=args.time_budget,
            request_timeout_sec=args.timeout,
        )
        total_logged += logged
        res = smart_money_discovery.qualify_as_smart_money(addr)
        if res.get('qualifies_smart_money'):
            qualified += 1
        time.sleep(0.2)
    print(f"✅ Backfill complete. Logged ~{total_logged} interactions; newly qualified: {qualified}")


def cmd_price(args: argparse.Namespace):
    """Price trades for addresses and update coverage (D-019 skeleton)."""
    require_repo()
    if not pricing_service:
        print("❌ Pricing service not available")
        return

    # Build address list
    if args.address:
        addresses = [args.address.lower()]
    else:
        # Prefer watchlist addresses first, then fall back to recent traders
        try:
            wl = smart_money_repository.get_smart_money_watchlist(min_sharpe=0.0, limit=args.top)
            addresses = [r.get('address') for r in (wl or []) if r.get('address')]
        except Exception:
            addresses = []
        if not addresses:
            pool = smart_money_repository.get_recent_traders(hours_back=min(args.days * 24, 24 * 30), limit=max(args.top, 50))
            addresses = pool[: args.top]

    if not addresses:
        print("ℹ️  No addresses to price")
        return

    total = len(addresses)
    print(f"🏷️  Pricing {total} addresses for {args.days} days (budget/address={args.time_budget}s)\n")
    started = time.time()
    totals = {"checked": 0, "priced_new": 0}

    def progress(i: int):
        width = 28
        done = int((i / total) * width)
        bar = "#" * done + "." * (width - done)
        elapsed = time.time() - started
        print(
            f"\r[{bar}] {i}/{total}  checked:{totals['checked']}  priced:{totals['priced_new']}  t={elapsed:0.1f}s",
            end="",
            flush=True,
        )

    for i, addr in enumerate(addresses, 1):
        res = pricing_service.price_address(
            addr,
            days=args.days,
            time_budget_sec=max(30, int(args.time_budget)),
            debug=getattr(args, 'debug', False),
        )
        totals["checked"] += res.get("checked", 0)
        totals["priced_new"] += res.get("priced_new", 0)
        progress(i)
        if not getattr(args, 'quiet', False):
            # Per-address concise line under the progress bar
            short = f"{addr[:10]}...{addr[-6:]}"
            cov = res.get("coverage_pct")
            pts = res.get("priced_trades_count")
            tots = res.get("total_swaps")
            print(
                f"\n  ✓ {short}  checked:{res.get('checked',0)}  priced+:{res.get('priced_new',0)}  coverage:{cov}% ({pts}/{tots})",
                flush=True,
            )
            time.sleep(0.05)

    # Final progress line
    progress(total)
    print()
    elapsed = round(time.time() - started, 1)
    print(f"\n✅ Pricing pass complete in {elapsed}s. Checked {totals['checked']} txs; newly priced ~{totals['priced_new']}.")


def cmd_metrics(args: argparse.Namespace):
    """Compute rolling 90d metrics for addresses and update trader_metrics (D-020)."""
    require_repo()
    if not metrics_service:
        print("❌ Metrics service not available")
        return

    # Build address list
    addresses: list[str] = []
    if args.address:
        addresses = [args.address.lower()]
    else:
        try:
            wl = smart_money_repository.get_smart_money_watchlist(min_sharpe=0.0, limit=args.top)
            addresses = [r.get('address') for r in (wl or []) if r.get('address')]
        except Exception:
            addresses = []
        if not addresses:
            pool = smart_money_repository.get_recent_traders(hours_back=args.hours, limit=max(args.top, 50))
            addresses = pool[: args.top]
    if not addresses:
        print("ℹ️  No addresses to compute metrics for")
        return

    total = len(addresses)
    print(f"📈 Computing metrics for {total} addresses (window={args.days}d)\n")
    started = time.time()
    for i, addr in enumerate(addresses, 1):
        m = metrics_service.compute_for_address(addr, days=args.days)
        if not args.quiet:
            print(f"  ✓ {addr[:10]}... metrics: pnl={m.get('pnl_usd_90d')} win={m.get('win_rate')} sharpe={m.get('sharpe_90d')} cov={m.get('coverage_pct')}%")
        if i % 25 == 0:
            print(f"   {i}/{total} done...")
        time.sleep(0.05)
    elapsed = round(time.time() - started, 1)
    print(f"✅ Metrics computation complete in {elapsed}s")


def cmd_activity(args: argparse.Namespace):
    """Backfill address activity (dex swaps, last_activity_at) for addresses using discovery service."""
    if not smart_money_discovery:
        print("❌ Discovery service not available")
        return
    if not smart_money_repository:
        print("❌ Repository not available")
        return
    addresses: list[str] = []
    if args.address:
        addresses = [args.address.lower()]
    else:
        wl = smart_money_repository.get_smart_money_watchlist(min_sharpe=0.0, limit=args.top) or []
        addresses = [r.get('address') for r in wl if r.get('address')]
        if not addresses:
            pool = smart_money_repository.get_recent_traders(hours_back=args.hours, limit=max(args.top, 50))
            addresses = pool[: args.top]
    if not addresses:
        print("ℹ️  No addresses for activity backfill")
        return
    print(f"📒 Backfilling activity for {len(addresses)} addresses (window={args.days}d)...")
    for i, addr in enumerate(addresses, 1):
        _ = smart_money_discovery.get_activity_metrics(addr)
        if i % 25 == 0:
            print(f"   {i}/{len(addresses)}...")
        time.sleep(0.05)
    print("✅ Activity backfill complete")


def cmd_refresh(args: argparse.Namespace):
    """Run price -> metrics -> activity-backfill in one pass for a cohort.

    Steps:
    1) Price recent trades (stable/ETH/leading ERC-20s) for --top addresses (lookback: --price-days)
    2) Compute metrics (90d by default) for the same addresses (lookback: --metrics-days)
    3) Backfill address_activity (dex swaps, last_activity_at) (lookback: --activity-days)
    """
    require_repo()
    if not pricing_service or not metrics_service or not smart_money_discovery:
        print("❌ Required services not available")
        return

    # Build address list (prefer watchlist, then recent traders)
    if args.address:
        addresses = [args.address.lower()]
    else:
        addresses = []
        try:
            wl = smart_money_repository.get_smart_money_watchlist(min_sharpe=0.0, limit=args.top) or []
            addresses.extend([r.get('address') for r in wl if r.get('address')])
        except Exception:
            pass
        if len(addresses) < args.top:
            pool = smart_money_repository.get_recent_traders(hours_back=args.hours, limit=max(args.top * 2, 100))
            for a in pool:
                if a not in addresses:
                    addresses.append(a)
                if len(addresses) >= args.top:
                    break

    if not addresses:
        print("ℹ️  No addresses to process")
        return

    total = len(addresses)
    print(f"🔁 Refresh pipeline for {total} addresses")

    # 1) Backfill dex interactions (improves activity + swap counts)
    print(f"🏗️  Backfill interactions: days={args.activity_days}")
    total_logged = 0
    for i, addr in enumerate(addresses, 1):
        try:
            logged = smart_money_discovery.backfill_address_interactions(addr, days=args.activity_days)
            total_logged += int(logged)
        except Exception:
            pass
        if not args.quiet and i % 25 == 0:
            print(f"   backfilled ~{total_logged} interactions  {i}/{total}")
        time.sleep(0.05)
    print(f"   ✔ backfilled ~{total_logged} interactions")

    # 2) Price
    print(f"🏷️  Pricing step: days={args.price_days} budget/address={args.time_budget}s")
    priced_new = 0
    checked = 0
    for i, addr in enumerate(addresses, 1):
        res = pricing_service.price_address(
            addr,
            days=args.price_days,
            time_budget_sec=max(30, int(args.time_budget)),
            debug=getattr(args, 'debug', False),
        )
        priced_new += int(res.get('priced_new', 0))
        checked += int(res.get('checked', 0))
        if not args.quiet and i % 25 == 0:
            print(f"   priced+ {priced_new} (checked {checked})  {i}/{total}")
        time.sleep(0.05)
    print(f"   ✔ priced+ ~{priced_new} across {checked} checked txs")

    # 3) Metrics
    print(f"📈 Metrics step: window={args.metrics_days}d")
    for i, addr in enumerate(addresses, 1):
        _ = metrics_service.compute_for_address(addr, days=args.metrics_days)
        if not args.quiet and i % 25 == 0:
            print(f"   {i}/{total} metrics updated")
        time.sleep(0.05)
    print("   ✔ metrics updated")

    # 4) Activity backfill (populate last_activity_at / counts summaries)
    print(f"📒 Activity step: window={args.activity_days}d")
    for i, addr in enumerate(addresses, 1):
        _ = smart_money_discovery.get_activity_metrics(addr)
        if not args.quiet and i % 25 == 0:
            print(f"   {i}/{total} activity updated")
        time.sleep(0.05)
    print("   ✔ activity updated")
    print("✅ Refresh pipeline complete")


def cmd_stats(args: argparse.Namespace):
    """Print qualified counts under strict/loose gates using Supabase client (no DB password)."""
    from src.data.supabase_client import supabase_client as sc
    if not sc:
        print("❌ Supabase client not initialized")
        return
    client = sc.get_client()
    # Build queries from args
    strict_trades = int(args.strict_trades)
    strict_cov = float(args.strict_cov)
    loose_trades = int(args.loose_trades)
    loose_cov = float(args.loose_cov)
    queries = [
        ("qualified_strict",
         f"SELECT COUNT(*) AS qualified_strict FROM smart_money_candidates WHERE priced_trades_count >= {strict_trades} AND coverage_pct >= {strict_cov};"),
        ("qualified_loose",
         f"SELECT COUNT(*) AS qualified_loose FROM smart_money_candidates WHERE priced_trades_count >= {loose_trades} AND coverage_pct >= {loose_cov};"),
        ("watchlist_strict",
         f"SELECT COUNT(*) AS watchlist_strict FROM smart_money_candidates WHERE qualifies_smart_money=TRUE AND priced_trades_count >= {strict_trades} AND coverage_pct >= {strict_cov};"),
    ]
    for name, q in queries:
        try:
            res = client.rpc('sql', {'query': q}).execute()
            print(name, res.data)
        except Exception as e:
            print(name, 'error:', e)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Smart Money Discovery CLI")
    sub = p.add_subparsers(dest="command")

    sp = sub.add_parser("seed", help="Seed routers/CEX from JSON or flags")
    sp.add_argument("--routers", help="Path to routers JSON (default: sample_dex_routers.json)")
    sp.add_argument("--cex", help="Path to CEX JSON (default: sample_cex_addresses.json)")
    sp.add_argument("--add-router", help="Add one router '0xaddr:Name'")
    sp.add_argument("--add-cex", help="Add one CEX '0xaddr:ExchangeName'")
    sp.set_defaults(func=cmd_seed)

    sp = sub.add_parser("discover", help="Run bounded discovery batch")
    sp.add_argument("--limit", type=int, default=100, help="Max candidates to process")
    sp.add_argument("--hours", type=int, default=24, help="Lookback window in hours for DEX scans (default: 24)")
    sp.add_argument("--max-routers", type=int, default=None, help="Max DEX routers to scan (overrides env)")
    sp.add_argument("--time-budget", type=int, default=None, help="Time budget in seconds (overrides env)")
    sp.add_argument("--offline", action="store_true", help="Disable network calls; use DB-only fallback")
    sp.set_defaults(func=cmd_discover)

    sp = sub.add_parser("funnel", help="Show candidate funnel stats")
    sp.set_defaults(func=cmd_funnel)

    sp = sub.add_parser("watchlist", help="List watchlist entries")
    sp.add_argument("--min-sharpe", type=float, default=1.0)
    sp.add_argument("--limit", type=int, default=50)
    sp.set_defaults(func=cmd_watchlist)

    sp = sub.add_parser("activity", help="Show per-address activity metrics")
    sp.add_argument("address", help="Ethereum address")
    sp.set_defaults(func=cmd_activity_show)

    sp = sub.add_parser("backfill", help="Backfill 90d interactions for addresses and re-qualify (bounded)")
    sp.add_argument("--address", help="Single address to backfill")
    sp.add_argument("--top", type=int, default=100, help="Top recent traders to backfill (when no --address)")
    sp.add_argument("--days", type=int, default=90, help="Days to backfill (default: 90)")
    sp.add_argument("--hours", type=int, default=168, help="Recent window (hours) to select pool (default: 168)")
    sp.add_argument("--tx-limit", type=int, default=None, help="Max tx to request per address (overrides env)")
    sp.add_argument("--time-budget", type=int, default=None, help="Per-address time budget seconds (overrides env)")
    sp.add_argument("--timeout", type=float, default=None, help="Per-request timeout seconds (overrides env)")
    sp.set_defaults(func=cmd_backfill)

    sp = sub.add_parser("price", help="Price trades and update coverage (D-019)")
    sp.add_argument("--address", help="Single address to price")
    sp.add_argument("--top", type=int, default=50, help="Top addresses to price when no --address")
    sp.add_argument("--days", type=int, default=90, help="Days to price (default: 90)")
    sp.add_argument("--time-budget", type=int, default=300, help="Per-address time budget seconds")
    sp.add_argument("--quiet", action="store_true", help="Show only progress bar (suppress per-address lines)")
    sp.add_argument("--debug", action="store_true", help="Verbose per-tx debug for first few matches per address")
    sp.set_defaults(func=cmd_price)

    sp = sub.add_parser("metrics", help="Compute 90d metrics (PnL/Sharpe/win) for addresses (D-020)")
    sp.add_argument("--address", help="Single address")
    sp.add_argument("--top", type=int, default=50, help="Top addresses (watchlist or recent) when no --address")
    sp.add_argument("--days", type=int, default=90, help="Days window (default: 90)")
    sp.add_argument("--hours", type=int, default=720, help="Recent trader pool hours when no watchlist (default: 720)")
    sp.add_argument("--quiet", action="store_true")
    sp.set_defaults(func=cmd_metrics)

    sp = sub.add_parser("activity-backfill", help="Backfill address_activity (last_active, swaps) for addresses")
    sp.add_argument("--address", help="Single address")
    sp.add_argument("--top", type=int, default=50)
    sp.add_argument("--days", type=int, default=90)
    sp.add_argument("--hours", type=int, default=720)
    sp.set_defaults(func=cmd_activity)

    sp = sub.add_parser("refresh", help="Run price -> metrics -> activity-backfill for a cohort")
    sp.add_argument("--address", help="Single address")
    sp.add_argument("--top", type=int, default=50)
    sp.add_argument("--hours", type=int, default=720, help="Recent trader pool hours (when no watchlist)")
    sp.add_argument("--price-days", type=int, default=30)
    sp.add_argument("--metrics-days", type=int, default=90)
    sp.add_argument("--activity-days", type=int, default=90)
    sp.add_argument("--time-budget", type=int, default=180)
    sp.add_argument("--quiet", action="store_true")
    sp.add_argument("--debug", action="store_true")
    sp.set_defaults(func=cmd_refresh)

    sp = sub.add_parser("stats", help="Show qualified counts under gate presets")
    sp.add_argument("--strict-trades", type=int, default=5)
    sp.add_argument("--strict-cov", type=float, default=60)
    sp.add_argument("--loose-trades", type=int, default=3)
    sp.add_argument("--loose-cov", type=float, default=40)
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("ens", help="Resolve ENS for addresses and cache results")
    sp.add_argument("--address", help="Single address")
    sp.add_argument("--top", type=int, default=50)
    sp.add_argument("--hours", type=int, default=720)
    sp.add_argument("--force", action="store_true", help="Bypass cache TTL")
    def _cmd_ens(args: argparse.Namespace):
        if not ens_service or not smart_money_repository:
            print("❌ ENS service not available")
            return
        if args.address:
            addrs = [args.address.lower()]
        else:
            wl = smart_money_repository.get_smart_money_watchlist(min_sharpe=0.0, limit=args.top) or []
            addrs = [r.get('address') for r in wl if r.get('address')]
            if not addrs:
                pool = smart_money_repository.get_recent_traders(hours_back=args.hours, limit=max(args.top, 50))
                addrs = pool[: args.top]
        if not addrs:
            print("ℹ️  No addresses to resolve")
            return
        print(f"🔎 Resolving ENS for {len(addrs)} addresses...")
        for i, a in enumerate(addrs, 1):
            name = ens_service.resolve(a, force=bool(args.force))
            if name:
                print(f"  ✓ {a[:10]}... → {name}")
            elif i % 25 == 0:
                print(f"   {i}/{len(addrs)}...")
            time.sleep(0.05)
        print("✅ ENS resolution complete")
    sp.set_defaults(func=_cmd_ens)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
