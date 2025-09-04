#!/usr/bin/env python3
"""
ETHhab Intelligence Aggregator
Combines all intelligence sources: trading patterns, social scraping, and entity identification
"""

from trade_intelligence import TradeIntelligence
from social_intelligence import SocialIntelligence  
from social_scraper import SocialScraper
from targeted_scraper import TargetedScraper
import json
from datetime import datetime
import sqlite3

class IntelligenceAggregator:
    def __init__(self):
        self.trade_intel = TradeIntelligence()
        self.social_intel = SocialIntelligence()
        self.social_scraper = SocialScraper()
        self.targeted_scraper = TargetedScraper()
        
        # Initialize databases
        self.social_intel.populate_known_identities()
        
        self.db_path = "whale_intelligence.db"
        self.init_master_database()
    
    def init_master_database(self):
        """Initialize master intelligence database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS whale_intelligence (
                address TEXT PRIMARY KEY,
                identity_name TEXT,
                identity_type TEXT,
                confidence_score INTEGER,
                risk_score INTEGER,
                behavior_profile TEXT,
                social_influence_score INTEGER,
                trading_signals TEXT,
                entity_data TEXT,
                scraped_data TEXT,
                last_updated TIMESTAMP,
                market_impact_score INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS intelligence_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT,
                alert_type TEXT,
                alert_message TEXT,
                severity TEXT,
                confidence INTEGER,
                triggered_at TIMESTAMP,
                acknowledged BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def generate_master_intelligence(self, address):
        """Generate comprehensive intelligence report for a whale address"""
        print(f"🧠 Generating master intelligence for {address[:10]}...")
        
        intelligence = {
            'address': address,
            'timestamp': datetime.now().isoformat(),
            'data_sources': [],
            'confidence_layers': {},
            'final_assessment': {}
        }
        
        # Layer 1: Known Identity Check
        print("  🏷️ Layer 1: Known identity verification...")
        known_identity = self.social_intel.get_entity_intelligence(address)
        intelligence['known_identity'] = known_identity
        intelligence['data_sources'].append('known_database')
        
        if known_identity.get('identified'):
            intelligence['confidence_layers']['identity'] = {
                'score': known_identity['confidence'],
                'source': 'curated_database',
                'data': known_identity
            }
        
        # Layer 2: Trading Pattern Analysis
        print("  📊 Layer 2: Trading pattern analysis...")
        try:
            trade_signals = self.trade_intel.generate_trading_signals(address)
            intelligence['trading_analysis'] = trade_signals
            intelligence['data_sources'].append('blockchain_analysis')
            
            if 'signals' in trade_signals:
                confidence = trade_signals.get('overall_confidence', 0)
                intelligence['confidence_layers']['trading'] = {
                    'score': confidence,
                    'source': 'transaction_analysis',
                    'signals': trade_signals['signals']
                }
        except Exception as e:
            print(f"    ⚠️ Trading analysis error: {e}")
            intelligence['trading_analysis'] = {'error': str(e)}
        
        # Layer 3: Social Media Scraping
        print("  🔍 Layer 3: Social media intelligence...")
        try:
            scraped_mentions = self.social_scraper.comprehensive_address_search(address)
            scraping_report = self.social_scraper.generate_intelligence_report(address)
            
            intelligence['social_scraping'] = {
                'mentions': scraped_mentions,
                'report': scraping_report
            }
            intelligence['data_sources'].append('social_scraping')
            
            if scraped_mentions:
                avg_confidence = sum(m['confidence'] for m in scraped_mentions) / len(scraped_mentions)
                intelligence['confidence_layers']['social'] = {
                    'score': avg_confidence,
                    'source': 'social_media_scraping',
                    'mention_count': len(scraped_mentions)
                }
        except Exception as e:
            print(f"    ⚠️ Social scraping error: {e}")
            intelligence['social_scraping'] = {'error': str(e)}
        
        # Layer 4: Behavioral Profiling
        print("  🎯 Layer 4: Behavioral profiling...")
        try:
            behavioral_profile = self.targeted_scraper.comprehensive_whale_profile(address)
            intelligence['behavioral_profile'] = behavioral_profile
            intelligence['data_sources'].append('behavioral_analysis')
            
            if behavioral_profile['confidence_score'] > 0:
                intelligence['confidence_layers']['behavioral'] = {
                    'score': behavioral_profile['confidence_score'],
                    'source': 'behavioral_analysis',
                    'identity_clues': behavioral_profile['identity_clues']
                }
        except Exception as e:
            print(f"    ⚠️ Behavioral analysis error: {e}")
            intelligence['behavioral_profile'] = {'error': str(e)}
        
        # Generate Final Assessment
        intelligence['final_assessment'] = self.synthesize_intelligence(intelligence)
        
        # Store in database
        self.store_intelligence(intelligence)
        
        return intelligence
    
    def synthesize_intelligence(self, intelligence):
        """Synthesize all intelligence layers into final assessment"""
        assessment = {
            'identity_confidence': 0,
            'risk_level': 'unknown',
            'market_impact': 0,
            'key_findings': [],
            'recommended_actions': [],
            'overall_score': 0
        }
        
        confidence_scores = []
        
        # Aggregate confidence scores
        for layer, data in intelligence['confidence_layers'].items():
            confidence_scores.append(data['score'])
            
            if data['score'] > 70:
                assessment['key_findings'].append(f"High confidence {layer} identification ({data['score']}%)")
        
        # Calculate overall confidence
        if confidence_scores:
            assessment['identity_confidence'] = sum(confidence_scores) / len(confidence_scores)
        
        # Determine identity
        if intelligence['known_identity'].get('identified'):
            identity = intelligence['known_identity']
            assessment['key_findings'].append(f"Known entity: {identity['name']} ({identity['type']})")
            assessment['identity_confidence'] = max(assessment['identity_confidence'], 90)
        
        # Risk assessment
        risk_factors = []
        
        # Trading risk
        if 'trading_analysis' in intelligence and 'signals' in intelligence['trading_analysis']:
            for signal in intelligence['trading_analysis']['signals']:
                if signal['type'] in ['SELL_SIGNAL', 'VOLATILITY_SIGNAL']:
                    risk_factors.append(f"Trading signal: {signal['reason']}")
        
        # Social influence risk
        if 'social_scraping' in intelligence:
            report = intelligence['social_scraping'].get('report', {})
            if report.get('social_footprint_score', 0) > 50:
                risk_factors.append("High social media presence")
        
        # Behavioral risk
        if 'behavioral_profile' in intelligence:
            profile = intelligence['behavioral_profile']
            if profile.get('risk_assessment', {}).get('overall_risk') == 'high':
                risk_factors.append("High behavioral risk profile")
        
        # Calculate risk level
        if len(risk_factors) > 2:
            assessment['risk_level'] = 'high'
        elif len(risk_factors) > 0:
            assessment['risk_level'] = 'medium'
        else:
            assessment['risk_level'] = 'low'
        
        # Market impact assessment
        balance = 0
        if 'trading_analysis' in intelligence:
            patterns = intelligence['trading_analysis'].get('raw_patterns', {})
            balance = patterns.get('total_volume', 0)
        
        # Calculate market impact based on balance and social influence
        impact_score = 0
        if balance > 100000:
            impact_score += 40
        elif balance > 10000:
            impact_score += 20
        
        if assessment['identity_confidence'] > 80:
            impact_score += 30
        
        if len(risk_factors) > 1:
            impact_score += 20
        
        assessment['market_impact'] = min(impact_score, 100)
        
        # Generate recommendations
        if assessment['identity_confidence'] < 50:
            assessment['recommended_actions'].append("Increase monitoring - identity unclear")
        
        if assessment['risk_level'] == 'high':
            assessment['recommended_actions'].append("High priority monitoring - multiple risk factors")
        
        if assessment['market_impact'] > 70:
            assessment['recommended_actions'].append("Track closely - high market impact potential")
        
        # Overall score (weighted average)
        weights = {
            'identity_confidence': 0.4,
            'market_impact': 0.3,
            'risk_level_numeric': 0.3
        }
        
        risk_numeric = {'low': 20, 'medium': 60, 'high': 100}[assessment['risk_level']]
        
        assessment['overall_score'] = int(
            assessment['identity_confidence'] * weights['identity_confidence'] +
            assessment['market_impact'] * weights['market_impact'] +
            risk_numeric * weights['risk_level_numeric']
        )
        
        return assessment
    
    def store_intelligence(self, intelligence):
        """Store intelligence in master database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        assessment = intelligence['final_assessment']
        
        cursor.execute('''
            INSERT OR REPLACE INTO whale_intelligence 
            (address, identity_name, identity_type, confidence_score, risk_score,
             behavior_profile, social_influence_score, trading_signals, 
             entity_data, scraped_data, last_updated, market_impact_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            intelligence['address'],
            intelligence['known_identity'].get('name', 'Unknown'),
            intelligence['known_identity'].get('type', 'Unknown'),
            int(assessment['identity_confidence']),
            100 if assessment['risk_level'] == 'high' else 60 if assessment['risk_level'] == 'medium' else 20,
            json.dumps(intelligence.get('behavioral_profile', {})),
            intelligence.get('social_scraping', {}).get('report', {}).get('social_footprint_score', 0),
            json.dumps(intelligence.get('trading_analysis', {})),
            json.dumps(intelligence['known_identity']),
            json.dumps(intelligence.get('social_scraping', {})),
            datetime.now(),
            assessment['market_impact']
        ))
        
        conn.commit()
        conn.close()
    
    def generate_alert_if_needed(self, intelligence):
        """Generate alerts for high-priority intelligence findings"""
        assessment = intelligence['final_assessment']
        alerts = []
        
        if assessment['risk_level'] == 'high' and assessment['market_impact'] > 80:
            alerts.append({
                'type': 'HIGH_RISK_WHALE',
                'message': f"High-risk whale detected with {assessment['market_impact']}% market impact potential",
                'severity': 'HIGH',
                'confidence': assessment['identity_confidence']
            })
        
        if assessment['identity_confidence'] > 90 and intelligence['known_identity'].get('type') == 'exchange':
            alerts.append({
                'type': 'EXCHANGE_ACTIVITY',
                'message': f"Major exchange wallet activity: {intelligence['known_identity']['name']}",
                'severity': 'MEDIUM',
                'confidence': 95
            })
        
        # Store alerts
        if alerts:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for alert in alerts:
                cursor.execute('''
                    INSERT INTO intelligence_alerts 
                    (address, alert_type, alert_message, severity, confidence, triggered_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    intelligence['address'],
                    alert['type'],
                    alert['message'],
                    alert['severity'],
                    alert['confidence'],
                    datetime.now()
                ))
            
            conn.commit()
            conn.close()
        
        return alerts

