#!/usr/bin/env python3
"""
ETHhab Social Scraper
Scrapes Twitter, GitHub, Reddit and other platforms to link ETH addresses to real identities
No API keys required - uses web scraping and public data
"""

import requests
import re
import time
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import sqlite3
from urllib.parse import quote_plus, urljoin
import random

class SocialScraper:
    def __init__(self):
        self.db_path = "whale_social.db"
        self.init_database()
        
        # User agents to rotate for scraping
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        
        # ETH address regex pattern
        self.eth_address_pattern = re.compile(r'0x[a-fA-F0-9]{40}')
        
    def init_database(self):
        """Initialize database for scraped social data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraped_mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT,
                platform TEXT,
                username TEXT,
                display_name TEXT,
                profile_url TEXT,
                bio TEXT,
                mention_context TEXT,
                followers_estimate INTEGER,
                verified BOOLEAN,
                confidence_score INTEGER,
                scraped_at TIMESTAMP,
                evidence_url TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS identity_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT,
                claimed_name TEXT,
                platform TEXT,
                username TEXT,
                evidence_type TEXT,
                evidence_text TEXT,
                confidence INTEGER,
                verified BOOLEAN,
                created_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_random_headers(self):
        """Get randomized headers for scraping"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def scrape_twitter_search(self, address, max_results=20):
        """Scrape Twitter search results for ETH address mentions"""
        search_query = f'"{address}"'
        
        # Use multiple search strategies
        search_urls = [
            f"https://nitter.net/search?f=tweets&q={quote_plus(search_query)}",
            f"https://nitter.pussthecat.org/search?f=tweets&q={quote_plus(search_query)}",
            f"https://nitter.fdn.fr/search?f=tweets&q={quote_plus(search_query)}"
        ]
        
        mentions = []
        
        for nitter_url in search_urls:
            try:
                response = requests.get(nitter_url, headers=self.get_random_headers(), timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find tweet containers
                    tweets = soup.find_all('div', class_='tweet-content')
                    
                    for tweet in tweets[:max_results]:
                        try:
                            # Extract username and content
                            username_elem = tweet.find_previous('a', class_='username')
                            username = username_elem.get('href', '').strip('/') if username_elem else 'unknown'
                            
                            # Get tweet text
                            tweet_text = tweet.get_text(strip=True)
                            
                            # Check if address is actually mentioned
                            if address.lower() in tweet_text.lower():
                                mentions.append({
                                    'platform': 'twitter',
                                    'username': username,
                                    'content': tweet_text[:500],  # Limit content length
                                    'mention_type': 'post',
                                    'confidence': 70,
                                    'source_url': nitter_url
                                })
                        except Exception as e:
                            continue
                    
                    if mentions:
                        break  # Found results, no need to try other instances
                        
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                print(f"Error scraping {nitter_url}: {e}")
                continue
        
        return mentions
    
    def scrape_github_search(self, address):
        """Scrape GitHub for ETH address mentions"""
        search_url = f"https://github.com/search?q={quote_plus(address)}&type=code"
        
        mentions = []
        
        try:
            response = requests.get(search_url, headers=self.get_random_headers(), timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find code results
                results = soup.find_all('div', class_='f4 text-normal')
                
                for result in results[:10]:  # Limit results
                    try:
                        # Extract repository info
                        repo_link = result.find('a')
                        if repo_link:
                            repo_name = repo_link.get('href', '').strip('/')
                            
                            # Extract context around the address
                            code_snippet = result.get_text(strip=True)
                            
                            mentions.append({
                                'platform': 'github',
                                'username': repo_name.split('/')[0] if '/' in repo_name else repo_name,
                                'content': code_snippet[:300],
                                'repository': repo_name,
                                'mention_type': 'code',
                                'confidence': 60,
                                'source_url': f"https://github.com{repo_link.get('href', '')}"
                            })
                    except Exception as e:
                        continue
        
        except Exception as e:
            print(f"Error scraping GitHub: {e}")
        
        return mentions
    
    def scrape_reddit_search(self, address):
        """Scrape Reddit for ETH address mentions"""
        search_url = f"https://www.reddit.com/search/?q={quote_plus(address)}"
        
        mentions = []
        
        try:
            # Use old Reddit for easier scraping
            old_reddit_url = f"https://old.reddit.com/search?q={quote_plus(address)}"
            response = requests.get(old_reddit_url, headers=self.get_random_headers(), timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find search results
                results = soup.find_all('div', class_='search-result-listing')
                
                for result in results[:10]:
                    try:
                        # Extract post info
                        title_elem = result.find('a', class_='search-title')
                        author_elem = result.find('a', class_='author')
                        
                        if title_elem and author_elem:
                            title = title_elem.get_text(strip=True)
                            author = author_elem.get_text(strip=True)
                            post_url = title_elem.get('href', '')
                            
                            mentions.append({
                                'platform': 'reddit',
                                'username': author,
                                'content': title,
                                'mention_type': 'post',
                                'confidence': 50,
                                'source_url': post_url
                            })
                    except Exception as e:
                        continue
        
        except Exception as e:
            print(f"Error scraping Reddit: {e}")
        
        return mentions
    
    def scrape_etherscan_comments(self, address):
        """Scrape Etherscan for address comments and tags"""
        etherscan_url = f"https://etherscan.io/address/{address}"
        
        mentions = []
        
        try:
            response = requests.get(etherscan_url, headers=self.get_random_headers(), timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for name tag
                name_tag = soup.find('span', class_='text-muted')
                if name_tag and name_tag.get_text(strip=True):
                    tag_text = name_tag.get_text(strip=True)
                    
                    mentions.append({
                        'platform': 'etherscan',
                        'username': 'etherscan',
                        'content': f"Address tagged as: {tag_text}",
                        'mention_type': 'label',
                        'confidence': 90,  # Etherscan tags are usually accurate
                        'source_url': etherscan_url
                    })
                
                # Look for comments section
                comments = soup.find_all('div', class_='media-comment')
                for comment in comments[:5]:
                    try:
                        comment_text = comment.get_text(strip=True)
                        if len(comment_text) > 10:  # Filter out empty comments
                            mentions.append({
                                'platform': 'etherscan',
                                'username': 'community',
                                'content': comment_text[:200],
                                'mention_type': 'comment',
                                'confidence': 40,
                                'source_url': etherscan_url
                            })
                    except Exception as e:
                        continue
        
        except Exception as e:
            print(f"Error scraping Etherscan: {e}")
        
        return mentions
    
    def analyze_bio_for_addresses(self, bio_text):
        """Analyze social media bio for ETH addresses"""
        addresses = self.eth_address_pattern.findall(bio_text)
        return addresses
    
    def comprehensive_address_search(self, address):
        """Perform comprehensive search across all platforms"""
        print(f"🔍 Searching for {address[:10]}... across platforms")
        
        all_mentions = []
        
        # Twitter search
        print("  🐦 Searching Twitter...")
        twitter_mentions = self.scrape_twitter_search(address)
        all_mentions.extend(twitter_mentions)
        time.sleep(2)
        
        # GitHub search
        print("  📊 Searching GitHub...")
        github_mentions = self.scrape_github_search(address)
        all_mentions.extend(github_mentions)
        time.sleep(2)
        
        # Reddit search
        print("  🤖 Searching Reddit...")
        reddit_mentions = self.scrape_reddit_search(address)
        all_mentions.extend(reddit_mentions)
        time.sleep(2)
        
        # Etherscan
        print("  🔗 Checking Etherscan...")
        etherscan_mentions = self.scrape_etherscan_comments(address)
        all_mentions.extend(etherscan_mentions)
        
        # Store results in database
        if all_mentions:
            self.store_mentions(address, all_mentions)
        
        return all_mentions
    
    def store_mentions(self, address, mentions):
        """Store scraped mentions in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for mention in mentions:
            cursor.execute('''
                INSERT INTO scraped_mentions 
                (address, platform, username, mention_context, confidence_score, 
                 scraped_at, evidence_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                address,
                mention['platform'],
                mention['username'],
                mention['content'],
                mention['confidence'],
                datetime.now(),
                mention.get('source_url', '')
            ))
        
        conn.commit()
        conn.close()
    
    def search_known_personalities(self):
        """Search for known crypto personalities and their addresses"""
        # List of known crypto Twitter personalities to search
        crypto_personalities = [
            'VitalikButerin',
            'elonmusk', 
            'aantonop',
            'CryptoCobain',
            'DefiWhale',
            'WhaleStats',
            'lookonchain',
            'arkham_intel'
        ]
        
        personality_data = {}
        
        for personality in crypto_personalities:
            print(f"🕵️ Investigating @{personality}")
            
            # Search their recent tweets for ETH addresses
            nitter_url = f"https://nitter.net/{personality}"
            
            try:
                response = requests.get(nitter_url, headers=self.get_random_headers(), timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Get bio
                    bio_elem = soup.find('div', class_='profile-bio')
                    bio_text = bio_elem.get_text() if bio_elem else ''
                    
                    # Get recent tweets
                    tweets = soup.find_all('div', class_='tweet-content')
                    
                    addresses_found = []
                    
                    # Search bio for addresses
                    bio_addresses = self.analyze_bio_for_addresses(bio_text)
                    addresses_found.extend(bio_addresses)
                    
                    # Search tweets for addresses
                    for tweet in tweets[:20]:  # Check last 20 tweets
                        tweet_text = tweet.get_text()
                        tweet_addresses = self.analyze_bio_for_addresses(tweet_text)
                        addresses_found.extend(tweet_addresses)
                    
                    if addresses_found:
                        personality_data[personality] = {
                            'addresses': list(set(addresses_found)),  # Remove duplicates
                            'bio': bio_text,
                            'confidence': 80 if bio_addresses else 60  # Higher confidence if in bio
                        }
                        
                        print(f"  ✅ Found {len(set(addresses_found))} addresses")
                
                time.sleep(3)  # Rate limiting
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                continue
        
        return personality_data
    
    def generate_intelligence_report(self, address):
        """Generate intelligence report from scraped data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all mentions for this address
        cursor.execute('''
            SELECT * FROM scraped_mentions WHERE address = ?
            ORDER BY confidence_score DESC
        ''', (address,))
        
        mentions = cursor.fetchall()
        conn.close()
        
        if not mentions:
            return {"status": "no_data", "message": "No social mentions found"}
        
        # Analyze mentions
        platforms = set()
        usernames = set()
        high_confidence_mentions = []
        
        for mention in mentions:
            platforms.add(mention[2])  # platform
            usernames.add(mention[3])  # username
            
            if mention[6] > 70:  # confidence_score > 70
                high_confidence_mentions.append({
                    'platform': mention[2],
                    'username': mention[3],
                    'content': mention[5],
                    'confidence': mention[6],
                    'url': mention[9]
                })
        
        # Generate identity hypothesis
        identity_hypothesis = None
        if high_confidence_mentions:
            # Look for patterns in high confidence mentions
            etherscan_tags = [m for m in high_confidence_mentions if m['platform'] == 'etherscan']
            if etherscan_tags:
                identity_hypothesis = {
                    'name': etherscan_tags[0]['content'].replace('Address tagged as: ', ''),
                    'source': 'etherscan_tag',
                    'confidence': etherscan_tags[0]['confidence']
                }
        
        report = {
            'address': address,
            'total_mentions': len(mentions),
            'platforms_found': list(platforms),
            'unique_usernames': len(usernames),
            'high_confidence_mentions': high_confidence_mentions,
            'identity_hypothesis': identity_hypothesis,
            'social_footprint_score': min(len(mentions) * 10 + len(platforms) * 5, 100),
            'generated_at': datetime.now().isoformat()
        }
        
        return report

def main():
    """Test the social scraper"""
    print("🕵️ ETHhab Social Scraper Test")
    print("=" * 50)
    
    scraper = SocialScraper()
    
    # Test with a known address
    test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"  # Vitalik's address
    
    print(f"\\n🔍 Testing comprehensive search for: {test_address}")
    
    # Perform comprehensive search
    mentions = scraper.comprehensive_address_search(test_address)
    
    print(f"\\n📊 Results:")
    print(f"Total mentions found: {len(mentions)}")
    
    for mention in mentions:
        print(f"  {mention['platform']}: @{mention['username']} (confidence: {mention['confidence']}%)")
        print(f"    Content: {mention['content'][:100]}...")
        print()
    
    # Generate intelligence report
    report = scraper.generate_intelligence_report(test_address)
    
    print(f"\\n🎯 Intelligence Report:")
    print(f"Social Footprint Score: {report.get('social_footprint_score', 0)}/100")
    print(f"Platforms: {', '.join(report.get('platforms_found', []))}")
    
    if report.get('identity_hypothesis'):
        hypothesis = report['identity_hypothesis']
        print(f"Identity Hypothesis: {hypothesis['name']} (confidence: {hypothesis['confidence']}%)")

if __name__ == "__main__":
    main()