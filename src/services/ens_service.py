#!/usr/bin/env python3
"""
ENS Resolution Service (reverse lookup with cache)
Uses public ENS resolver API (ensideas) when network is enabled.
Falls back to cached results; no-op when network disabled.
"""

from __future__ import annotations
from typing import Optional, Dict, List
from datetime import datetime, timedelta

from config import config
from ..data.smart_money_repository import smart_money_repository


class ENSService:
    def __init__(self):
        if not smart_money_repository:
            raise ValueError("Repository not available")
        self.repo = smart_money_repository
        self.disable_network = getattr(config, 'SMART_MONEY_DISABLE_NETWORK', False)
        # TTL for cache refresh
        self.ttl_days = 30

    def _get_cached_row(self, address: str) -> Optional[Dict]:
        try:
            client = self.repo.client
            res = client.table('ens_cache').select('*').eq('address', address.lower()).limit(1).execute()
            if not res.data:
                return None
            return res.data[0]
        except Exception:
            return None

    def cache_update(self, address: str, ens: Optional[str]) -> None:
        try:
            self.repo.client.table('ens_cache').upsert({
                'address': address.lower(),
                'ens': ens or None,
                'last_resolved': datetime.utcnow().isoformat(),
            }, on_conflict='address').execute()
        except Exception:
            pass

    def get_cached(self, address: str) -> Optional[str]:
        row = self._get_cached_row(address)
        return row.get('ens') if row else None

    def resolve(self, address: str, force: bool = False) -> Optional[str]:
        address = address.lower()
        # Check cache and TTL
        cached_row = self._get_cached_row(address)
        if cached_row and not force:
            try:
                last = cached_row.get('last_resolved')
                if last:
                    last_dt = datetime.fromisoformat(str(last).replace('Z', '+00:00'))
                    if datetime.utcnow() - last_dt < timedelta(days=self.ttl_days):
                        return cached_row.get('ens')
            except Exception:
                # If parsing fails, return cached value
                return cached_row.get('ens')
        if self.disable_network:
            return cached_row.get('ens') if cached_row else None

        # Try public ENS resolver API
        try:
            import requests
            url = f"https://api.ensideas.com/ens/resolve/{address}"
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                return self.get_cached(address)
            data = resp.json()
            ens = data.get('name') or data.get('reverse')
            if ens:
                self.cache_update(address, ens)
                return ens
            # Cache negative result to avoid repeated calls
            self.cache_update(address, None)
            return None
        except Exception:
            return cached_row.get('ens') if cached_row else None

    def resolve_bulk(self, addresses: List[str], force: bool = False) -> Dict[str, Optional[str]]:
        out: Dict[str, Optional[str]] = {}
        for addr in addresses:
            out[addr] = self.resolve(addr, force=force)
        return out


ens_service = ENSService() if smart_money_repository else None
