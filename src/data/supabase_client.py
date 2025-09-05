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
        if not config.SUPABASE_URL or not (config.SUPABASE_ANON_KEY or config.SUPABASE_SERVICE_ROLE_KEY):
            raise ValueError("Supabase credentials not configured. Please set SUPABASE_URL and either SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY")
        
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
        """Guide schema creation. DDL is not supported via PostgREST.

        Supabase's REST API cannot execute CREATE TABLE statements. Apply the
        SQL in `scripts/supabase_production_schema.sql` (and migrations under
        `supabase/migrations/`) using the Supabase SQL Editor or the Supabase CLI.
        """
        print("🏗️  Creating database schema...")
        print("ℹ️  DDL cannot be run via Supabase REST. Use one of:")
        print("  - Supabase SQL Editor: open scripts/supabase_production_schema.sql and run it")
        print("  - Supabase CLI: `supabase db push` with the migrations in ./supabase/migrations")

        # Best-effort check: do tables already exist?
        try:
            self.client.table('whales').select('id').limit(1).execute()
            self.client.table('whale_roi_scores').select('id').limit(1).execute()
            print("✅ Tables appear to exist already")
            return True
        except Exception:
            print("❌ Tables not found yet. Please apply the SQL schema as noted above.")
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
supabase_client = SupabaseClient() if (config.SUPABASE_URL and (config.SUPABASE_ANON_KEY or config.SUPABASE_SERVICE_ROLE_KEY)) else None

if __name__ == "__main__":
    if supabase_client:
        print("🔗 Testing Supabase connection...")
        success = supabase_client.test_connection()
        if success:
            print("🏗️  Creating database schema...")
            supabase_client.create_tables()
    else:
        print("❌ Supabase not configured. Please set environment variables.")
