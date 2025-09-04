#!/usr/bin/env python3
"""
ETHhab Intelligence Web App
Complete whale tracking with trade intelligence and social analysis
"""

import json
import time
import os
from datetime import datetime, timedelta
from minimal_whale_scanner import MinimalWhaleScanner
from intelligence_aggregator import IntelligenceAggregator
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
import webbrowser
import threading
import sqlite3

class ETHhabIntelligenceHandler(SimpleHTTPRequestHandler):
    # Class-level cache for full whale list
    whale_cache = {}
    cache_timestamp = None
    cache_duration = timedelta(minutes=5)  # Cache for 5 minutes
    
    # Individual whale data cache (persistent for 1 hour per whale)
    individual_whale_cache = {}
    whale_cache_duration = timedelta(hours=1)  # Cache individual whales for 1 hour
    
    def __init__(self, *args, **kwargs):
        self.aggregator = IntelligenceAggregator()
        self.load_whale_cache()
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.get_html().encode())
        
        elif self.path == '/api/whales':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Check cache first
            now = datetime.now()
            if (self.cache_timestamp and 
                now - self.cache_timestamp < self.cache_duration and
                self.whale_cache):
                print("🚀 Serving cached whale data...")
                self.wfile.write(json.dumps(self.whale_cache).encode())
                return
            
            # Get whale data using smart caching
            scanner = MinimalWhaleScanner()
            whale_data = []
            
            print(f"🔍 Scanning {len(scanner.whale_addresses)} whale addresses with smart caching...")
            
            # Smart scanning with cache - no batching needed for cached data
            cached_count = 0
            fresh_count = 0
            
            for i, address in enumerate(scanner.whale_addresses):
                print(f"📊 Processing whale {i+1}/{len(scanner.whale_addresses)}: {address[:10]}...")
                
                # Use our smart caching system
                whale_info = self.get_whale_scan_data(address, scanner)
                
                if whale_info:
                    whale_data.append(whale_info)
                    
                    # Track cache usage
                    if address in self.individual_whale_cache:
                        cached_data = self.individual_whale_cache[address]
                        if datetime.now() - cached_data['cached_at'] < self.whale_cache_duration:
                            cached_count += 1
                        else:
                            fresh_count += 1
                    else:
                        fresh_count += 1
                
                # Pause between fresh API calls to respect rate limits
                # (cached calls don't need delays)
                if whale_info and address not in self.individual_whale_cache:
                    time.sleep(0.3)
            
            print(f"📈 Scan complete: {cached_count} cached, {fresh_count} fresh API calls")
            
            # Cache the results
            self.whale_cache = whale_data
            self.cache_timestamp = now
            print(f"💾 Cached {len(whale_data)} whales for {self.cache_duration.total_seconds()/60} minutes")
            
            self.wfile.write(json.dumps(whale_data).encode())
        
        elif self.path.startswith('/api/intelligence/'):
            # Extract address from URL
            address = self.path.split('/')[-1]
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Generate full intelligence report
            print(f"🧠 Generating intelligence for {address[:10]}...")
            try:
                intelligence = self.aggregator.generate_master_intelligence(address)
                self.wfile.write(json.dumps(intelligence, default=str).encode())
            except Exception as e:
                error_response = {'error': str(e), 'address': address}
                self.wfile.write(json.dumps(error_response).encode())
        
        elif self.path.startswith('/api/memecoins/'):
            # Extract address from URL
            address = self.path.split('/')[-1]
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Get memecoin transactions for this whale
            print(f"🐸 Analyzing memecoin activity for {address[:10]}...")
            try:
                memecoins = self.get_whale_memecoins(address)
                self.wfile.write(json.dumps(memecoins, default=str).encode())
            except Exception as e:
                error_response = {'error': str(e), 'address': address}
                self.wfile.write(json.dumps(error_response).encode())
        
        elif self.path == '/api/feed':
            # Whale activity feed endpoint
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Generate intelligent whale feed
            print("📰 Generating whale activity feed...")
            try:
                feed = self.generate_whale_feed()
                self.wfile.write(json.dumps(feed, default=str).encode())
            except Exception as e:
                error_response = {'error': str(e), 'feed': []}
                self.wfile.write(json.dumps(error_response).encode())

        elif self.path == '/api/reload':
            # Hot-reload endpoint
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Clear cache to force fresh data
            self.whale_cache = {}
            self.cache_timestamp = None
            print("🔄 Cache cleared for hot-reload")
            
            # Cache statistics
            total_cached = len(self.individual_whale_cache)
            expired_count = 0
            for address, data in self.individual_whale_cache.items():
                if datetime.now() - data['cached_at'] >= self.whale_cache_duration:
                    expired_count += 1
            
            response = {
                'status': 'reloaded', 
                'timestamp': str(datetime.now()),
                'cache_stats': {
                    'total_whales_cached': total_cached,
                    'expired_entries': expired_count,
                    'fresh_entries': total_cached - expired_count
                }
            }
            self.wfile.write(json.dumps(response).encode())
        
        else:
            super().do_GET()
    
    def get_whale_intelligence(self, address):
        """Get existing intelligence from database"""
        try:
            conn = sqlite3.connect('whale_intelligence.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT identity_name, identity_type, confidence_score, risk_score, 
                       market_impact_score, last_updated 
                FROM whale_intelligence WHERE address = ?
            ''', (address,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'identity_name': result[0],
                    'identity_type': result[1],
                    'confidence_score': result[2],
                    'risk_score': result[3],
                    'market_impact_score': result[4],
                    'last_updated': result[5],
                    'has_intelligence': True
                }
            else:
                return {'has_intelligence': False}
        except Exception as e:
            print(f"Error getting intelligence: {e}")
            return {'has_intelligence': False}
    
    def get_whale_memecoins(self, address):
        """Get memecoin transactions for a whale"""
        try:
            scanner = MinimalWhaleScanner()
            transactions = scanner.get_recent_transactions(address, 100)
            
            # Known memecoin contract addresses (simplified list)
            memecoin_contracts = {
                '0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce': {'name': 'SHIB', 'symbol': 'SHIB'},
                '0xa0b86a33e6ba3b15f908dcj029e9b0': {'name': 'PEPE', 'symbol': 'PEPE'},
                '0x4d224452801aced8b2f0aebe155379bb5d594381': {'name': 'DOGE', 'symbol': 'DOGE'},
                '0x6b175474e89094c44da98b954eedeac495271d0f': {'name': 'FLOKI', 'symbol': 'FLOKI'},
                # Add more memecoin addresses as needed
            }
            
            memecoin_activity = []
            
            for tx in transactions:
                to_address = tx.get('to', '').lower()
                if to_address in memecoin_contracts:
                    memecoin = memecoin_contracts[to_address]
                    amount_eth = int(tx['value']) / 1e18
                    
                    if amount_eth > 0.1:  # Only significant transactions
                        memecoin_activity.append({
                            'token_name': memecoin['name'],
                            'token_symbol': memecoin['symbol'],
                            'contract_address': to_address,
                            'amount_eth': round(amount_eth, 4),
                            'hash': tx['hash'],
                            'timestamp': tx['timeStamp'],
                            'block_number': tx['blockNumber']
                        })
            
            # Sort by timestamp (most recent first)
            memecoin_activity.sort(key=lambda x: int(x['timestamp']), reverse=True)
            
            return {
                'address': address,
                'total_memecoin_transactions': len(memecoin_activity),
                'recent_activity': memecoin_activity[:10],  # Last 10 transactions
                'analysis_timestamp': str(datetime.now())
            }
            
        except Exception as e:
            print(f"Error analyzing memecoins for {address}: {e}")
            return {
                'address': address,
                'error': str(e),
                'total_memecoin_transactions': 0,
                'recent_activity': []
            }
    
    def get_cached_whale_data(self, address):
        """Get cached whale data if still valid"""
        if address in self.individual_whale_cache:
            cached_data = self.individual_whale_cache[address]
            cache_time = cached_data.get('cached_at')
            if cache_time and datetime.now() - cache_time < self.whale_cache_duration:
                print(f"   💾 Using cached data for {address[:10]}... (age: {datetime.now() - cache_time})")
                return cached_data['data']
        return None
    
    def cache_whale_data(self, address, whale_data):
        """Cache whale data with timestamp"""
        self.individual_whale_cache[address] = {
            'data': whale_data,
            'cached_at': datetime.now()
        }
        print(f"   💾 Cached whale data for {address[:10]}... (expires in 1 hour)")
        
        # Auto-save cache to disk every 10 new entries
        if len(self.individual_whale_cache) % 10 == 0:
            self.save_whale_cache()
    
    def get_whale_scan_data(self, address, scanner):
        """Get whale data from cache or API with smart rate limiting"""
        try:
            # Check cache first
            cached_data = self.get_cached_whale_data(address)
            if cached_data:
                return cached_data
            
            # Get fresh data from API
            print(f"   📡 Fetching fresh data for {address[:10]}...")
            
            entity_info = scanner.get_entity_info(address)
            balance = scanner.get_eth_balance(address)
            
            # Skip if below whale threshold to save API calls
            if balance < 10000:
                print(f"   ❌ Skipping {address[:10]}... - Below whale threshold ({balance:,.0f} ETH)")
                return None
            
            transactions = scanner.get_recent_transactions(address, 50)
            intelligence = self.get_whale_intelligence(address)
            volume_metrics = scanner.calculate_volume_metrics(transactions)
            volume = sum(int(tx['value'])/1e18 for tx in transactions[:5])
            
            # Proper whale classification
            if balance >= 1000000:
                tier = "Institutional (1M+ ETH)"
                emoji = "🏛️"
            elif balance >= 500000:
                tier = "Mega Whale (500K+ ETH)"
                emoji = "🐋"
            elif balance >= 100000:
                tier = "Large Whale (100K+ ETH)"
                emoji = "🦈"
            elif balance >= 50000:
                tier = "Whale (50K+ ETH)"
                emoji = "🐟"
            elif balance >= 10000:
                tier = "Mini Whale (10K+ ETH)"
                emoji = "🐠"
            else:
                return None  # Below threshold
            
            whale_data = {
                'address': address,
                'balance': round(balance, 2),
                'tier': tier,
                'emoji': emoji,
                'tier_text': tier,
                
                # Entity information
                'entity_name': entity_info['name'],
                'entity_type': entity_info['entity_type'],
                'category': entity_info['category'],
                
                # Multi-period volumes
                'volume_1d': round(volume_metrics['volume_1d'], 2),
                'volume_7d': round(volume_metrics['volume_7d'], 2),
                'volume_30d': round(volume_metrics['volume_30d'], 2),
                'volume_365d': round(volume_metrics['volume_365d'], 2),
                
                # Trade frequency
                'trades_1d': volume_metrics['trades_1d'],
                'trades_7d': volume_metrics['trades_7d'],
                'trades_30d': volume_metrics['trades_30d'],
                'trades_365d': volume_metrics['trades_365d'],
                'trade_frequency': round(volume_metrics['trade_frequency_7d'], 2),
                
                # Legacy fields
                'volume': round(volume, 2),
                'transactions': len(transactions),
                'intelligence': intelligence
            }
            
            # Cache the data
            self.cache_whale_data(address, whale_data)
            
            # Rate limiting only for fresh API calls
            time.sleep(0.25)
            
            return whale_data
            
        except Exception as e:
            print(f"   ❌ Error scanning {address[:10]}...: {e}")
            return None
    
    def load_whale_cache(self):
        """Load whale cache from disk"""
        try:
            cache_file = 'whale_cache.json'
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                    
                # Convert timestamps back to datetime objects
                for address, data in cache_data.items():
                    if 'cached_at' in data:
                        data['cached_at'] = datetime.fromisoformat(data['cached_at'])
                
                self.individual_whale_cache = cache_data
                print(f"📂 Loaded {len(cache_data)} whales from cache file")
            else:
                print("📂 No existing cache file found")
        except Exception as e:
            print(f"⚠️  Error loading cache: {e}")
    
    def save_whale_cache(self):
        """Save whale cache to disk"""
        try:
            cache_file = 'whale_cache.json'
            
            # Convert datetime objects to strings for JSON serialization
            cache_data = {}
            for address, data in self.individual_whale_cache.items():
                cache_data[address] = data.copy()
                if 'cached_at' in cache_data[address]:
                    cache_data[address]['cached_at'] = data['cached_at'].isoformat()
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            print(f"💾 Saved {len(cache_data)} whales to cache file")
        except Exception as e:
            print(f"⚠️  Error saving cache: {e}")
    
    def generate_whale_feed(self):
        """Generate intelligent whale activity feed"""
        try:
            scanner = MinimalWhaleScanner()
            feed_items = []
            
            # Sample more whales for better feed coverage
            sample_whales = scanner.whale_addresses[:25]  # Top 25 for more activity
            
            for address in sample_whales:
                try:
                    entity_info = scanner.get_entity_info(address)
                    whale_name = entity_info['name']
                    whale_type = entity_info['entity_type']
                    
                    # Get recent transactions
                    transactions = scanner.get_recent_transactions(address, 5)
                    balance = scanner.get_eth_balance(address)
                    
                    # Generate smart feed items for this whale
                    whale_items = self.analyze_whale_activity(
                        address, whale_name, whale_type, transactions, balance
                    )
                    feed_items.extend(whale_items)
                    
                except Exception as e:
                    print(f"Error analyzing {address}: {e}")
                    continue
            
            # Sort by timestamp (most recent first) and limit to 20 items
            feed_items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            
            return {
                'feed': feed_items[:20],
                'generated_at': str(datetime.now()),
                'total_items': len(feed_items)
            }
            
        except Exception as e:
            print(f"Error generating feed: {e}")
            return {
                'feed': [],
                'error': str(e),
                'generated_at': str(datetime.now())
            }
    
    def analyze_whale_activity(self, address, whale_name, whale_type, transactions, balance):
        """Analyze whale transactions and generate human-readable feed items"""
        feed_items = []
        
        # Expanded token contracts database
        token_contracts = {
            # Major Memecoins
            '0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce': {
                'name': 'Shiba Inu', 'symbol': 'SHIB', 'category': 'memecoin'
            },
            '0x6982508145454ce325ddbe47a25d4ec3d2311933': {
                'name': 'Pepe', 'symbol': 'PEPE', 'category': 'memecoin'
            },
            '0x4d224452801aced8b2f0aebe155379bb5d594381': {
                'name': 'ApeCoin', 'symbol': 'APE', 'category': 'gaming'
            },
            '0xa4bdb11dc0a2bec88d24a3aa1e6bb17201112ebe': {
                'name': 'Stargate Finance', 'symbol': 'STG', 'category': 'defi'
            },
            '0x3845badade8e6dff049820680d1f14bd3903a5d0': {
                'name': 'SAND', 'symbol': 'SAND', 'category': 'gaming'
            },
            '0x0f5d2fb29fb7d3cfee444a200298f468908cc942': {
                'name': 'Decentraland', 'symbol': 'MANA', 'category': 'gaming'
            },
            '0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9': {
                'name': 'Aave', 'symbol': 'AAVE', 'category': 'defi'
            },
            '0xc18360217d8f7ab5e7c516566761ea12ce7f9d72': {
                'name': 'Ethereum Name Service', 'symbol': 'ENS', 'category': 'utility'
            },
            '0x1f9840a85d5af5bf1d1762f925bdaddc4201f984': {
                'name': 'Uniswap', 'symbol': 'UNI', 'category': 'defi'
            },
            '0x514910771af9ca656af840dff83e8264ecf986ca': {
                'name': 'Chainlink', 'symbol': 'LINK', 'category': 'defi'
            },
            '0x6b3595068778dd592e39a122f4f5a5cf09c90fe2': {
                'name': 'SushiToken', 'symbol': 'SUSHI', 'category': 'defi'
            },
            '0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2': {
                'name': 'Maker', 'symbol': 'MKR', 'category': 'defi'
            },
            '0xa0b73e1ff0b80914ab6fe0444e65848c4c34450b': {
                'name': 'Cronos', 'symbol': 'CRO', 'category': 'exchange'
            },
            '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599': {
                'name': 'Wrapped Bitcoin', 'symbol': 'WBTC', 'category': 'btc'
            },
            '0xa0b86a33e6ba3b15f908dcf64e1e6cc01f0b64c4ce': {
                'name': 'Shiba Inu', 'symbol': 'SHIB', 'category': 'memecoin'
            },
            
            # Hot New Memecoins
            '0x72e4f9f808c49a2a61de9c5896298920dc4eeea9': {
                'name': 'Bitcoin Minetrix', 'symbol': 'BTCMTX', 'category': 'memecoin'
            },
            '0x24fcfc492c1393274b6bcd568ac9e225bec93584': {
                'name': 'Floki Inu', 'symbol': 'FLOKI', 'category': 'memecoin'
            },
            '0x42bbfa2e77757c645eeaad1655e0911a7553efbc': {
                'name': 'Bored Ape Yacht Club', 'symbol': 'BAYC', 'category': 'nft'
            },
            
            # Layer 2 Tokens  
            '0x0cec1a9154ff802e7934fc916ed7ca50bde6844e': {
                'name': 'PoolTogether', 'symbol': 'POOL', 'category': 'defi'
            },
            '0x4e3fbd56cd56c3e72c1403e103b45db9da5b9d2b': {
                'name': 'Convex Finance', 'symbol': 'CVX', 'category': 'defi'
            },
            '0xd26114cd6ee289accf82350c8d8487fedb8a0c07': {
                'name': 'OmiseGO', 'symbol': 'OMG', 'category': 'layer2'
            },
            
            # AI/Tech Tokens
            '0x8207c1ffc5b6804f6024322ccf34f29c3541ae26': {
                'name': 'Origin Protocol', 'symbol': 'OGN', 'category': 'tech'
            },
            '0x0bc529c00c6401aef6d220be8c6ea1667f6ad93e': {
                'name': 'yearn.finance', 'symbol': 'YFI', 'category': 'defi'
            },
            '0x6810e776880c02933d47db1b9fc05908e5386b96': {
                'name': 'Gnosis', 'symbol': 'GNO', 'category': 'dao'
            }
        }
        
        # Generate whale classification
        if balance >= 1000000:
            whale_tier = "🏛️ Institutional Giant"
        elif balance >= 100000:
            whale_tier = "🐋 Mega Whale"
        elif balance >= 50000:
            whale_tier = "🦈 Large Whale"
        else:
            whale_tier = "🐟 Whale"
        
        # Analyze transactions for interesting activity
        for i, tx in enumerate(transactions[:3]):  # Analyze recent transactions
            try:
                amount_eth = int(tx['value']) / 1e18
                timestamp = int(tx['timeStamp'])
                tx_hash = tx['hash']
                to_address = tx.get('to', '').lower()
                from_address = tx.get('from', '').lower()
                
                # Skip small transactions
                if amount_eth < 1.0:
                    continue
                
                # Generate different types of feed items
                if amount_eth > 1000:  # Large ETH movement
                    if from_address == address.lower():
                        action_type = "🔴 MASSIVE SELL"
                        description = f"{whale_tier} {whale_name} just moved {amount_eth:,.0f} ETH (${amount_eth * 1800:,.0f})"
                        impact = self.calculate_market_impact(amount_eth, "sell")
                    else:
                        action_type = "🟢 MASSIVE BUY"
                        description = f"{whale_tier} {whale_name} just accumulated {amount_eth:,.0f} ETH (${amount_eth * 1800:,.0f})"
                        impact = self.calculate_market_impact(amount_eth, "buy")
                        
                elif to_address in token_contracts:
                    # Token-related transaction (simulated)
                    token = token_contracts[to_address]
                    usd_value = amount_eth * 1800  # Rough ETH price
                    
                    action_type = f"🎯 {token['category'].upper()} PLAY"
                    description = f"{whale_tier} {whale_name} bought ${usd_value:,.0f} worth of {token['name']} ({token['symbol']})"
                    impact = f"Could signal {token['category']} sector momentum"
                    
                elif amount_eth > 100:  # Medium transaction
                    action_type = "💰 POSITION CHANGE"
                    usd_value = amount_eth * 1800
                    description = f"{whale_tier} {whale_name} moved {amount_eth:,.0f} ETH (${usd_value:,.0f})"
                    impact = "Monitoring for follow-up moves"
                
                else:
                    continue  # Skip small transactions
                
                # Create feed item
                feed_item = {
                    'id': f"{address}_{timestamp}_{i}",
                    'action_type': action_type,
                    'description': description,
                    'whale_name': whale_name,
                    'whale_type': whale_type,
                    'whale_tier': whale_tier,
                    'amount_eth': amount_eth,
                    'usd_value': amount_eth * 1800,
                    'impact': impact,
                    'timestamp': timestamp,
                    'tx_hash': tx_hash,
                    'time_ago': self.get_time_ago(timestamp),
                    'confidence': self.calculate_confidence(whale_type, amount_eth)
                }
                
                feed_items.append(feed_item)
                
            except Exception as e:
                print(f"Error processing transaction: {e}")
                continue
        
        return feed_items
    
    def calculate_market_impact(self, amount_eth, action_type):
        """Calculate potential market impact"""
        if amount_eth > 5000:
            return f"🚨 MAJOR impact expected ({action_type})"
        elif amount_eth > 1000:
            return f"📈 Significant market movement likely"
        else:
            return f"👀 Watch for price action"
    
    def calculate_confidence(self, whale_type, amount_eth):
        """Calculate confidence score for the signal"""
        base_score = 50
        
        # Whale type multiplier
        if whale_type == "Centralized Exchange":
            base_score += 20  # Exchanges often have insider info
        elif whale_type == "Foundation":
            base_score += 30  # Foundations are strategic
        elif whale_type == "DeFi Protocol":
            base_score += 25  # Protocols know their space
        
        # Amount multiplier
        if amount_eth > 5000:
            base_score += 30
        elif amount_eth > 1000:
            base_score += 20
        elif amount_eth > 100:
            base_score += 10
        
        return min(95, max(10, base_score))  # Cap between 10-95%
    
    def get_time_ago(self, timestamp):
        """Convert timestamp to human-readable time ago"""
        try:
            now = datetime.now()
            tx_time = datetime.fromtimestamp(timestamp)
            diff = now - tx_time
            
            if diff.days > 0:
                return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                return "Just now"
        except:
            return "Recently"
    
    def get_html(self):
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ETHhab Intelligence 🧠 - Advanced Whale Tracking</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
            background: #fafafa;
            min-height: 100vh;
            color: #0d1421;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 32px 0;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 8px;
            font-weight: 600;
            color: #0d1421;
            letter-spacing: -0.02em;
        }
        
        .header p {
            font-size: 1rem;
            color: #7c8b9a;
            font-weight: 400;
        }
        
        .intelligence-badge {
            display: inline-block;
            background: #ff6b6b;
            padding: 6px 16px;
            border-radius: 12px;
            font-size: 0.875rem;
            margin-top: 12px;
            color: white;
            font-weight: 500;
        }
        
        .controls {
            display: flex;
            justify-content: center;
            gap: 16px;
            margin-bottom: 32px;
            flex-wrap: wrap;
        }
        
        .table-controls {
            background: white;
            padding: 24px;
            border-radius: 16px;
            margin-bottom: 24px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }
        
        .filter-row {
            display: flex;
            gap: 20px;
            margin-bottom: 16px;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        
        .filter-group label {
            font-size: 0.875rem;
            color: #475569;
            font-weight: 500;
        }
        
        .filter-select {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 8px 12px;
            color: #0d1421;
            font-size: 0.875rem;
            min-width: 120px;
            transition: border-color 0.2s ease;
        }
        
        .filter-select:focus {
            outline: none;
            border-color: #4f46e5;
            box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
        }
        
        .filter-select option {
            background: white;
            color: #0d1421;
        }
        
        .column-toggles {
            border-top: 1px solid #e2e8f0;
            padding-top: 16px;
            margin-top: 16px;
        }
        
        .column-toggles h4 {
            margin-bottom: 12px;
            color: #0d1421;
            font-size: 0.875rem;
            font-weight: 600;
        }
        
        .toggle-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 8px;
        }
        
        .column-toggle {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.875rem;
            color: #475569;
        }
        
        .column-toggle input[type="checkbox"] {
            accent-color: #4f46e5;
        }
        
        .filter-stats {
            background: #f8fafc;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 0.875rem;
            margin-left: auto;
            color: #475569;
            border: 1px solid #e2e8f0;
        }
        
        .scan-btn {
            background: #4f46e5;
            border: none;
            padding: 12px 24px;
            font-size: 1rem;
            color: white;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
            font-weight: 500;
        }
        
        .scan-btn:hover {
            background: #4338ca;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
        }
        
        .intel-btn {
            background: #059669;
            border: none;
            padding: 12px 24px;
            font-size: 1rem;
            color: white;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
            font-weight: 500;
        }
        
        .intel-btn:hover {
            background: #047857;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3);
        }
        
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }
        
        .metric-card {
            background: white;
            padding: 24px;
            border-radius: 16px;
            text-align: center;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
            transition: all 0.2s ease;
        }
        
        .metric-card:hover {
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            transform: translateY(-2px);
        }
        
        .metric-card h3 {
            font-size: 2rem;
            margin-bottom: 8px;
            font-weight: 700;
            color: #0d1421;
        }
        
        .metric-card p {
            color: #7c8b9a;
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        .winners-board {
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin: 32px 0;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }
        
        .winners-board h2 {
            text-align: center;
            margin-bottom: 24px;
            font-size: 1.5rem;
            color: #0d1421;
            font-weight: 600;
        }
        
        .whale-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #e2e8f0;
        }
        
        .whale-table th,
        .whale-table td {
            padding: 16px 12px;
            text-align: left;
            border-bottom: 1px solid #f1f5f9;
        }
        
        .whale-table th {
            background: #f8fafc;
            font-weight: 600;
            cursor: pointer;
            user-select: none;
            position: relative;
            transition: background 0.2s;
            color: #475569;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.025em;
        }
        
        .whale-table th:hover {
            background: #f1f5f9;
        }
        
        .whale-table th.sortable::after {
            content: ' ↕️';
            font-size: 0.75rem;
        }
        
        .whale-table th.sort-asc::after {
            content: ' ⬆️';
        }
        
        .whale-table th.sort-desc::after {
            content: ' ⬇️';
        }
        
        .whale-table tbody tr:nth-child(even) {
            background: #f8fafc;
        }
        
        .whale-table tbody tr:hover {
            background: #f1f5f9;
            cursor: pointer;
        }
        
        .rank-cell {
            font-weight: 700;
            color: #059669;
            text-align: center;
            width: 50px;
        }
        
        .tier-cell {
            text-align: center;
            font-size: 1.2rem;
        }
        
        .address-cell {
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
            font-size: 0.875rem;
            color: #475569;
        }
        
        .balance-cell {
            font-weight: 600;
            color: #059669;
            text-align: right;
        }
        
        .volume-cell {
            color: #dc2626;
            text-align: right;
            font-weight: 500;
        }
        
        .usd-cell {
            color: #d97706;
            text-align: right;
            font-weight: 500;
        }
        
        .intelligence-cell {
            text-align: center;
        }
        
        .intel-score {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 8px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.025em;
        }
        
        .intel-high {
            background: #dcfce7;
            color: #166534;
        }
        
        .intel-medium {
            background: #fef3c7;
            color: #92400e;
        }
        
        .intel-low {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .intel-unknown {
            background: #f1f5f9;
            color: #475569;
        }
        
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(8px);
        }
        
        .modal-content {
            background: white;
            margin: 5% auto;
            padding: 32px;
            border-radius: 16px;
            width: 90%;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
            color: #0d1421;
            border: 1px solid #e2e8f0;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }
        
        .close {
            color: #7c8b9a;
            float: right;
            font-size: 24px;
            font-weight: 400;
            cursor: pointer;
            line-height: 1;
        }
        
        .close:hover {
            color: #0d1421;
        }
        
        .loading {
            text-align: center;
            padding: 64px;
        }
        
        .spinner {
            border: 3px solid #e2e8f0;
            border-radius: 50%;
            border-top: 3px solid #4f46e5;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .footer {
            text-align: center;
            margin-top: 64px;
            padding: 24px;
            color: #7c8b9a;
            font-size: 0.875rem;
        }
        
        /* Activity Feed Styles */
        .activity-feed {
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin: 32px 0;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }
        
        .activity-feed h2 {
            color: #0d1421;
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .feed-content {
            max-height: 600px;
            overflow-y: auto;
        }
        
        .feed-item {
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            transition: all 0.2s ease;
            background: white;
        }
        
        .feed-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            border-color: #4f46e5;
        }
        
        .feed-item-header {
            display: flex;
            justify-content: between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .action-type {
            font-weight: 700;
            font-size: 0.875rem;
            padding: 4px 12px;
            border-radius: 8px;
            text-transform: uppercase;
            letter-spacing: 0.025em;
        }
        
        .action-massive-sell {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .action-massive-buy {
            background: #dcfce7;
            color: #166534;
        }
        
        .action-memecoin-play {
            background: #fef3c7;
            color: #92400e;
        }
        
        .action-defi-play {
            background: #dbeafe;
            color: #1e40af;
        }
        
        .action-position-change {
            background: #f3e8ff;
            color: #6b21a8;
        }
        
        .feed-description {
            font-size: 1rem;
            color: #0d1421;
            font-weight: 500;
            margin: 8px 0;
            line-height: 1.5;
        }
        
        .feed-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #f1f5f9;
            font-size: 0.875rem;
            color: #7c8b9a;
        }
        
        .feed-impact {
            font-style: italic;
            color: #475569;
        }
        
        .confidence-score {
            background: #f8fafc;
            padding: 2px 8px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.75rem;
        }
        
        .confidence-high {
            background: #dcfce7;
            color: #166534;
        }
        
        .confidence-medium {
            background: #fef3c7;
            color: #92400e;
        }
        
        .confidence-low {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .time-ago {
            font-weight: 500;
            color: #059669;
        }
        
        @media (max-width: 768px) {
            .whale-table {
                font-size: 0.8rem;
            }
            
            .whale-table th,
            .whale-table td {
                padding: 8px 4px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🧠 ETHhab Intelligence</h1>
            <p>"Advanced Whale Tracking with AI-Powered Social Intelligence"</p>
            <div class="intelligence-badge">
                🕵️ Multi-Layer Intelligence • 📊 Trade Signals • 🔍 Social Analysis
            </div>
        </header>
        
        <div class="controls">
            <button class="scan-btn" onclick="loadWhales()">🔄 Scan Whales</button>
            <button class="intel-btn" onclick="generateIntelligence()">🧠 Deep Intelligence Scan</button>
            <button class="scan-btn" onclick="loadFeed()" style="background: #10b981;">📰 Activity Feed</button>
            <button class="scan-btn" onclick="hotReload()" style="background: #f59e0b;">⚡ Hot Reload</button>
        </div>
        
        <!-- Activity Feed Section -->
        <div id="activity-feed" class="activity-feed" style="display: none;">
            <h2>🚨 Live Whale Activity Feed</h2>
            <p style="margin-bottom: 20px; color: #7c8b9a;">Real-time whale movements translated into plain English</p>
            <div id="feed-content" class="feed-content">
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Loading whale activity...</p>
                </div>
            </div>
        </div>
        
        <div id="summary" class="summary"></div>
        
        <div class="winners-board">
            <h2>🏆 Whale Intelligence Board</h2>
            <div style="text-align: center; margin-bottom: 15px;">
                <span style="opacity: 0.8;">🧠 AI-Powered Analysis • 🔍 Social Intelligence • 📊 Trading Signals</span>
            </div>
            
            <!-- Table Controls -->
            <div class="table-controls">
                <div class="filter-row">
                    <div class="filter-group">
                        <label>🏷️ Entity Type</label>
                        <select id="entityFilter" class="filter-select" onchange="applyFilters()">
                            <option value="all">All Types</option>
                            <option value="Centralized Exchange">🏦 Exchanges</option>
                            <option value="Protocol Infrastructure">⚙️ Protocols</option>
                            <option value="DeFi Protocol">🔄 DeFi</option>
                            <option value="Foundation">🏛️ Foundations</option>
                            <option value="Unknown Entity">❓ Unknown</option>
                        </select>
                    </div>
                    
                    <div class="filter-group">
                        <label>🐋 Whale Tier</label>
                        <select id="tierFilter" class="filter-select" onchange="applyFilters()">
                            <option value="all">All Tiers</option>
                            <option value="Institutional">🏛️ Institutional (1M+)</option>
                            <option value="Mega Whale">🐋 Mega Whale (500K+)</option>
                            <option value="Large Whale">🦈 Large Whale (100K+)</option>
                            <option value="Whale">🐟 Whale (50K+)</option>
                            <option value="Mini Whale">🐠 Mini Whale (10K+)</option>
                        </select>
                    </div>
                    
                    <div class="filter-group">
                        <label>📊 Min Balance (ETH)</label>
                        <select id="balanceFilter" class="filter-select" onchange="applyFilters()">
                            <option value="0">Any Amount</option>
                            <option value="10000">10K+ ETH</option>
                            <option value="50000">50K+ ETH</option>
                            <option value="100000">100K+ ETH</option>
                            <option value="500000">500K+ ETH</option>
                            <option value="1000000">1M+ ETH</option>
                        </select>
                    </div>
                    
                    <div class="filter-group">
                        <label>🧠 Intelligence</label>
                        <select id="intelligenceFilter" class="filter-select" onchange="applyFilters()">
                            <option value="all">All Levels</option>
                            <option value="verified">✅ Verified (90%+)</option>
                            <option value="high">🎯 High (70%+)</option>
                            <option value="medium">🔍 Medium (50%+)</option>
                            <option value="unknown">❓ Unknown</option>
                        </select>
                    </div>
                    
                    <div class="filter-stats" id="filterStats">
                        Showing: 0 whales
                    </div>
                </div>
                
                <div class="column-toggles">
                    <h4>👁️ Column Visibility</h4>
                    <div class="toggle-grid">
                        <div class="column-toggle">
                            <input type="checkbox" id="col-entity" checked onchange="toggleColumn('entity')">
                            <label for="col-entity">Entity Name</label>
                        </div>
                        <div class="column-toggle">
                            <input type="checkbox" id="col-tier" checked onchange="toggleColumn('tier')">
                            <label for="col-tier">Tier</label>
                        </div>
                        <div class="column-toggle">
                            <input type="checkbox" id="col-balance" checked onchange="toggleColumn('balance')">
                            <label for="col-balance">Balance</label>
                        </div>
                        <div class="column-toggle">
                            <input type="checkbox" id="col-volume-1d" checked onchange="toggleColumn('volume-1d')">
                            <label for="col-volume-1d">Volume (1D)</label>
                        </div>
                        <div class="column-toggle">
                            <input type="checkbox" id="col-volume-7d" checked onchange="toggleColumn('volume-7d')">
                            <label for="col-volume-7d">Volume (7D)</label>
                        </div>
                        <div class="column-toggle">
                            <input type="checkbox" id="col-volume-30d" onchange="toggleColumn('volume-30d')">
                            <label for="col-volume-30d">Volume (30D)</label>
                        </div>
                        <div class="column-toggle">
                            <input type="checkbox" id="col-volume-365d" onchange="toggleColumn('volume-365d')">
                            <label for="col-volume-365d">Volume (1Y)</label>
                        </div>
                        <div class="column-toggle">
                            <input type="checkbox" id="col-frequency" checked onchange="toggleColumn('frequency')">
                            <label for="col-frequency">Trade Frequency</label>
                        </div>
                        <div class="column-toggle">
                            <input type="checkbox" id="col-intelligence" checked onchange="toggleColumn('intelligence')">
                            <label for="col-intelligence">Confidence Score</label>
                        </div>
                    </div>
                </div>
            </div>
            <table class="whale-table" id="whaleTable">
                <thead>
                    <tr>
                        <th class="sortable" data-sort="rank">#</th>
                        <th class="sortable col-entity" data-sort="entity">Entity Name</th>
                        <th class="sortable col-tier" data-sort="tier">Tier</th>
                        <th class="sortable" data-sort="address">Address</th>
                        <th class="sortable col-balance" data-sort="balance">ETH Balance</th>
                        <th class="sortable" data-sort="usd">USD Value</th>
                        <th class="sortable col-volume-1d" data-sort="volume_1d">Volume (1D)</th>
                        <th class="sortable col-volume-7d" data-sort="volume_7d">Volume (7D)</th>
                        <th class="sortable col-volume-30d" data-sort="volume_30d" style="display:none;">Volume (30D)</th>
                        <th class="sortable col-volume-365d" data-sort="volume_365d" style="display:none;">Volume (1Y)</th>
                        <th class="sortable col-frequency" data-sort="frequency">Trade Freq/Day</th>
                        <th class="sortable col-intelligence" data-sort="intelligence">Confidence Score*</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="whaleTableBody">
                    <tr>
                        <td colspan="13" style="text-align: center; padding: 40px;">
                            <div class="spinner"></div>
                            <p>Loading whale intelligence...</p>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; margin: 20px 0;">
            <h4 style="color: #f1c40f; margin-bottom: 10px;">📖 Column Explanations</h4>
            <p><strong>Confidence Score*:</strong> Multi-layer AI confidence system that combines:</p>
            <ul style="margin-left: 20px;">
                <li><strong>🏷️ Identity Database:</strong> Known exchanges, protocols, foundations (high confidence)</li>
                <li><strong>📊 Trading Patterns:</strong> Transaction behavior analysis (exchange-like, DeFi, individual)</li>
                <li><strong>🔍 Social Intelligence:</strong> Twitter/Reddit mentions and discussions</li>
                <li><strong>🎯 Behavioral Profiling:</strong> Advanced pattern recognition for entity type</li>
            </ul>
            <p><em>Click "🧠 Intel" button for detailed 4-layer analysis report!</em></p>
            <p><strong>Trade Frequency:</strong> Average number of transactions per day over the last 7 days.</p>
            <p><strong>Volume (1D/7D/30D/1Y):</strong> Total ETH moved in the specified time period (incoming + outgoing).</p>
            <p><strong>Tier Classification:</strong> 🏛️ Institutional (1M+ ETH) • 🐋 Mega Whale (500K+ ETH) • 🦈 Large Whale (100K+ ETH) • 🐟 Whale (50K+ ETH) • 🐠 Mini Whale (10K+ ETH)</p>
        </div>
        
        <footer class="footer">
            <p>🧠 <strong>ETHhab Intelligence</strong> - Advanced whale tracking with social intelligence</p>
            <p>Last updated: <span id="lastUpdate">Never</span></p>
        </footer>
    </div>

    <!-- Intelligence Modal -->
    <div id="intelligenceModal" class="modal">
        <div class="modal-content">
            <span class="close">&times;</span>
            <div id="intelligenceContent">
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Generating intelligence report...</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        let whaleData = [];
        let filteredWhaleData = [];
        let currentSort = { column: 'balance', direction: 'desc' };
        
        // Filter state
        let filters = {
            entityType: 'all',
            tier: 'all',
            balance: 0,
            intelligence: 'all'
        };
        
        function formatNumber(num) {
            return new Intl.NumberFormat().format(Math.round(num));
        }
        
        function formatAddress(address) {
            return address.substring(0, 10) + '...' + address.substring(address.length - 6);
        }
        
        function formatETH(amount) {
            if (amount >= 1000000) {
                return (amount / 1000000).toFixed(1) + 'M';
            } else if (amount >= 1000) {
                return (amount / 1000).toFixed(1) + 'K';
            } else {
                return amount.toFixed(2);
            }
        }
        
        function formatUSD(amount) {
            const usd = amount * 3000;
            if (usd >= 1000000000) {
                return '$' + (usd / 1000000000).toFixed(1) + 'B';
            } else if (usd >= 1000000) {
                return '$' + (usd / 1000000).toFixed(1) + 'M';
            } else if (usd >= 1000) {
                return '$' + (usd / 1000).toFixed(1) + 'K';
            } else {
                return '$' + usd.toFixed(0);
            }
        }
        
        function getIntelligenceDisplay(intelligence) {
            if (!intelligence || !intelligence.has_intelligence) {
                return '<span class="intel-score intel-unknown">🔍 No Data</span>';
            }
            
            const score = intelligence.confidence_score || 0;
            const identityName = intelligence.identity_name || 'Unknown';
            const identityType = intelligence.identity_type || 'unknown';
            
            let className = 'intel-unknown';
            let icon = '🔍';
            let text = 'Unknown';
            
            if (score >= 90) {
                className = 'intel-high';
                text = 'Verified';
                icon = '✅';
            } else if (score >= 70) {
                className = 'intel-high';
                text = 'High Confidence';
                icon = '🎯';
            } else if (score >= 50) {
                className = 'intel-medium';
                text = 'Medium';
                icon = '🔍';
            } else if (score > 0) {
                className = 'intel-low';
                text = 'Low';
                icon = '❓';
            }
            
            // Add entity type context
            let typeIcon = '';
            if (identityType === 'exchange') typeIcon = '🏦';
            else if (identityType === 'contract') typeIcon = '📜';
            else if (identityType === 'foundation') typeIcon = '🏛️';
            else if (identityType === 'protocol') typeIcon = '⚙️';
            
            return `<div style="text-align: center;">
                        <span class="intel-score ${className}">${icon} ${text}</span><br>
                        <small style="opacity: 0.8;">${typeIcon} ${score}% Confidence</small>
                    </div>`;
        }
        
        function showLoading() {
            document.getElementById('whaleTableBody').innerHTML = `
                <tr>
                    <td colspan="13" style="text-align: center; padding: 40px;">
                        <div class="spinner"></div>
                        <p>🐋 Scanning blockchain for whales...</p>
                    </td>
                </tr>
            `;
        }
        
        function updateSummary() {
            const totalWhales = whaleData.length;
            const totalEth = whaleData.reduce((sum, whale) => sum + whale.balance, 0);
            const avgBalance = totalEth / totalWhales;
            const totalVolume = whaleData.reduce((sum, whale) => sum + whale.volume, 0);
            
            document.getElementById('summary').innerHTML = `
                <div class="metric-card">
                    <h3>🐋 ${totalWhales}</h3>
                    <p>Total Whales</p>
                </div>
                <div class="metric-card">
                    <h3>💰 ${formatNumber(totalEth)}</h3>
                    <p>Total ETH</p>
                </div>
                <div class="metric-card">
                    <h3>📈 ${formatNumber(avgBalance)}</h3>
                    <p>Avg Balance</p>
                </div>
                <div class="metric-card">
                    <h3>🧠 ${whaleData.filter(w => w.intelligence && w.intelligence.has_intelligence).length}</h3>
                    <p>Identified</p>
                </div>
            `;
        }
        
        function updateTable() {
            // Initialize filtered data if empty
            if (filteredWhaleData.length === 0 && whaleData.length > 0) {
                filteredWhaleData = [...whaleData];
            }
            
            updateFilteredTable();
        }
        
        function toggleColumn(columnClass) {
            const checkbox = document.getElementById(`col-${columnClass}`);
            const columns = document.querySelectorAll(`.col-${columnClass}`);
            
            columns.forEach(col => {
                col.style.display = checkbox.checked ? '' : 'none';
            });
        }
        
        function applyFilters() {
            // Get filter values
            filters.entityType = document.getElementById('entityFilter').value;
            filters.tier = document.getElementById('tierFilter').value;
            filters.balance = parseFloat(document.getElementById('balanceFilter').value);
            filters.intelligence = document.getElementById('intelligenceFilter').value;
            
            // Apply filters
            filteredWhaleData = whaleData.filter(whale => {
                // Entity type filter
                if (filters.entityType !== 'all' && whale.entity_type !== filters.entityType) {
                    return false;
                }
                
                // Tier filter
                if (filters.tier !== 'all') {
                    const tierCheck = whale.tier_text || whale.tier;
                    if (!tierCheck.includes(filters.tier)) {
                        return false;
                    }
                }
                
                // Balance filter
                if (whale.balance < filters.balance) {
                    return false;
                }
                
                // Intelligence filter
                if (filters.intelligence !== 'all') {
                    const intelligence = whale.intelligence;
                    const score = intelligence?.confidence_score || 0;
                    
                    switch (filters.intelligence) {
                        case 'verified':
                            if (score < 90) return false;
                            break;
                        case 'high':
                            if (score < 70) return false;
                            break;
                        case 'medium':
                            if (score < 50) return false;
                            break;
                        case 'unknown':
                            if (intelligence?.has_intelligence) return false;
                            break;
                    }
                }
                
                return true;
            });
            
            // Update display
            updateFilteredTable();
            updateFilterStats();
        }
        
        function updateFilteredTable() {
            const tableBody = document.getElementById('whaleTableBody');
            
            if (filteredWhaleData.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="13" style="text-align: center; padding: 40px; color: #f39c12;">
                            🔍 No whales match the current filters
                        </td>
                    </tr>
                `;
                return;
            }
            
            const rowsHtml = filteredWhaleData.map((whale, index) => {
                const rank = index + 1;
                let rankDisplay = rank;
                
                if (rank === 1) rankDisplay = '🥇';
                else if (rank === 2) rankDisplay = '🥈';
                else if (rank === 3) rankDisplay = '🥉';
                
                return `
                    <tr onclick="showWhaleDetails('${whale.address}')" style="cursor: pointer;">
                        <td class="rank-cell">${rankDisplay}</td>
                        <td class="col-entity">${whale.entity_name || 'Unknown'}</td>
                        <td class="col-tier tier-cell">${whale.emoji} ${whale.tier_text || whale.tier}</td>
                        <td class="address-cell">${formatAddress(whale.address)}</td>
                        <td class="col-balance balance-cell">${formatETH(whale.balance)} ETH</td>
                        <td class="usd-cell">${formatUSD(whale.balance)}</td>
                        <td class="col-volume-1d volume-cell">${formatETH(whale.volume_1d || 0)} ETH</td>
                        <td class="col-volume-7d volume-cell">${formatETH(whale.volume_7d || 0)} ETH</td>
                        <td class="col-volume-30d volume-cell" style="display:none;">${formatETH(whale.volume_30d || 0)} ETH</td>
                        <td class="col-volume-365d volume-cell" style="display:none;">${formatETH(whale.volume_365d || 0)} ETH</td>
                        <td class="col-frequency" style="text-align: center;">${(whale.trade_frequency || 0).toFixed(1)}/day</td>
                        <td class="col-intelligence intelligence-cell">${getIntelligenceDisplay(whale.intelligence)}</td>
                        <td style="text-align: center;">
                            <button onclick="event.stopPropagation(); generateWhaleIntelligence('${whale.address}')" 
                                    style="background: #4834d4; color: white; border: none; padding: 4px 8px; border-radius: 5px; cursor: pointer; margin: 2px; font-size: 0.8rem;">
                                🧠 Intel
                            </button>
                            <button onclick="event.stopPropagation(); showMemecoins('${whale.address}')" 
                                    style="background: #10b981; color: white; border: none; padding: 4px 8px; border-radius: 5px; cursor: pointer; margin: 2px; font-size: 0.8rem;">
                                🐸 Memes
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
            
            tableBody.innerHTML = rowsHtml;
        }
        
        function updateFilterStats() {
            const total = whaleData.length;
            const shown = filteredWhaleData.length;
            const totalETH = filteredWhaleData.reduce((sum, whale) => sum + whale.balance, 0);
            
            document.getElementById('filterStats').innerHTML = `
                Showing: ${shown}/${total} whales (${formatNumber(totalETH)} ETH)
            `;
        }
        
        function sortWhales(column) {
            if (currentSort.column === column) {
                currentSort.direction = currentSort.direction === 'desc' ? 'asc' : 'desc';
            } else {
                currentSort.column = column;
                currentSort.direction = column === 'address' ? 'asc' : 'desc';
            }
            
            whaleData.sort((a, b) => {
                let aVal, bVal;
                
                switch(column) {
                    case 'balance':
                        aVal = a.balance;
                        bVal = b.balance;
                        break;
                    case 'volume':
                        aVal = a.volume;
                        bVal = b.volume;
                        break;
                    case 'intelligence':
                        aVal = a.intelligence && a.intelligence.confidence_score ? a.intelligence.confidence_score : 0;
                        bVal = b.intelligence && b.intelligence.confidence_score ? b.intelligence.confidence_score : 0;
                        break;
                    case 'tier':
                        const tierOrder = {'Institutional': 4, 'Mega Whale': 3, 'Large Whale': 2, 'Mini Whale': 1};
                        aVal = tierOrder[a.tier];
                        bVal = tierOrder[b.tier];
                        break;
                    case 'address':
                        aVal = a.address.toLowerCase();
                        bVal = b.address.toLowerCase();
                        break;
                    default:
                        return 0;
                }
                
                if (currentSort.direction === 'asc') {
                    return aVal > bVal ? 1 : -1;
                } else {
                    return aVal < bVal ? 1 : -1;
                }
            });
            
            // Sort filtered data the same way
            filteredWhaleData.sort((a, b) => {
                let aVal, bVal;
                
                switch(column) {
                    case 'balance':
                        aVal = a.balance;
                        bVal = b.balance;
                        break;
                    case 'volume':
                        aVal = a.volume;
                        bVal = b.volume;
                        break;
                    case 'intelligence':
                        aVal = a.intelligence && a.intelligence.confidence_score ? a.intelligence.confidence_score : 0;
                        bVal = b.intelligence && b.intelligence.confidence_score ? b.intelligence.confidence_score : 0;
                        break;
                    case 'tier':
                        const tierOrder = {'Institutional': 4, 'Mega Whale': 3, 'Large Whale': 2, 'Mini Whale': 1};
                        aVal = tierOrder[a.tier];
                        bVal = tierOrder[b.tier];
                        break;
                    case 'address':
                        aVal = a.address.toLowerCase();
                        bVal = b.address.toLowerCase();
                        break;
                    default:
                        return 0;
                }
                
                if (currentSort.direction === 'asc') {
                    return aVal > bVal ? 1 : -1;
                } else {
                    return aVal < bVal ? 1 : -1;
                }
            });
            
            updateFilteredTable();
            updateSortHeaders();
        }
        
        function updateSortHeaders() {
            document.querySelectorAll('.whale-table th').forEach(th => {
                th.classList.remove('sort-asc', 'sort-desc');
                th.classList.add('sortable');
            });
            
            const currentHeader = document.querySelector(`[data-sort="${currentSort.column}"]`);
            if (currentHeader) {
                currentHeader.classList.add(currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
            }
        }
        
        function showWhaleDetails(address) {
            const whale = whaleData.find(w => w.address === address);
            if (whale) {
                let details = `🐋 Whale Details\\n\\n`;
                details += `Address: ${whale.address}\\n`;
                details += `Tier: ${whale.tier}\\n`;
                details += `Balance: ${formatNumber(whale.balance)} ETH\\n`;
                details += `USD Value: ${formatUSD(whale.balance)}\\n`;
                details += `Recent Volume: ${formatNumber(whale.volume)} ETH\\n`;
                
                if (whale.intelligence && whale.intelligence.has_intelligence) {
                    details += `\\nIntelligence:\\n`;
                    details += `Identity: ${whale.intelligence.identity_name}\\n`;
                    details += `Type: ${whale.intelligence.identity_type}\\n`;
                    details += `Confidence: ${whale.intelligence.confidence_score}%\\n`;
                    details += `Risk Score: ${whale.intelligence.risk_score}/100\\n`;
                }
                
                alert(details);
            }
        }
        
        async function loadWhales() {
            // Show whale table, hide feed
            showWhaleTable();
            
            showLoading();
            
            try {
                const response = await fetch('/api/whales');
                whaleData = await response.json();
                
                // Initialize filtered data and filters
                filteredWhaleData = [...whaleData];
                applyFilters();
                
                sortWhales('balance');
                updateSummary();
                
                document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
            } catch (error) {
                console.error('Error loading whale data:', error);
                document.getElementById('whaleTableBody').innerHTML = `
                    <tr>
                        <td colspan="13" style="text-align: center; padding: 20px; color: #e74c3c;">
                            ❌ Error loading whale data
                        </td>
                    </tr>
                `;
            }
        }
        
        async function generateWhaleIntelligence(address) {
            const modal = document.getElementById('intelligenceModal');
            const content = document.getElementById('intelligenceContent');
            
            modal.style.display = 'block';
            content.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>🧠 Generating deep intelligence for ${address.substring(0, 10)}...</p>
                    <p><small>Analyzing trading patterns, social mentions, and behavioral data...</small></p>
                </div>
            `;
            
            try {
                const response = await fetch(`/api/intelligence/${address}`);
                const intelligence = await response.json();
                
                if (intelligence.error) {
                    content.innerHTML = `
                        <h2>❌ Intelligence Error</h2>
                        <p>${intelligence.error}</p>
                    `;
                } else {
                    displayIntelligenceReport(intelligence);
                }
                
            } catch (error) {
                content.innerHTML = `
                    <h2>❌ Error</h2>
                    <p>Failed to generate intelligence report: ${error.message}</p>
                `;
            }
        }
        
        function displayIntelligenceReport(intelligence) {
            const content = document.getElementById('intelligenceContent');
            const assessment = intelligence.final_assessment;
            
            let html = `
                <h2>🧠 Intelligence Report</h2>
                <h3>${intelligence.address}</h3>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;">
                    <div class="metric-card">
                        <h3>${assessment.overall_score}/100</h3>
                        <p>Overall Score</p>
                    </div>
                    <div class="metric-card">
                        <h3>${assessment.identity_confidence.toFixed(1)}%</h3>
                        <p>Identity Confidence</p>
                    </div>
                    <div class="metric-card">
                        <h3>${assessment.risk_level.toUpperCase()}</h3>
                        <p>Risk Level</p>
                    </div>
                    <div class="metric-card">
                        <h3>${assessment.market_impact}/100</h3>
                        <p>Market Impact</p>
                    </div>
                </div>
            `;
            
            if (intelligence.known_identity && intelligence.known_identity.identified) {
                const identity = intelligence.known_identity;
                html += `
                    <h3>🏷️ Identity</h3>
                    <p><strong>Name:</strong> ${identity.name}</p>
                    <p><strong>Type:</strong> ${identity.type}</p>
                    <p><strong>Category:</strong> ${identity.category}</p>
                    ${identity.twitter ? `<p><strong>Twitter:</strong> ${identity.twitter}</p>` : ''}
                `;
            }
            
            if (assessment.key_findings && assessment.key_findings.length > 0) {
                html += `
                    <h3>🔍 Key Findings</h3>
                    <ul>
                `;
                assessment.key_findings.forEach(finding => {
                    html += `<li>${finding}</li>`;
                });
                html += `</ul>`;
            }
            
            if (assessment.recommended_actions && assessment.recommended_actions.length > 0) {
                html += `
                    <h3>💡 Recommended Actions</h3>
                    <ul>
                `;
                assessment.recommended_actions.forEach(action => {
                    html += `<li>${action}</li>`;
                });
                html += `</ul>`;
            }
            
            html += `
                <h3>📊 Data Sources</h3>
                <p>${intelligence.data_sources.join(', ')}</p>
                
                <p style="margin-top: 20px; opacity: 0.8; font-size: 0.9rem;">
                    Generated at: ${intelligence.timestamp}
                </p>
            `;
            
            content.innerHTML = html;
        }
        
        function generateIntelligence() {
            alert('🧠 Deep Intelligence Scan\\n\\nThis will analyze all whales with advanced social intelligence and trading pattern analysis.\\n\\nClick the "🧠 Intel" button next to individual whales for detailed reports!');
        }
        
        function hotReload() {
            fetch('/api/reload')
                .then(response => response.json())
                .then(data => {
                    console.log('Hot reload:', data);
                    // Reload the whale data
                    loadWhales();
                    alert('⚡ Hot reload complete! Fresh data loaded.');
                })
                .catch(error => {
                    console.error('Hot reload error:', error);
                    alert('❌ Hot reload failed: ' + error);
                });
        }
        
        function showMemecoins(address) {
            const modal = document.getElementById('modal');
            const content = document.getElementById('modal-content');
            
            modal.style.display = 'block';
            content.innerHTML = '<div class="loading"><div class="spinner"></div><p>🐸 Analyzing memecoin activity...</p></div>';
            
            fetch(`/api/memecoins/${address}`)
                .then(response => response.json())
                .then(data => displayMemecoins(data))
                .catch(error => {
                    content.innerHTML = `<h2>❌ Error</h2><p>Failed to load memecoin data: ${error}</p>`;
                });
        }
        
        function displayMemecoins(data) {
            const content = document.getElementById('modal-content');
            
            let html = `
                <span class="close" onclick="document.getElementById('modal').style.display='none'">&times;</span>
                <h2>🐸 Memecoin Activity</h2>
                <p><strong>Address:</strong> ${data.address}</p>
                <p><strong>Total Memecoin Transactions:</strong> ${data.total_memecoin_transactions}</p>
            `;
            
            if (data.recent_activity && data.recent_activity.length > 0) {
                html += `
                    <h3>Recent Memecoin Purchases</h3>
                    <table style="width: 100%; margin-top: 10px;">
                        <tr style="background: rgba(0,0,0,0.1);">
                            <th>Token</th>
                            <th>Amount (ETH)</th>
                            <th>Date</th>
                            <th>TX Hash</th>
                        </tr>
                `;
                
                data.recent_activity.forEach(tx => {
                    const date = new Date(parseInt(tx.timestamp) * 1000).toLocaleDateString();
                    const shortHash = tx.hash.substring(0, 10) + '...';
                    
                    html += `
                        <tr>
                            <td><strong>${tx.token_symbol}</strong> (${tx.token_name})</td>
                            <td>${tx.amount_eth} ETH</td>
                            <td>${date}</td>
                            <td style="font-family: monospace; font-size: 0.8rem;">${shortHash}</td>
                        </tr>
                    `;
                });
                
                html += `</table>`;
            } else {
                html += `<p>💤 No recent memecoin activity detected for this whale.</p>`;
            }
            
            html += `<p style="margin-top: 20px; opacity: 0.8; font-size: 0.9rem;">Analysis completed: ${data.analysis_timestamp}</p>`;
            
            content.innerHTML = html;
        }
        
        function loadFeed() {
            const feedSection = document.getElementById('activity-feed');
            const feedContent = document.getElementById('feed-content');
            const whaleSection = document.querySelector('.winners-board');
            
            // Show feed, hide whale table
            feedSection.style.display = 'block';
            whaleSection.style.display = 'none';
            
            // Show loading
            feedContent.innerHTML = '<div class="loading"><div class="spinner"></div><p>Analyzing whale activity...</p></div>';
            
            fetch('/api/feed')
                .then(response => response.json())
                .then(data => displayFeed(data))
                .catch(error => {
                    feedContent.innerHTML = `<div style="text-align: center; padding: 40px;"><h3>❌ Error</h3><p>Failed to load activity feed: ${error}</p></div>`;
                });
        }
        
        function displayFeed(data) {
            const feedContent = document.getElementById('feed-content');
            
            if (data.error) {
                feedContent.innerHTML = `<div style="text-align: center; padding: 40px;"><h3>❌ Error</h3><p>${data.error}</p></div>`;
                return;
            }
            
            if (!data.feed || data.feed.length === 0) {
                feedContent.innerHTML = `<div style="text-align: center; padding: 40px;"><h3>💤 No Activity</h3><p>No significant whale activity detected recently.</p></div>`;
                return;
            }
            
            let html = '';
            
            data.feed.forEach(item => {
                const actionClass = getActionClass(item.action_type);
                const confidenceClass = getConfidenceClass(item.confidence);
                
                html += `
                    <div class="feed-item" onclick="window.open('https://etherscan.io/tx/${item.tx_hash}', '_blank')">
                        <div class="feed-item-header">
                            <span class="action-type ${actionClass}">${item.action_type}</span>
                            <span class="time-ago">${item.time_ago}</span>
                        </div>
                        
                        <div class="feed-description">
                            ${item.description}
                        </div>
                        
                        <div class="feed-meta">
                            <span class="feed-impact">${item.impact}</span>
                            <span class="confidence-score ${confidenceClass}">
                                ${item.confidence}% confidence
                            </span>
                        </div>
                    </div>
                `;
            });
            
            // Add refresh info
            html += `
                <div style="text-align: center; margin-top: 20px; color: #7c8b9a; font-size: 0.875rem;">
                    <p>📊 Showing ${data.feed.length} recent activities • Generated: ${new Date(data.generated_at).toLocaleTimeString()}</p>
                    <button onclick="loadFeed()" style="margin-top: 10px; background: #4f46e5; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer;">
                        🔄 Refresh Feed
                    </button>
                </div>
            `;
            
            feedContent.innerHTML = html;
        }
        
        function getActionClass(actionType) {
            if (actionType.includes('MASSIVE SELL')) return 'action-massive-sell';
            if (actionType.includes('MASSIVE BUY')) return 'action-massive-buy';
            if (actionType.includes('MEMECOIN')) return 'action-memecoin-play';
            if (actionType.includes('DEFI')) return 'action-defi-play';
            return 'action-position-change';
        }
        
        function getConfidenceClass(confidence) {
            if (confidence >= 70) return 'confidence-high';
            if (confidence >= 50) return 'confidence-medium';
            return 'confidence-low';
        }
        
        function showWhaleTable() {
            const feedSection = document.getElementById('activity-feed');
            const whaleSection = document.querySelector('.winners-board');
            
            // Hide feed, show whale table
            feedSection.style.display = 'none';
            whaleSection.style.display = 'block';
        }
        
        // Event listeners
        window.addEventListener('load', () => {
            loadWhales();
            
            document.querySelectorAll('.whale-table th[data-sort]').forEach(th => {
                th.addEventListener('click', () => {
                    const sortColumn = th.getAttribute('data-sort');
                    if (sortColumn !== 'rank') {
                        sortWhales(sortColumn);
                    }
                });
            });
            
            // Modal close functionality
            document.querySelector('.close').addEventListener('click', () => {
                document.getElementById('intelligenceModal').style.display = 'none';
            });
            
            window.addEventListener('click', (event) => {
                const modal = document.getElementById('intelligenceModal');
                if (event.target === modal) {
                    modal.style.display = 'none';
                }
            });
        });
        
        // Auto-refresh every 5 minutes
        setInterval(loadWhales, 300000);
    </script>
</body>
</html>
        '''

def start_intelligence_server():
    """Start ETHhab Intelligence server"""
    PORT = 8003
    
    with socketserver.TCPServer(("", PORT), ETHhabIntelligenceHandler) as httpd:
        print(f"🧠 ETHhab Intelligence launching on http://localhost:{PORT}")
        print("🚀 Features: Advanced whale tracking, social intelligence, trading signals")
        print("🔍 Multi-layer analysis: Known entities, transaction patterns, social scraping")
        print("📊 Real-time intelligence reports with confidence scoring")
        print("\\n🌐 Opening browser...")
        
        def open_browser():
            time.sleep(3)
            webbrowser.open(f'http://localhost:{PORT}')
        
        threading.Thread(target=open_browser, daemon=True).start()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\\n🛑 ETHhab Intelligence server stopped")

if __name__ == "__main__":
    start_intelligence_server()