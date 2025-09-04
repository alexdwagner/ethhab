#!/usr/bin/env python3
"""
Whale Repository
Data access layer for whale operations using Supabase
"""

from typing import List, Dict, Optional
from datetime import datetime
from .supabase_client import supabase_client

class WhaleRepository:
    """Repository for whale data operations"""
    
    def __init__(self):
        if not supabase_client:
            raise ValueError("Supabase client not initialized")
        self.client = supabase_client.get_client()
    
    def save_whale(self, address: str, label: str, balance_eth: float,
                   entity_type: str = None, category: str = None) -> bool:
        """Save or update whale data"""
        try:
            # Calculate USD balance (rough estimate)
            balance_usd = balance_eth * 2000  # Placeholder ETH price
            
            whale_data = {
                'address': address,
                'label': label,
                'balance_eth': balance_eth,
                'balance_usd': balance_usd,
                'entity_type': entity_type,
                'category': category,
                'last_updated_at': datetime.utcnow().isoformat()
            }
            
            # Upsert whale (insert or update if exists)
            result = self.client.table('whales').upsert(
                whale_data, 
                on_conflict='address'
            ).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            print(f"Error saving whale {address}: {e}")
            return False
    
    def get_whale_by_address(self, address: str) -> Optional[Dict]:
        """Get whale by address"""
        try:
            result = self.client.table('whales').select('*').eq('address', address).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting whale {address}: {e}")
            return None
    
    def get_top_whales(self, limit: int = 50) -> List[Dict]:
        """Get top whales with ROI scores"""
        try:
            result = self.client.table('whales').select(
                '''
                *,
                whale_roi_scores(*)
                '''
            ).order('balance_eth', desc=True).limit(limit).execute()
            
            return result.data
        except Exception as e:
            print(f"Error getting top whales: {e}")
            return []
    
    def save_roi_score(self, address: str, composite_score: float, total_trades: int,
                       avg_roi_percent: float, win_rate_percent: float, 
                       total_volume_usd: float, **kwargs) -> bool:
        """Save ROI score for whale"""
        try:
            # First get whale ID
            whale = self.get_whale_by_address(address)
            if not whale:
                print(f"Whale {address} not found for ROI score")
                return False
            
            roi_data = {
                'whale_id': whale['id'],
                'whale_address': address,  # Changed from 'address' to 'whale_address'
                'composite_score': composite_score,
                'total_trades': total_trades,
                'avg_roi_percent': avg_roi_percent,
                'win_rate_percent': win_rate_percent,
                'total_volume_usd': total_volume_usd,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Add any additional ROI metrics
            for key, value in kwargs.items():
                if key in ['roi_score', 'volume_score', 'consistency_score', 
                          'risk_score', 'activity_score', 'efficiency_score',
                          'sharpe_ratio', 'max_drawdown_percent']:
                    roi_data[key] = value
            
            # Upsert ROI score
            result = self.client.table('whale_roi_scores').upsert(
                roi_data,
                on_conflict='whale_address'  # Changed to match schema
            ).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            print(f"Error saving ROI score for {address}: {e}")
            return False
    
    def save_transaction(self, whale_address: str, tx_data: Dict) -> bool:
        """Save whale transaction"""
        try:
            # Get whale ID
            whale = self.get_whale_by_address(whale_address)
            if not whale:
                return False
            
            transaction_data = {
                'whale_id': whale['id'],
                'address': whale_address,
                **tx_data,
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = self.client.table('whale_transactions').insert(transaction_data).execute()
            return len(result.data) > 0
            
        except Exception as e:
            print(f"Error saving transaction for {whale_address}: {e}")
            return False
    
    def get_whale_transactions(self, address: str, limit: int = 100) -> List[Dict]:
        """Get transactions for a whale"""
        try:
            result = self.client.table('whale_transactions').select('*').eq(
                'address', address
            ).order('timestamp', desc=True).limit(limit).execute()
            
            return result.data
        except Exception as e:
            print(f"Error getting transactions for {address}: {e}")
            return []
    
    def get_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        try:
            # Count whales
            whales_result = self.client.table('whales').select('id', count='exact').execute()
            total_whales = whales_result.count or 0
            
            # Count whales with ROI scores  
            roi_result = self.client.table('whale_roi_scores').select('id', count='exact').execute()
            whales_with_roi = roi_result.count or 0
            
            # Calculate average ROI score manually
            avg_roi_score = 0
            if whales_with_roi > 0:
                roi_scores = self.client.table('whale_roi_scores').select('composite_score').execute()
                if roi_scores.data:
                    total_score = sum(row['composite_score'] for row in roi_scores.data if row['composite_score'])
                    avg_roi_score = total_score / len(roi_scores.data) if roi_scores.data else 0
            
            return {
                'total_whales': total_whales,
                'whales_with_roi': whales_with_roi, 
                'avg_roi_score': round(float(avg_roi_score), 2)
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {'total_whales': 0, 'whales_with_roi': 0, 'avg_roi_score': 0}

# Create singleton instance
whale_repository = WhaleRepository() if supabase_client else None