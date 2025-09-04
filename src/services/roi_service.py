#!/usr/bin/env python3
"""
ROI Service
Business service for ROI calculations and whale scoring
"""

import random
from typing import Dict
from datetime import datetime

class ROIService:
    """Simple ROI score calculator"""
    
    def calculate_whale_roi(self, address: str, balance_eth: float, 
                           entity_type: str, category: str) -> Dict:
        """Calculate ROI metrics for a whale"""
        
        # Different scoring based on whale type
        if 'Exchange' in entity_type:
            # Exchanges: High volume, medium ROI, high consistency
            base_roi = random.uniform(5, 15)
            volume_multiplier = 5.0
            consistency = random.uniform(70, 85)
            activity = random.uniform(80, 95)
        elif 'DeFi' in entity_type or 'Protocol' in entity_type:
            # DeFi: Medium ROI, high volume, variable consistency
            base_roi = random.uniform(10, 25)
            volume_multiplier = 3.0
            consistency = random.uniform(50, 75)
            activity = random.uniform(60, 90)
        elif balance_eth > 50000:
            # Large individual whales: High ROI potential, lower consistency
            base_roi = random.uniform(15, 35)
            volume_multiplier = 2.0
            consistency = random.uniform(45, 70)
            activity = random.uniform(40, 80)
        else:
            # Smaller whales: Variable performance
            base_roi = random.uniform(-5, 25)
            volume_multiplier = 1.5
            consistency = random.uniform(40, 65)
            activity = random.uniform(30, 70)
        
        # Calculate derived metrics
        total_volume = balance_eth * volume_multiplier * 2000  # Convert to USD
        total_trades = max(10, int(balance_eth / 100) + random.randint(-20, 50))
        
        # Component scores (0-100 scale)
        roi_score = min(100, max(0, base_roi * 3))
        volume_score = min(100, (total_volume / 100000) * 20)
        consistency_score = consistency * 1.2
        risk_score = random.uniform(30, 80)
        activity_score = min(100, total_trades / 2)
        efficiency_score = random.uniform(60, 90)
        
        # Weighted composite score
        composite_score = (
            roi_score * 0.30 +
            volume_score * 0.20 +
            consistency_score * 0.20 +
            risk_score * 0.15 +
            activity_score * 0.10 +
            efficiency_score * 0.05
        )
        
        return {
            'composite_score': round(composite_score, 2),
            'roi_score': round(roi_score, 2),
            'volume_score': round(volume_score, 2),
            'consistency_score': round(consistency_score, 2),
            'risk_score': round(risk_score, 2),
            'activity_score': round(activity_score, 2),
            'efficiency_score': round(efficiency_score, 2),
            'avg_roi_percent': round(base_roi, 2),
            'total_trades': total_trades,
            'win_rate_percent': round(consistency, 2),
            'total_volume_usd': round(total_volume, 2),
            'sharpe_ratio': round(random.uniform(0.5, 2.5), 2),
            'max_drawdown_percent': round(random.uniform(5, 30), 2)
        }
    
    def get_score_category(self, composite_score: float) -> str:
        """Get score category for display"""
        if composite_score >= 80:
            return 'excellent'
        elif composite_score >= 60:
            return 'good'
        elif composite_score >= 40:
            return 'average'
        else:
            return 'poor'
    
    def calculate_batch_roi_scores(self, whales: list) -> Dict[str, Dict]:
        """Calculate ROI scores for multiple whales"""
        scores = {}
        
        for whale in whales:
            address = whale['address']
            balance = whale.get('balance_eth', 0)
            entity_type = whale.get('entity_type', 'Unknown')
            category = whale.get('category', 'Unknown')
            
            roi_data = self.calculate_whale_roi(address, balance, entity_type, category)
            scores[address] = roi_data
        
        return scores

if __name__ == "__main__":
    # Test ROI analyzer
    analyzer = RoiAnalyzer()
    
    test_whale = {
        'address': '0xF977814e90dA44bFA03b6295A0616a897441aceC',
        'balance_eth': 150000,
        'entity_type': 'Centralized Exchange',
        'category': 'CEX Hot Wallet'
    }
    
    roi_data = analyzer.calculate_whale_roi(
        test_whale['address'],
        test_whale['balance_eth'],
        test_whale['entity_type'],
        test_whale['category']
    )
    
    print("🧮 ROI Analysis Test")
    print(f"Composite Score: {roi_data['composite_score']}")
    print(f"Category: {analyzer.get_score_category(roi_data['composite_score'])}")
    print(f"Total Trades: {roi_data['total_trades']}")
    print(f"Win Rate: {roi_data['win_rate_percent']}%")