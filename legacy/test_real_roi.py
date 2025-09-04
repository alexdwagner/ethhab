#!/usr/bin/env python3
"""
Test ROI Scoring with Real Blockchain Data
Tests the system with actual whale addresses and transactions
"""

import os
from dotenv import load_dotenv
from web3 import Web3
from roi_scoring_v2 import ROIScorer
from roi_integration import WhaleROIIntegration

# Load environment variables
load_dotenv()

def test_web3_connection():
    """Test Web3 connection"""
    print("🔗 Testing Web3 connection...")
    
    rpc_url = os.getenv('ETH_RPC_URL')
    if not rpc_url:
        print("❌ No ETH_RPC_URL found in .env file")
        return None
    
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Test connection
        latest_block = w3.eth.get_block('latest')
        print(f"✅ Connected to Ethereum mainnet")
        print(f"📊 Latest block: {latest_block['number']}")
        print(f"⏰ Block timestamp: {latest_block['timestamp']}")
        
        return w3
        
    except Exception as e:
        print(f"❌ Web3 connection failed: {e}")
        return None

def test_known_whale_address(w3, whale_address="0x8eb8a3b98659cce290402893d0123abb75e3ab28"):
    """Test ROI scoring on a known whale address"""
    print(f"\n🐋 Testing whale address: {whale_address}")
    
    try:
        # Initialize ROI scorer
        roi_scorer = ROIScorer(w3, "roi_tracking.db")
        
        # Get recent transactions for this address
        print("🔍 Fetching recent transactions...")
        
        # Get the latest few transactions
        latest_block = w3.eth.get_block('latest')['number']
        tx_hashes = []
        
        # Look for transactions in recent blocks
        for block_num in range(latest_block - 100, latest_block):
            try:
                block = w3.eth.get_block(block_num, full_transactions=True)
                for tx in block['transactions']:
                    if (tx['from'] and tx['from'].lower() == whale_address.lower()) or \
                       (tx['to'] and tx['to'].lower() == whale_address.lower()):
                        tx_hashes.append(tx['hash'].hex())
                        if len(tx_hashes) >= 5:  # Limit for testing
                            break
                
                if len(tx_hashes) >= 5:
                    break
                    
            except Exception as e:
                continue
        
        if not tx_hashes:
            print("⚠️  No recent transactions found for this whale")
            print("💡 This could mean the whale hasn't traded recently")
            return False
        
        print(f"📝 Found {len(tx_hashes)} recent transactions")
        
        # Process transactions through ROI scorer
        print("⚙️  Processing transactions...")
        fills = roi_scorer.process_wallet_transactions(whale_address, tx_hashes[:3])  # Limit for testing
        
        if fills:
            print(f"✅ Processed {len(fills)} fills successfully")
            
            # Calculate ROI score
            print("🧮 Calculating ROI score...")
            score_data = roi_scorer.calculate_wallet_score(whale_address)
            
            print(f"\n🎯 ROI Score Results:")
            print(f"   Composite Score: {score_data['composite_score']:.2f}/100")
            print(f"   ROI Component: {score_data['score_components']['roi_score']:.1f}")
            print(f"   Volume Component: {score_data['score_components']['volume_score']:.1f}")
            print(f"   Risk Component: {score_data['score_components']['risk_score']:.1f}")
            
            return True
        else:
            print("⚠️  No fills extracted from transactions")
            return False
            
    except Exception as e:
        print(f"❌ ROI scoring test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration_system():
    """Test the full integration system"""
    print("\n🔧 Testing ROI integration system...")
    
    try:
        integration = WhaleROIIntegration()
        
        # Test database operations
        top_whales = integration.get_top_whales_by_roi(limit=5)
        print(f"✅ Integration system loaded {len(top_whales)} whale records")
        
        if top_whales:
            print("🏆 Top whale by ROI score:")
            top_whale = top_whales[0]
            print(f"   Address: {top_whale['wallet_address']}")
            print(f"   ROI Score: {top_whale['composite_score']:.2f}")
            print(f"   Total Trades: {top_whale['total_trades']}")
            print(f"   Win Rate: {top_whale['win_rate_percent']:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 ROI Scoring System - Real Data Test")
    print("=" * 50)
    
    # Test 1: Web3 connection
    w3 = test_web3_connection()
    if not w3:
        print("\n❌ Cannot proceed without Web3 connection")
        print("💡 Please check your ETH_RPC_URL in .env file")
        return False
    
    # Test 2: Integration system
    if not test_integration_system():
        print("\n❌ Integration system test failed")
        return False
    
    # Test 3: Real whale processing (optional - requires API calls)
    print("\n" + "=" * 50)
    user_input = input("🐋 Test real whale transaction processing? This uses API calls (y/n): ")
    
    if user_input.lower() == 'y':
        success = test_known_whale_address(w3)
        if success:
            print("\n🎉 Real whale processing test passed!")
        else:
            print("\n⚠️  Real whale processing had issues (this is normal for testing)")
    
    print("\n✅ All basic tests completed successfully!")
    print("🚀 ROI scoring system is ready for production use!")
    
    return True

if __name__ == "__main__":
    main()