#!/usr/bin/env python3
"""
Whale Database Management Tool
CLI tool for managing whale addresses in the database
"""

import sys
import json
sys.path.insert(0, '.')

from src.data.whale_repository import whale_repository

def add_whale(address: str, label: str, entity_type: str = "Unknown", category: str = "Unknown"):
    """Add a single whale address to the database"""
    if not whale_repository:
        print("❌ Database not available")
        return False
    
    try:
        success = whale_repository.save_whale(
            address=address,
            label=label,
            balance_eth=0.0,  # Will be updated by scanner
            entity_type=entity_type,
            category=category
        )
        
        if success:
            print(f"✅ Added whale: {label} ({address})")
        else:
            print(f"⚠️  Whale may already exist: {address}")
        
        return success
    except Exception as e:
        print(f"❌ Error adding whale: {e}")
        return False

def list_whales():
    """List all whales in the database"""
    if not whale_repository:
        print("❌ Database not available")
        return
    
    try:
        whales = whale_repository.get_top_whales(limit=1000)
        
        print(f"\n🐋 Total whales in database: {len(whales)}")
        print("-" * 80)
        
        for whale in whales:
            balance = whale.get('balance_eth', 0)
            print(f"• {whale['label']:<40} {whale['address'][:10]}... {balance:>15,.2f} ETH")
            
    except Exception as e:
        print(f"❌ Error listing whales: {e}")

def import_from_json(filename: str):
    """Import whale addresses from a JSON file"""
    if not whale_repository:
        print("❌ Database not available")
        return False
    
    try:
        with open(filename, 'r') as f:
            whales_data = json.load(f)
        
        print(f"📄 Importing {len(whales_data)} whales from {filename}...")
        
        successful = 0
        failed = 0
        
        for whale in whales_data:
            try:
                success = whale_repository.save_whale(
                    address=whale.get("address"),
                    label=whale.get("label", "Unknown"),
                    balance_eth=0.0,
                    entity_type=whale.get("entity_type", "Unknown"),
                    category=whale.get("category", "Unknown")
                )
                
                if success:
                    successful += 1
                    print(f"✅ Added: {whale.get('label')}")
                else:
                    failed += 1
                    
            except Exception as e:
                failed += 1
                print(f"❌ Error: {e}")
        
        print(f"\n📊 Import complete: {successful} added, {failed} failed/skipped")
        return successful > 0
        
    except Exception as e:
        print(f"❌ Error importing from {filename}: {e}")
        return False

def export_to_json(filename: str):
    """Export all whale addresses to a JSON file"""
    if not whale_repository:
        print("❌ Database not available")
        return False
    
    try:
        whales = whale_repository.get_top_whales(limit=1000)
        
        export_data = []
        for whale in whales:
            export_data.append({
                "address": whale['address'],
                "label": whale.get('label', ''),
                "entity_type": whale.get('entity_type', 'Unknown'),
                "category": whale.get('category', 'Unknown'),
                "balance_eth": float(whale.get('balance_eth', 0))
            })
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"✅ Exported {len(export_data)} whales to {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Error exporting to {filename}: {e}")
        return False

def remove_whale(address: str):
    """Remove a whale from the database"""
    if not whale_repository:
        print("❌ Database not available")
        return False
    
    try:
        # Note: You'll need to add a delete method to whale_repository if not exists
        print(f"⚠️  Delete functionality not yet implemented in repository")
        print(f"Would remove whale: {address}")
        return False
        
    except Exception as e:
        print(f"❌ Error removing whale: {e}")
        return False

def get_stats():
    """Get database statistics"""
    if not whale_repository:
        print("❌ Database not available")
        return
    
    try:
        stats = whale_repository.get_stats()
        
        print("\n📊 Whale Database Statistics")
        print("-" * 40)
        print(f"Total whales: {stats.get('total_whales', 0)}")
        print(f"Whales with ROI scores: {stats.get('whales_with_roi', 0)}")
        print(f"Average ROI score: {stats.get('avg_roi_score', 0):.2f}")
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")

def main():
    """Main CLI function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage whale addresses in database')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Add whale command
    add_parser = subparsers.add_parser('add', help='Add a whale address')
    add_parser.add_argument('address', help='Ethereum address')
    add_parser.add_argument('label', help='Whale label/name')
    add_parser.add_argument('--type', default='Unknown', help='Entity type')
    add_parser.add_argument('--category', default='Unknown', help='Category')
    
    # List command
    subparsers.add_parser('list', help='List all whales')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import from JSON file')
    import_parser.add_argument('file', help='JSON file path')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export to JSON file')
    export_parser.add_argument('file', help='JSON file path')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove a whale')
    remove_parser.add_argument('address', help='Ethereum address')
    
    # Stats command
    subparsers.add_parser('stats', help='Show database statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'add':
        add_whale(args.address, args.label, args.type, args.category)
    elif args.command == 'list':
        list_whales()
    elif args.command == 'import':
        import_from_json(args.file)
    elif args.command == 'export':
        export_to_json(args.file)
    elif args.command == 'remove':
        remove_whale(args.address)
    elif args.command == 'stats':
        get_stats()

if __name__ == "__main__":
    main()