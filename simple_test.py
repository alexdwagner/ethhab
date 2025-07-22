#!/usr/bin/env python3
import os
from dotenv import load_dotenv

# Test if we can at least load the environment
load_dotenv()

print("🐋 ETHhab Basic Test")
print("=" * 30)

# Test API keys
alchemy_key = os.getenv('ALCHEMY_API_KEY')
etherscan_key = os.getenv('ETHERSCAN_API_KEY')

if alchemy_key:
    print(f"✅ Alchemy API key: {alchemy_key[:10]}...")
else:
    print("❌ Alchemy API key missing")

if etherscan_key:
    print(f"✅ Etherscan API key: {etherscan_key[:10]}...")
else:
    print("❌ Etherscan API key missing")

# Test if we can create a simple database
try:
    import sqlite3
    conn = sqlite3.connect('test.db')
    conn.execute('CREATE TABLE IF NOT EXISTS test (id INTEGER)')
    conn.close()
    print("✅ SQLite database works")
    os.remove('test.db')
except Exception as e:
    print(f"❌ Database error: {e}")

print("\n🎯 Ready to install remaining packages!")
print("Run: python3 -m pip install requests web3 --user")