#!/usr/bin/env python3
"""
Basic Tests
Simple tests for whale tracker components
"""

import sys
import unittest
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.dbOperations import DbOperations
from src.analyzers.roiAnalyzer import RoiAnalyzer
from src.scanners.whale_scanner import WhaleScanner
from config import config

class TestDatabase(unittest.TestCase):
    """Test database operations"""
    
    def setUp(self):
        """Set up test database"""
        self.db = DbOperations(":memory:")  # Use in-memory database for tests
    
    def test_database_creation(self):
        """Test that database tables are created"""
        stats = self.db.get_stats()
        self.assertEqual(stats['total_whales'], 0)
        self.assertEqual(stats['whales_with_roi'], 0)
    
    def test_save_whale(self):
        """Test saving whale data"""
        success = self.db.save_whale(
            "0x1234567890123456789012345678901234567890",
            "Test Whale",
            1000.0,
            "Test Entity",
            "Test Category"
        )
        self.assertTrue(success)
        
        stats = self.db.get_stats()
        self.assertEqual(stats['total_whales'], 1)
    
    def test_save_roi_score(self):
        """Test saving ROI score"""
        address = "0x1234567890123456789012345678901234567890"
        
        # First save a whale
        self.db.save_whale(address, "Test Whale", 1000.0)
        
        # Then save ROI score
        success = self.db.save_roi_score(address, 75.5, 100, 25.0, 70.0, 50000.0)
        self.assertTrue(success)
        
        stats = self.db.get_stats()
        self.assertEqual(stats['whales_with_roi'], 1)
        self.assertGreater(stats['avg_roi_score'], 0)

class TestROIAnalyzer(unittest.TestCase):
    """Test ROI analyzer"""
    
    def setUp(self):
        """Set up ROI analyzer"""
        self.analyzer = RoiAnalyzer()
    
    def test_calculate_roi(self):
        """Test ROI calculation"""
        roi_data = self.analyzer.calculate_whale_roi(
            "0x1234567890123456789012345678901234567890",
            10000.0,  # 10K ETH
            "Centralized Exchange",
            "CEX Hot Wallet"
        )
        
        # Check that all required fields are present
        required_fields = [
            'composite_score', 'roi_score', 'volume_score', 
            'consistency_score', 'risk_score', 'activity_score', 
            'efficiency_score', 'total_trades', 'win_rate_percent'
        ]
        
        for field in required_fields:
            self.assertIn(field, roi_data)
        
        # Check score ranges
        self.assertGreaterEqual(roi_data['composite_score'], 0)
        self.assertLessEqual(roi_data['composite_score'], 100)
        self.assertGreater(roi_data['total_trades'], 0)
    
    def test_score_category(self):
        """Test score categorization"""
        self.assertEqual(self.analyzer.get_score_category(85), 'excellent')
        self.assertEqual(self.analyzer.get_score_category(65), 'good')
        self.assertEqual(self.analyzer.get_score_category(45), 'average')
        self.assertEqual(self.analyzer.get_score_category(25), 'poor')

class TestWhaleScanner(unittest.TestCase):
    """Test whale scanner"""
    
    def setUp(self):
        """Set up whale scanner"""
        self.scanner = WhaleScanner()
    
    def test_whale_addresses_loaded(self):
        """Test that whale addresses are loaded"""
        addresses = self.scanner.whale_addresses
        self.assertGreater(len(addresses), 0)
        
        # Check that addresses are properly formatted
        for address in addresses[:5]:  # Check first 5
            self.assertTrue(address.startswith('0x'))
            self.assertEqual(len(address), 42)
    
    def test_whale_info_structure(self):
        """Test whale info data structure"""
        # Get info for first whale (without API call)
        address = self.scanner.whale_addresses[0]
        whale_info = self.scanner.get_whale_info(address)
        
        required_fields = ['address', 'name', 'entity_type', 'category', 'balance_eth']
        for field in required_fields:
            self.assertIn(field, whale_info)
    
    def test_is_whale_address(self):
        """Test whale address detection"""
        # Test with known whale address
        known_address = self.scanner.whale_addresses[0]
        self.assertTrue(self.scanner.is_whale_address(known_address))
        
        # Test with unknown address
        unknown_address = "0x0000000000000000000000000000000000000000"
        self.assertFalse(self.scanner.is_whale_address(unknown_address))

class TestConfig(unittest.TestCase):
    """Test configuration"""
    
    def test_config_loaded(self):
        """Test that configuration is loaded"""
        self.assertIsNotNone(config.DATABASE_PATH)
        self.assertIsNotNone(config.DATA_DIR)
        self.assertIsNotNone(config.DEFAULT_PORT)
    
    def test_directories_exist(self):
        """Test that required directories exist"""
        self.assertTrue(config.DATA_DIR.exists())

def run_tests():
    """Run all tests"""
    print("🧪 Running Whale Tracker Tests")
    print("=" * 40)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestROIAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestWhaleScanner))
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    if result.wasSuccessful():
        print(f"\n✅ All {result.testsRun} tests passed!")
        return True
    else:
        print(f"\n❌ {len(result.failures)} failures, {len(result.errors)} errors")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)