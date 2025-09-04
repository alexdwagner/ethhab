#!/usr/bin/env python3
"""
Database Consolidation Script
Merges all whale tracking databases into a single whale_tracker.db
"""

import sqlite3
import os
from datetime import datetime

def create_unified_schema():
    """Create unified database schema"""
    schema_sql = """
    -- Core whale tracking
    CREATE TABLE IF NOT EXISTS whales (
        address VARCHAR(42) PRIMARY KEY,
        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_balance_eth DECIMAL(18,8),
        label VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hash VARCHAR(66) UNIQUE NOT NULL,
        from_address VARCHAR(42) NOT NULL,
        to_address VARCHAR(42),
        value_eth DECIMAL(18,8) NOT NULL,
        value_usd DECIMAL(18,2),
        gas_used INTEGER,
        gas_price DECIMAL(18,0),
        block_number INTEGER NOT NULL,
        block_timestamp TIMESTAMP NOT NULL,
        transaction_type VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        whale_address VARCHAR(42) NOT NULL,
        transaction_hash VARCHAR(66) NOT NULL,
        alert_type VARCHAR(50) NOT NULL,
        amount_eth DECIMAL(18,8) NOT NULL,
        amount_usd DECIMAL(18,2),
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Intelligence system
    CREATE TABLE IF NOT EXISTS whale_intelligence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wallet_address VARCHAR(42) NOT NULL,
        intelligence_data TEXT,
        score DECIMAL(5,2),
        analysis_timestamp TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS intelligence_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wallet_address VARCHAR(42) NOT NULL,
        alert_type VARCHAR(50) NOT NULL,
        alert_data TEXT,
        severity VARCHAR(20) DEFAULT 'medium',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ROI Scoring System
    CREATE TABLE IF NOT EXISTS token_fills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wallet_address VARCHAR(42) NOT NULL,
        token_address VARCHAR(42) NOT NULL,
        token_symbol VARCHAR(20) NOT NULL,
        token_decimals INTEGER NOT NULL,
        direction VARCHAR(4) NOT NULL, -- BUY/SELL
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
    );

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
    );

    CREATE TABLE IF NOT EXISTS daily_equity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wallet_address VARCHAR(42) NOT NULL,
        date DATE NOT NULL,
        portfolio_value_usd DECIMAL(18,2) NOT NULL,
        realized_pnl_usd DECIMAL(18,2) NOT NULL,
        unrealized_pnl_usd DECIMAL(18,2) NOT NULL,
        total_invested_usd DECIMAL(18,2) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(wallet_address, date)
    );

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
    );

    -- Social intelligence
    CREATE TABLE IF NOT EXISTS whale_identities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wallet_address VARCHAR(42) NOT NULL,
        identity_type VARCHAR(50) NOT NULL,
        identity_value VARCHAR(255) NOT NULL,
        confidence_score DECIMAL(3,2) DEFAULT 0.5,
        source VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(wallet_address, identity_type, identity_value)
    );

    CREATE TABLE IF NOT EXISTS social_mentions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wallet_address VARCHAR(42) NOT NULL,
        platform VARCHAR(50) NOT NULL,
        mention_text TEXT NOT NULL,
        url VARCHAR(500),
        sentiment VARCHAR(20),
        engagement_score INTEGER DEFAULT 0,
        scraped_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_transactions_from ON transactions(from_address, block_timestamp);
    CREATE INDEX IF NOT EXISTS idx_transactions_to ON transactions(to_address, block_timestamp);
    CREATE INDEX IF NOT EXISTS idx_alerts_whale ON alerts(whale_address, created_at);
    CREATE INDEX IF NOT EXISTS idx_fills_wallet_time ON token_fills(wallet_address, block_timestamp);
    CREATE INDEX IF NOT EXISTS idx_lots_wallet_exit ON closed_trade_lots(wallet_address, exit_timestamp);
    CREATE INDEX IF NOT EXISTS idx_roi_score ON whale_roi_scores(composite_score DESC);
    CREATE INDEX IF NOT EXISTS idx_social_wallet ON social_mentions(wallet_address, scraped_at);
    """
    
    return schema_sql

