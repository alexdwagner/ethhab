#!/usr/bin/env python3
"""
ROI Scoring System Setup & Initialization
Sets up the ROI scoring system for immediate use
"""

import os
import sqlite3
from datetime import datetime
from roi_scoring_v2 import create_roi_tracking_schema
from roi_integration import WhaleROIIntegration

def create_env_file():
    """Create .env file with required environment variables"""
    env_content = """# ROI Scoring System Configuration

# Ethereum RPC URL - Get from Alchemy, Infura, or QuickNode
ETH_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY_HERE

# Etherscan API Key (optional, for transaction history)
ETHERSCAN_API_KEY=YOUR_ETHERSCAN_API_KEY_HERE

# CoinGecko Pro API Key (optional, for better rate limits)
COINGECKO_API_KEY=YOUR_COINGECKO_API_KEY_HERE

# Database paths
WHALE_DB_PATH=whale_intelligence.db
ROI_DB_PATH=roi_tracking.db
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created .env file - please update with your API keys")
    else:
        print("✅ .env file already exists")

def initialize_databases():
    """Initialize ROI tracking database"""
    print("Initializing ROI tracking database...")
    
    # Create ROI tracking schema
    create_roi_tracking_schema("roi_tracking.db")
    print("✅ ROI tracking database initialized")
    
    # Check existing whale database
    if os.path.exists("whale_intelligence.db"):
        conn = sqlite3.connect("whale_intelligence.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"✅ Found existing whale database with {len(tables)} tables")
        conn.close()
    else:
        print("⚠️  No existing whale database found - ROI system will create new data")

def test_integration():
    """Test basic integration functionality"""
    print("Testing ROI integration...")
    
    try:
        # Initialize integration (this will work even without Web3)
        integration = WhaleROIIntegration()
        print("✅ ROI integration initialized successfully")
        
        # Test database operations
        conn = sqlite3.connect("roi_tracking.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        conn.close()
        
        if table_count >= 4:
            print(f"✅ ROI database has {table_count} tables ready")
        else:
            print(f"⚠️  ROI database only has {table_count} tables")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def create_sample_whale_data():
    """Create sample whale data for testing"""
    print("Creating sample whale data...")
    
    sample_whales = [
        {
            'address': '0x8eb8a3b98659cce290402893d0123abb75e3ab28',
            'name': 'Sample Whale 1',
            'roi_score': 75.5
        },
        {
            'address': '0xf977814e90da44bfa03b6295a0616a897441acec',
            'name': 'Binance 8',
            'roi_score': 45.2
        },
        {
            'address': '0x28c6c06298d514db089934071355e5743bf21d60',
            'name': 'Binance 14',
            'roi_score': 52.8
        }
    ]
    
    # Add to existing database
    db_path = "whale_intelligence.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create sample whales table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sample_whales (
            address VARCHAR(42) PRIMARY KEY,
            name VARCHAR(100),
            roi_score DECIMAL(5,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    for whale in sample_whales:
        cursor.execute("""
            INSERT OR REPLACE INTO sample_whales (address, name, roi_score)
            VALUES (?, ?, ?)
        """, (whale['address'], whale['name'], whale['roi_score']))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Added {len(sample_whales)} sample whales")

def print_next_steps():
    """Print next steps for user"""
    print("\n🚀 ROI Scoring System Setup Complete!")
    print("=" * 50)
    print("Next Steps:")
    print()
    print("1. 📝 Update .env file with your API keys:")
    print("   - Get Ethereum RPC URL from Alchemy/Infura/QuickNode")
    print("   - Get Etherscan API key (optional)")
    print()
    print("2. 🔧 Install dependencies (if needed):")
    print("   pip install --break-system-packages web3 requests")
    print()
    print("3. 🐋 Start scoring whales:")
    print("   python3 roi_integration.py")
    print()
    print("4. 📊 View results:")
    print("   - Run your existing whale intelligence app")
    print("   - ROI scores will be integrated automatically")
    print()
    print("Files created:")
    print("✅ roi_scoring_v2.py - Core ROI scoring engine")
    print("✅ roi_integration.py - Integration with existing system")
    print("✅ roi_tracking.db - ROI data storage")
    print("✅ .env - Configuration file")

def main():
    """Main setup function"""
    print("🛠️  Setting up ROI Scoring System")
    print("=" * 40)
    
    # Step 1: Create environment file
    create_env_file()
    
    # Step 2: Initialize databases
    initialize_databases()
    
    # Step 3: Test integration
    if test_integration():
        print("✅ Basic integration test passed")
    
    # Step 4: Create sample data
    create_sample_whale_data()
    
    # Step 5: Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()