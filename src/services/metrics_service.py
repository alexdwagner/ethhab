#!/usr/bin/env python3
"""
Metrics Service (D-020)
Computes rolling 90d metrics for traders from priced_trades and updates trader_metrics.
"""

from __future__ import annotations
from typing import Dict, List
from datetime import datetime
import math

from ..data.smart_money_repository import smart_money_repository


class MetricsService:
    def __init__(self):
        if not smart_money_repository:
            raise ValueError("Repository not available")
        self.repo = smart_money_repository

    def compute_for_address(self, address: str, days: int = 90) -> Dict:
        address = address.lower()
        trades = self.repo.get_priced_trades_for_address(address, days=days)
        nets: List[float] = []
        for t in trades:
            try:
                nets.append(float(t.get('usd_in', 0)) - float(t.get('usd_out', 0)))
            except Exception:
                continue
        priced_count = len(nets)
        pnl = sum(nets) if nets else 0.0
        win_rate = 0.0
        sharpe = 0.0
        max_dd = 0.0
        if priced_count > 0:
            wins = sum(1 for n in nets if n > 0)
            win_rate = wins / priced_count
            # Sharpe: mean/std of per-trade net USD as a simple proxy
            mean = pnl / priced_count
            var = 0.0
            if priced_count > 1:
                var = sum((n - mean) ** 2 for n in nets) / (priced_count - 1)
            std = math.sqrt(var)
            sharpe = (mean / std) if std > 0 else 0.0
            # Max drawdown on cumulative net
            cum = 0.0
            peak = 0.0
            for n in nets:
                cum += n
                if cum > peak:
                    peak = cum
                dd = peak - cum
                if dd > max_dd:
                    max_dd = dd

        # coverage from candidates table (precomputed)
        cov = self.repo.update_coverage_for_address(address, days=days)
        metrics = {
            'priced_trades_count': priced_count,
            'coverage_pct': cov.get('coverage_pct', 0.0),
            'pnl_usd_90d': pnl,
            'win_rate': round(win_rate, 4),
            'sharpe_90d': round(sharpe, 4),
            'max_drawdown_usd': round(max_dd, 2),
        }
        self.repo.upsert_trader_metrics(address, metrics, window='90d')
        return metrics


metrics_service = MetricsService() if smart_money_repository else None

