#!/usr/bin/env python3
"""
Whale Discovery CLI
Uses the whale discovery service to find new whale addresses
"""

import sys
sys.path.insert(0, '.')

from src.services.whale_discovery_service import whale_discovery_service
from src.data.whale_repository import whale_repository

def main():
    """Run whale discovery"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Discover new whale addresses')
    parser.add_argument('--max', type=int, default=50, 
                       help='Maximum whales to discover (default: 50)')
    parser.add_argument('--blocks', type=int, default=100,
                       help='Number of recent blocks to analyze (default: 100)')
    
    args = parser.parse_args()
    
    if not whale_discovery_service:
        print("❌ Discovery service not available - check API keys")
        return 1
    
    if not whale_repository:
        print("❌ Database not available")
        return 1
    
    # Check current status
    stats = whale_repository.get_stats()
    current_count = stats.get('total_whales', 0)
    
    print(f"🐋 Whale Discovery")
    print("=" * 40)
    print(f"Current whales in database: {current_count}")
    print(f"Target: Discover up to {args.max} new whales")
    print(f"Analyzing last {args.blocks} blocks")
    print()
    
    # Run discovery
    new_whales = whale_discovery_service.discover_and_save_whales(
        max_discoveries=args.max
    )
    
    # Check results
    new_stats = whale_repository.get_stats()
    new_count = new_stats.get('total_whales', 0)
    
    print(f"\n📊 Discovery Results:")
    print(f"   • Started with: {current_count} whales")
    print(f"   • Discovered: {new_whales} new whales")
    print(f"   • Total now: {new_count} whales")
    
    if new_count >= 50:
        print("\n✅ SUCCESS: 50+ whales in database!")
        print("Run scanner to update balances: python3 whale_background_scanner.py scan")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())