#!/usr/bin/env python3
"""
Whale Service
Business service for whale scanning and management
"""

import requests
import time
from typing import Dict, List, Optional
from config import config

class WhaleService:
    """Enhanced whale scanner with modular architecture"""
    
    def __init__(self):
        self.etherscan_key = config.ETHERSCAN_API_KEY
        from ..data.whale_repository import whale_repository
        self.whale_repo = whale_repository
    
    @property
    def whale_addresses(self) -> List[str]:
        """Get list of all whale addresses from database"""
        if not self.whale_repo:
            return []
        
        try:
            # Get all whales from database
            whales = self.whale_repo.get_top_whales(limit=1000)  # Get all whales
            return [whale['address'] for whale in whales]
        except Exception as e:
            print(f"Error getting whale addresses from database: {e}")
            return []
    
    def _get_whale_metadata(self, address: str) -> Dict:
        """Get whale metadata from database"""
        if not self.whale_repo:
            return {}
        
        try:
            whale = self.whale_repo.get_whale_by_address(address)
            if whale:
                return {
                    'name': whale.get('label', ''),
                    'ens': self._extract_ens_from_label(whale.get('label', '')),
                    'description': self._generate_description(whale),
                    'entity_type': whale.get('entity_type', 'Unknown'),
                    'category': whale.get('category', 'Unknown')
                }
        except Exception as e:
            print(f"Error getting whale metadata for {address}: {e}")
        
        return {}
    
    def _extract_ens_from_label(self, label: str) -> str:
        """Extract ENS name if label contains .eth"""
        if '.eth' in label.lower():
            return label.lower()
        return ''
    
    def _generate_description(self, whale_data: Dict) -> str:
        """Generate description based on whale category and entity type"""
        entity_type = whale_data.get('entity_type', '')
        category = whale_data.get('category', '')
        
        if entity_type == 'Centralized Exchange':
            return f"CEX {category.replace('CEX ', '')}"
        elif entity_type == 'DeFi Protocol':
            return f"DeFi {category}"
        elif entity_type == 'Individual Whale':
            if category == 'Founder':
                return "Ethereum Co-Founder"
            elif category == 'Trader':
                return "DeFi Trader"
            else:
                return "Individual Whale"
        elif entity_type == 'Foundation':
            return f"{category} Fund"
        else:
            return whale_data.get('label', 'Unknown Wallet')
    
    def get_balance(self, address: str) -> Optional[Dict]:
        """Get ETH balance for an address"""
        if not self.etherscan_key:
            return None
            
        try:
            url = "https://api.etherscan.io/api"
            params = {
                'module': 'account',
                'action': 'balance',
                'address': address,
                'tag': 'latest',
                'apikey': self.etherscan_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == '1':
                    balance_wei = int(data['result'])
                    balance_eth = balance_wei / 1e18
                    
                    return {
                        'address': address,
                        'balance': str(balance_eth),
                        'balance_wei': str(balance_wei),
                        'block': 'latest'
                    }
            
            return None
            
        except Exception as e:
            print(f"Error getting balance for {address}: {e}")
            return None
    
    def _get_display_info(self, address: str, whale_info: Dict) -> tuple:
        """Get smart display name and description from database metadata"""
        # Get metadata from database
        metadata = self._get_whale_metadata(address)
        
        # Priority 1: ENS name
        if metadata.get('ens'):
            return metadata['ens'], metadata.get('description', '')
        
        # Priority 2: Known institutional/protocol name  
        if metadata.get('name') and not metadata['name'].startswith('Whale'):
            return metadata['name'], metadata.get('description', '')
        
        # Priority 3: Truncated address for unknown whales
        return f"0x{address[2:11]}...", "Unknown Whale"
    
    def get_whale_info(self, address: str) -> Dict:
        """Get comprehensive whale information with smart naming"""
        # Get metadata from database
        metadata = self._get_whale_metadata(address)
        balance_info = self.get_balance(address)
        
        # Get smart display name and description
        display_name, description = self._get_display_info(address, {})
        
        result = {
            'address': address,
            'name': metadata.get('name', f'Whale {address[:8]}'),  # Legacy field
            'display_name': display_name,
            'description': description,
            'ens': metadata.get('ens', ''),
            'entity_type': metadata.get('entity_type', 'Unknown'),
            'category': metadata.get('category', 'Unknown'),
            'balance_eth': 0,
            'balance_usd': 0,
            'last_updated': None
        }
        
        if balance_info:
            balance_eth = float(balance_info['balance'])
            result.update({
                'balance_eth': balance_eth,
                'balance_usd': balance_eth * 2000,  # Approximate ETH price
                'last_updated': time.time()
            })
        
        return result
    
    def get_whale_info_cached(self, address: str, cached_balance_eth: float = 0, 
                             cached_balance_usd: float = 0, last_updated: str = None) -> Dict:
        """Get whale information using cached database data only (NO API CALLS)"""
        # Get metadata from database
        metadata = self._get_whale_metadata(address)
        
        # Get smart display name and description
        display_name, description = self._get_display_info(address, {})
        
        result = {
            'address': address,
            'name': metadata.get('name', f'Whale {address[:8]}'),  # Legacy field
            'display_name': display_name,
            'description': description,
            'ens': metadata.get('ens', ''),
            'entity_type': metadata.get('entity_type', 'Unknown'),
            'category': metadata.get('category', 'Unknown'),
            'balance_eth': float(cached_balance_eth or 0),
            'balance_usd': float(cached_balance_usd or 0),
            'last_updated': last_updated
        }
        
        return result
    
    def scan_all_whales(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        """Scan all whale addresses and return their information"""
        addresses = self.whale_addresses[offset:]
        if limit:
            addresses = addresses[:limit]
        
        whales = []
        
        for i, address in enumerate(addresses):
            print(f"Scanning whale {offset+i+1}/{len(self.whale_addresses)}: {address[:10]}...")
            
            whale_info = self.get_whale_info(address)
            whales.append(whale_info)
            
            # Rate limiting
            if i < len(addresses) - 1:
                time.sleep(0.3)
        
        return whales
    
    def get_whale_by_category(self, category: str) -> List[Dict]:
        """Get whales filtered by category from database"""
        if not self.whale_repo:
            return []
        
        try:
            # Get all whales and filter by category
            all_whales = self.whale_repo.get_top_whales(limit=1000)
            filtered_addresses = [
                whale['address'] for whale in all_whales
                if whale.get('category') == category
            ]
            
            whales = []
            for address in filtered_addresses:
                whale_info = self.get_whale_info(address)
                whales.append(whale_info)
            
            return whales
            
        except Exception as e:
            print(f"Error getting whales by category {category}: {e}")
            return []
    
    def is_whale_address(self, address: str) -> bool:
        """Check if address is a known whale in database"""
        if not self.whale_repo:
            return False
        
        try:
            whale = self.whale_repo.get_whale_by_address(address)
            return whale is not None
        except Exception as e:
            print(f"Error checking if {address} is whale: {e}")
            return False

if __name__ == "__main__":
    # Test the whale scanner
    scanner = WhaleScanner()
    print(f"Found {len(scanner.whale_addresses)} whale addresses")
    
    # Test scanning first few whales
    whales = scanner.scan_all_whales(limit=3)
    for whale in whales:
        print(f"{whale['name']}: {whale['balance_eth']:.2f} ETH")