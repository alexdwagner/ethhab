#!/usr/bin/env python3
"""
ETHhab Test Script
Quick test to verify your whale tracking setup
"""

def test_imports():
    """Test if all required packages are installed"""
    try:
        import requests
        import web3
        import sqlalchemy
        import pandas
        import streamlit
        print("✅ All packages imported successfully!")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_api_keys():
    """Test if API keys are configured"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    alchemy_key = os.getenv('ALCHEMY_API_KEY')
    etherscan_key = os.getenv('ETHERSCAN_API_KEY')
    
    if not alchemy_key:
        print("❌ ALCHEMY_API_KEY not found in .env")
        return False
    
    if not etherscan_key:
        print("❌ ETHERSCAN_API_KEY not found in .env")
        return False
    
    print("✅ API keys configured!")
    return True

def test_database():
    """Test database connection"""
    try:
        from database import DatabaseManager
        db = DatabaseManager()
        print("✅ Database connection successful!")
        db.close()
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_web3_connection():
    """Test Web3 connection to Ethereum"""
    try:
        from web3 import Web3
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        alchemy_key = os.getenv('ALCHEMY_API_KEY')
        alchemy_url = f"https://eth-mainnet.g.alchemy.com/v2/{alchemy_key}"
        
        w3 = Web3(Web3.HTTPProvider(alchemy_url))
        
        if w3.is_connected():
            latest_block = w3.eth.block_number
            print(f"✅ Connected to Ethereum! Latest block: {latest_block}")
            return True
        else:
            print("❌ Failed to connect to Ethereum")
            return False
    except Exception as e:
        print(f"❌ Web3 connection error: {e}")
        return False

def main():
    print("🐋 ETHhab Setup Test")
    print("=" * 50)
    
    tests = [
        ("Package Imports", test_imports),
        ("API Keys", test_api_keys),
        ("Database", test_database),
        ("Ethereum Connection", test_web3_connection)
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n🧪 Testing {name}...")
        if test_func():
            passed += 1
        else:
            print(f"   Fix this before running ETHhab!")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 ETHhab is ready to hunt whales!")
        print("\nNext steps:")
        print("1. Run: python3 whale_scanner.py")
        print("2. Run: streamlit run dashboard.py")
    else:
        print("❌ Fix the failing tests above before proceeding")

if __name__ == "__main__":
    main()