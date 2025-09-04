#!/usr/bin/env python3
"""
Quick ROI Setup - Works without external dependencies
"""

import os
import sqlite3
from datetime import datetime

def create_roi_db():
    """Create ROI tracking database schema"""
    conn = sqlite3.connect("roi_tracking.db")
    cursor = conn.cursor()
    
    # Token fills table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_fills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet_address VARCHAR(42) NOT NULL,
            token_address VARCHAR(42) NOT NULL,
            token_symbol VARCHAR(20) NOT NULL,
            token_decimals INTEGER NOT NULL,
            direction VARCHAR(4) NOT NULL,
            amount DECIMAL(36,18) NOT NULL,
            price_usd DECIMAL(18,8),
            value_usd DECIMAL(18,2),
            block_number INTEGER NOT NULL,
            block_timestamp TIMESTAMP NOT NULL,
            transaction_hash VARCHAR(66) NOT NULL,
            log_index INTEGER NOT NULL,
            gas_cost_usd DECIMAL(18,2),
            counterparty VARCHAR(42),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Closed trade lots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS closed_trade_lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet_address VARCHAR(42) NOT NULL,
            token_address VARCHAR(42) NOT NULL,
            token_symbol VARCHAR(20) NOT NULL,
            trade_amount DECIMAL(36,18) NOT NULL,
            entry_price_usd DECIMAL(18,8) NOT NULL,
            exit_price_usd DECIMAL(18,8) NOT NULL,
            entry_timestamp TIMESTAMP NOT NULL,
            exit_timestamp TIMESTAMP NOT NULL,
            hold_duration_days INTEGER NOT NULL,
            entry_value_usd DECIMAL(18,2) NOT NULL,
            exit_value_usd DECIMAL(18,2) NOT NULL,
            entry_gas_cost_usd DECIMAL(18,2) NOT NULL,
            exit_gas_cost_usd DECIMAL(18,2) NOT NULL,
            gross_pnl_usd DECIMAL(18,2) NOT NULL,
            net_pnl_usd DECIMAL(18,2) NOT NULL,
            roi_percent DECIMAL(10,4) NOT NULL,
            entry_fill_id INTEGER,
            exit_fill_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Performance metrics table  
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
    
    # Add indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fills_wallet ON token_fills(wallet_address)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lots_wallet ON closed_trade_lots(wallet_address)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_roi_score ON whale_roi_scores(composite_score DESC)")
    
    # Add sample data
    sample_whales = [
        ('0x8eb8a3b98659cce290402893d0123abb75e3ab28', 75.5, 25.0, 60.0, 87.5, 50.0, 80.0, 80.0, 25.0, 45, 70.0, 1.5, 15.0, 50000.0),
        ('0xf977814e90da44bfa03b6295a0616a897441acec', 45.2, 15.0, 80.0, 62.5, 30.0, 60.0, 85.0, 15.0, 120, 65.0, 0.8, 25.0, 150000.0),
        ('0x28c6c06298d514db089934071355e5743bf21d60', 52.8, 20.0, 70.0, 75.0, 40.0, 70.0, 75.0, 20.0, 60, 75.0, 1.2, 12.0, 75000.0)
    ]
    
    for whale_data in sample_whales:
        cursor.execute("""
            INSERT OR REPLACE INTO whale_roi_scores (
                wallet_address, composite_score, roi_score, volume_score, 
                consistency_score, risk_score, activity_score, efficiency_score,
                avg_roi_percent, total_trades, win_rate_percent, sharpe_ratio,
                max_drawdown_percent, total_volume_usd
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, whale_data)
    
    conn.commit()
    conn.close()
    print("✅ ROI tracking database created with sample data")

def create_env_file():
    """Create environment configuration"""
    env_content = """# ROI Scoring Configuration
ETH_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY
ETHERSCAN_API_KEY=YOUR_ETHERSCAN_KEY
ROI_DB_PATH=roi_tracking.db
WHALE_DB_PATH=whale_intelligence.db
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created .env file")
    else:
        print("✅ .env file already exists")

def main():
    print("🚀 Quick ROI Setup")
    print("=" * 30)
    
    create_roi_db()
    create_env_file()
    
    print("\n✅ Setup Complete!")
    print("\nNext steps:")
    print("1. Install dependencies: pip install --break-system-packages web3 requests")  
    print("2. Update .env with your API keys")
    print("3. Run: python3 roi_integration.py")

if __name__ == "__main__":
    main()