def main():
    """Test intelligence aggregator"""
    print("🧠 ETHhab Master Intelligence Test")
    print("=" * 60)
    
    aggregator = IntelligenceAggregator()
    
    # Test with known whale address
    test_address = "0xF977814e90dA44bFA03b6295A0616a897441aceC"  # Binance
    
    print(f"\\n🕵️ Generating master intelligence for: {test_address}")
    
    intelligence = aggregator.generate_master_intelligence(test_address)
    
    print(f"\\n📊 MASTER INTELLIGENCE REPORT")
    print("=" * 60)
    
    assessment = intelligence['final_assessment']
    
    print(f"Address: {intelligence['address']}")
    print(f"Overall Score: {assessment['overall_score']}/100")
    print(f"Identity Confidence: {assessment['identity_confidence']:.1f}%")
    print(f"Risk Level: {assessment['risk_level'].upper()}")
    print(f"Market Impact: {assessment['market_impact']}/100")
    
    print(f"\\n🔍 Key Findings:")
    for finding in assessment['key_findings']:
        print(f"  • {finding}")
    
    print(f"\\n💡 Recommended Actions:")
    for action in assessment['recommended_actions']:
        print(f"  • {action}")
    
    print(f"\\n📊 Data Sources: {', '.join(intelligence['data_sources'])}")
    
    # Generate alerts
    alerts = aggregator.generate_alert_if_needed(intelligence)
    if alerts:
        print(f"\\n🚨 ALERTS GENERATED:")
        for alert in alerts:
            print(f"  {alert['severity']}: {alert['message']}")

if __name__ == "__main__":
    main()