#!/usr/bin/env python3
"""
Whale Discovery Service
Discovers new whale addresses through transaction analysis
"""

import requests
import time
from typing import Dict, List, Set
from config import config
from ..data.whale_repository import whale_repository

class WhaleDiscoveryService:
    """Service for discovering new whale addresses"""
    
    def __init__(self):
        self.etherscan_key = config.ETHERSCAN_API_KEY
        self.whale_threshold = config.WHALE_THRESHOLD
        self.discovered_addresses = set()
        
    def discover_from_recent_transfers(self) -> List[str]:
        """
        Discover whales by monitoring recent large ETH transfers
        Uses Etherscan's free tier transaction list API
        """
        if not self.etherscan_key:
            return []
        
        discovered = set()
        
        try:
            # Get recent transactions from known large addresses (ETH2 deposit contract)
            # This is a workaround - we look at who's interacting with major contracts
            url = "https://api.etherscan.io/api"
            
            # Get transactions TO the ETH2 deposit contract (people staking large amounts)
            params = {
                'module': 'account',
                'action': 'txlist',
                'address': '0x00000000219ab540356cBB839Cbe05303d7705Fa',  # ETH2 deposit
                'page': '1',
                'offset': '100',
                'sort': 'desc',
                'apikey': self.etherscan_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json().get('result', [])
                
                if isinstance(result, list):
                    for tx in result:
                        # Check transaction value
                        value_wei = int(tx.get('value', '0'))
                        value_eth = value_wei / 1e18
                        
                        # If large deposit (>32 ETH), track the sender
                        if value_eth >= 32:  # ETH2 validator deposit size
                            from_addr = tx.get('from', '').lower()
                            if from_addr and from_addr != '0x0000000000000000000000000000000000000000':
                                discovered.add(from_addr)
            
            # Rate limiting
            time.sleep(0.5)
            
            # Also check WETH contract for large wrapping/unwrapping
            params['address'] = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'  # WETH
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json().get('result', [])
                
                if isinstance(result, list):
                    for tx in result:
                        value_wei = int(tx.get('value', '0'))
                        value_eth = value_wei / 1e18
                        
                        # Large WETH operations (>100 ETH)
                        if value_eth >= 100:
                            from_addr = tx.get('from', '').lower()
                            to_addr = tx.get('to', '').lower()
                            
                            if from_addr and from_addr != '0x0000000000000000000000000000000000000000':
                                discovered.add(from_addr)
                            if to_addr and to_addr != '0x0000000000000000000000000000000000000000':
                                discovered.add(to_addr)
            
        except Exception as e:
            print(f"Error discovering from transfers: {e}")
        
        return list(discovered)
    
    def discover_from_large_transactions(self, block_count: int = 100) -> List[str]:
        """
        Discover whales by analyzing recent large transactions
        Returns list of potential whale addresses
        """
        if not self.etherscan_key:
            return []
        
        discovered = set()
        
        try:
            # Get latest block number
            url = "https://api.etherscan.io/api"
            params = {
                'module': 'proxy',
                'action': 'eth_blockNumber',
                'apikey': self.etherscan_key
            }
            
            response = requests.get(url, params=params)
            latest_block = int(response.json()['result'], 16)
            
            # Analyze recent blocks for large transactions
            for block_offset in range(0, block_count, 10):
                block_num = latest_block - block_offset
                
                # Get block transactions
                params = {
                    'module': 'proxy',
                    'action': 'eth_getBlockByNumber',
                    'tag': hex(block_num),
                    'boolean': 'true',
                    'apikey': self.etherscan_key
                }
                
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    block_data = response.json().get('result', {})
                    transactions = block_data.get('transactions', [])
                    
                    for tx in transactions:
                        # Check transaction value
                        value_wei = int(tx.get('value', '0x0'), 16)
                        value_eth = value_wei / 1e18
                        
                        # If large transaction (>100 ETH), track addresses
                        if value_eth > 100:
                            from_addr = tx.get('from', '').lower()
                            to_addr = tx.get('to', '').lower()
                            
                            if from_addr and from_addr != '0x0000000000000000000000000000000000000000':
                                discovered.add(from_addr)
                            if to_addr and to_addr != '0x0000000000000000000000000000000000000000':
                                discovered.add(to_addr)
                
                # Rate limiting
                time.sleep(0.25)
                
        except Exception as e:
            print(f"Error discovering from transactions: {e}")
        
        return list(discovered)
    
    def discover_from_token_holders(self, token_addresses: List[str] = None) -> List[str]:
        """
        Discover whales from top holders of major tokens
        """
        if not self.etherscan_key:
            return []
        
        # Default to major tokens if not specified
        if not token_addresses:
            token_addresses = [
                '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',  # USDC
                '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT
                '0x6B175474E89094C44Da98b954EedeAC495271d0F',  # DAI
                '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
            ]
        
        discovered = set()
        
        for token_addr in token_addresses:
            try:
                # Get token holders
                url = "https://api.etherscan.io/api"
                params = {
                    'module': 'token',
                    'action': 'tokenholderlist',
                    'contractaddress': token_addr,
                    'page': '1',
                    'offset': '100',
                    'apikey': self.etherscan_key
                }
                
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    result = response.json().get('result', [])
                    
                    # Check if result is a list (success) or string (error)
                    if not isinstance(result, list):
                        print(f"   Token holder API returned: {result}")
                        continue
                    
                    holders = result
                    for holder in holders[:50]:  # Top 50 holders
                        address = holder.get('TokenHolderAddress', '').lower()
                        if address and address != '0x0000000000000000000000000000000000000000':
                            discovered.add(address)
                
                # Rate limiting
                time.sleep(0.25)
                
            except Exception as e:
                print(f"Error discovering from token {token_addr}: {e}")
        
        return list(discovered)
    
    def qualify_as_whale(self, address: str) -> Dict:
        """
        Check if address qualifies as a whale based on criteria
        Returns qualification data
        """
        try:
            url = "https://api.etherscan.io/api"
            
            # Check ETH balance
            params = {
                'module': 'account',
                'action': 'balance',
                'address': address,
                'tag': 'latest',
                'apikey': self.etherscan_key
            }
            
            response = requests.get(url, params=params)
            if response.status_code != 200:
                return None
            
            balance_wei = int(response.json()['result'])
            balance_eth = balance_wei / 1e18
            
            # Check if meets threshold
            if balance_eth < self.whale_threshold:
                return None
            
            # Get transaction count for activity check
            params = {
                'module': 'proxy',
                'action': 'eth_getTransactionCount',
                'address': address,
                'tag': 'latest',
                'apikey': self.etherscan_key
            }
            
            response = requests.get(url, params=params)
            tx_count = int(response.json()['result'], 16)
            
            # Qualify as whale if balance > threshold and active
            if balance_eth >= self.whale_threshold and tx_count > 10:
                return {
                    'address': address,
                    'balance_eth': balance_eth,
                    'tx_count': tx_count,
                    'qualified': True,
                    'entity_type': 'Unknown',
                    'category': 'Discovered Whale'
                }
            
        except Exception as e:
            print(f"Error qualifying {address}: {e}")
        
        return None
    
    def discover_and_save_whales(self, max_discoveries: int = 50) -> int:
        """
        Full discovery pipeline: find, qualify, and save new whales
        """
        print(f"🔍 Starting whale discovery (target: {max_discoveries} new whales)")
        
        # Phase 1: Discover from recent transfers (free tier compatible)
        print("📊 Phase 1: Analyzing recent ETH transfers...")
        transfer_candidates = self.discover_from_recent_transfers()
        print(f"   Found {len(transfer_candidates)} addresses from transfers")
        
        # Phase 2: Skip token holders (requires Pro tier)
        # print("📊 Phase 2: Analyzing token holders...")
        # token_candidates = self.discover_from_token_holders()
        token_candidates = []
        
        # Combine and deduplicate
        all_candidates = set(transfer_candidates) | set(token_candidates)
        print(f"📊 Total unique candidates: {len(all_candidates)}")
        
        # Phase 3: Qualify candidates
        print("📊 Phase 3: Qualifying candidates...")
        qualified_count = 0
        
        for i, address in enumerate(all_candidates):
            if qualified_count >= max_discoveries:
                break
            
            print(f"   Checking {i+1}/{len(all_candidates)}: {address[:10]}...")
            
            # Check if already in database
            existing = whale_repository.get_whale_by_address(address)
            if existing:
                print(f"   ⚠️  Already tracked")
                continue
            
            # Qualify as whale
            whale_data = self.qualify_as_whale(address)
            
            if whale_data and whale_data['qualified']:
                # Save to database
                success = whale_repository.save_whale(
                    address=whale_data['address'],
                    label=f"Discovered Whale #{qualified_count + 1}",
                    balance_eth=whale_data['balance_eth'],
                    entity_type=whale_data['entity_type'],
                    category=whale_data['category']
                )
                
                if success:
                    qualified_count += 1
                    print(f"   ✅ Qualified! Balance: {whale_data['balance_eth']:.2f} ETH")
            else:
                print(f"   ❌ Not qualified")
            
            # Rate limiting
            time.sleep(0.3)
        
        print(f"\n✅ Discovery complete: {qualified_count} new whales added")
        return qualified_count

# Global instance
whale_discovery_service = WhaleDiscoveryService() if config.ETHERSCAN_API_KEY else None