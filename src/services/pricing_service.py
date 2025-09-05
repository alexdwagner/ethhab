#!/usr/bin/env python3
"""
Pricing Service (D-019 skeleton)
Fetches receipts (with cache), matches stablecoin legs, and upserts priced_trades.
Current implementation provides structure with safe fallbacks when network is disabled.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import time

from config import config
from ..data.smart_money_repository import smart_money_repository


class PricingService:
    def __init__(self):
        if not smart_money_repository:
            raise ValueError("Repository not available")
        self.repo = smart_money_repository
        self.eth_rpc_url = getattr(config, 'ETH_RPC_URL', '')
        self.etherscan_key = getattr(config, 'ETHERSCAN_API_KEY', '')
        self.disable_network = getattr(config, 'SMART_MONEY_DISABLE_NETWORK', False)
        self.request_timeout = getattr(config, 'SMART_MONEY_BACKFILL_REQUEST_TIMEOUT_SEC', 8.0)
        # Optional external price API (current spot only). Uses 0x public price endpoint.
        # Set env SMART_MONEY_DISABLE_NETWORK=1 to fully disable external calls.
        self.enable_price_api = not getattr(config, 'SMART_MONEY_DISABLE_NETWORK', False)
        # Hardcoded stablecoins for mainnet (address -> decimals)
        self.stablecoins: Dict[str, int] = {
            '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48': 6,   # USDC
            '0xdac17f958d2ee523a2206206994597c13d831ec7': 6,   # USDT
            '0x6b175474e89094c44da98b954eedeac495271d0f': 18,  # DAI
        }
        # Leading tokens (address -> decimals) used for parsing logs.
        # Pricing without external APIs will fall back to stable legs only.
        self.token_info: Dict[str, Tuple[int, str]] = {
            '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2': (18, ''),  # WETH
            '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599': (8, ''),   # WBTC
            '0x514910771af9ca656af840dff83e8264ecf986ca': (18, ''),  # LINK
            '0x1f9840a85d5af5bf1d1762f925bdaddc4201f984': (18, ''),  # UNI
            '0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9': (18, ''),  # AAVE
            '0x5a98fcbea516cf06857215779fd812ca3bef1b32': (18, ''),  # LDO
            '0xae7ab96520de3a18e5e111b5eaab095312d7fe84': (18, ''),  # stETH
            '0xae78736cd615f374d3085123a210448e74fc6393': (18, ''),  # rETH
            '0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2': (18, ''),  # MKR
            '0xc011a72400e58ecd99ee497cf89e3775d4bd732f': (18, ''),  # SNX
            '0xd533a949740bb3306d119cc777fa900ba034cd52': (18, ''),  # CRV
            '0xba100000625a3754423978a60c9317c58a424e3d': (18, ''),  # BAL
            '0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce': (18, ''),  # SHIB
            '0x6982508145454ce325ddbe47a25d4ec3d2311933': (18, ''),  # PEPE
            '0x912ce59144191c1204e64559fe8253a0e49e6548': (18, ''),  # ARB
            '0x0a3f6849f78076aefaDf113F5BED87720274dDC0': (18, ''),  # OP
        }

    def price_address(self, address: str, days: int = 90, time_budget_sec: int = 120, debug: bool = False) -> Dict:
        """Price recent interactions for a single address (bounded)."""
        start = time.time()
        address = address.lower()
        interactions = self.repo.get_recent_interactions_for_address(address, days=days, limit=2000)
        priced_count = 0
        checked = 0
        for it in interactions:
            if time.time() - start > time_budget_sec:
                break
            tx_hash = (it.get('tx_hash') or '').lower()
            router = (it.get('router_address') or '').lower()
            ts = it.get('timestamp')
            if not tx_hash:
                continue
            checked += 1
            # Try cache
            cached = self.repo.get_cached_receipt(tx_hash)
            if not cached and self.disable_network:
                # Skip pricing without network; rely on existing priced_trades if any
                continue
            if not cached:
                rec = self._fetch_and_cache_receipt(tx_hash)
                if not rec:
                    if debug and checked <= 5:
                        print(f"   ⚠️  No receipt for {tx_hash[:10]}...")
                    continue
                cached = rec

            usd_in, usd_out, match_info = self._price_from_cached_receipt(cached, address, ts, debug=(debug and checked <= 10))
            # Add ETH value leg if present in tx
            eth_in, eth_out = self._get_eth_value_legs(tx_hash, address, ts)
            usd_in += eth_in
            usd_out += eth_out
            if usd_in == 0 and usd_out == 0:
                if debug and checked <= 10:
                    print(f"   ⋯ No USD legs for {tx_hash[:10]}... | matches={match_info.get('matches',0)}")
                continue
            side = 'buy' if usd_out > usd_in else ('sell' if usd_in > usd_out else 'route')
            trade = {
                'address': address.lower(),
                'tx_hash': tx_hash,
                'router': router,
                'block_number': cached.get('block_number'),
                'block_ts': ts or cached.get('block_ts') or datetime.utcnow().isoformat(),
                'side': side,
                'usd_in': float(usd_in),
                'usd_out': float(usd_out),
                'pricing_method': 'stable_leg',
                'pricing_confidence': 1.0,
            }
            if self.repo.upsert_priced_trade(trade):
                if debug:
                    print(f"   ✅ Priced {tx_hash[:10]}...  side={side}  usd_in={usd_in:.2f}  usd_out={usd_out:.2f}")
                priced_count += 1

        cov = self.repo.update_coverage_for_address(address, days=days)
        return {
            'address': address,
            'checked': checked,
            'priced_new': priced_count,
            **cov,
        }

    def _fetch_and_cache_receipt(self, tx_hash: str) -> Optional[Dict]:
        try:
            if not self.eth_rpc_url:
                return None
            payload = {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'eth_getTransactionReceipt',
                'params': [tx_hash],
            }
            import requests
            resp = requests.post(self.eth_rpc_url, json=payload, timeout=self.request_timeout)
            if resp.status_code != 200:
                return None
            data = resp.json().get('result')
            if not data:
                return None
            block_number = int(data.get('blockNumber', '0x0'), 16) if data.get('blockNumber') else None
            status_hex = data.get('status') or '0x1'
            status = 1 if status_hex == '0x1' else 0
            logs = data.get('logs') or []
            self.repo.upsert_receipt_cache(
                tx_hash=tx_hash,
                block_ts=datetime.utcnow().isoformat(),
                status=status,
                logs_json=logs,
                meta={
                    'block_number': block_number,
                    'from_address': (data.get('from') or '').lower(),
                    'to_address': (data.get('to') or '').lower(),
                },
            )
            return {
                'tx_hash': tx_hash,
                'block_number': block_number,
                'status': status,
                'logs_json': logs,
            }
        except Exception as e:
            print(f"Receipt fetch failed for {tx_hash}: {e}")
            return None

    def _price_from_cached_receipt(self, cached: Dict, wallet: str, ts_iso: Optional[str], debug: bool = False) -> Tuple[float, float, Dict]:
        try:
            wallet_lc = wallet.lower()
            logs = cached.get('logs_json') or []
            if isinstance(logs, str):
                import json as _json
                logs = _json.loads(logs)
            TRANSFER_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
            usd_in = 0.0
            usd_out = 0.0
            matches = 0
            for log in logs:
                topics = log.get('topics') or []
                if not topics or (topics[0] or '').lower() != TRANSFER_TOPIC:
                    continue
                token = (log.get('address') or '').lower()
                dec = self.stablecoins.get(token)
                # If not a stable, try known leading tokens; else default 18
                if dec is None:
                    if token in self.token_info:
                        dec = self.token_info[token][0]
                    else:
                        dec = 18
                from_topic = topics[1] if len(topics) > 1 else ''
                to_topic = topics[2] if len(topics) > 2 else ''
                from_addr = '0x' + from_topic[-40:].lower() if from_topic else ''
                to_addr = '0x' + to_topic[-40:].lower() if to_topic else ''
                try:
                    value_wei = int((log.get('data') or '0x0'), 16)
                except Exception:
                    value_wei = 0
                amount = value_wei / (10 ** dec)
                if amount <= 0:
                    continue
                # For non-stables, fetch price and convert to USD
                if token in self.stablecoins:
                    price_usd = 1.0
                else:
                    price_usd = self._get_token_price_usd(token, ts_iso)
                    if price_usd is None:
                        # If no price, skip contribution
                        continue
                if to_addr == wallet_lc:
                    usd_in += amount * price_usd
                    matches += 1
                elif from_addr == wallet_lc:
                    usd_out += amount * price_usd
                    matches += 1
            if debug:
                print(f"     ↳ transfers matched={matches}  usd_in={usd_in:.2f}  usd_out={usd_out:.2f}")
            return usd_in, usd_out, {'matches': matches}
        except Exception as e:
            print(f"Pricing parse failed: {e}")
            return 0.0, 0.0

    def _get_eth_value_legs(self, tx_hash: str, wallet: str, ts_iso: Optional[str]) -> Tuple[float, float]:
        """Fetch transaction to derive ETH value sent/received by wallet and convert to USD."""
        try:
            if not self.eth_rpc_url:
                return 0.0, 0.0
            payload = {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'eth_getTransactionByHash',
                'params': [tx_hash],
            }
            import requests
            resp = requests.post(self.eth_rpc_url, json=payload, timeout=self.request_timeout)
            if resp.status_code != 200:
                return 0.0, 0.0
            tx = resp.json().get('result') or {}
            from_addr = (tx.get('from') or '').lower()
            to_addr = (tx.get('to') or '').lower()
            try:
                val_wei = int((tx.get('value') or '0x0'), 16)
            except Exception:
                val_wei = 0
            eth_amount = val_wei / 1e18
            if eth_amount <= 0:
                return 0.0, 0.0
            eth_price = self._get_eth_price_usd(ts_iso)
            if eth_price is None:
                return 0.0, 0.0
            wallet_lc = wallet.lower()
            if from_addr == wallet_lc:
                return 0.0, eth_amount * eth_price
            if to_addr == wallet_lc:
                return eth_amount * eth_price, 0.0
            return 0.0, 0.0
        except Exception:
            return 0.0, 0.0

    def _get_eth_price_usd(self, ts_iso: Optional[str]) -> Optional[float]:
        return self._get_token_price_usd('eth', ts_iso)

    def _get_token_price_usd(self, token_address_or_eth: str, ts_iso: Optional[str]) -> Optional[float]:
        """Get USD price for token.
        Order: DB cache -> external spot price (0x) -> None.
        """
        try:
            if not ts_iso:
                ts = int(time.time())
            else:
                ts = int(datetime.fromisoformat(ts_iso.replace('Z', '+00:00')).timestamp())
            bucket_dt = datetime.utcfromtimestamp(ts).replace(minute=0, second=0, microsecond=0)
            bucket_iso = bucket_dt.isoformat() + 'Z'
            key_addr = token_address_or_eth.lower()
            cached = self.repo.get_cached_token_price(key_addr, bucket_iso)
            if cached is not None:
                return cached

            # External spot price (current) as fallback for MVP
            if self.enable_price_api:
                spot = self._fetch_spot_price_usd_via_zeroex(key_addr)
                if spot is not None:
                    # Cache under current hour bucket
                    self.repo.upsert_token_price(key_addr, bucket_iso, float(spot), source='0x')
                    return float(spot)
            return None
        except Exception as e:
            print(f"Price lookup failed: {e}")
            return None

    def _fetch_spot_price_usd_via_zeroex(self, token_address_or_eth: str) -> Optional[float]:
        """Fetch current USD price via 0x price API (sell 1 token for USDC).
        Returns price in USD or None.
        """
        try:
            import requests
            usdc = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
            weth = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
            if token_address_or_eth == 'eth':
                token = weth
                decimals = 18
            else:
                token = token_address_or_eth
                decimals = self.stablecoins.get(token) or self.token_info.get(token, (18, ''))[0]
            # Sell 1 token to get USDC price
            sell_amount = str(10 ** int(decimals))
            url = 'https://api.0x.org/swap/v1/price'
            params = {
                'sellToken': token,
                'buyToken': usdc,
                'sellAmount': sell_amount,
            }
            headers = {}
            # Prefer ZEROX_SWAP_API_KEY; fallback to ZEROX_API_KEY if present
            api_key = getattr(config, 'ZEROX_SWAP_API_KEY', '') or getattr(config, 'ZEROX_API_KEY', '')
            if api_key:
                headers['0x-api-key'] = api_key
            resp = requests.get(url, params=params, headers=headers, timeout=self.request_timeout)
            if resp.status_code != 200:
                return None
            data = resp.json()
            # price = buyToken per 1 sellToken (i.e., USDC per token)
            price = float(data.get('price')) if data.get('price') is not None else None
            return price
        except Exception:
            return None


# Global instance
pricing_service = PricingService() if smart_money_repository else None

    
    
    
