#!/usr/bin/env python3
"""
Supabase Database Client
Manages connection and operations with Supabase PostgreSQL
"""

from supabase import create_client, Client
from typing import List, Dict, Optional, Any
import os
from config import config

class SupabaseClient:
    """Supabase database client wrapper"""
    
    def __init__(self):
        if not config.SUPABASE_URL or not config.SUPABASE_ANON_KEY:
            raise ValueError("Supabase credentials not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY")
        
        # Prefer service role for backend writes (bypasses RLS where appropriate).
        # Falls back to anon key if service role is not provided.
        key = config.SUPABASE_SERVICE_ROLE_KEY or config.SUPABASE_ANON_KEY
        self.client: Client = create_client(
            config.SUPABASE_URL,
            key
        )
    
    def get_client(self) -> Client:
        """Get Supabase client instance"""
        return self.client
    
    def create_tables(self):
        """Create database schema by executing SQL directly"""
        
        print("🏗️  Creating database schema...")
        
        try:
            # Create whales table
            self.client.rpc('sql', {'query': '''
                CREATE TABLE IF NOT EXISTS whales (
                    id SERIAL PRIMARY KEY,
                    address VARCHAR(42) UNIQUE NOT NULL,
                    label VARCHAR(255),
                    balance_eth DECIMAL(20,8) DEFAULT 0,
                    balance_usd DECIMAL(20,2) DEFAULT 0,
                    entity_type VARCHAR(100),
                    category VARCHAR(100),
                    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
                    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            '''}).execute()
            
            print("✅ Whales table created")
            
            # Create ROI scores table
            self.client.rpc('sql', {'query': '''
                CREATE TABLE IF NOT EXISTS whale_roi_scores (
                    id SERIAL PRIMARY KEY,
                    whale_id INTEGER REFERENCES whales(id) ON DELETE CASCADE,
                    address VARCHAR(42) NOT NULL,
                    composite_score DECIMAL(5,2) DEFAULT 0,
                    roi_score DECIMAL(5,2) DEFAULT 0,
                    volume_score DECIMAL(5,2) DEFAULT 0,
                    consistency_score DECIMAL(5,2) DEFAULT 0,
                    risk_score DECIMAL(5,2) DEFAULT 0,
                    activity_score DECIMAL(5,2) DEFAULT 0,
                    efficiency_score DECIMAL(5,2) DEFAULT 0,
                    total_trades INTEGER DEFAULT 0,
                    avg_roi_percent DECIMAL(10,4) DEFAULT 0,
                    win_rate_percent DECIMAL(10,4) DEFAULT 0,
                    total_volume_usd DECIMAL(20,2) DEFAULT 0,
                    sharpe_ratio DECIMAL(6,3) DEFAULT 0,
                    max_drawdown_percent DECIMAL(6,2) DEFAULT 0,
                    calculated_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    
                    UNIQUE(whale_id),
                    UNIQUE(address)
                );
            '''}).execute()
            
            print("✅ ROI scores table created")
            
            # Create indexes
            self.client.rpc('sql', {'query': '''
                CREATE INDEX IF NOT EXISTS idx_whales_address ON whales(address);
                CREATE INDEX IF NOT EXISTS idx_whales_balance_eth ON whales(balance_eth DESC);
                CREATE INDEX IF NOT EXISTS idx_roi_composite ON whale_roi_scores(composite_score DESC);
            '''}).execute()
            
            print("✅ Database indexes created")
            print("✅ Supabase schema created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error creating Supabase schema: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            # Try a simple database query that doesn't require specific tables
            result = self.client.rpc('version').execute()
            print("✅ Supabase connection successful")
            return True
        except Exception as e:
            print(f"❌ Supabase connection failed: {e}")
            # Try alternative test - just check if client can authenticate
            try:
                # This will fail gracefully if no tables exist but connection works
                self.client.table('_dummy_').select('*').limit(0).execute()
                print("✅ Supabase connection successful (auth verified)")
                return True
            except Exception as e2:
                if 'PGRST116' in str(e2) or 'relation' in str(e2):
                    # Table doesn't exist but connection works
                    print("✅ Supabase connection successful")
                    return True
                print(f"❌ Supabase connection failed: {e2}")
                return False

# Create singleton instance
supabase_client = SupabaseClient() if config.SUPABASE_URL and config.SUPABASE_ANON_KEY else None

if __name__ == "__main__":
    if supabase_client:
        print("🔗 Testing Supabase connection...")
        success = supabase_client.test_connection()
        if success:
            print("🏗️  Creating database schema...")
            supabase_client.create_tables()
    else:
        print("❌ Supabase not configured. Please set environment variables.")
