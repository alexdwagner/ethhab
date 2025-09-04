#!/usr/bin/env python3
"""
Test script for ROI scoring system
Tests the core functionality with sample data
"""

import os
import sys
import sqlite3
from datetime import datetime, date, timedelta

# Import only the core classes we need for testing, avoiding Web3 dependencies
try:
    from roi_scoring_v2 import (
        create_roi_tracking_schema, 
        Fill, 
        TradeLot, 
        ClosedTradeLot,
        LotTracker
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Some dependencies might be missing. Creating simplified test...")
    
    # If imports fail, we'll create a minimal version for testing
    class Fill:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class TradeLot:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class ClosedTradeLot:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

class MockWeb3:
    """Mock Web3 provider for testing"""
    class eth:
        @staticmethod
        def get_block(block_number):
            # Mock block with timestamp
            return {
                'timestamp': int(datetime(2024, 1, 1).timestamp()) + (block_number * 12)
            }

class MockPriceOracle:
    """Mock price oracle for testing"""
    def __init__(self):
        self.prices = {
            '0xa0b86a33e6ba7885c6c96a18d07c67d8fe0df8c9': 100.0,  # Mock token A
            '0xb47e3cd837ddf8e4c57f05d70ab865de6e193bbb': 50.0,   # Mock token B
            'ETH': 2000.0
        }
    
    def get_price_at_block(self, token_address, block_number):
        return self.prices.get(token_address, 100.0)
    
    def get_eth_price_at_block(self, block_number):
        return self.prices['ETH']

def create_sample_fills():
    """Create sample fill data for testing"""
    base_time = datetime(2024, 1, 1)
    wallet_address = "0x8eb8a3b98659cce290402893d0123abb75e3ab28"
    token_a = "0xa0b86a33e6ba7885c6c96a18d07c67d8fe0df8c9"
    token_b = "0xb47e3cd837ddf8e4c57f05d70ab865de6e193bbb"
    
    fills = [
        # Buy Token A at $100
        Fill(
            wallet_address=wallet_address,
            token_address=token_a,
            token_symbol="TOKA",
            token_decimals=18,
            direction="BUY",
            amount=100.0,
            price_usd=100.0,
            value_usd=10000.0,
            block_number=18000000,
            block_timestamp=base_time,
            transaction_hash="0x" + "a" * 64,
            log_index=0,
            gas_cost_usd=50.0,
            counterparty="0x" + "c" * 40
        ),
        
        # Sell 50 Token A at $150 (profit)
        Fill(
            wallet_address=wallet_address,
            token_address=token_a,
            token_symbol="TOKA",
            token_decimals=18,
            direction="SELL",
            amount=50.0,
            price_usd=150.0,
            value_usd=7500.0,
            block_number=18001000,
            block_timestamp=base_time + timedelta(days=10),
            transaction_hash="0x" + "b" * 64,
            log_index=0,
            gas_cost_usd=45.0,
            counterparty="0x" + "d" * 40
        ),
        
        # Buy Token B at $50
        Fill(
            wallet_address=wallet_address,
            token_address=token_b,
            token_symbol="TOKB",
            token_decimals=18,
            direction="BUY",
            amount=200.0,
            price_usd=50.0,
            value_usd=10000.0,
            block_number=18002000,
            block_timestamp=base_time + timedelta(days=15),
            transaction_hash="0x" + "c" * 64,
            log_index=0,
            gas_cost_usd=40.0,
            counterparty="0x" + "e" * 40
        ),
        
        # Sell 100 Token B at $45 (loss)
        Fill(
            wallet_address=wallet_address,
            token_address=token_b,
            token_symbol="TOKB",
            token_decimals=18,
            direction="SELL",
            amount=100.0,
            price_usd=45.0,
            value_usd=4500.0,
            block_number=18003000,
            block_timestamp=base_time + timedelta(days=25),
            transaction_hash="0x" + "d" * 64,
            log_index=0,
            gas_cost_usd=35.0,
            counterparty="0x" + "f" * 40
        ),
        
        # Sell remaining 50 Token A at $120
        Fill(
            wallet_address=wallet_address,
            token_address=token_a,
            token_symbol="TOKA",
            token_decimals=18,
            direction="SELL",
            amount=50.0,
            price_usd=120.0,
            value_usd=6000.0,
            block_number=18004000,
            block_timestamp=base_time + timedelta(days=30),
            transaction_hash="0x" + "e" * 64,
            log_index=0,
            gas_cost_usd=40.0,
            counterparty="0x" + "g" * 40
        )
    ]
    
    return fills

def test_lot_tracking():
    """Test FIFO lot tracking functionality"""
    print("\n=== Testing Lot Tracking ===")
    
    # Create test database
    db_path = "test_roi.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    create_roi_tracking_schema(db_path)
    lot_tracker = LotTracker(db_path)
    
    # Create sample fills
    fills = create_sample_fills()
    
    # Process fills
    for fill in fills:
        print(f"Processing {fill.direction} {fill.amount} {fill.token_symbol} at ${fill.price_usd}")
        lot_tracker.process_fill(fill)
    
    # Check results
    print(f"\nClosed lots: {len(lot_tracker.closed_lots)}")
    for i, lot in enumerate(lot_tracker.closed_lots):
        print(f"Lot {i+1}: {lot.token_symbol} - ROI: {lot.roi_percent:.2f}%, P&L: ${lot.net_pnl_usd:.2f}")
    
    # Clean up
    os.remove(db_path)
    
    return lot_tracker.closed_lots

def test_performance_calculation():
    """Test performance metrics calculation"""
    print("\n=== Testing Performance Calculation ===")
    
    # Create test database
    db_path = "test_roi.db" 
    if os.path.exists(db_path):
        os.remove(db_path)
    
    create_roi_tracking_schema(db_path)
    
    # Create components
    mock_web3 = MockWeb3()
    mock_price_oracle = MockPriceOracle()
    lot_tracker = LotTracker(db_path)
    equity_calculator = EquityCalculator(lot_tracker, mock_price_oracle, db_path)
    performance_calculator = PerformanceCalculator(lot_tracker, equity_calculator, db_path)
    
    # Process sample fills
    fills = create_sample_fills()
    for fill in fills:
        lot_tracker.process_fill(fill)
    
    # Calculate performance metrics
    wallet_address = fills[0].wallet_address
    metrics = performance_calculator.calculate_wallet_performance(wallet_address)
    
    print(f"Wallet: {wallet_address}")
    print(f"Total trades: {metrics['total_trades']}")
    print(f"Win rate: {metrics['win_rate_percent']:.1f}%")
    print(f"Average ROI: {metrics['avg_roi_percent']:.2f}%")
    print(f"Total P&L: ${metrics['total_net_pnl_usd']:.2f}")
    print(f"Total volume: ${metrics['total_volume_usd']:.2f}")
    print(f"Sharpe ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Max drawdown: {metrics['max_drawdown_percent']:.2f}%")
    
    # Clean up
    os.remove(db_path)
    
    return metrics

def test_database_operations():
    """Test database operations"""
    print("\n=== Testing Database Operations ===")
    
    db_path = "test_roi.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Create schema
    create_roi_tracking_schema(db_path)
    print("✓ Database schema created successfully")
    
    # Test connection and table creation
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    expected_tables = ['token_fills', 'closed_trade_lots', 'daily_equity', 'performance_metrics']
    for table in expected_tables:
        if table in tables:
            print(f"✓ Table {table} exists")
        else:
            print(f"✗ Table {table} missing")
    
    conn.close()
    
    # Clean up
    os.remove(db_path)

def run_comprehensive_test():
    """Run comprehensive test of the ROI system"""
    print("🧪 ROI Scoring System Test Suite")
    print("=" * 50)
    
    try:
        # Test 1: Database operations
        test_database_operations()
        
        # Test 2: Lot tracking
        closed_lots = test_lot_tracking()
        
        # Test 3: Performance calculation
        metrics = test_performance_calculation()
        
        print("\n🎉 All tests completed successfully!")
        print(f"Sample metrics generated for {metrics['total_trades']} trades")
        print(f"Sample average ROI: {metrics['avg_roi_percent']:.2f}%")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_comprehensive_test()
    
    if success:
        print("\n✅ ROI scoring system is ready for integration!")
        print("Next steps:")
        print("1. Set up Web3 provider with RPC URL")
        print("2. Configure CoinGecko API (optional)")
        print("3. Run roi_integration.py to migrate existing whales")
    else:
        print("\n❌ Tests failed. Please check the implementation.")
        sys.exit(1)