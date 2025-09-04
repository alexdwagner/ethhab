#!/usr/bin/env python3
"""
Smart Money Repository
Database operations for smart money discovery and tracking
"""

from typing import List, Dict, Optional
from datetime import datetime
from .supabase_client import supabase_client

class SmartMoneyRepository:
    """Repository for smart money data operations"""
    
    def __init__(self):
        if not supabase_client:
            raise ValueError("Supabase client not initialized")
        self.client = supabase_client.get_client()
    
    # DEX Router Management
    def get_dex_routers(self, active_only: bool = True) -> List[Dict]:
        """Get all DEX router addresses from database"""
        try:
            query = self.client.table('dex_routers').select('*')
            if active_only:
                query = query.eq('is_active', True)
            result = query.execute()
            return result.data
        except Exception as e:
            print(f"Error getting DEX routers: {e}")
            return []
    
    def add_dex_router(self, address: str, name: str, version: str = None) -> bool:
        """Add a new DEX router to the registry"""
        try:
            data = {
                'address': address.lower(),
                'name': name,
                'version': version,
                'is_active': True
            }
            result = self.client.table('dex_routers').insert(data).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error adding DEX router: {e}")
            return False
    
    # CEX Address Management
    def get_cex_addresses(self, active_only: bool = True) -> List[Dict]:
        """Get all CEX addresses from database"""
        try:
            query = self.client.table('cex_addresses').select('*')
            if active_only:
                query = query.eq('is_active', True)
            result = query.execute()
            return result.data
        except Exception as e:
            print(f"Error getting CEX addresses: {e}")
            return []
    
    def add_cex_address(self, address: str, exchange_name: str, address_type: str = 'hot_wallet') -> bool:
        """Add a new CEX address to the registry"""
        try:
            data = {
                'address': address.lower(),
                'exchange_name': exchange_name,
                'address_type': address_type,
                'is_active': True
            }
            result = self.client.table('cex_addresses').insert(data).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error adding CEX address: {e}")
            return False
    
    # Contract Exclusion Management
    def get_excluded_contracts(self) -> List[str]:
        """Get list of contract addresses to exclude"""
        try:
            result = self.client.table('known_contracts').select('address').eq('should_exclude', True).execute()
            return [row['address'] for row in result.data]
        except Exception as e:
            print(f"Error getting excluded contracts: {e}")
            return []
    
    def add_known_contract(self, address: str, contract_type: str, name: str = None, should_exclude: bool = True) -> bool:
        """Add a known contract for exclusion"""
        try:
            data = {
                'address': address.lower(),
                'contract_type': contract_type,
                'name': name,
                'should_exclude': should_exclude
            }
            result = self.client.table('known_contracts').insert(data).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error adding known contract: {e}")
            return False
    
    # Address Activity Tracking
    def update_address_activity(self, address: str, activity_data: Dict) -> bool:
        """Update or insert address activity metrics"""
        try:
            data = {
                'address': address.lower(),
                'dex_swap_count': activity_data.get('dex_swap_count', 0),
                'unique_protocols': activity_data.get('unique_protocols', 0),
                'total_gas_spent_eth': activity_data.get('total_gas_spent_eth', 0),
                'first_seen_at': activity_data.get('first_seen_at'),
                'last_activity_at': activity_data.get('last_activity_at'),
                'withdrew_from_cex': activity_data.get('withdrew_from_cex', False),
                'uses_defi': activity_data.get('uses_defi', False),
                'is_contract': activity_data.get('is_contract', False),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            result = self.client.table('address_activity').upsert(
                data,
                on_conflict='address'
            ).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error updating address activity: {e}")
            return False
    
    def get_address_activity(self, address: str) -> Optional[Dict]:
        """Get activity metrics for an address"""
        try:
            result = self.client.table('address_activity').select('*').eq('address', address.lower()).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting address activity: {e}")
            return None
    
    # DEX Interaction Logging
    def log_dex_interaction(self, address: str, router_address: str, tx_data: Dict) -> bool:
        """Log a DEX interaction with idempotency on tx_hash."""
        try:
            data = {
                'address': address.lower(),
                'router_address': router_address.lower(),
                'tx_hash': tx_data.get('tx_hash'),
                'block_number': tx_data.get('block_number'),
                'timestamp': tx_data.get('timestamp'),
                'gas_spent_eth': tx_data.get('gas_spent_eth', 0)
            }
            # Upsert ensures re-runs don't fail on unique tx_hash
            result = self.client.table('dex_interactions').upsert(
                data,
                on_conflict='tx_hash'
            ).execute()
            # Some PostgREST versions return no data for upsert; treat as success
            return True
        except Exception as e:
            # Treat duplicate key as benign
            msg = str(e)
            if 'duplicate key value violates unique constraint' in msg or '23505' in msg:
                return True
            print(f"Error logging DEX interaction: {e}")
            return False
    
    def get_dex_interactions(self, address: str, days: int = 90) -> List[Dict]:
        """Get DEX interactions for an address in the last N days"""
        try:
            from datetime import timedelta
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            result = self.client.table('dex_interactions').select('*').eq(
                'address', address.lower()
            ).gte('timestamp', cutoff_date).execute()
            
            return result.data
        except Exception as e:
            print(f"Error getting DEX interactions: {e}")
            return []

    # Pricing Schema (D-019.1)
    # tx_receipts_cache helpers
    def get_cached_receipt(self, tx_hash: str) -> Optional[Dict]:
        try:
            res = self.client.table('tx_receipts_cache').select('*').eq('tx_hash', tx_hash).limit(1).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            print(f"Error fetching cached receipt: {e}")
            return None

    def upsert_receipt_cache(self, tx_hash: str, block_ts: str, status: int, logs_json: Dict, meta: Dict = None) -> bool:
        try:
            data = {
                'tx_hash': tx_hash,
                'block_ts': block_ts,
                'status': status,
                'logs_json': logs_json,
                'block_number': (meta or {}).get('block_number'),
                'from_address': (meta or {}).get('from_address'),
                'to_address': (meta or {}).get('to_address'),
                'fetched_at': datetime.utcnow().isoformat(),
            }
            self.client.table('tx_receipts_cache').upsert(data, on_conflict='tx_hash').execute()
            return True
        except Exception as e:
            print(f"Error upserting receipt cache: {e}")
            return False

    # priced_trades helpers
    def upsert_priced_trade(self, trade: Dict) -> bool:
        try:
            # Expect keys as defined in schema; tx_hash must be present
            if not trade.get('tx_hash'):
                return False
            self.client.table('priced_trades').upsert(trade, on_conflict='tx_hash').execute()
            return True
        except Exception as e:
            # Ignore duplicate unique violations
            if 'duplicate key' in str(e) or '23505' in str(e):
                return True
            print(f"Error upserting priced trade: {e}")
            return False

    def count_priced_trades(self, address: str, days: int = 90) -> int:
        try:
            from datetime import timedelta
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            res = self.client.table('priced_trades').select('id', count='exact').eq('address', address.lower()).gte('block_ts', cutoff).execute()
            return res.count or 0
        except Exception as e:
            print(f"Error counting priced trades: {e}")
            return 0

    def get_recent_interactions_for_address(self, address: str, days: int = 90, limit: int = 2000) -> List[Dict]:
        try:
            from datetime import timedelta
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            res = self.client.table('dex_interactions').select('tx_hash,router_address,timestamp').eq('address', address.lower()).gte('timestamp', cutoff).order('timestamp', desc=True).limit(limit).execute()
            return res.data or []
        except Exception as e:
            print(f"Error fetching recent interactions: {e}")
            return []

    def update_coverage_for_address(self, address: str, days: int = 90) -> Dict:
        """Compute coverage_pct and priced_trades_count for an address and update candidates row."""
        try:
            priced = self.count_priced_trades(address, days=days)
            # Compute total_swaps within the same lookback window to match priced count
            from datetime import timedelta
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            di = self.client.table('dex_interactions').select('id', count='exact').eq('address', address.lower()).gte('timestamp', cutoff).execute()
            total_swaps = di.count or 0
            coverage = 0.0
            if total_swaps > 0:
                coverage = round(min(100.0, 100.0 * priced / float(total_swaps)), 2)
            # Update candidate row
            self.client.table('smart_money_candidates').upsert({
                'address': address.lower(),
                'priced_trades_count': priced,
                'coverage_pct': coverage,
                'last_priced_at': datetime.utcnow().isoformat(),
            }, on_conflict='address').execute()
            return {'priced_trades_count': priced, 'coverage_pct': coverage, 'total_swaps': total_swaps}
        except Exception as e:
            print(f"Error updating coverage: {e}")
            return {'priced_trades_count': 0, 'coverage_pct': 0.0, 'total_swaps': 0}

    # Trader metrics (D-020)
    def get_priced_trades_for_address(self, address: str, days: int = 90) -> List[Dict]:
        try:
            from datetime import timedelta
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            res = self.client.table('priced_trades').select('usd_in,usd_out,block_ts').eq('address', address.lower()).gte('block_ts', cutoff).order('block_ts', desc=True).execute()
            return res.data or []
        except Exception as e:
            print(f"Error fetching priced trades: {e}")
            return []

    def upsert_trader_metrics(self, address: str, metrics: Dict, window: str = '90d') -> bool:
        try:
            data = {
                'address': address.lower(),
                'metrics_window': window,
                'priced_trades_count': int(metrics.get('priced_trades_count', 0)),
                'coverage_pct': metrics.get('coverage_pct'),
                'pnl_usd_90d': metrics.get('pnl_usd_90d'),
                'win_rate': metrics.get('win_rate'),
                'sharpe_90d': metrics.get('sharpe_90d'),
                'max_drawdown_usd': metrics.get('max_drawdown_usd'),
                'updated_at': datetime.utcnow().isoformat(),
            }
            self.client.table('trader_metrics').upsert(data, on_conflict='address,metrics_window').execute()
            return True
        except Exception as e:
            print(f"Error upserting trader metrics: {e}")
            return False

    def get_trader_metrics_bulk(self, addresses: List[str], window: str = '90d') -> Dict[str, Dict]:
        try:
            if not addresses:
                return {}
            res = self.client.table('trader_metrics').select('*').eq('metrics_window', window).in_('address', [a.lower() for a in addresses]).execute()
            rows = res.data or []
            return {r['address']: r for r in rows}
        except Exception as e:
            print(f"Error fetching trader metrics bulk: {e}")
            return {}

    # Token metadata / price cache
    def get_token_metadata(self, address: str) -> Optional[Dict]:
        try:
            res = self.client.table('token_metadata').select('*').eq('address', address.lower()).limit(1).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            print(f"Error getting token metadata: {e}")
            return None

    def upsert_token_metadata(self, meta: Dict) -> bool:
        try:
            if not meta.get('address'):
                return False
            self.client.table('token_metadata').upsert(meta, on_conflict='address').execute()
            return True
        except Exception as e:
            print(f"Error upserting token metadata: {e}")
            return False

    def get_cached_token_price(self, address: str, ts_bucket: str) -> Optional[float]:
        try:
            res = self.client.table('token_prices').select('usd').eq('address', address.lower()).eq('ts_bucket', ts_bucket).limit(1).execute()
            if res.data:
                return float(res.data[0]['usd'])
            return None
        except Exception as e:
            print(f"Error getting cached token price: {e}")
            return None

    def upsert_token_price(self, address: str, ts_bucket: str, usd: float, source: str = 'coingecko') -> bool:
        try:
            data = {
                'address': address.lower(),
                'ts_bucket': ts_bucket,
                'usd': usd,
                'source': source,
                'fetched_at': datetime.utcnow().isoformat(),
            }
            self.client.table('token_prices').upsert(data, on_conflict='address,ts_bucket').execute()
            return True
        except Exception as e:
            print(f"Error upserting token price: {e}")
            return False
    
    # Smart Money Candidate Management
    def update_smart_money_candidate(self, address: str, metrics: Dict) -> bool:
        """Update or insert smart money candidate"""
        try:
            data = {
                'address': address.lower(),
                'status': metrics.get('status', 'candidate'),
                'dex_swaps_90d': metrics.get('dex_swaps_90d', 0),
                'volume_90d_usd': metrics.get('volume_90d_usd'),
                'sharpe_ratio': metrics.get('sharpe_ratio'),
                'win_rate': metrics.get('win_rate'),
                'confidence_score': metrics.get('confidence_score'),
                'qualifies_smart_money': metrics.get('qualifies_smart_money', False),
                'last_evaluated_at': datetime.utcnow().isoformat()
            }
            
            result = self.client.table('smart_money_candidates').upsert(
                data,
                on_conflict='address'
            ).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error updating smart money candidate: {e}")
            return False
    
    def get_smart_money_watchlist(self, min_sharpe: float = 1.0, limit: int = 100) -> List[Dict]:
        """Get smart money traders that qualify for the watchlist"""
        try:
            result = self.client.table('smart_money_candidates').select('*').eq(
                'qualifies_smart_money', True
            ).gte('sharpe_ratio', min_sharpe).order(
                'sharpe_ratio', desc=True
            ).limit(limit).execute()
            
            return result.data
        except Exception as e:
            print(f"Error getting smart money watchlist: {e}")
            return []
    
    def get_candidate_funnel_stats(self) -> Dict:
        """Get statistics on the candidate funnel"""
        try:
            # Count candidates at each stage
            all_candidates = self.client.table('smart_money_candidates').select('id', count='exact').execute()
            scored = self.client.table('smart_money_candidates').select('id', count='exact').eq('status', 'scored').execute()
            watchlist = self.client.table('smart_money_candidates').select('id', count='exact').eq('status', 'watchlist').execute()
            
            return {
                'total_candidates': all_candidates.count or 0,
                'scored_traders': scored.count or 0,
                'watchlist_traders': watchlist.count or 0,
                'conversion_rate': (watchlist.count / all_candidates.count * 100) if all_candidates.count else 0
            }
        except Exception as e:
            print(f"Error getting funnel stats: {e}")
            return {
                'total_candidates': 0,
                'scored_traders': 0,
                'watchlist_traders': 0,
                'conversion_rate': 0
            }

    # Discovery helpers
    def get_recent_traders(self, hours_back: int = 24, limit: int = 500) -> List[str]:
        """Return distinct addresses seen in dex_interactions within the lookback window."""
        try:
            from datetime import datetime, timedelta
            cutoff = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat()
            # Fetch most recent interactions, then distinct addresses in code
            res = self.client.table('dex_interactions').select('address,timestamp').gte(
                'timestamp', cutoff
            ).order('timestamp', desc=True).limit(max(limit * 5, 1000)).execute()
            rows = res.data or []
            seen = []
            added = set()
            for r in rows:
                addr = (r.get('address') or '').lower()
                if addr and addr not in added:
                    added.add(addr)
                    seen.append(addr)
                    if len(seen) >= limit:
                        break
            return seen
        except Exception as e:
            print(f"Error getting recent traders: {e}")
            return []

    # Leaderboard Aggregation (fallback without DB views)
    def get_smart_money_leaderboard(self, limit: int = 50, min_dex_swaps: int = 10,
                                    active_within_days: int = 30,
                                    sort: str = 'auto',
                                    priced_only: bool = False,
                                    min_coverage: float = None,
                                    min_priced_trades: int = None) -> (List[Dict], bool):
        """Assemble a lightweight leaderboard by joining candidates with activity in app code.

        Sorting preference:
        - If sharpe_ratio present and >= 10 priced trades coverage in future, sort by sharpe_ratio desc
        - Otherwise fallback to dex_swap_count desc, last_activity_at desc
        """
        try:
            # Fetch candidate rows (oversample to allow filtering)
            cand_res = self.client.table('smart_money_candidates').select('*').order(
                'dex_swaps_90d', desc=True
            ).limit(max(limit * 4, 100)).execute()
            candidates = cand_res.data or []

            if not candidates:
                return [], False

            # Gather addresses for bulk activity query
            addresses = [c['address'] for c in candidates if c.get('address')]
            # Bulk fetch activity
            act_query = self.client.table('address_activity').select('*')
            # Supabase Python client supports in_ filter
            act_res = act_query.in_('address', addresses).execute()
            activities = {a['address']: a for a in (act_res.data or [])}

            # Combine and filter
            combined: List[Dict] = []
            from datetime import timedelta
            cutoff = (datetime.utcnow() - timedelta(days=active_within_days)).isoformat()

            for c in candidates:
                addr = c.get('address')
                a = activities.get(addr, {})
                dex_swaps = a.get('dex_swap_count', c.get('dex_swaps_90d', 0) or 0)
                last_activity = a.get('last_activity_at')

                if dex_swaps < min_dex_swaps:
                    continue
                if last_activity and last_activity < cutoff:
                    continue

                row = {
                    'address': addr,
                    'status': c.get('status', 'candidate'),
                    'dex_swaps_90d': dex_swaps,
                    'unique_protocols_90d': a.get('unique_protocols'),
                    'last_activity_at': last_activity,
                    'total_gas_spent_eth': a.get('total_gas_spent_eth'),
                    'sharpe_ratio': c.get('sharpe_ratio'),
                    'win_rate': c.get('win_rate'),
                    'volume_90d_usd': c.get('volume_90d_usd'),
                    # Placeholders for D-019 coverage metrics
                    'coverage_pct': c.get('coverage_pct'),
                    'priced_trades_count': c.get('priced_trades_count'),
                }
                # Apply priced-only gating if requested
                if priced_only:
                    cov = row.get('coverage_pct') or 0
                    pct_min = min_coverage if min_coverage is not None else 60
                    pt_min = min_priced_trades if min_priced_trades is not None else 10
                    if (row.get('priced_trades_count') or 0) < pt_min or cov < pct_min:
                        continue
                combined.append(row)

            # Attach ENS from whales labels (simple heuristic) and ens_cache
            try:
                lbl_res = self.client.table('whales').select('address,label').in_('address', addresses).execute()
                labels = {w['address']: w.get('label') for w in (lbl_res.data or [])}
                ens_rows = self.client.table('ens_cache').select('address,ens').in_('address', addresses).execute()
                ens_map = {e['address']: e.get('ens') for e in (ens_rows.data or [])}
            except Exception:
                labels, ens_map = {}, {}

            # Attach trader metrics (D-020)
            metrics = self.get_trader_metrics_bulk([r['address'] for r in combined])
            for r in combined:
                m = metrics.get(r['address']) or {}
                if m:
                    if m.get('sharpe_90d') is not None:
                        r['sharpe_ratio'] = m.get('sharpe_90d')
                    if m.get('win_rate') is not None:
                        r['win_rate'] = m.get('win_rate')
                    if m.get('pnl_usd_90d') is not None:
                        r['pnl_usd_90d'] = m.get('pnl_usd_90d')
                # ENS from label if present
                lbl = labels.get(r['address'])
                if lbl and '.eth' in lbl:
                    r['ens'] = lbl
                elif ens_map.get(r['address']):
                    r['ens'] = ens_map.get(r['address'])

            # Sorting
            fallback = False
            s = (sort or 'auto').lower()
            if s in ('sharpe', 'auto'):
                sharpe_present = any((r.get('sharpe_ratio') is not None) for r in combined)
                if sharpe_present:
                    combined.sort(key=lambda r: (-(r.get('sharpe_ratio') or 0), -(r.get('dex_swaps_90d') or 0)))
                else:
                    fallback = True
                    combined.sort(key=lambda r: (-(r.get('dex_swaps_90d') or 0), (r.get('last_activity_at') or '')))
            elif s == 'pnl':
                pnl_present = any((r.get('pnl_usd_90d') is not None) for r in combined)
                if pnl_present:
                    combined.sort(key=lambda r: (-(r.get('pnl_usd_90d') or 0)))
                else:
                    fallback = True
                    combined.sort(key=lambda r: (-(r.get('dex_swaps_90d') or 0), (r.get('last_activity_at') or '')))
            elif s == 'win_rate':
                combined.sort(key=lambda r: (-(r.get('win_rate') or 0)))
            elif s == 'last_activity':
                combined.sort(key=lambda r: (r.get('last_activity_at') or ''), reverse=True)
            elif s == 'activity':
                combined.sort(key=lambda r: (-(r.get('dex_swaps_90d') or 0), (r.get('last_activity_at') or '')))
            else:
                combined.sort(key=lambda r: (-(r.get('dex_swaps_90d') or 0), (r.get('last_activity_at') or '')))

            return combined[:limit], fallback
        except Exception as e:
            print(f"Error assembling smart money leaderboard: {e}")
            return [], False

    def get_watchlist_sorted(self, min_sharpe: float = 0.0, limit: int = 100,
                              sort: str = 'auto', priced_only: bool = False,
                              min_coverage: float = None, min_priced_trades: int = None) -> (List[Dict], bool):
        """Get watchlist traders with flexible sorting and optional priced-only gating."""
        try:
            result = self.client.table('smart_money_candidates').select('*').eq(
                'qualifies_smart_money', True
            ).limit(max(limit * 4, 200)).execute()
            rows = result.data or []
            # Apply gating
            if priced_only:
                gated = []
                pct_min = min_coverage if min_coverage is not None else 60
                pt_min = min_priced_trades if min_priced_trades is not None else 10
                for r in rows:
                    cov = (r.get('coverage_pct') or 0)
                    if (r.get('priced_trades_count') or 0) >= pt_min and cov >= pct_min:
                        gated.append(r)
                rows = gated

            # Attach ENS via whales/ens_cache
            try:
                addresses = [r['address'] for r in rows if r.get('address')]
                lbl_res = self.client.table('whales').select('address,label').in_('address', addresses).execute()
                labels = {w['address']: w.get('label') for w in (lbl_res.data or [])}
                ens_rows = self.client.table('ens_cache').select('address,ens').in_('address', addresses).execute()
                ens_map = {e['address']: e.get('ens') for e in (ens_rows.data or [])}
                for r in rows:
                    lbl = labels.get(r['address'])
                    if lbl and '.eth' in lbl:
                        r['ens'] = lbl
                    elif ens_map.get(r['address']):
                        r['ens'] = ens_map.get(r['address'])
            except Exception:
                pass

            # Attach trader metrics (D-020)
            metrics = self.get_trader_metrics_bulk([r['address'] for r in rows])
            for r in rows:
                m = metrics.get(r['address']) or {}
                if m:
                    if m.get('sharpe_90d') is not None:
                        r['sharpe_ratio'] = m.get('sharpe_90d')
                    if m.get('win_rate') is not None:
                        r['win_rate'] = m.get('win_rate')
                    if m.get('pnl_usd_90d') is not None:
                        r['pnl_usd_90d'] = m.get('pnl_usd_90d')

            fallback = False
            s = (sort or 'auto').lower()
            if s in ('sharpe', 'auto'):
                sharpe_present = any((r.get('sharpe_ratio') is not None) for r in rows)
                if sharpe_present:
                    rows.sort(key=lambda r: (-(r.get('sharpe_ratio') or 0), -(r.get('dex_swaps_90d') or 0)))
                else:
                    fallback = True
                    rows.sort(key=lambda r: (-(r.get('dex_swaps_90d') or 0), (r.get('last_activity_at') or '')))
            elif s == 'pnl':
                pnl_present = any((r.get('pnl_usd_90d') is not None) for r in rows)
                if pnl_present:
                    rows.sort(key=lambda r: (-(r.get('pnl_usd_90d') or 0)))
                else:
                    fallback = True
                    rows.sort(key=lambda r: (-(r.get('dex_swaps_90d') or 0), (r.get('last_activity_at') or '')))
            elif s == 'win_rate':
                rows.sort(key=lambda r: (-(r.get('win_rate') or 0)))
            elif s == 'last_activity':
                rows.sort(key=lambda r: (r.get('last_activity_at') or ''), reverse=True)
            elif s == 'activity':
                rows.sort(key=lambda r: (-(r.get('dex_swaps_90d') or 0), (r.get('last_activity_at') or '')))
            else:
                rows.sort(key=lambda r: (-(r.get('dex_swaps_90d') or 0), (r.get('last_activity_at') or '')))

            return rows[:limit], fallback
        except Exception as e:
            print(f"Error getting smart money watchlist: {e}")
            return [], False
    
    # Bootstrap Discovery Methods
    def save_discovered_contract(self, address: str, contract_type: str, confidence: float, 
                                discovery_method: str, validation_data: Dict = None) -> bool:
        """Save a newly discovered contract with confidence score"""
        try:
            data = {
                'address': address.lower(),
                'contract_type': contract_type,
                'confidence_score': confidence,
                'discovery_method': discovery_method,
                'validation_data': validation_data or {},
                'first_seen': datetime.utcnow().isoformat(),
                'last_validated': datetime.utcnow().isoformat(),
                'is_verified': False
            }
            result = self.client.table('discovered_contracts').insert(data).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error saving discovered contract: {e}")
            return False
    
    def get_discovery_candidates(self, contract_type: str = None, min_confidence: float = 0.7) -> List[Dict]:
        """Get discovered contracts that meet confidence threshold"""
        try:
            query = self.client.table('discovered_contracts').select('*').gte('confidence_score', min_confidence)
            if contract_type:
                query = query.eq('contract_type', contract_type)
            result = query.order('confidence_score', desc=True).execute()
            return result.data
        except Exception as e:
            print(f"Error getting discovery candidates: {e}")
            return []
    
    def bootstrap_populate_seeds(self, min_confidence: float = 0.8) -> Dict[str, int]:
        """Populate seed tables from high-confidence discoveries"""
        try:
            stats = {'routers_added': 0, 'cex_added': 0}
            
            # Add DEX routers
            dex_discoveries = self.get_discovery_candidates('dex_router', min_confidence)
            for discovery in dex_discoveries:
                # Check if already exists
                existing = self.client.table('dex_routers').select('address').eq('address', discovery['address']).execute()
                if not existing.data:
                    success = self.add_dex_router(
                        discovery['address'], 
                        discovery['validation_data'].get('name', f"Router-{discovery['address'][:8]}"),
                        discovery['validation_data'].get('version')
                    )
                    if success:
                        stats['routers_added'] += 1
            
            # Add CEX addresses  
            cex_discoveries = self.get_discovery_candidates('cex_wallet', min_confidence)
            for discovery in cex_discoveries:
                existing = self.client.table('cex_addresses').select('address').eq('address', discovery['address']).execute()
                if not existing.data:
                    success = self.add_cex_address(
                        discovery['address'],
                        discovery['validation_data'].get('exchange_name', f"CEX-{discovery['address'][:8]}"),
                        discovery['validation_data'].get('address_type', 'hot_wallet')
                    )
                    if success:
                        stats['cex_added'] += 1
            
            return stats
        except Exception as e:
            print(f"Error populating seeds: {e}")
            return {'routers_added': 0, 'cex_added': 0}
    
    def save_discovery_pattern(self, pattern_type: str, pattern_data: Dict, success_rate: float = 1.0) -> bool:
        """Save a pattern used for discovery for future reference"""
        try:
            data = {
                'pattern_type': pattern_type,
                'pattern_data': pattern_data,
                'success_rate': success_rate,
                'last_matched': datetime.utcnow().isoformat()
            }
            result = self.client.table('discovery_patterns').insert(data).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error saving discovery pattern: {e}")
            return False
    
    def clear_discovery_cache(self, older_than_hours: int = 24) -> bool:
        """Clear old discovery data to prevent stale results"""
        try:
            cutoff = (datetime.utcnow() - timedelta(hours=older_than_hours)).isoformat()
            result = self.client.table('discovered_contracts').delete().lt('first_seen', cutoff).execute()
            return True
        except Exception as e:
            print(f"Error clearing discovery cache: {e}")
            return False

# Create singleton instance
smart_money_repository = SmartMoneyRepository() if supabase_client else None