def migrate_data_from_db(source_db, target_conn, table_mappings):
    """Migrate data from source database to target"""
    if not os.path.exists(source_db):
        print(f"⚠️  Source database {source_db} not found - skipping")
        return 0
    
    source_conn = sqlite3.connect(source_db)
    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()
    
    total_migrated = 0
    
    # Check what tables exist in source
    source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    source_tables = [row[0] for row in source_cursor.fetchall()]
    
    for source_table, target_table in table_mappings.items():
        if source_table not in source_tables:
            continue
            
        try:
            # Get all data from source table
            source_cursor.execute(f"SELECT * FROM {source_table}")
            rows = source_cursor.fetchall()
            
            if not rows:
                continue
            
            # Get column names
            source_cursor.execute(f"PRAGMA table_info({source_table})")
            columns = [col[1] for col in source_cursor.fetchall()]
            
            # Prepare insert statement
            placeholders = ','.join(['?' for _ in columns])
            insert_sql = f"INSERT OR IGNORE INTO {target_table} ({','.join(columns)}) VALUES ({placeholders})"
            
            # Insert data
            target_cursor.executemany(insert_sql, rows)
            migrated_count = target_cursor.rowcount
            total_migrated += migrated_count
            
            print(f"✅ Migrated {migrated_count} rows from {source_table} to {target_table}")
            
        except Exception as e:
            print(f"⚠️  Error migrating {source_table}: {e}")
            continue
    
    source_conn.close()
    return total_migrated

def consolidate_databases():
    """Main consolidation function"""
    print("🔄 Consolidating Whale Tracker Databases")
    print("=" * 50)
    
    # Create unified database
    target_db = "whale_tracker.db"
    
    # Remove existing unified database if it exists
    if os.path.exists(target_db):
        backup_name = f"whale_tracker_backup_{int(datetime.now().timestamp())}.db"
        os.rename(target_db, backup_name)
        print(f"📦 Backed up existing database to {backup_name}")
    
    # Create new unified database
    target_conn = sqlite3.connect(target_db)
    target_cursor = target_conn.cursor()
    
    # Create schema
    print("🏗️  Creating unified schema...")
    schema_sql = create_unified_schema()
    target_cursor.executescript(schema_sql)
    target_conn.commit()
    print("✅ Unified schema created")
    
    # Define table mappings for migration
    migrations = [
        {
            'source_db': 'ethhab.db',
            'mappings': {
                'whales': 'whales',
                'transactions': 'transactions', 
                'alerts': 'alerts'
            }
        },
        {
            'source_db': 'whale_intelligence.db',
            'mappings': {
                'whale_intelligence': 'whale_intelligence',
                'intelligence_alerts': 'intelligence_alerts'
            }
        },
        {
            'source_db': 'roi_tracking.db',
            'mappings': {
                'token_fills': 'token_fills',
                'closed_trade_lots': 'closed_trade_lots',
                'daily_equity': 'daily_equity',
                'whale_roi_scores': 'whale_roi_scores'
            }
        },
        {
            'source_db': 'whale_social.db',
            'mappings': {
                'whale_identities': 'whale_identities',
                'social_mentions': 'social_mentions',
                'scraped_mentions': 'social_mentions',  # Map old table name
                'entity_links': 'whale_identities',     # Map old table name
                'identity_claims': 'whale_identities'   # Map old table name
            }
        }
    ]
    
    # Perform migrations
    total_migrated = 0
    for migration in migrations:
        print(f"\n📊 Migrating from {migration['source_db']}...")
        migrated = migrate_data_from_db(
            migration['source_db'], 
            target_conn, 
            migration['mappings']
        )
        total_migrated += migrated
    
    target_conn.commit()
    target_conn.close()
    
    # Summary
    print(f"\n🎉 Database Consolidation Complete!")
    print(f"📊 Total rows migrated: {total_migrated}")
    print(f"💾 Unified database: {target_db}")
    
    # Check final database size
    if os.path.exists(target_db):
        size_kb = os.path.getsize(target_db) / 1024
        print(f"💿 Final database size: {size_kb:.1f} KB")
    
    # List tables in final database
    final_conn = sqlite3.connect(target_db)
    final_cursor = final_conn.cursor()
    final_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in final_cursor.fetchall()]
    final_conn.close()
    
    print(f"\n📋 Final database contains {len(tables)} tables:")
    for table in tables:
        print(f"   ✅ {table}")
    
    return target_db

if __name__ == "__main__":
    unified_db = consolidate_databases()
    
    print(f"\n🔧 Next Steps:")
    print(f"1. Update .env to use: DATABASE_PATH={unified_db}")
    print(f"2. Update all code references to use unified database")
    print(f"3. Test the system with: python3 test_unified_system.py")
    print(f"4. Archive old database files once confirmed working")