import requests
import time
from web3 import Web3
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from database import DatabaseManager

load_dotenv()

class WhaleScanner:
    def __init__(self):
        self.alchemy_key = os.getenv('ALCHEMY_API_KEY')
        self.etherscan_key = os.getenv('ETHERSCAN_API_KEY')
        self.whale_threshold = float(os.getenv('WHALE_THRESHOLD', 1000))
        
        # Setup Web3 connection
        alchemy_url = f"https://eth-mainnet.g.alchemy.com/v2/{self.alchemy_key}"
        self.w3 = Web3(Web3.HTTPProvider(alchemy_url))
        
        self.db = DatabaseManager()
        
        # Known whale addresses to start with (top ETH holders)
        self.known_whales = [
            "0x00000000219ab540356cBB839Cbe05303d7705Fa",  # Beacon Deposit Contract
            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # Wrapped ETH
            "0xF977814e90dA44bFA03b6295A0616a897441aceC",  # Binance 8
            "0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a",  # Bitfinex 
            "0xDFd5293D8e347dFe59E90eFd55b2956a1343963d",  # Kraken 3
            "0xDA9dfA130Df4dE4673b89022EE50ff26f6EA73Cf",  # Kraken 4
            "0x742d35Cc6634C0532925a3b8D158d177d87e5F47",  # Robinhood 2
        ]
    
    def get_eth_balance(self, address):
        """Get ETH balance for an address"""
        try:
            balance_wei = self.w3.eth.get_balance(address)
            balance_eth = self.w3.from_wei(balance_wei, 'ether')
            return float(balance_eth)
        except Exception as e:
            print(f"Error getting balance for {address}: {e}")
            return 0
    
    def get_recent_transactions(self, address, limit=100):
        """Get recent transactions for an address using Etherscan API"""
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
                print(f"Etherscan API error: {data.get('message', 'Unknown error')}")
                return []
        except Exception as e:
            print(f"Error fetching transactions for {address}: {e}")
            return []
    
    def analyze_transaction_patterns(self, address, transactions):
        """Analyze transaction patterns for whale behavior"""
        if not transactions:
            return {}
        
        # Calculate metrics
        total_volume = 0
        inflows = 0
        outflows = 0
        large_transactions = []
        
        for tx in transactions:
            amount_eth = float(self.w3.from_wei(int(tx['value']), 'ether'))
            total_volume += amount_eth
            
            if tx['to'].lower() == address.lower():
                inflows += amount_eth
            else:
                outflows += amount_eth
            
            # Flag large transactions (>100 ETH)
            if amount_eth > 100:
                large_transactions.append({
                    'hash': tx['hash'],
                    'amount': amount_eth,
                    'timestamp': datetime.fromtimestamp(int(tx['timeStamp']))
                })
        
        return {
            'total_volume': total_volume,
            'inflows': inflows,
            'outflows': outflows,
            'net_flow': inflows - outflows,
            'large_transactions': large_transactions,
            'transaction_count': len(transactions)
        }
    
    def scan_whale(self, address):
        """Scan a single whale address for updates"""
        print(f"Scanning whale: {address}")
        
        # Get current balance
        balance = self.get_eth_balance(address)
        
        if balance < self.whale_threshold:
            print(f"Address {address} below whale threshold ({balance:.2f} ETH)")
            return
        
        # Add or update whale in database
        whale = self.db.add_whale(address, balance)
        self.db.update_whale_balance(address, balance)
        
        # Get recent transactions
        transactions = self.get_recent_transactions(address, 50)
        
        # Analyze patterns
        patterns = self.analyze_transaction_patterns(address, transactions)
        
        # Check for alerts
        self.check_alerts(address, balance, patterns)
        
        # Store recent transactions
        for tx in transactions[:10]:  # Store last 10 transactions
            try:
                amount_eth = float(self.w3.from_wei(int(tx['value']), 'ether'))
                
                # Determine transaction type
                if tx['to'].lower() == address.lower():
                    tx_type = "inflow"
                elif tx['from'].lower() == address.lower():
                    tx_type = "outflow"
                else:
                    tx_type = "internal"
                
                tx_data = {
                    'hash': tx['hash'],
                    'whale_address': address,
                    'from_address': tx['from'],
                    'to_address': tx['to'],
                    'amount': amount_eth,
                    'gas_price': float(tx['gasPrice']) / 1e9,  # Convert to Gwei
                    'gas_used': int(tx['gasUsed']),
                    'block_number': int(tx['blockNumber']),
                    'timestamp': datetime.fromtimestamp(int(tx['timeStamp'])),
                    'transaction_type': tx_type
                }
                
                self.db.add_transaction(tx_data)
            except Exception as e:
                print(f"Error processing transaction {tx['hash']}: {e}")
        
        time.sleep(0.2)  # Rate limiting
    
    def check_alerts(self, address, balance, patterns):
        """Check for alert conditions"""
        
        # Large transaction alert (>1000 ETH)
        for large_tx in patterns['large_transactions']:
            if large_tx['amount'] > 1000:
                message = f"Large transaction: {large_tx['amount']:.2f} ETH"
                self.db.add_alert(address, "large_transaction", message, large_tx['amount'])
        
        # Accumulation alert (net positive flow >500 ETH)
        if patterns['net_flow'] > 500:
            message = f"Accumulation detected: +{patterns['net_flow']:.2f} ETH net flow"
            self.db.add_alert(address, "accumulation", message, patterns['net_flow'])
        
        # Distribution alert (net negative flow >500 ETH)
        if patterns['net_flow'] < -500:
            message = f"Distribution detected: {patterns['net_flow']:.2f} ETH net flow"
            self.db.add_alert(address, "distribution", message, abs(patterns['net_flow']))
    
    def discover_new_whales(self):
        """Discover new whale addresses from recent large transactions"""
        print("Discovering new whales...")
        
        # Get latest block
        latest_block = self.w3.eth.block_number
        
        # Check last 100 blocks for large transactions
        for block_num in range(latest_block - 100, latest_block):
            try:
                block = self.w3.eth.get_block(block_num, full_transactions=True)
                
                for tx in block.transactions:
                    if tx.value > 0:
                        amount_eth = float(self.w3.from_wei(tx.value, 'ether'))
                        
                        # Check for large transactions (>500 ETH)
                        if amount_eth > 500:
                            # Check if sender/receiver are whales
                            for address in [tx['from'], tx['to']]:
                                if address:
                                    balance = self.get_eth_balance(address)
                                    if balance >= self.whale_threshold:
                                        print(f"Found potential whale: {address} ({balance:.2f} ETH)")
                                        self.db.add_whale(address, balance)
                            
                            time.sleep(0.1)  # Rate limiting
                            
            except Exception as e:
                print(f"Error checking block {block_num}: {e}")
                continue
    
    def run_scan(self):
        """Run a full scan of all known whales"""
        print("Starting whale scan...")
        
        # Scan known whales
        for address in self.known_whales:
            try:
                self.scan_whale(address)
            except Exception as e:
                print(f"Error scanning {address}: {e}")
        
        # Scan database whales
        db_whales = self.db.get_top_whales(50)
        for whale in db_whales:
            try:
                self.scan_whale(whale.address)
            except Exception as e:
                print(f"Error scanning {whale.address}: {e}")
        
        # Discover new whales
        try:
            self.discover_new_whales()
        except Exception as e:
            print(f"Error discovering new whales: {e}")
        
        print("Whale scan completed!")

if __name__ == "__main__":
    scanner = WhaleScanner()
    scanner.run_scan()