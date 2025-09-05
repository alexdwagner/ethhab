#!/usr/bin/env python3
"""
Whale Tracker Configuration
Centralized configuration management
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # Base paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    CACHE_DIR = DATA_DIR / "cache"
    
    # Supabase Database (Required)
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
    SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
    
    # API Configuration
    ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', '')
    ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY', '')
    ETH_RPC_URL = os.getenv('ETH_RPC_URL', f'https://eth-mainnet.g.alchemy.com/v2/{os.getenv("ALCHEMY_API_KEY", "")}')
    # 0x Swap API key (optional for higher rate limits)
    # Canonical var: ZEROX_SWAP_API_KEY
    ZEROX_SWAP_API_KEY = os.getenv('ZEROX_SWAP_API_KEY', '')
    # Backward-compat alias
    ZEROX_API_KEY = ZEROX_SWAP_API_KEY or os.getenv('ZEROX_API_KEY', '')

    # Whale tracking
    WHALE_THRESHOLD = float(os.getenv('WHALE_THRESHOLD', '1000'))

    # Smart Money discovery thresholds (tunable)
    SMART_MONEY_MIN_SWAPS = int(os.getenv('SMART_MONEY_MIN_SWAPS', '10'))
    SMART_MONEY_ACTIVE_DAYS = int(os.getenv('SMART_MONEY_ACTIVE_DAYS', '60'))
    SMART_MONEY_MIN_PROTOCOLS = int(os.getenv('SMART_MONEY_MIN_PROTOCOLS', '1'))

    # Smart Money discovery execution controls
    # Limits and timeouts to avoid long/hanging runs
    SMART_MONEY_MAX_ROUTERS_PER_RUN = int(os.getenv('SMART_MONEY_MAX_ROUTERS_PER_RUN', '5'))
    SMART_MONEY_DISCOVERY_TIME_BUDGET_SEC = int(os.getenv('SMART_MONEY_DISCOVERY_TIME_BUDGET_SEC', '60'))
    SMART_MONEY_REQUEST_TIMEOUT_SEC = float(os.getenv('SMART_MONEY_REQUEST_TIMEOUT_SEC', '5'))
    SMART_MONEY_DISABLE_NETWORK = os.getenv('SMART_MONEY_DISABLE_NETWORK', '0') in ('1', 'true', 'True')

    # Backfill controls
    SMART_MONEY_BACKFILL_REQUEST_TIMEOUT_SEC = float(os.getenv('SMART_MONEY_BACKFILL_REQUEST_TIMEOUT_SEC', '8'))
    SMART_MONEY_BACKFILL_MAX_TX = int(os.getenv('SMART_MONEY_BACKFILL_MAX_TX', '2500'))  # per-address cap
    SMART_MONEY_BACKFILL_TIME_BUDGET_SEC = int(os.getenv('SMART_MONEY_BACKFILL_TIME_BUDGET_SEC', '120'))
    
    # Caching
    WHALE_CACHE_DURATION_MINUTES = 5
    INDIVIDUAL_WHALE_CACHE_DURATION_HOURS = 1
    
    # Server
    DEFAULT_PORT = int(os.getenv('PORT', '8080'))
    HOST = os.getenv('HOST', 'localhost')
    
    # ROI Scoring
    ROI_RISK_FREE_RATE = 0.02
    ROI_PRICE_CACHE_HOURS = 24
    
    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist"""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.CACHE_DIR.mkdir(exist_ok=True)
    
    @classmethod
    def validate_config(cls):
        """Validate configuration - Supabase required"""
        issues = []
        
        # Required for core functionality
        if not cls.SUPABASE_URL:
            issues.append("SUPABASE_URL not set (Required)")
        
        if not cls.SUPABASE_ANON_KEY:
            issues.append("SUPABASE_ANON_KEY not set (Required)")
        
        # Required for whale scanning
        if not cls.ETHERSCAN_API_KEY:
            issues.append("ETHERSCAN_API_KEY not set (Required)")
        
        if not cls.ALCHEMY_API_KEY:
            issues.append("ALCHEMY_API_KEY not set (Required)")
            
        return issues

# Create singleton instance
config = Config()
config.ensure_directories()

if __name__ == "__main__":
    # Configuration test
    print("🔧 Whale Tracker Configuration")
    print("=" * 40)
    print(f"Database: {config.DATABASE_PATH}")
    print(f"Data Directory: {config.DATA_DIR}")
    print(f"Cache Directory: {config.CACHE_DIR}")
    print(f"ETH RPC URL: {config.ETH_RPC_URL}")
    
    issues = config.validate_config()
    if issues:
        print(f"\n⚠️  Configuration Issues:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print(f"\n✅ Configuration is valid")
