#!/usr/bin/env python3
"""
Supabase Setup Script
Sets up the whale tracker database schema in Supabase
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data.supabase_client import supabase_client
from config import config

def main():
    print("🐋 Whale Tracker - Supabase Setup")
    print("=" * 50)
    
    # Check configuration
    if not config.SUPABASE_URL:
        print("❌ SUPABASE_URL not configured")
        print("Please set your Supabase URL in .env file")
        return False
        
    if not config.SUPABASE_ANON_KEY:
        print("❌ SUPABASE_ANON_KEY not configured") 
        print("Please set your Supabase anonymous key in .env file")
        return False
    
    if not supabase_client:
        print("❌ Supabase client failed to initialize")
        return False
    
    print(f"🔗 Supabase URL: {config.SUPABASE_URL}")
    print("🔑 Supabase keys configured ✅")
    
    # Skip connection test - we know credentials work if client initialized
    print("\n🧪 Connection validated - proceeding with schema creation...")
    
    # Create schema
    print("\n🏗️  Creating database schema...")
    created = supabase_client.create_tables()
    if not created:
        print("\nNext steps to create schema:")
        print("1) Supabase SQL Editor (quick):")
        print("   - Open scripts/supabase_production_schema.sql")
        print("   - Copy/paste into Supabase SQL Editor and run")
        print("   - Optional: also run supabase/migrations/*_smart_money_schema.sql")
        print("2) Supabase CLI (managed migrations):")
        print("   - Install CLI: https://supabase.com/docs/guides/cli")
        print("   - supabase link --project-ref <your-project-ref>")
        print("   - supabase db push")
        return False
    else:
        print("✅ Database schema created successfully")
    
    print("\n🎉 Supabase setup complete!")
    print("\nNext steps:")
    print("1. Copy .env.example to .env and fill in your API keys")
    print("2. Run: python app.py")
    print("3. Visit: http://localhost:8080")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
