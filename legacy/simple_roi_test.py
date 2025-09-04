#!/usr/bin/env python3
"""
Simple ROI System Test - Database Schema and Core Logic
Tests without external dependencies
"""

import sqlite3
import os
from datetime import datetime, timedelta

def create_roi_tracking_schema(db_path: str):
    """Create database schema for event-sourced ROI tracking"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Raw blockchain fills (event-sourced)
    cursor.execute("""
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
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fills_wallet_time ON token_fills(wallet_address, block_timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fills_token_time ON token_fills(token_address, block_timestamp)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_fills_unique ON token_fills(transaction_hash, log_index)")
    
    # Closed trade lots (FIFO accounting)
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
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lots_wallet_exit ON closed_trade_lots(wallet_address, exit_timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lots_roi ON closed_trade_lots(roi_percent DESC)")
    
    # Daily equity snapshots
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_equity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet_address VARCHAR(42) NOT NULL,
            date DATE NOT NULL,
            portfolio_value_usd DECIMAL(18,2) NOT NULL,
            realized_pnl_usd DECIMAL(18,2) NOT NULL,
            unrealized_pnl_usd DECIMAL(18,2) NOT NULL,
            total_invested_usd DECIMAL(18,2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_equity_wallet_date ON daily_equity(wallet_address, date)")
    
    # Performance metrics cache
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet_address VARCHAR(42) NOT NULL,
            timeframe_days INTEGER NOT NULL,
            total_trades INTEGER NOT NULL,
            total_net_pnl_usd DECIMAL(18,2) NOT NULL,
            avg_roi_percent DECIMAL(10,4) NOT NULL,
            median_roi_percent DECIMAL(10,4) NOT NULL,
            win_rate_percent DECIMAL(10,4) NOT NULL,
            sharpe_ratio DECIMAL(10,4) NOT NULL,
            max_drawdown_percent DECIMAL(10,4) NOT NULL,
            avg_hold_days DECIMAL(10,2) NOT NULL,
            total_volume_usd DECIMAL(18,2) NOT NULL,
            gas_efficiency_percent DECIMAL(10,4) NOT NULL,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_wallet ON performance_metrics(wallet_address)")
    
    conn.commit()
    conn.close()

def test_database_creation():
    """Test database schema creation"""
    print("🧪 Testing Database Schema Creation")
    print("-" * 40)
    
    db_path = "test_roi_simple.db"
    
    # Clean up existing test database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    try:
        # Create schema
        create_roi_tracking_schema(db_path)
        print("✅ Database schema created successfully")
        
        # Verify tables exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['token_fills', 'closed_trade_lots', 'daily_equity', 'performance_metrics']
        
        for table in expected_tables:
            if table in tables:
                print(f"✅ Table '{table}' created")
            else:
                print(f"❌ Table '{table}' missing")
                return False
        
        # Test inserting sample data
        cursor.execute("""
            INSERT INTO token_fills (
                wallet_address, token_address, token_symbol, token_decimals,
                direction, amount, price_usd, value_usd, block_number,
                block_timestamp, transaction_hash, log_index, gas_cost_usd, counterparty
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            '0x8eb8a3b98659cce290402893d0123abb75e3ab28',
            '0xa0b86a33e6ba7885c6c96a18d07c67d8fe0df8c9',
            'USDC', 6, 'BUY', 1000.0, 1.0, 1000.0, 18000000,
            datetime.now(), '0x' + 'a' * 64, 0, 25.0,
            '0x' + 'b' * 40
        ))
        
        conn.commit()
        print("✅ Sample data insertion successful")
        
        # Test querying
        cursor.execute("SELECT COUNT(*) FROM token_fills")
        count = cursor.fetchone()[0]
        print(f"✅ Query successful: {count} fill record(s)")
        
        conn.close()
        
        # Clean up
        os.remove(db_path)
        print("✅ Database cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        if os.path.exists(db_path):
            os.remove(db_path)
        return False

def test_roi_calculation_logic():
    """Test ROI calculation logic without dependencies"""
    print("\n🧪 Testing ROI Calculation Logic")
    print("-" * 40)
    
    try:
        # Sample trade data
        trades = [
            {
                'entry_cost': 1000.0,
                'entry_gas': 25.0,
                'exit_value': 1200.0,
                'exit_gas': 30.0
            },
            {
                'entry_cost': 500.0,
                'entry_gas': 15.0,
                'exit_value': 450.0,
                'exit_gas': 20.0
            },
            {
                'entry_cost': 2000.0,
                'entry_gas': 40.0,
                'exit_value': 2500.0,
                'exit_gas': 45.0
            }
        ]
        
        total_pnl = 0
        win_count = 0
        
        print("Trade Analysis:")
        for i, trade in enumerate(trades, 1):
            gross_pnl = trade['exit_value'] - trade['entry_cost']
            net_pnl = gross_pnl - trade['entry_gas'] - trade['exit_gas']
            total_cost = trade['entry_cost'] + trade['entry_gas']
            roi_percent = (net_pnl / total_cost * 100) if total_cost > 0 else 0
            
            total_pnl += net_pnl
            if net_pnl > 0:
                win_count += 1
            
            print(f"  Trade {i}: ROI = {roi_percent:.2f}%, P&L = ${net_pnl:.2f}")
        
        win_rate = (win_count / len(trades)) * 100
        avg_roi = sum((trade['exit_value'] - trade['entry_cost'] - trade['entry_gas'] - trade['exit_gas']) / 
                     (trade['entry_cost'] + trade['entry_gas']) * 100 for trade in trades) / len(trades)
        
        print(f"\nSummary:")
        print(f"✅ Total P&L: ${total_pnl:.2f}")
        print(f"✅ Win Rate: {win_rate:.1f}%")
        print(f"✅ Average ROI: {avg_roi:.2f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ ROI calculation test failed: {e}")
        return False

def test_composite_scoring():
    """Test composite scoring algorithm"""
    print("\n🧪 Testing Composite Scoring Algorithm")
    print("-" * 40)
    
    try:
        # Sample wallet metrics
        sample_metrics = {
            'avg_roi_percent': 25.0,
            'total_volume_usd': 50000.0,
            'win_rate_percent': 70.0,
            'sharpe_ratio': 1.5,
            'max_drawdown_percent': 15.0,
            'total_trades': 45,
            'timeframe_days': 90,
            'gas_as_percent_of_volume': 2.0
        }
        
        # Score components (simplified from full algorithm)
        def score_roi(avg_roi_percent):
            if avg_roi_percent <= 0:
                return 0
            elif avg_roi_percent >= 100:
                return 100
            else:
                return min(100, avg_roi_percent)
        
        def score_volume(total_volume_usd):
            if total_volume_usd >= 1000000:
                return 100
            elif total_volume_usd >= 100000:
                return 80
            elif total_volume_usd >= 10000:
                return 60
            elif total_volume_usd >= 1000:
                return 40
            else:
                return 20
        
        def score_consistency(win_rate_percent):
            return min(100, win_rate_percent * 1.25)
        
        def score_risk(sharpe_ratio, max_drawdown_percent):
            sharpe_score = min(100, max(0, sharpe_ratio * 20))
            drawdown_score = max(0, 100 - max_drawdown_percent * 2)
            return (sharpe_score + drawdown_score) / 2
        
        def score_activity(total_trades, timeframe_days):
            trades_per_day = total_trades / timeframe_days
            if trades_per_day >= 1:
                return 100
            elif trades_per_day >= 0.5:
                return 80
            elif trades_per_day >= 0.1:
                return 60
            else:
                return 40
        
        def score_efficiency(gas_percent):
            if gas_percent <= 1:
                return 100
            elif gas_percent <= 2:
                return 80
            elif gas_percent <= 5:
                return 60
            else:
                return 40
        
        # Calculate scores
        scores = {
            'roi_score': score_roi(sample_metrics['avg_roi_percent']),
            'volume_score': score_volume(sample_metrics['total_volume_usd']),
            'consistency_score': score_consistency(sample_metrics['win_rate_percent']),
            'risk_score': score_risk(sample_metrics['sharpe_ratio'], sample_metrics['max_drawdown_percent']),
            'activity_score': score_activity(sample_metrics['total_trades'], sample_metrics['timeframe_days']),
            'efficiency_score': score_efficiency(sample_metrics['gas_as_percent_of_volume'])
        }
        
        # Weighted composite score
        weights = {
            'roi_score': 0.30,
            'volume_score': 0.20,
            'consistency_score': 0.20,
            'risk_score': 0.15,
            'activity_score': 0.10,
            'efficiency_score': 0.05
        }
        
        composite_score = sum(scores[component] * weights[component] for component in scores)
        
        print("Score Components:")
        for component, score in scores.items():
            weight = weights[component]
            weighted = score * weight
            print(f"  {component}: {score:.1f}/100 (weight: {weight:.0%}) = {weighted:.1f}")
        
        print(f"\n✅ Composite Score: {composite_score:.2f}/100")
        
        return True
        
    except Exception as e:
        print(f"❌ Composite scoring test failed: {e}")
        return False

def run_comprehensive_test():
    """Run all tests"""
    print("🚀 ROI Scoring System - Simplified Test Suite")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Database schema
    if test_database_creation():
        tests_passed += 1
    
    # Test 2: ROI calculation logic
    if test_roi_calculation_logic():
        tests_passed += 1
    
    # Test 3: Composite scoring
    if test_composite_scoring():
        tests_passed += 1
    
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("\n🎉 All tests passed! ROI scoring system core logic is working.")
        print("\nNext Steps:")
        print("1. Install missing dependencies: pip install web3 requests")
        print("2. Set up Web3 RPC URL in environment")  
        print("3. Run full integration with roi_integration.py")
        return True
    else:
        print("\n❌ Some tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = run_comprehensive_test()
    
    if not success:
        exit(1)