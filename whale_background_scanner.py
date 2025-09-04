#!/usr/bin/env python3
"""
Whale Background Scanner CLI
Command line interface for managing background whale scanning
"""

import sys
import time
import signal
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, '.')

from config import config
from src.services.whale_scanner_service import whale_scanner_service

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print(f"\n🛑 Received signal {signum}, shutting down...")
    if whale_scanner_service:
        whale_scanner_service.stop_background_scanning()
    sys.exit(0)

def run_single_scan():
    """Run a single whale scan"""
    if not whale_scanner_service:
        print("❌ Whale scanner service not available - check configuration")
        return
    
    print("🚀 Running single whale scan...")
    result = whale_scanner_service.run_full_scan()
    
    print("\n📈 Scan Summary:")
    print(f"   • Addresses scanned: {result['total_addresses']}")
    print(f"   • Successful: {result['successful_scans']}")
    print(f"   • Failed: {result['failed_scans']}")
    print(f"   • Total ETH: {result['total_eth']:,.2f} ETH")
    print(f"   • Duration: {result['scan_duration_seconds']:.1f}s")

def run_background_daemon(interval_hours: int = 1):
    """Run background scanning daemon"""
    if not whale_scanner_service:
        print("❌ Whale scanner service not available - check configuration")
        return
    
    print(f"🐋 Whale Background Scanner Daemon")
    print(f"=" * 40)
    print(f"⏰ Scan interval: {interval_hours} hour(s)")
    print(f"🗄️  Database: Supabase PostgreSQL")
    print(f"🔑 API Keys: {'✅' if config.ETHERSCAN_API_KEY else '❌'} Etherscan")
    
    # Get current whale count from database
    whale_count = len(whale_scanner_service.whale_service.whale_addresses)
    print(f"📊 Whale addresses in database: {whale_count}")
    
    if whale_count == 0:
        print("\n⚠️  No whale addresses found in database!")
        print("Add whale addresses using: python3 manage_whales.py add <address> <label>")
        return
    
    print("Press Ctrl+C to stop\n")
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start background scanning
    whale_scanner_service.start_background_scanning(interval_hours)
    
    try:
        # Keep the main thread alive
        while whale_scanner_service.is_running:
            time.sleep(30)  # Check every 30 seconds
            
            # Print periodic status
            status = whale_scanner_service.get_scan_status()
            if status['last_scan_time']:
                print(f"ℹ️  Last scan: {status['last_scan_time']} | Status: {'Running' if status['is_running'] else 'Stopped'}")
            
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

def show_status():
    """Show current scanner status"""
    if not whale_scanner_service:
        print("❌ Whale scanner service not available")
        return
    
    status = whale_scanner_service.get_scan_status()
    
    print("🐋 Whale Scanner Status")
    print("=" * 25)
    print(f"Status: {'🟢 Running' if status['is_running'] else '🔴 Stopped'}")
    print(f"Interval: {status['scan_interval_hours']} hour(s)")
    print(f"Whale addresses: {status['total_whale_addresses']}")
    print(f"Last scan: {status['last_scan_time'] or 'Never'}")
    print(f"Thread alive: {'Yes' if status['thread_alive'] else 'No'}")

def main():
    """Main CLI function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Whale Background Scanner')
    parser.add_argument('command', choices=['scan', 'daemon', 'status'], 
                       help='Command to run')
    parser.add_argument('--interval', type=int, default=1,
                       help='Scan interval in hours for daemon mode (default: 1)')
    
    args = parser.parse_args()
    
    # Validate configuration
    if not config.ETHERSCAN_API_KEY:
        print("❌ ETHERSCAN_API_KEY not configured")
        print("Please set your API key in the .env file")
        return 1
    
    if not whale_scanner_service:
        print("❌ Whale scanner service initialization failed")
        print("Check your Supabase configuration")
        return 1
    
    # Execute command
    if args.command == 'scan':
        run_single_scan()
    elif args.command == 'daemon':
        run_background_daemon(args.interval)
    elif args.command == 'status':
        show_status()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())