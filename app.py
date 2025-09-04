#!/usr/bin/env python3
"""
Whale Tracker Application
Main entry point for the whale tracking system
"""

import sys
import time
import webbrowser
import threading
from http.server import HTTPServer

# Add src to path for imports
sys.path.insert(0, '.')

from config import config
from src.api.handlers import WhaleAPIHandler
from src.data.supabase_client import supabase_client

def open_browser(port: int):
    """Open browser after server starts"""
    time.sleep(1)
    webbrowser.open(f'http://{config.HOST}:{port}')

def run_server(port: int = None):
    """Run the whale tracker server"""
    port = port or config.DEFAULT_PORT
    
    print("🐋 Starting Whale Tracker Application")
    print("=" * 50)
    print(f"🌐 Server: http://{config.HOST}:{port}")
    
    # Database info - Supabase only
    if supabase_client:
        print(f"🗄️  Database: Supabase PostgreSQL ✅")
    else:
        print(f"❌ Supabase not configured!")
        print("Please run: python scripts/setup_supabase.py")
        return
        
    print(f"🔑 API Keys: {'✅' if config.ETHERSCAN_API_KEY else '❌'} Etherscan, {'✅' if config.ALCHEMY_API_KEY else '❌'} Alchemy")
    print("-" * 50)
    
    # Check configuration
    issues = config.validate_config()
    if issues:
        print("⚠️  Configuration Issues:")
        for issue in issues:
            print(f"   - {issue}")
        print("   App will run with limited functionality")
        print("-" * 50)
    
    # Create server
    try:
        server = HTTPServer((config.HOST, port), WhaleAPIHandler)
        print(f"🚀 Server running on port {port}")
        print(f"📈 Features: Whale scanning, ROI scoring, Live dashboard")
        print(f"⚡ Auto-refresh enabled")
        print("\nEndpoints:")
        print("   / - Main dashboard")
        print("   /api/whales - Whale data with ROI scores")
        print("   /api/stats - Database statistics")
        print("   /api/scan/status - Background scanner status")
        print("   /api/scan/trigger - Trigger whale scan (dev only)")
        print("   /health - Health check")
        print("\nPress Ctrl+C to stop...")
        
        # Open browser in background
        browser_thread = threading.Thread(target=open_browser, args=(port,))
        browser_thread.daemon = True
        browser_thread.start()
        
        # Start server
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\n👋 Shutting down Whale Tracker...")
        server.shutdown()
        
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use")
            print(f"Try: python app.py --port {port + 1}")
        else:
            print(f"❌ Server error: {e}")
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main():
    """Main function with command line argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Whale Tracker Application')
    parser.add_argument('--port', type=int, default=config.DEFAULT_PORT,
                       help=f'Server port (default: {config.DEFAULT_PORT})')
    parser.add_argument('--config', action='store_true',
                       help='Show configuration and exit')
    parser.add_argument('--test-db', action='store_true',
                       help='Test database connection and exit')
    
    args = parser.parse_args()
    
    if args.config:
        # Show configuration
        print("🔧 Whale Tracker Configuration")
        print("=" * 40)
        print(f"🗄️  Database: Supabase PostgreSQL")
        print(f"🔗 Supabase URL: {'Set' if config.SUPABASE_URL else 'Not set'}")
        print(f"🔑 Supabase Key: {'Set' if config.SUPABASE_ANON_KEY else 'Not set'}")
        print(f"📁 Data Directory: {config.DATA_DIR}")
        print(f"🔍 Etherscan API Key: {'Set ✅' if config.ETHERSCAN_API_KEY else 'Not set ❌'}")
        print(f"⚡ Alchemy API Key: {'Set ✅' if config.ALCHEMY_API_KEY else 'Not set ❌'}")
        print(f"🐋 Whale Threshold: {config.WHALE_THRESHOLD} ETH")
        
        issues = config.validate_config()
        if issues:
            print(f"\n⚠️  Issues:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print(f"\n✅ Configuration is valid")
        return
    
    if args.test_db:
        # Test database
        print("🧪 Testing database connection...")
        try:
            from src.database.dbOperations import DbOperations
            db = DbOperations()
            stats = db.get_stats()
            print(f"✅ Database connection successful")
            print(f"📊 Stats: {stats}")
        except Exception as e:
            print(f"❌ Database test failed: {e}")
        return
    
    # Run server
    run_server(args.port)

if __name__ == "__main__":
    main()