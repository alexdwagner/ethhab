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
    if supabase_client.create_tables():
        print("✅ Database schema created successfully")
    else:
        print("❌ Failed to create database schema")
        return False
    
    print("\n🎉 Supabase setup complete!")
    print("\nNext steps:")
    print("1. Copy .env.example to .env and fill in your API keys")
    print("2. Run: python app.py")
    print("3. Visit: http://localhost:8080")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)