#!/usr/bin/env python3
"""
ETHhab Trade Intelligence Engine
Analyzes whale transactions for buy/sell signals and trading patterns
"""

import requests
import time
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
import os
from dotenv import load_dotenv

load_dotenv()

class TradeIntelligence:
    def __init__(self):
        self.etherscan_key = os.getenv('ETHERSCAN_API_KEY')
        
        # Known exchange addresses for identifying buy/sell signals
        self.exchange_addresses = {
            '0xF977814e90dA44bFA03b6295A0616a897441aceC': 'Binance',
            '0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a': 'Bitfinex',
            '0xDFd5293D8e347dFe59E90eFd55b2956a1343963d': 'Kraken',
            '0x742d35Cc6634C0532925a3b8D158d177d87e5F47': 'Robinhood',
            '0x28C6c06298d514Db089934071355E5743bf21d60': 'Coinbase',
            '0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549': 'Coinbase_2',
            '0x503828976D22510aad0201ac7EC88293211D23Da': 'Coinbase_3',
            '0xddfAbCdc4D8FFC6d5beaf154f18B778f892A0740': 'Coinbase_4',
            '0x3cd751e6b0078be393132286c442345e5dc49699': 'Coinbase_5',
            '0xb5d85CBf7cB3EE0D56b3bB207D5Fc4B82f43F511': 'Coinbase_6'
        }
        
        # DeFi protocols (for identifying DeFi activity vs exchange activity)
        self.defi_protocols = {
            '0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9': 'Aave',
            '0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643': 'Compound_cDAI',
            '0x39AA39c021dfbaE8faC545936693aC917d5E7563': 'Compound_cUSDC',
            '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2': 'WETH',
            '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984': 'Uniswap',
            '0x6B175474E89094C44Da98b954EedeAC495271d0F': 'MakerDAO_DAI'
        }
    
    def get_whale_transactions(self, address, days=7, limit=1000):
        """Get recent transactions for detailed analysis"""
        url = "https://api.etherscan.io/api"
        
        # Calculate start block (approximate)
        blocks_per_day = 7200  # ~12 second blocks
        start_block = self.get_latest_block() - (days * blocks_per_day)
        
        params = {
            'module': 'account',
            'action': 'txlist',
            'address': address,
            'startblock': start_block,
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
                print(f"API error: {data.get('message', 'Unknown error')}")
                return []
        except Exception as e:
            print(f"Error fetching transactions: {e}")
            return []
    
    def get_latest_block(self):
        """Get latest block number"""
        url = "https://api.etherscan.io/api"
        params = {
            'module': 'proxy',
            'action': 'eth_blockNumber',
            'apikey': self.etherscan_key
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            return int(data['result'], 16)
        except:
            return 19000000  # Fallback
    
    def analyze_trading_patterns(self, address):
        """Comprehensive trading pattern analysis"""
        transactions = self.get_whale_transactions(address, days=30)
        
        if not transactions:
            return {"error": "No transaction data available"}
        
        # Initialize analysis
        exchange_flows = defaultdict(lambda: {'in': 0, 'out': 0, 'count': 0})
        defi_activity = defaultdict(lambda: {'in': 0, 'out': 0, 'count': 0})
        large_movements = []
        time_patterns = defaultdict(int)
        
        total_volume = 0
        gas_spent = 0
        
        for tx in transactions:
            amount_eth = float(int(tx['value']) / 1e18)
            gas_cost = float(int(tx['gasUsed']) * int(tx['gasPrice']) / 1e18)
            
            total_volume += amount_eth
            gas_spent += gas_cost
            
            # Analyze time patterns
            timestamp = int(tx['timeStamp'])
            hour = datetime.fromtimestamp(timestamp).hour
            time_patterns[hour] += 1
            
            # Check for large movements (>100 ETH)
            if amount_eth > 100:
                large_movements.append({
                    'amount': amount_eth,
                    'timestamp': timestamp,
                    'from': tx['from'],
                    'to': tx['to'],
                    'hash': tx['hash']
                })
            
            # Analyze exchange interactions
            if tx['to'].lower() in [addr.lower() for addr in self.exchange_addresses.keys()]:
                # Whale sending TO exchange (potential sell)
                exchange_name = self.exchange_addresses.get(tx['to'])
                if exchange_name:
                    exchange_flows[exchange_name]['in'] += amount_eth
                    exchange_flows[exchange_name]['count'] += 1
            
            elif tx['from'].lower() in [addr.lower() for addr in self.exchange_addresses.keys()]:
                # Whale receiving FROM exchange (potential buy)
                exchange_name = self.exchange_addresses.get(tx['from'])
                if exchange_name:
                    exchange_flows[exchange_name]['out'] += amount_eth
                    exchange_flows[exchange_name]['count'] += 1
            
            # Analyze DeFi interactions
            for protocol_addr, protocol_name in self.defi_protocols.items():
                if tx['to'].lower() == protocol_addr.lower():
                    defi_activity[protocol_name]['in'] += amount_eth
                    defi_activity[protocol_name]['count'] += 1
                elif tx['from'].lower() == protocol_addr.lower():
                    defi_activity[protocol_name]['out'] += amount_eth
                    defi_activity[protocol_name]['count'] += 1
        
        return {
            'total_volume': total_volume,
            'gas_spent': gas_spent,
            'transaction_count': len(transactions),
            'exchange_flows': dict(exchange_flows),
            'defi_activity': dict(defi_activity),
            'large_movements': large_movements,
            'time_patterns': dict(time_patterns),
            'analysis_period_days': 30
        }
    
    def generate_trading_signals(self, address):
        """Generate buy/sell signals based on whale behavior"""
        patterns = self.analyze_trading_patterns(address)
        
        if 'error' in patterns:
            return patterns
        
        signals = []
        confidence_score = 0
        
        # Analyze exchange flows for buy/sell pressure
        total_to_exchanges = 0
        total_from_exchanges = 0
        
        for exchange, flows in patterns['exchange_flows'].items():
            total_to_exchanges += flows['in']
            total_from_exchanges += flows['out']
        
        # Signal 1: Exchange Flow Analysis
        net_exchange_flow = total_from_exchanges - total_to_exchanges
        if net_exchange_flow > 1000:  # More than 1000 ETH net inflow from exchanges
            signals.append({
                'type': 'BUY_SIGNAL',
                'strength': 'STRONG' if net_exchange_flow > 5000 else 'MODERATE',
                'reason': f'Whale withdrew {net_exchange_flow:.0f} ETH from exchanges (accumulation)',
                'confidence': 85 if net_exchange_flow > 5000 else 65
            })
            confidence_score += 20
        elif net_exchange_flow < -1000:  # More than 1000 ETH net outflow to exchanges
            signals.append({
                'type': 'SELL_SIGNAL',
                'strength': 'STRONG' if net_exchange_flow < -5000 else 'MODERATE',
                'reason': f'Whale deposited {abs(net_exchange_flow):.0f} ETH to exchanges (distribution)',
                'confidence': 85 if net_exchange_flow < -5000 else 65
            })
            confidence_score += 20
        
        # Signal 2: Large Movement Analysis
        recent_large_moves = [m for m in patterns['large_movements'] 
                            if datetime.fromtimestamp(m['timestamp']) > datetime.now() - timedelta(days=7)]
        
        if len(recent_large_moves) >= 3:
            avg_amount = sum(m['amount'] for m in recent_large_moves) / len(recent_large_moves)
            signals.append({
                'type': 'VOLATILITY_SIGNAL',
                'strength': 'HIGH',
                'reason': f'{len(recent_large_moves)} large movements (avg {avg_amount:.0f} ETH) in 7 days',
                'confidence': 70
            })
            confidence_score += 15
        
        # Signal 3: DeFi Activity Analysis
        total_defi_volume = sum(activity['in'] + activity['out'] 
                              for activity in patterns['defi_activity'].values())
        
        if total_defi_volume > patterns['total_volume'] * 0.3:  # >30% DeFi activity
            signals.append({
                'type': 'DEFI_SIGNAL',
                'strength': 'MODERATE',
                'reason': f'High DeFi activity ({total_defi_volume:.0f} ETH, {total_defi_volume/patterns["total_volume"]*100:.1f}% of volume)',
                'confidence': 60
            })
            confidence_score += 10
        
        # Signal 4: Time Pattern Analysis
        if patterns['time_patterns']:
            peak_hours = sorted(patterns['time_patterns'].items(), 
                              key=lambda x: x[1], reverse=True)[:3]
            
            # Check if whale is active during specific market hours
            us_market_hours = [hour for hour, count in peak_hours if 13 <= hour <= 21]  # 9AM-5PM EST in UTC
            if len(us_market_hours) >= 2:
                signals.append({
                    'type': 'TIMING_SIGNAL',
                    'strength': 'MODERATE',
                    'reason': f'Active during US market hours: {us_market_hours}',
                    'confidence': 55
                })
                confidence_score += 5
        
        return {
            'address': address,
            'signals': signals,
            'overall_confidence': min(confidence_score, 100),
            'analysis_timestamp': datetime.now().isoformat(),
            'raw_patterns': patterns
        }
    
    def get_whale_intelligence_summary(self, address):
        """Get comprehensive whale intelligence report"""
        signals = self.generate_trading_signals(address)
        
        if 'error' in signals:
            return signals
        
        patterns = signals['raw_patterns']
        
        # Generate summary insights
        insights = []
        
        # Trading behavior classification
        if patterns['total_volume'] > 100000:
            behavior = "INSTITUTIONAL_TRADER"
        elif patterns['total_volume'] > 10000:
            behavior = "LARGE_TRADER"
        elif len(patterns['exchange_flows']) > 2:
            behavior = "MULTI_EXCHANGE_USER"
        elif patterns['defi_activity']:
            behavior = "DEFI_NATIVE"
        else:
            behavior = "HODLER"
        
        insights.append(f"Behavior Profile: {behavior}")
        insights.append(f"30-day Volume: {patterns['total_volume']:.0f} ETH")
        insights.append(f"Gas Spent: {patterns['gas_spent']:.2f} ETH")
        
        # Risk assessment
        risk_score = 0
        if patterns['total_volume'] > 50000:
            risk_score += 30
        if len(patterns['large_movements']) > 5:
            risk_score += 25
        if len(patterns['exchange_flows']) > 1:
            risk_score += 20
        if patterns['transaction_count'] > 100:
            risk_score += 15
        
        risk_level = "HIGH" if risk_score > 70 else "MEDIUM" if risk_score > 40 else "LOW"
        
        return {
            'address': address,
            'behavior_profile': behavior,
            'risk_level': risk_level,
            'risk_score': min(risk_score, 100),
            'insights': insights,
            'trading_signals': signals['signals'],
            'confidence': signals['overall_confidence'],
            'last_updated': datetime.now().isoformat()
        }

if __name__ == "__main__":
    # Test the intelligence engine
    ti = TradeIntelligence()
    
    test_address = "0xF977814e90dA44bFA03b6295A0616a897441aceC"  # Binance whale
    
    print("🧠 ETHhab Trade Intelligence Test")
    print("=" * 50)
    
    intelligence = ti.get_whale_intelligence_summary(test_address)
    
    print(f"Address: {test_address}")
    print(f"Behavior: {intelligence.get('behavior_profile', 'Unknown')}")
    print(f"Risk Level: {intelligence.get('risk_level', 'Unknown')}")
    print(f"Confidence: {intelligence.get('confidence', 0)}%")
    
    print("\\nTrading Signals:")
    for signal in intelligence.get('trading_signals', []):
        print(f"  {signal['type']}: {signal['reason']} (Confidence: {signal['confidence']}%)")
    
    print("\\nInsights:")
    for insight in intelligence.get('insights', []):
        print(f"  - {insight}")