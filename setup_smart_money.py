#!/usr/bin/env python3
"""
Setup Smart Money Database
Initialize tables only - NO hardcoded addresses
"""

import sys
import json
sys.path.insert(0, '.')

from src.data.smart_money_repository import smart_money_repository

def import_dex_routers_from_file(filename: str):
    """Import DEX routers from a JSON file provided by user"""
    if not smart_money_repository:
        print("❌ Repository not available")
        return False
    
    try:
        with open(filename, 'r') as f:
            routers = json.load(f)
        
        print(f"📊 Importing {len(routers)} DEX routers from {filename}...")
        added = 0
        for router in routers:
            success = smart_money_repository.add_dex_router(
                router['address'], 
                router['name'], 
                router.get('version')
            )
            if success:
                added += 1
                print(f"   ✅ Added {router['name']}")
        
        print(f"Imported {added} DEX routers")
        return added > 0
        
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        print("Please create a JSON file with DEX router data")
        print("Format: [{'address': '0x...', 'name': 'Router Name', 'version': 'V1'}]")
        return False
    except Exception as e:
        print(f"❌ Error importing: {e}")
        return False

def import_cex_addresses_from_file(filename: str):
    """Import CEX addresses from a JSON file provided by user"""
    if not smart_money_repository:
        print("❌ Repository not available")
        return False
    
    try:
        with open(filename, 'r') as f:
            addresses = json.load(f)
        
        print(f"📊 Importing {len(addresses)} CEX addresses from {filename}...")
        added = 0
        for addr in addresses:
            success = smart_money_repository.add_cex_address(
                addr['address'],
                addr['exchange_name'],
                addr.get('address_type', 'hot_wallet')
            )
            if success:
                added += 1
                print(f"   ✅ Added {addr['exchange_name']}")
        
        print(f"Imported {added} CEX addresses")
        return added > 0
        
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        print("Please create a JSON file with CEX address data")
        print("Format: [{'address': '0x...', 'exchange_name': 'Exchange', 'address_type': 'hot_wallet'}]")
        return False
    except Exception as e:
        print(f"❌ Error importing: {e}")
        return False

def main():
    """Main setup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup Smart Money Database')
    parser.add_argument('--import-dex', metavar='FILE', 
                       help='Import DEX routers from JSON file')
    parser.add_argument('--import-cex', metavar='FILE',
                       help='Import CEX addresses from JSON file')
    parser.add_argument('--create-sample-files', action='store_true',
                       help='Create sample JSON files (empty templates)')
    
    args = parser.parse_args()
    
    if not smart_money_repository:
        print("❌ Smart money repository not available")
        print("Check Supabase configuration")
        return 1
    
    if args.create_sample_files:
        # Create empty template files for users to fill in
        sample_dex = [
            {
                "address": "PASTE_DEX_ROUTER_ADDRESS_HERE",
                "name": "Router Name",
                "version": "V1"
            }
        ]
        
        sample_cex = [
            {
                "address": "PASTE_CEX_WALLET_ADDRESS_HERE",
                "exchange_name": "Exchange Name",
                "address_type": "hot_wallet"
            }
        ]
        
        with open('sample_dex_routers.json', 'w') as f:
            json.dump(sample_dex, f, indent=2)
        
        with open('sample_cex_addresses.json', 'w') as f:
            json.dump(sample_cex, f, indent=2)
        
        print("✅ Created sample files:")
        print("   • sample_dex_routers.json")
        print("   • sample_cex_addresses.json")
        print("\nEdit these files with your data, then run:")
        print("python3 setup_smart_money.py --import-dex sample_dex_routers.json")
        print("python3 setup_smart_money.py --import-cex sample_cex_addresses.json")
        return 0
    
    if args.import_dex:
        import_dex_routers_from_file(args.import_dex)
    
    if args.import_cex:
        import_cex_addresses_from_file(args.import_cex)
    
    if not args.import_dex and not args.import_cex:
        parser.print_help()
        print("\nℹ️  Start with: python3 setup_smart_money.py --create-sample-files")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())