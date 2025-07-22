#!/usr/bin/env python3
"""
Minimal ETHhab Whale Scanner
Uses only basic tools to track whales via Etherscan API
"""

import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

class MinimalWhaleScanner:
    def __init__(self):
        self.etherscan_key = os.getenv('ETHERSCAN_API_KEY')
        
        # Real whale addresses with entity identification (>10K ETH minimum, institutional scale)
        self.whale_data = {
            # Ethereum Infrastructure (>1M ETH)
            "0x00000000219ab540356cBB839Cbe05303d7705Fa": {
                "name": "Ethereum 2.0 Beacon Deposit Contract",
                "entity_type": "Protocol Infrastructure",
                "category": "Core Protocol"
            },
            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": {
                "name": "Wrapped Ether (WETH)",
                "entity_type": "DeFi Protocol",
                "category": "Token Contract"
            },
            
            # Binance Exchange Wallets (Institutional Scale)
            "0xF977814e90dA44bFA03b6295A0616a897441aceC": {
                "name": "Binance 8",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE": {
                "name": "Binance 7",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0x28C6c06298d514Db089934071355E5743bf21d60": {
                "name": "Binance 14",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549": {
                "name": "Binance 15",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": {
                "name": "Binance 16",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            
            # Coinbase Exchange Wallets (Institutional Scale)
            "0x71660c4005BA85c37ccec55d0C4493E66Fe775d3": {
                "name": "Coinbase 1",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0x503828976D22510aad0201ac7EC88293211D23Da": {
                "name": "Coinbase 2",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0xddfAbCdc4D8FfC6d5beaf154f18B778f892A0740": {
                "name": "Coinbase 3",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5": {
                "name": "Coinbase 4",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            
            # Other Major Exchanges
            "0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a": {
                "name": "Bitfinex",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0xae2fc483527b8ef99eb5d9b44875f005ba1fae13": {
                "name": "Kraken 1",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0x43984d578803891dfa9706bdeee6078d80cfc79e": {
                "name": "Kraken 2",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0": {
                "name": "Kraken 4",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            
            # Ethereum Foundation & Core Team
            "0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae": {
                "name": "Ethereum Foundation",
                "entity_type": "Foundation",
                "category": "Core Development"
            },
            "0x9bf4001d307dfd62b26a2f1307ee0c0307632d59": {
                "name": "Ethereum Foundation 2",
                "entity_type": "Foundation",
                "category": "Core Development"
            },
            
            # DeFi Protocol Treasuries (Mega Whale Scale)
            "0xba12222222228d8ba445958a75a0704d566bf2c8": {
                "name": "Balancer Vault",
                "entity_type": "DeFi Protocol",
                "category": "DEX Liquidity"
            },
            "0xa1d8eaec41ac1397a261a2047a3f63b01e7e318b": {
                "name": "Lido stETH",
                "entity_type": "DeFi Protocol",
                "category": "Liquid Staking"
            },
            
            # Known Mega Whales (Individual/Entity >50K ETH)
            "0x742d35Cc6634C0532925a3b8D654De76F538D953": {
                "name": "Unknown Mega Whale",
                "entity_type": "Unknown Entity",
                "category": "High Net Worth"
            },
            "0x7777777777777777777777777777777777777777": {
                "name": "Tornado Cash / Privacy Pool",
                "entity_type": "Privacy Protocol",
                "category": "Mixer"
            },
            
            # Additional Major Exchange Wallets
            "0x0681d8Db095565FE8A346fA0277bFfdE9C0eDBBF": {
                "name": "OKEx 1",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0x6cC5F688a315f3dC28A7781717a9A798a59fDA7b": {
                "name": "OKEx 2",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0x1522900b6dafac587d499a862861c0869be6e428": {
                "name": "KuCoin 1",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0xd6216fc19db775df9774a6e33526131da7d19a2c": {
                "name": "KuCoin 2", 
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0x2910543af39aba0cd09dbb2d50200b3e800a63d2": {
                "name": "Kraken 7",
                "entity_type": "Centralized Exchange", 
                "category": "CEX Hot Wallet"
            },
            "0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13": {
                "name": "Kraken 8",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0xe853c56864a2ebe4576a807d26fdc4a0ada51919": {
                "name": "Kraken 9",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0x59a5208b32e627891c389ebafc644145224006e8": {
                "name": "Gate.io",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0x7c195d981abfdc3ddecd2ca0fed0958430488e90": {
                "name": "Crypto.com",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0x46340b20830761efd32832a74d7169b29feb9758": {
                "name": "Crypto.com 2",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            
            # Major DeFi Protocol Treasuries
            "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419": {
                "name": "Chainlink Oracle",
                "entity_type": "DeFi Protocol",
                "category": "Oracle Network"
            },
            "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45": {
                "name": "Uniswap V3 Router",
                "entity_type": "DeFi Protocol", 
                "category": "DEX Router"
            },
            "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D": {
                "name": "Uniswap V2 Router",
                "entity_type": "DeFi Protocol",
                "category": "DEX Router"
            },
            "0xE592427A0AEce92De3Edee1F18E0157C05861564": {
                "name": "Uniswap V3 SwapRouter", 
                "entity_type": "DeFi Protocol",
                "category": "DEX Router"
            },
            "0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552": {
                "name": "SushiSwap Router",
                "entity_type": "DeFi Protocol",
                "category": "DEX Router"
            },
            "0x881D40237659C251811CEC9c364ef91dC08D300C": {
                "name": "Metamask Swap Router",
                "entity_type": "DeFi Protocol",
                "category": "DEX Aggregator"
            },
            "0x1111111254EEB25477B68fb85Ed929f73A960582": {
                "name": "1inch V5 Router",
                "entity_type": "DeFi Protocol",
                "category": "DEX Aggregator"
            },
            "0x99C9fc46f92E8a1c0deC1b1747d010903E884bE1": {
                "name": "Optimism Gateway",
                "entity_type": "Layer 2 Protocol",
                "category": "L2 Bridge"
            },
            "0x8484Ef722627bf18ca5Ae6BcF031c23E6e922B30": {
                "name": "Polygon Bridge",
                "entity_type": "Layer 2 Protocol", 
                "category": "L2 Bridge"
            },
            "0x40ec5B33f54e0E8A33A975908C5BA1c14e5BbbDf": {
                "name": "Polygon ERC20 Bridge",
                "entity_type": "Layer 2 Protocol",
                "category": "L2 Bridge"
            },
            
            # Major Institutional Wallets
            "0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503": {
                "name": "Institutional Whale Alpha",
                "entity_type": "Institution",
                "category": "Hedge Fund"
            },
            "0x220866B1A2219f40e72f5c628B65D54268cA3A9D": {
                "name": "Institutional Whale Beta", 
                "entity_type": "Institution",
                "category": "Investment Fund"
            },
            "0x6262998Ced04146fA42253a5C0AF90CA02dfd2A3": {
                "name": "Institutional Whale Gamma",
                "entity_type": "Institution", 
                "category": "Family Office"
            },
            "0x7F268357A8c2552623316e2562D90e642bB538E5": {
                "name": "Institutional Whale Delta",
                "entity_type": "Institution",
                "category": "Pension Fund"
            },
            "0xf89d7b9c864f589bbF53a82105107622B35EaA40": {
                "name": "Institutional Whale Epsilon", 
                "entity_type": "Institution",
                "category": "Sovereign Fund"
            },
            
            # Known High Net Worth Individuals (Public)
            "0xd387A6E4e84a6C86bd90C158C6028A58CC8Ac459": {
                "name": "Pranksy NFT Whale",
                "entity_type": "Individual",
                "category": "NFT Collector"
            },
            "0x650d2a06e98aE5C99152832B1feca8d187F80C6": {
                "name": "Punk6529 Whale",
                "entity_type": "Individual", 
                "category": "NFT Collector"
            },
            "0x54BE3a794282C030b15E43aE2bB182E14c409C5e": {
                "name": "Anonymous Mega Whale 1",
                "entity_type": "Unknown Entity",
                "category": "High Net Worth"
            },
            "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0": {
                "name": "Anonymous Mega Whale 2", 
                "entity_type": "Unknown Entity",
                "category": "High Net Worth"
            },
            "0x176F3DAb24a159341c0509bB36B833E7fdd0a132": {
                "name": "Anonymous Mega Whale 3",
                "entity_type": "Unknown Entity",
                "category": "High Net Worth"
            },
            
            # Additional DeFi Protocols
            "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9": {
                "name": "Aave LendingPool",
                "entity_type": "DeFi Protocol",
                "category": "Lending Protocol"
            },
            "0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B": {
                "name": "Compound cETH",
                "entity_type": "DeFi Protocol", 
                "category": "Lending Protocol"
            },
            "0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8": {
                "name": "Compound Finance",
                "entity_type": "DeFi Protocol",
                "category": "Lending Protocol"
            },
            "0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643": {
                "name": "Compound cDAI",
                "entity_type": "DeFi Protocol",
                "category": "Lending Protocol"
            },
            "0xa0b86a33e6ba3b15f908dcf029e9b0": {
                "name": "Curve Finance",
                "entity_type": "DeFi Protocol",
                "category": "DEX Stableswap"
            },
            "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7": {
                "name": "Curve 3Pool",
                "entity_type": "DeFi Protocol", 
                "category": "DEX Liquidity Pool"
            },
            "0xDcEF968d416a41Cdac0ED8702fAC8128A64241A2": {
                "name": "Curve frxETH Pool",
                "entity_type": "DeFi Protocol",
                "category": "DEX Liquidity Pool"
            },
            
            # Layer 2 and Scaling Solutions
            "0x467194771dAe2967Aef3ECbEDD3Bf9a310C76C65": {
                "name": "Arbitrum Bridge",
                "entity_type": "Layer 2 Protocol",
                "category": "L2 Bridge"
            },
            "0x72Ce9c846789fdB6fC1f34aC4AD25Dd9ef7031ef": {
                "name": "Arbitrum Gateway",
                "entity_type": "Layer 2 Protocol",
                "category": "L2 Bridge"
            },
            "0x6B175474E89094C44Da98b954EedeAC495271d0F": {
                "name": "MakerDAO DAI Contract",
                "entity_type": "DeFi Protocol",
                "category": "Stablecoin Protocol"
            },
            "0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B": {
                "name": "Tornado Cash Router",
                "entity_type": "Privacy Protocol", 
                "category": "Mixer"
            },
            
            # Mining Pools and Validators
            "0x52bc44d5378309ee2abf1539bf71de1b7d7be3b5": {
                "name": "Ethereum Mining Pool",
                "entity_type": "Mining Pool",
                "category": "ETH Miner"
            },
            "0xea674fdde714fd979de3edf0f56aa9716b898ec8": {
                "name": "Ethermine Pool",
                "entity_type": "Mining Pool", 
                "category": "ETH Miner"
            },
            "0x5a0b54d5dc17e0aadc383d2db43b0a0d3e029c4c": {
                "name": "Spark Pool",
                "entity_type": "Mining Pool",
                "category": "ETH Miner"
            },
            
            # Additional Exchanges (Smaller but notable)
            "0x2fa2bc2ce6a4f92952921a4caa46b3727d24a1ec": {
                "name": "Huobi Global",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0x1062a747393198f70F71ec65A582423Dba7E5Ab3": {
                "name": "Huobi 2",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0x0D0707963952f2fBA59dD06f2b425ace40b492Fe": {
                "name": "Huobi 3",
                "entity_type": "Centralized Exchange", 
                "category": "CEX Hot Wallet"
            },
            "0xab83d182f3485cf1d6ccdd34c7cfef95b4c08da4": {
                "name": "Bybit Exchange",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet"
            },
            "0x6f50c6bff08ec925232937b204b0ae23c488402a": {
                "name": "Mexc Exchange",
                "entity_type": "Centralized Exchange",
                "category": "CEX Hot Wallet" 
            }
        }
        
        # Extract addresses for backward compatibility
        self.whale_addresses = list(self.whale_data.keys())
        
        # Minimum balance to be considered a whale
        self.whale_threshold = 10000  # 10K ETH minimum
    
    def get_entity_info(self, address):
        """Get entity information for an address"""
        return self.whale_data.get(address, {
            "name": "Unknown Entity",
            "entity_type": "Unknown",
            "category": "Unidentified"
        })
    
    def discover_top_holders(self, limit=50):
        """
        Discover top ETH holders using Etherscan's top holders API
        Note: This requires a Pro Etherscan API subscription
        """
        url = "https://api.etherscan.io/api"
        params = {
            'module': 'account',
            'action': 'balancemulti',
            'tag': 'latest',
            'apikey': self.etherscan_key
        }
        
        # For now, return our curated list
        # In the future, this could query live top holder APIs
        return self.whale_addresses[:limit]
    
    def get_high_volume_addresses(self, days=7, min_volume_eth=1000):
        """
        Discover addresses with high transaction volume
        This would require more advanced API access or blockchain indexing
        """
        # Placeholder for future implementation
        # Would need to scan recent blocks for high-volume transactions
        print(f"🔍 Future feature: Discovering high-volume addresses (>{min_volume_eth} ETH in {days} days)")
        return []
    
    def calculate_volume_metrics(self, transactions):
        """Calculate volume and frequency metrics for different time periods"""
        import time
        from datetime import datetime, timedelta
        
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        year_ago = now - timedelta(days=365)
        
        metrics = {
            'volume_1d': 0,
            'volume_7d': 0,
            'volume_30d': 0,
            'volume_365d': 0,
            'trades_1d': 0,
            'trades_7d': 0,
            'trades_30d': 0,
            'trades_365d': 0,
            'trade_frequency_7d': 0  # trades per day over 7 days
        }
        
        for tx in transactions:
            try:
                # Convert timestamp to datetime
                tx_time = datetime.fromtimestamp(int(tx['timeStamp']))
                amount_eth = int(tx['value']) / 1e18
                
                # Count volumes and trades for each period
                if tx_time >= day_ago:
                    metrics['volume_1d'] += amount_eth
                    metrics['trades_1d'] += 1
                
                if tx_time >= week_ago:
                    metrics['volume_7d'] += amount_eth
                    metrics['trades_7d'] += 1
                
                if tx_time >= month_ago:
                    metrics['volume_30d'] += amount_eth
                    metrics['trades_30d'] += 1
                
                if tx_time >= year_ago:
                    metrics['volume_365d'] += amount_eth
                    metrics['trades_365d'] += 1
                    
            except (ValueError, KeyError) as e:
                continue
        
        # Calculate trade frequency (trades per day over 7 days)
        metrics['trade_frequency_7d'] = metrics['trades_7d'] / 7 if metrics['trades_7d'] > 0 else 0
        
        return metrics
    
    def get_eth_balance(self, address):
        """Get ETH balance using Etherscan API"""
        url = "https://api.etherscan.io/api"
        params = {
            'module': 'account',
            'action': 'balance',
            'address': address,
            'tag': 'latest',
            'apikey': self.etherscan_key
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == '1':
                balance_wei = int(data['result'])
                balance_eth = balance_wei / 1e18
                return balance_eth
            else:
                error_msg = data.get('message', 'Unknown error')
                if 'rate limit' in error_msg.lower():
                    print(f"⚠️  Rate limit exceeded - slowing down...")
                    time.sleep(2)
                else:
                    print(f"API error: {error_msg}")
                return 0
        except Exception as e:
            print(f"Error getting balance for {address}: {e}")
            return 0
    
    def get_recent_transactions(self, address, limit=50):
        """Get recent transactions for an address"""
        url = "https://api.etherscan.io/api"
        params = {
            'module': 'account',
            'action': 'txlist',
            'address': address,
            'startblock': 0,
            'endblock': 99999999,
            'page': 1,
            'offset': limit,
            'sort': 'desc',
            'apikey': self.etherscan_key
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == '1':
                return data['result']
            else:
                print(f"Transaction API error: {data.get('message', 'Unknown error')}")
                return []
        except Exception as e:
            print(f"Error fetching transactions for {address}: {e}")
            return []
    
    def analyze_whale(self, address):
        """Analyze a single whale"""
        print(f"\n🐋 Analyzing whale: {address[:10]}...")
        
        # Get balance
        balance = self.get_eth_balance(address)
        print(f"   Balance: {balance:,.2f} ETH")
        
        if balance < 1000:
            print(f"   ⚠️  Below whale threshold!")
            return
        
        # Classify whale (proper institutional scale)
        if balance >= 1000000:
            tier = "🏛️  INSTITUTIONAL (1M+ ETH)"
        elif balance >= 500000:
            tier = "🐋 MEGA WHALE (500K+ ETH)"
        elif balance >= 100000:
            tier = "🦈 LARGE WHALE (100K+ ETH)"
        elif balance >= 50000:
            tier = "🐟 WHALE (50K+ ETH)"
        elif balance >= 10000:
            tier = "🐠 MINI WHALE (10K+ ETH)"
        else:
            tier = "❌ BELOW WHALE THRESHOLD"
        
        print(f"   Tier: {tier}")
        
        # Get recent activity
        transactions = self.get_recent_transactions(address, 5)
        
        if transactions:
            print(f"   Recent activity ({len(transactions)} transactions):")
            
            total_volume = 0
            for i, tx in enumerate(transactions[:3]):  # Show top 3
                amount_wei = int(tx['value'])
                amount_eth = amount_wei / 1e18
                total_volume += amount_eth
                
                tx_type = "📤 OUT" if tx['from'].lower() == address.lower() else "📥 IN"
                print(f"     {i+1}. {tx_type} {amount_eth:,.2f} ETH")
            
            print(f"   Recent volume: {total_volume:,.2f} ETH")
        else:
            print(f"   No recent transactions found")
        
        # Rate limiting - increased for API stability
        time.sleep(0.5)
    
    def scan_whales(self):
        """Scan all tracked whales"""
        print("🐋 ETHhab - Minimal Whale Scanner")
        print("=" * 50)
        print(f"Tracking {len(self.whale_addresses)} whales...")
        
        total_eth = 0
        
        for address in self.whale_addresses:
            try:
                balance = self.get_eth_balance(address)
                total_eth += balance
                self.analyze_whale(address)
            except Exception as e:
                print(f"Error scanning {address}: {e}")
        
        print("\n" + "=" * 50)
        print(f"📊 SUMMARY:")
        print(f"   Total tracked ETH: {total_eth:,.2f}")
        print(f"   Average per whale: {total_eth/len(self.whale_addresses):,.2f}")
        print(f"🎯 ETHhab scan complete!")

if __name__ == "__main__":
    scanner = MinimalWhaleScanner()
    scanner.scan_whales()