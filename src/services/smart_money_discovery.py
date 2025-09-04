#!/usr/bin/env python3
"""
Smart Money Discovery Service
Discovers active traders based on DEX activity using database-driven configuration
"""

import requests
import time
from typing import Dict, List, Set, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from config import config
from ..data.smart_money_repository import smart_money_repository

class SmartMoneyDiscovery:
    """Discover smart money through behavior patterns using database configuration"""
    
    def __init__(self):
        self.etherscan_key = config.ETHERSCAN_API_KEY
        self.repo = smart_money_repository
        
        if not self.repo:
            raise ValueError("Smart money repository not initialized")
        
        # Load configuration from database
        self.dex_routers = {}
        self.cex_addresses = {}
        self.excluded_contracts = set()
        self._load_configuration()

        # Execution controls
        self.request_timeout_sec: float = getattr(config, 'SMART_MONEY_REQUEST_TIMEOUT_SEC', 5.0)
        self.max_routers_per_run: int = getattr(config, 'SMART_MONEY_MAX_ROUTERS_PER_RUN', 5)
        self.time_budget_sec: int = getattr(config, 'SMART_MONEY_DISCOVERY_TIME_BUDGET_SEC', 60)
        self.disable_network: bool = getattr(config, 'SMART_MONEY_DISABLE_NETWORK', False)
        # Backfill specific controls
        self.backfill_timeout_sec: float = getattr(config, 'SMART_MONEY_BACKFILL_REQUEST_TIMEOUT_SEC', self.request_timeout_sec)
        self.backfill_max_tx: int = getattr(config, 'SMART_MONEY_BACKFILL_MAX_TX', 2500)
        self.backfill_time_budget_sec: int = getattr(config, 'SMART_MONEY_BACKFILL_TIME_BUDGET_SEC', 120)
        
        # Track candidates in memory during discovery
        self.candidates = defaultdict(lambda: {
            'dex_swaps': 0,
            'protocols_touched': set(),
            'gas_spent': 0,
            'last_activity': None,
            'first_seen': None,
            'is_contract': False,
            'withdrew_from_cex': False,
            'uses_defi': False
        })
    
    def _load_configuration(self):
        """Load DEX routers, CEX addresses, and exclusions from database"""
        # Load DEX routers
        routers = self.repo.get_dex_routers(active_only=True)
        self.dex_routers = {r['address']: r['name'] for r in routers}
        print(f"📋 Loaded {len(self.dex_routers)} DEX routers from database")
        
        # Load CEX addresses
        cex_addrs = self.repo.get_cex_addresses(active_only=True)
        self.cex_addresses = {c['address']: c['exchange_name'] for c in cex_addrs}
        print(f"📋 Loaded {len(self.cex_addresses)} CEX addresses from database")
        
        # Load excluded contracts
        self.excluded_contracts = set(self.repo.get_excluded_contracts())
        print(f"📋 Loaded {len(self.excluded_contracts)} excluded contracts from database")
    
    def discover_dex_traders(self, hours_back: int = 24) -> Set[str]:
        """Discover addresses interacting with DEX routers"""
        discovered = set()
        start_ts = time.time()

        # If network disabled or no API key, skip to DB fallback
        if self.disable_network or not self.etherscan_key:
            try:
                recent = self.repo.get_recent_traders(hours_back=hours_back, limit=500)
                for a in recent:
                    if not self._is_excluded_address(a):
                        discovered.add(a)
                if discovered:
                    print(f"   (offline) Derived {len(discovered)} traders from stored interactions")
                return discovered
            except Exception as e:
                print(f"Offline discovery failed: {e}")
                return set()

        # Limit routers per run and respect time budget
        routers_iter = list(self.dex_routers.items())[: max(0, self.max_routers_per_run)]
        for router_address, router_name in routers_iter:
            if time.time() - start_ts > self.time_budget_sec:
                print("⏱️  Time budget reached during DEX scan; stopping early")
                break
            print(f"🔍 Scanning {router_name} interactions...")
            
            try:
                # Get recent transactions TO the router
                url = "https://api.etherscan.io/api"
                params = {
                    'module': 'account',
                    'action': 'txlist',
                    'address': router_address,
                    'page': '1',
                    'offset': '100',
                    'sort': 'desc',
                    'apikey': self.etherscan_key
                }
                
                response = requests.get(url, params=params, timeout=self.request_timeout_sec)
                if response.status_code == 200:
                    result = response.json().get('result', [])
                    
                    if isinstance(result, list):
                        for tx in result:
                            timestamp = int(tx.get('timeStamp', 0))
                            if timestamp > time.time() - (hours_back * 3600):
                                from_addr = tx.get('from', '').lower()
                                
                                if from_addr and not self._is_excluded_address(from_addr):
                                    discovered.add(from_addr)
                                    self._update_candidate_metrics(from_addr, tx, router_name)
                                    
                                    # Log interaction to database
                                    self.repo.log_dex_interaction(from_addr, router_address, {
                                        'tx_hash': tx.get('hash'),
                                        'block_number': int(tx.get('blockNumber', 0)),
                                        'timestamp': datetime.fromtimestamp(timestamp).isoformat(),
                                        'gas_spent_eth': self._calculate_gas_eth(tx)
                                    })
                
                time.sleep(0.2)  # Rate limiting
                
            except Exception as e:
                print(f"Error scanning {router_name}: {e}")
        
        # Fallback: derive from stored interactions if API returns nothing
        if not discovered:
            try:
                recent = self.repo.get_recent_traders(hours_back=hours_back, limit=500)
                for a in recent:
                    if not self._is_excluded_address(a):
                        discovered.add(a)
                if discovered:
                    print(f"   (fallback) Derived {len(discovered)} traders from stored interactions")
            except Exception as e:
                print(f"Fallback discovery failed: {e}")
        
        return discovered
    
    def discover_cex_withdrawals(self) -> Set[str]:
        """Find addresses withdrawing from CEXs"""
        discovered = set()
        if self.disable_network or not self.etherscan_key:
            return discovered

        # Limit to first 3 CEXs (or fewer) to avoid rate limits
        for cex_address, cex_name in list(self.cex_addresses.items())[:3]:
            print(f"🏦 Scanning {cex_name} withdrawals...")
            
            try:
                url = "https://api.etherscan.io/api"
                params = {
                    'module': 'account',
                    'action': 'txlist',
                    'address': cex_address,
                    'page': '1',
                    'offset': '50',
                    'sort': 'desc',
                    'apikey': self.etherscan_key
                }
                
                response = requests.get(url, params=params, timeout=self.request_timeout_sec)
                if response.status_code == 200:
                    result = response.json().get('result', [])
                    
                    if isinstance(result, list):
                        for tx in result:
                            if tx.get('from', '').lower() == cex_address.lower():
                                to_addr = tx.get('to', '').lower()
                                value_eth = int(tx.get('value', 0)) / 1e18
                                
                                if to_addr and value_eth > 0.1 and not self._is_excluded_address(to_addr):
                                    discovered.add(to_addr)
                                    self.candidates[to_addr]['withdrew_from_cex'] = True
                
                time.sleep(0.2)
                
            except Exception as e:
                print(f"Error scanning {cex_name}: {e}")
        
        return discovered
    
    def _calculate_gas_eth(self, tx: Dict) -> float:
        """Calculate gas cost in ETH"""
        gas_used = int(tx.get('gasUsed', 0))
        gas_price = int(tx.get('gasPrice', 0))
        return (gas_used * gas_price) / 1e18
    
    def _update_candidate_metrics(self, address: str, tx: Dict, protocol: str):
        """Update candidate metrics based on transaction"""
        candidate = self.candidates[address]
        
        candidate['dex_swaps'] += 1
        candidate['protocols_touched'].add(protocol)
        candidate['gas_spent'] += self._calculate_gas_eth(tx)
        
        timestamp = int(tx.get('timeStamp', 0))
        if not candidate['first_seen'] or timestamp < candidate['first_seen']:
            candidate['first_seen'] = timestamp
        if not candidate['last_activity'] or timestamp > candidate['last_activity']:
            candidate['last_activity'] = timestamp
    
    def _is_excluded_address(self, address: str) -> bool:
        """Check if address should be excluded"""
        # Check exclusion list
        if address in self.excluded_contracts:
            return True
        
        # Check if it's a CEX
        if address in self.cex_addresses:
            return True
        
        # Check if it's a DEX router
        if address in self.dex_routers:
            return True
        
        # Exclude zero address
        if address == '0x0000000000000000000000000000000000000000':
            return True
        
        return False
    
    def get_activity_metrics(self, address: str) -> Optional[Dict]:
        """Get detailed activity metrics for an address"""
        # First check database
        existing_activity = self.repo.get_address_activity(address)
        if existing_activity and existing_activity.get('updated_at'):
            # If data is less than 1 hour old, use it
            last_update = datetime.fromisoformat(existing_activity['updated_at'].replace('Z', '+00:00'))
            if (datetime.utcnow() - last_update).seconds < 3600:
                return existing_activity
        
        # Otherwise fetch fresh data
        metrics = {
            'address': address,
            'dex_swap_count': 0,
            'unique_protocols': 0,
            'total_gas_spent_eth': 0,
            'first_seen_at': None,
            'last_activity_at': None,
            'withdrew_from_cex': False,
            'uses_defi': False
        }
        
        try:
            # Get recent DEX interactions from database
            dex_interactions = self.repo.get_dex_interactions(address, days=90)
            
            if dex_interactions:
                metrics['dex_swap_count'] = len(dex_interactions)
                
                protocols = set()
                total_gas = 0
                first_time = None
                last_time = None
                
                for interaction in dex_interactions:
                    router = interaction.get('router_address')
                    if router in self.dex_routers:
                        protocols.add(self.dex_routers[router])
                    
                    total_gas += float(interaction.get('gas_spent_eth', 0))
                    
                    timestamp = interaction.get('timestamp')
                    if timestamp:
                        if not first_time or timestamp < first_time:
                            first_time = timestamp
                        if not last_time or timestamp > last_time:
                            last_time = timestamp
                
                metrics['unique_protocols'] = len(protocols)
                metrics['total_gas_spent_eth'] = total_gas
                metrics['first_seen_at'] = first_time
                metrics['last_activity_at'] = last_time
            
            # Update database
            self.repo.update_address_activity(address, metrics)
            
        except Exception as e:
            print(f"Error getting metrics for {address}: {e}")
        
        return metrics
    
    def qualify_as_smart_money(self, address: str) -> Dict:
        """Determine if address qualifies as smart money"""
        metrics = self.get_activity_metrics(address)
        
        if not metrics:
            return {'qualifies_smart_money': False}
        
        # Thresholds (tunable via env)
        min_swaps = getattr(config, 'SMART_MONEY_MIN_SWAPS', 10)
        min_protocols = getattr(config, 'SMART_MONEY_MIN_PROTOCOLS', 1)
        active_days = getattr(config, 'SMART_MONEY_ACTIVE_DAYS', 60)

        qualifies = (
            metrics.get('dex_swap_count', 0) >= min_swaps and
            metrics.get('unique_protocols', 0) >= min_protocols and
            metrics.get('last_activity_at') is not None
        )
        
        # Check if active in last 30 days
        if qualifies and metrics['last_activity_at']:
            last_activity = datetime.fromisoformat(metrics['last_activity_at'].replace('Z', '+00:00'))
            days_since = (datetime.utcnow() - last_activity).days
            qualifies = qualifies and (days_since <= active_days)
        
        result = {
            'address': address,
            'qualifies_smart_money': qualifies,
            'dex_swaps_90d': metrics.get('dex_swap_count', 0),
            'status': 'watchlist' if qualifies else 'candidate'
        }
        
        # Update database
        self.repo.update_smart_money_candidate(address, result)
        
        return result

    def backfill_address_interactions(self, address: str, days: int = 90,
                                      max_tx: Optional[int] = None,
                                      time_budget_sec: Optional[int] = None,
                                      request_timeout_sec: Optional[float] = None) -> int:
        """Backfill DEX interactions for a single address by scanning its normal tx list.
        Returns number of interactions logged.
        """
        try:
            if not self.etherscan_key:
                print("Backfill skipped: ETHERSCAN_API_KEY not set")
                return 0

            url = "https://api.etherscan.io/api"
            # Bound the number of transactions we request and time we spend
            tx_cap = min(max_tx or self.backfill_max_tx, 10000)
            timeout = request_timeout_sec or self.backfill_timeout_sec
            time_budget = max(1, int(time_budget_sec or self.backfill_time_budget_sec))
            start_ts = time.time()
            params = {
                'module': 'account',
                'action': 'txlist',
                'address': address,
                'page': '1',
                'offset': str(tx_cap),
                'sort': 'desc',
                'apikey': self.etherscan_key
            }
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code != 200:
                return 0
            result = resp.json().get('result', [])
            if not isinstance(result, list):
                return 0

            cutoff_ts = time.time() - days * 86400
            count = 0
            dex_router_set = set(k.lower() for k in self.dex_routers.keys())

            for tx in result:
                try:
                    to_addr = (tx.get('to') or '').lower()
                    if not to_addr or to_addr not in dex_router_set:
                        continue
                    ts = int(tx.get('timeStamp', 0))
                    if ts < cutoff_ts:
                        break  # txs are sorted desc; stop early
                    self.repo.log_dex_interaction(address, to_addr, {
                        'tx_hash': tx.get('hash'),
                        'block_number': int(tx.get('blockNumber', 0)),
                        'timestamp': datetime.fromtimestamp(ts).isoformat(),
                        'gas_spent_eth': self._calculate_gas_eth(tx)
                    })
                    count += 1
                    # Respect time budget
                    if time.time() - start_ts > time_budget:
                        break
                except Exception:
                    continue
            return count
        except Exception as e:
            print(f"Backfill failed for {address}: {e}")
            return 0
    
    def discover_smart_money_batch(self, max_candidates: int = 50, hours_back: int = 24,
                                   max_routers: Optional[int] = None,
                                   time_budget_sec: Optional[int] = None,
                                   offline: Optional[bool] = None) -> List[Dict]:
        """Main discovery pipeline"""
        print("🚀 Starting Smart Money Discovery")
        print("=" * 40)
        
        # Reload configuration in case it changed
        self._load_configuration()

        # Apply optional overrides for this run
        if max_routers is not None:
            self.max_routers_per_run = max(0, int(max_routers))
        if time_budget_sec is not None:
            self.time_budget_sec = max(1, int(time_budget_sec))
        if offline is not None:
            self.disable_network = bool(offline)
        
        # Phase 1: Discover candidates
        print("\n📊 Phase 1: Discovering candidates...")
        
        dex_traders = self.discover_dex_traders(hours_back=hours_back)
        print(f"   Found {len(dex_traders)} DEX traders")
        
        cex_withdrawers = self.discover_cex_withdrawals()
        print(f"   Found {len(cex_withdrawers)} CEX withdrawals")
        
        all_candidates = dex_traders | cex_withdrawers
        print(f"\n📊 Total unique candidates: {len(all_candidates)}")
        
        # Phase 2: Qualify candidates
        print("\n📊 Phase 2: Qualifying candidates...")
        
        smart_money = []
        for i, address in enumerate(list(all_candidates)[:max_candidates]):
            if i % 10 == 0:
                print(f"   Processing {i}/{min(len(all_candidates), max_candidates)}...")
            
            result = self.qualify_as_smart_money(address)
            if result['qualifies_smart_money']:
                smart_money.append(result)
                print(f"   ✅ Qualified: {address[:10]}... ({result['dex_swaps_90d']} swaps)")
            
            time.sleep(0.25)  # Rate limiting
        
        # Get funnel stats
        stats = self.repo.get_candidate_funnel_stats()
        
        print(f"\n📊 Funnel Statistics:")
        print(f"   • Total candidates: {stats['total_candidates']}")
        print(f"   • Scored traders: {stats['scored_traders']}")
        print(f"   • Watchlist: {stats['watchlist_traders']}")
        print(f"   • Conversion rate: {stats['conversion_rate']:.1f}%")
        
        print(f"\n✅ Discovery complete: {len(smart_money)} new smart money traders found")
        
        return smart_money

# Global instance
smart_money_discovery = SmartMoneyDiscovery() if smart_money_repository else None
