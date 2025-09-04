#!/usr/bin/env python3
"""
Enhanced ETHhab Whale Scanner with Trade Intelligence
Combines whale tracking with advanced analytics and social intelligence
"""

from minimal_whale_scanner import MinimalWhaleScanner
from trade_intelligence import TradeIntelligence
from social_intelligence import SocialIntelligence
import time

class EnhancedWhaleScanner(MinimalWhaleScanner):
    def __init__(self):
        super().__init__()
        self.trade_intel = TradeIntelligence()
        self.social_intel = SocialIntelligence()
        
        # Populate social intelligence database
        self.social_intel.populate_known_identities()
    
    def analyze_whale_with_intelligence(self, address):
        """Enhanced whale analysis with trade and social intelligence"""
        print(f"\\n🧠 Deep Analysis: {address[:10]}...")
        
        # Basic whale data
        balance = self.get_eth_balance(address)
        transactions = self.get_recent_transactions(address, 10)
        
        if balance < 1000:
            return {"error": "Below whale threshold"}
        
        # Trade intelligence
        print("  📊 Analyzing trading patterns...")
        trade_signals = self.trade_intel.generate_trading_signals(address)
        
        # Social intelligence
        print("  🕵️ Gathering social intelligence...")
        social_report = self.social_intel.generate_social_report(address)
        
        # Combine all intelligence
        enhanced_data = {
            'address': address,
            'balance': balance,
            'recent_transactions': len(transactions),
            'trade_intelligence': trade_signals,
            'social_intelligence': social_report,
            'analysis_timestamp': time.time()
        }
        
        # Generate summary insights
        insights = []
        
        # Trading insights
        if 'signals' in trade_signals:
            for signal in trade_signals['signals']:
                insights.append({
                    'type': 'trading',
                    'level': signal['strength'],
                    'message': signal['reason'],
                    'confidence': signal['confidence']
                })
        
        # Social insights
        if social_report['entity_intelligence'].get('identified'):
            insights.append({
                'type': 'identity',
                'level': 'HIGH',
                'message': f"Identified as {social_report['entity_intelligence']['name']}",
                'confidence': social_report['entity_intelligence']['confidence']
            })
        
        if social_report['social_presence']['social_influence_score'] > 70:
            insights.append({
                'type': 'social',
                'level': 'HIGH', 
                'message': f"High social influence ({social_report['social_presence']['social_influence_score']}/100)",
                'confidence': 85
            })
        
        enhanced_data['insights'] = insights
        enhanced_data['overall_risk_score'] = self.calculate_risk_score(enhanced_data)
        
        return enhanced_data
    
    def calculate_risk_score(self, whale_data):
        """Calculate overall risk score for whale"""
        risk_score = 0
        
        # Balance risk (higher balance = higher impact risk)
        balance = whale_data['balance']
        if balance > 1000000:
            risk_score += 40
        elif balance > 100000:
            risk_score += 30
        elif balance > 10000:
            risk_score += 20
        else:
            risk_score += 10
        
        # Trading signal risk
        if 'trade_intelligence' in whale_data and 'signals' in whale_data['trade_intelligence']:
            signals = whale_data['trade_intelligence']['signals']
            
            for signal in signals:
                if signal['type'] in ['SELL_SIGNAL', 'VOLATILITY_SIGNAL']:
                    risk_score += 15
                elif signal['type'] == 'BUY_SIGNAL':
                    risk_score += 5  # Buy signals are less risky for market
        
        # Social influence risk
        social_score = whale_data['social_intelligence']['social_presence']['social_influence_score']
        if social_score > 80:
            risk_score += 20  # High influence = high market impact risk
        elif social_score > 50:
            risk_score += 10
        
        # Identity risk
        if not whale_data['social_intelligence']['entity_intelligence'].get('identified'):
            risk_score += 15  # Unknown entities are riskier
        
        return min(risk_score, 100)
    
    def scan_whales_with_intelligence(self):
        """Scan whales with full intelligence analysis"""
        print("🧠 ETHhab Enhanced Intelligence Scan")
        print("=" * 60)
        
        enhanced_whales = []
        
        for address in self.whale_addresses[:3]:  # Limit to 3 for demo
            try:
                enhanced_data = self.analyze_whale_with_intelligence(address)
                if 'error' not in enhanced_data:
                    enhanced_whales.append(enhanced_data)
                time.sleep(1)  # Rate limiting
            except Exception as e:
                print(f"Error analyzing {address}: {e}")
        
        # Sort by risk score
        enhanced_whales.sort(key=lambda x: x['overall_risk_score'], reverse=True)
        
        print("\\n" + "=" * 60)
        print("🎯 INTELLIGENCE SUMMARY")
        print("=" * 60)
        
        for i, whale in enumerate(enhanced_whales, 1):
            print(f"\\n#{i} Risk Score: {whale['overall_risk_score']}/100")
            print(f"Address: {whale['address'][:10]}...")
            print(f"Balance: {whale['balance']:,.0f} ETH")
            
            # Show key insights
            print("Key Insights:")
            for insight in whale['insights'][:3]:  # Top 3 insights
                print(f"  🔍 {insight['message']} (Confidence: {insight['confidence']}%)")
            
            # Show identity if known
            identity = whale['social_intelligence']['entity_intelligence']
            if identity.get('identified'):
                print(f"  🏷️ Identity: {identity['name']} ({identity['type']})")
                if identity.get('twitter'):
                    followers = whale['social_intelligence']['social_presence']['estimated_followers']
                    print(f"  🐦 Twitter: {identity['twitter']} ({followers:,} followers)")
        
        return enhanced_whales

if __name__ == "__main__":
    enhanced_scanner = EnhancedWhaleScanner()
    enhanced_scanner.scan_whales_with_intelligence()