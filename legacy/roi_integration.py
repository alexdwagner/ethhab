#!/usr/bin/env python3
"""
ROI Scoring Integration with Existing Whale Tracker
Connects the new ROI scoring system with existing database and scanners
"""

import os
import json
import sqlite3
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from web3 import Web3
import logging

from roi_scoring_v2 import ROIScorer, create_roi_tracking_schema
from minimal_whale_scanner import MinimalWhaleScanner

logger = logging.getLogger(__name__)

class WhaleROIIntegration:
    """Integration class to add ROI scoring to existing whale tracking system"""
    
    def __init__(self, existing_db_path: str = "whale_intelligence.db", roi_db_path: str = "roi_tracking.db"):
        self.existing_db_path = existing_db_path
        self.roi_db_path = roi_db_path
        
        # Initialize ROI tracking database
        create_roi_tracking_schema(roi_db_path)
        
        # Initialize Web3 (you'll need to add your RPC URL)
        rpc_url = os.getenv('ETH_RPC_URL', 'https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY')
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Initialize ROI scorer
        self.roi_scorer = ROIScorer(self.w3, roi_db_path)
        
        # Initialize minimal whale scanner for getting transactions
        self.whale_scanner = MinimalWhaleScanner()
    
    def migrate_existing_whales(self):
        """Migrate existing whale data to ROI tracking system"""
        logger.info("Starting migration of existing whale data...")
        
        # Get all whales from existing database
        whales = self.get_existing_whales()
        logger.info(f"Found {len(whales)} whales to migrate")
        
        for i, whale in enumerate(whales):
            wallet_address = whale['wallet_address']
            logger.info(f"Migrating whale {i+1}/{len(whales)}: {wallet_address}")
            
            try:
                # Get transactions for this whale
                tx_hashes = self.get_whale_transactions(wallet_address)
                
                if tx_hashes:
                    # Process transactions through ROI scorer
                    self.roi_scorer.process_wallet_transactions(wallet_address, tx_hashes)
                    
                    # Calculate ROI score
                    roi_data = self.roi_scorer.calculate_wallet_score(wallet_address)
                    
                    # Update existing whale record with ROI data
                    self.update_whale_with_roi_data(wallet_address, roi_data)
                    
                    logger.info(f"Migrated {wallet_address} with ROI score: {roi_data['composite_score']}")
                else:
                    logger.warning(f"No transactions found for whale {wallet_address}")
                    
            except Exception as e:
                logger.error(f"Error migrating whale {wallet_address}: {e}")
                continue
        
        logger.info("Migration completed!")
    
    def get_existing_whales(self) -> List[Dict]:
        """Get all whales from existing database"""
        if not os.path.exists(self.existing_db_path):
            logger.warning(f"Existing database {self.existing_db_path} not found")
            return []
        
        conn = sqlite3.connect(self.existing_db_path)
        cursor = conn.cursor()
        
        # Check if whales table exists and get structure
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        whales = []
        
        # Try different possible table names and structures
        possible_queries = [
            "SELECT DISTINCT wallet_address FROM whales",
            "SELECT DISTINCT address AS wallet_address FROM whale_transactions", 
            "SELECT DISTINCT from_address AS wallet_address FROM transactions WHERE amount_usd > 100000",
            "SELECT DISTINCT to_address AS wallet_address FROM transactions WHERE amount_usd > 100000"
        ]
        
        for query in possible_queries:
            try:
                cursor.execute(query)
                rows = cursor.fetchall()
                for row in rows:
                    if row[0] and row[0].startswith('0x'):
                        whales.append({'wallet_address': row[0].lower()})
                if whales:
                    break
            except Exception as e:
                logger.debug(f"Query failed: {query} - {e}")
                continue
        
        conn.close()
        
        # Remove duplicates
        unique_whales = []
        seen_addresses = set()
        for whale in whales:
            addr = whale['wallet_address'].lower()
            if addr not in seen_addresses:
                unique_whales.append(whale)
                seen_addresses.add(addr)
        
        return unique_whales
    
    def get_whale_transactions(self, wallet_address: str, limit: int = 100) -> List[str]:
        """Get transaction hashes for a whale address"""
        try:
            # Use Etherscan API or similar to get transaction list
            # This is a simplified version - you'd want to use a proper API
            transactions = self.whale_scanner.get_wallet_transactions(wallet_address, limit=limit)
            return [tx.get('hash', '') for tx in transactions if tx.get('hash')]
        except Exception as e:
            logger.error(f"Error getting transactions for {wallet_address}: {e}")
            return []
    
    def update_whale_with_roi_data(self, wallet_address: str, roi_data: Dict):
        """Update existing whale record with ROI data"""
        if not os.path.exists(self.existing_db_path):
            return
        
        conn = sqlite3.connect(self.existing_db_path)
        cursor = conn.cursor()
        
        try:
            # Check if roi_scores table exists, if not create it
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS whale_roi_scores (
                    wallet_address VARCHAR(42) PRIMARY KEY,
                    composite_score DECIMAL(5,2) NOT NULL,
                    roi_score DECIMAL(5,2) NOT NULL,
                    volume_score DECIMAL(5,2) NOT NULL,
                    consistency_score DECIMAL(5,2) NOT NULL,
                    risk_score DECIMAL(5,2) NOT NULL,
                    activity_score DECIMAL(5,2) NOT NULL,
                    efficiency_score DECIMAL(5,2) NOT NULL,
                    avg_roi_percent DECIMAL(10,4) NOT NULL,
                    total_trades INTEGER NOT NULL,
                    win_rate_percent DECIMAL(10,4) NOT NULL,
                    sharpe_ratio DECIMAL(10,4) NOT NULL,
                    max_drawdown_percent DECIMAL(10,4) NOT NULL,
                    total_volume_usd DECIMAL(18,2) NOT NULL,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert or update ROI data
            cursor.execute("""
                INSERT OR REPLACE INTO whale_roi_scores (
                    wallet_address, composite_score, roi_score, volume_score,
                    consistency_score, risk_score, activity_score, efficiency_score,
                    avg_roi_percent, total_trades, win_rate_percent, sharpe_ratio,
                    max_drawdown_percent, total_volume_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                wallet_address,
                roi_data['composite_score'],
                roi_data['score_components']['roi_score'],
                roi_data['score_components']['volume_score'],
                roi_data['score_components']['consistency_score'],
                roi_data['score_components']['risk_score'],
                roi_data['score_components']['activity_score'],
                roi_data['score_components']['efficiency_score'],
                roi_data['raw_metrics']['avg_roi_percent'],
                roi_data['raw_metrics']['total_trades'],
                roi_data['raw_metrics']['win_rate_percent'],
                roi_data['raw_metrics']['sharpe_ratio'],
                roi_data['raw_metrics']['max_drawdown_percent'],
                roi_data['raw_metrics']['total_volume_usd']
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error updating whale ROI data: {e}")
        finally:
            conn.close()
    
    def get_top_whales_by_roi(self, limit: int = 50, min_trades: int = 5) -> List[Dict]:
        """Get top performing whales by ROI score"""
        conn = sqlite3.connect(self.existing_db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    wallet_address,
                    composite_score,
                    avg_roi_percent,
                    total_trades,
                    win_rate_percent,
                    total_volume_usd,
                    sharpe_ratio,
                    max_drawdown_percent,
                    calculated_at
                FROM whale_roi_scores 
                WHERE total_trades >= ?
                ORDER BY composite_score DESC 
                LIMIT ?
            """, (min_trades, limit))
            
            rows = cursor.fetchall()
            
            whales = []
            for row in rows:
                whale = {
                    'wallet_address': row[0],
                    'composite_score': float(row[1]),
                    'avg_roi_percent': float(row[2]),
                    'total_trades': int(row[3]),
                    'win_rate_percent': float(row[4]),
                    'total_volume_usd': float(row[5]),
                    'sharpe_ratio': float(row[6]),
                    'max_drawdown_percent': float(row[7]),
                    'calculated_at': row[8]
                }
                whales.append(whale)
            
            return whales
            
        except Exception as e:
            logger.error(f"Error getting top whales: {e}")
            return []
        finally:
            conn.close()
    
    def refresh_whale_roi_score(self, wallet_address: str, days_lookback: int = 90) -> Dict:
        """Refresh ROI score for a specific whale"""
        logger.info(f"Refreshing ROI score for {wallet_address}")
        
        try:
            # Get recent transactions
            tx_hashes = self.get_whale_transactions(wallet_address, limit=200)
            
            if tx_hashes:
                # Process transactions
                self.roi_scorer.process_wallet_transactions(wallet_address, tx_hashes)
                
                # Calculate new score
                roi_data = self.roi_scorer.calculate_wallet_score(wallet_address, days_lookback)
                
                # Update database
                self.update_whale_with_roi_data(wallet_address, roi_data)
                
                return roi_data
            else:
                logger.warning(f"No transactions found for {wallet_address}")
                return {}
                
        except Exception as e:
            logger.error(f"Error refreshing ROI score for {wallet_address}: {e}")
            return {}
    
    def get_whale_performance_report(self, wallet_address: str) -> Dict:
        """Get comprehensive performance report for a whale"""
        # Get ROI data from ROI database
        roi_metrics = self.roi_scorer.performance_calculator.calculate_wallet_performance(wallet_address)
        
        # Get additional context from existing database
        conn = sqlite3.connect(self.existing_db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM whale_roi_scores 
                WHERE wallet_address = ?
            """, (wallet_address,))
            
            roi_score_row = cursor.fetchone()
            
            report = {
                'wallet_address': wallet_address,
                'roi_metrics': roi_metrics,
                'roi_scores': roi_score_row,
                'generated_at': datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {'error': str(e)}
        finally:
            conn.close()
    
    def export_roi_data_to_json(self, output_file: str = "whale_roi_data.json"):
        """Export all ROI data to JSON for analysis"""
        whales = self.get_top_whales_by_roi(limit=1000, min_trades=1)
        
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'total_whales': len(whales),
            'whales': whales
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Exported ROI data for {len(whales)} whales to {output_file}")
        return output_file

# Enhanced minimal whale scanner with transaction fetching
class EnhancedWhaleScanner(MinimalWhaleScanner):
    """Enhanced whale scanner with transaction history fetching"""
    
    def __init__(self):
        super().__init__()
        self.etherscan_api_key = os.getenv('ETHERSCAN_API_KEY', '')
        self.etherscan_base_url = "https://api.etherscan.io/api"
    
    def get_wallet_transactions(self, wallet_address: str, limit: int = 100) -> List[Dict]:
        """Get transaction history for a wallet"""
        if not self.etherscan_api_key:
            logger.warning("No Etherscan API key found. Using mock data.")
            return self.get_mock_transactions(wallet_address, limit)
        
        import requests
        
        try:
            params = {
                'module': 'account',
                'action': 'txlist',
                'address': wallet_address,
                'startblock': 0,
                'endblock': 99999999,
                'page': 1,
                'offset': limit,
                'sort': 'desc',
                'apikey': self.etherscan_api_key
            }
            
            response = requests.get(self.etherscan_base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == '1':
                    return data['result']
            
            logger.error(f"Etherscan API error: {response.text}")
            return []
            
        except Exception as e:
            logger.error(f"Error fetching transactions from Etherscan: {e}")
            return []
    
    def get_mock_transactions(self, wallet_address: str, limit: int) -> List[Dict]:
        """Generate mock transaction data for testing"""
        mock_transactions = []
        base_block = 18000000
        
        for i in range(min(limit, 20)):  # Limit mock data
            tx = {
                'hash': f'0x{"a" * 64}',  # Mock transaction hash
                'blockNumber': str(base_block + i),
                'timeStamp': str(int(datetime.now().timestamp()) - i * 3600),
                'from': wallet_address,
                'to': '0x' + 'b' * 40,
                'value': str(1000000000000000000),  # 1 ETH in wei
                'gas': '21000',
                'gasPrice': '20000000000',
                'gasUsed': '21000'
            }
            mock_transactions.append(tx)
        
        return mock_transactions

if __name__ == "__main__":
    # Example usage
    integration = WhaleROIIntegration()
    
    # Test with a sample whale address
    sample_address = "0x8eb8a3b98659cce290402893d0123abb75e3ab28"  # Example address
    
    print("Testing ROI integration...")
    
    # Refresh score for sample whale
    roi_data = integration.refresh_whale_roi_score(sample_address)
    
    if roi_data:
        print(f"ROI Score for {sample_address}: {roi_data['composite_score']}")
    
    # Get top whales
    top_whales = integration.get_top_whales_by_roi(limit=10)
    print(f"Found {len(top_whales)} top whales by ROI")
    
    # Export data
    export_file = integration.export_roi_data_to_json()
    print(f"Exported data to {export_file}")