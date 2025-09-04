#!/usr/bin/env python3
"""
ETHhab Social Intelligence Engine
Links wallet addresses to social media accounts and real-world entities
"""

import requests
import json
import re
from datetime import datetime
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

class SocialIntelligence:
    def __init__(self):
        self.db_path = "whale_social.db"
        self.init_database()
        
        # Known whale identities (manually curated database)
        self.known_identities = {
            '0x00000000219ab540356cBB839Cbe05303d7705Fa': {
                'name': 'Ethereum 2.0 Beacon Chain Deposit Contract',
                'type': 'contract',
                'description': 'Official Ethereum staking contract',
                'twitter': '@ethereum',
                'verified': True,
                'category': 'protocol'
            },
            '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2': {
                'name': 'Wrapped Ether (WETH)',
                'type': 'contract', 
                'description': 'Canonical WETH contract',
                'twitter': None,
                'verified': True,
                'category': 'defi'
            },
            '0xF977814e90dA44bFA03b6295A0616a897441aceC': {
                'name': 'Binance 8',
                'type': 'exchange',
                'description': 'Binance hot wallet',
                'twitter': '@binance',
                'verified': True,
                'category': 'exchange'
            },
            '0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a': {
                'name': 'Bitfinex',
                'type': 'exchange',
                'description': 'Bitfinex exchange wallet',
                'twitter': '@bitfinex', 
                'verified': True,
                'category': 'exchange'
            },
            '0xDFd5293D8e347dFe59E90eFd55b2956a1343963d': {
                'name': 'Kraken 3',
                'type': 'exchange',
                'description': 'Kraken exchange wallet',
                'twitter': '@krakenfx',
                'verified': True,
                'category': 'exchange'
            },
            '0x742d35Cc6634C0532925a3b8D158d177d87e5F47': {
                'name': 'Robinhood 2',
                'type': 'exchange',
                'description': 'Robinhood crypto wallet',
                'twitter': '@RobinhoodApp',
                'verified': True,
                'category': 'exchange'
            }
        }
    
    def init_database(self):
        """Initialize SQLite database for social intelligence"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS whale_identities (
                address TEXT PRIMARY KEY,
                name TEXT,
                type TEXT,
                description TEXT,
                twitter_handle TEXT,
                twitter_followers INTEGER,
                verified BOOLEAN,
                category TEXT,
                confidence_score INTEGER,
                last_updated TIMESTAMP,
                data_source TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT,
                platform TEXT,
                username TEXT,
                mention_text TEXT,
                mention_url TEXT,
                timestamp TIMESTAMP,
                sentiment REAL,
                engagement_score INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entity_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT,
                entity_name TEXT,
                entity_type TEXT,
                link_type TEXT,
                confidence REAL,
                evidence TEXT,
                verified BOOLEAN,
                created_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_known_identity(self, address, identity_data):
        """Add or update a known whale identity"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO whale_identities 
            (address, name, type, description, twitter_handle, verified, category, 
             confidence_score, last_updated, data_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            address,
            identity_data['name'],
            identity_data['type'],
            identity_data['description'],
            identity_data.get('twitter'),
            identity_data['verified'],
            identity_data['category'],
            100,  # Known identities have 100% confidence
            datetime.now(),
            'manual_curation'
        ))
        
        conn.commit()
        conn.close()
    
    def populate_known_identities(self):
        """Populate database with known whale identities"""
        for address, identity in self.known_identities.items():
            self.add_known_identity(address, identity)
        print(f"✅ Populated {len(self.known_identities)} known whale identities")
    
    def search_twitter_mentions(self, address, search_terms=None):
        """Search for Twitter mentions of a wallet address"""
        # Note: This would require Twitter API access
        # For now, we'll simulate the functionality
        
        mentions = []
        
        # Simulate finding mentions
        if address in self.known_identities:
            identity = self.known_identities[address]
            if identity.get('twitter'):
                mentions.append({
                    'platform': 'twitter',
                    'username': identity['twitter'],
                    'mention_text': f"Official account for {identity['name']}",
                    'verified': True,
                    'followers': self.estimate_followers(identity['twitter']),
                    'confidence': 100
                })
        
        return mentions
    
    def estimate_followers(self, twitter_handle):
        """Estimate follower count for major accounts"""
        follower_estimates = {
            '@ethereum': 3500000,
            '@binance': 9000000,
            '@bitfinex': 750000,
            '@krakenfx': 850000,
            '@RobinhoodApp': 500000
        }
        return follower_estimates.get(twitter_handle, 10000)
    
    def analyze_address_patterns(self, address):
        """Analyze address for patterns that might indicate entity type"""
        patterns = {
            'exchange_indicators': [],
            'defi_indicators': [],
            'whale_indicators': [],
            'contract_indicators': []
        }
        
        # Check if address is in known lists
        if address in self.known_identities:
            identity = self.known_identities[address]
            patterns[f"{identity['category']}_indicators"].append(f"Known {identity['type']}: {identity['name']}")
        
        # Pattern analysis based on address characteristics
        if address.endswith('0000') or address.endswith('1111'):
            patterns['contract_indicators'].append('Vanity address pattern (likely contract)')
        
        # Check against common exchange patterns
        exchange_patterns = [
            '0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE',  # Binance pattern
            '0x28C6c06298d514Db089934071355E5743bf21d60'   # Coinbase pattern
        ]
        
        for pattern in exchange_patterns:
            if address[:10] == pattern[:10]:  # Similar prefix
                patterns['exchange_indicators'].append('Address pattern similar to known exchange')
        
        return patterns
    
    def get_entity_intelligence(self, address):
        """Get comprehensive entity intelligence for an address"""
        # Check database first
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM whale_identities WHERE address = ?
        ''', (address,))
        
        db_result = cursor.fetchone()
        conn.close()
        
        if db_result:
            return {
                'address': address,
                'identified': True,
                'name': db_result[1],
                'type': db_result[2],
                'description': db_result[3],
                'twitter': db_result[4],
                'verified': bool(db_result[6]),
                'category': db_result[7],
                'confidence': db_result[8],
                'source': 'database'
            }
        
        # If not in database, analyze patterns
        patterns = self.analyze_address_patterns(address)
        mentions = self.search_twitter_mentions(address)
        
        # Generate intelligence based on available data
        intelligence = {
            'address': address,
            'identified': False,
            'patterns': patterns,
            'social_mentions': mentions,
            'confidence': 0,
            'source': 'analysis'
        }
        
        # Try to classify based on patterns
        if patterns['exchange_indicators']:
            intelligence.update({
                'type': 'exchange',
                'category': 'exchange',
                'confidence': 60,
                'description': 'Likely exchange wallet based on patterns'
            })
        elif patterns['contract_indicators']:
            intelligence.update({
                'type': 'contract',
                'category': 'protocol',
                'confidence': 70,
                'description': 'Likely smart contract based on patterns'
            })
        elif mentions:
            intelligence.update({
                'type': 'identified',
                'confidence': 80,
                'description': 'Identity found through social mentions'
            })
        
        return intelligence
    
    def generate_social_report(self, address):
        """Generate comprehensive social intelligence report"""
        entity_intel = self.get_entity_intelligence(address)
        
        report = {
            'address': address,
            'entity_intelligence': entity_intel,
            'social_presence': {
                'twitter_identified': bool(entity_intel.get('twitter')),
                'verified_account': entity_intel.get('verified', False),
                'estimated_followers': 0,
                'social_influence_score': 0
            },
            'risk_assessment': {
                'identity_risk': 'LOW',
                'regulatory_risk': 'LOW', 
                'reputation_risk': 'LOW'
            },
            'recommendations': []
        }
        
        # Calculate social influence score
        if entity_intel.get('twitter'):
            followers = self.estimate_followers(entity_intel['twitter'])
            report['social_presence']['estimated_followers'] = followers
            
            if followers > 1000000:
                report['social_presence']['social_influence_score'] = 90
            elif followers > 100000:
                report['social_presence']['social_influence_score'] = 70
            elif followers > 10000:
                report['social_presence']['social_influence_score'] = 50
            else:
                report['social_presence']['social_influence_score'] = 20
        
        # Risk assessment
        if entity_intel.get('category') == 'exchange':
            report['risk_assessment']['regulatory_risk'] = 'MEDIUM'
            report['recommendations'].append('Monitor for regulatory compliance issues')
        
        if entity_intel.get('verified'):
            report['risk_assessment']['identity_risk'] = 'LOW'
        elif entity_intel.get('confidence', 0) < 50:
            report['risk_assessment']['identity_risk'] = 'HIGH'
            report['recommendations'].append('Identity verification needed')
        
        # Generate actionable recommendations
        if not entity_intel.get('identified'):
            report['recommendations'].append('Investigate wallet through transaction analysis')
            report['recommendations'].append('Search for social media mentions manually')
        
        if entity_intel.get('category') == 'exchange' and entity_intel.get('twitter'):
            report['recommendations'].append('Monitor exchange Twitter for market sentiment')
        
        report['generated_at'] = datetime.now().isoformat()
        
        return report

def main():
    """Test the social intelligence system"""
    print("🕵️ ETHhab Social Intelligence Test")
    print("=" * 50)
    
    si = SocialIntelligence()
    
    # Populate known identities
    si.populate_known_identities()
    
    # Test with known whale
    test_address = "0xF977814e90dA44bFA03b6295A0616a897441aceC"
    
    print(f"\\n🔍 Analyzing: {test_address}")
    
    report = si.generate_social_report(test_address)
    
    print(f"\\n📊 Social Intelligence Report:")
    print(f"Identified: {report['entity_intelligence'].get('identified', False)}")
    
    if report['entity_intelligence'].get('name'):
        print(f"Name: {report['entity_intelligence']['name']}")
        print(f"Type: {report['entity_intelligence']['type']}")
        print(f"Description: {report['entity_intelligence']['description']}")
    
    if report['entity_intelligence'].get('twitter'):
        print(f"Twitter: {report['entity_intelligence']['twitter']}")
        print(f"Estimated Followers: {report['social_presence']['estimated_followers']:,}")
        print(f"Social Influence Score: {report['social_presence']['social_influence_score']}/100")
    
    print(f"\\n⚠️ Risk Assessment:")
    for risk_type, level in report['risk_assessment'].items():
        print(f"  {risk_type}: {level}")
    
    print(f"\\n💡 Recommendations:")
    for rec in report['recommendations']:
        print(f"  - {rec}")

if __name__ == "__main__":
    main()