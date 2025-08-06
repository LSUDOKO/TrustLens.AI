#!/usr/bin/env python3
"""
Debug script to check API configuration and test real blockchain data
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_env_config():
    """Check environment configuration"""
    print("🔍 Environment Configuration Check")
    print("=" * 50)
    
    # Check for API keys
    etherscan_key = os.getenv('ETHERSCAN_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    print(f"ETHERSCAN_API_KEY: {'✅ SET' if etherscan_key and etherscan_key != 'YOUR_ETHERSCAN_API_KEY_HERE' else '❌ NOT SET'}")
    print(f"OPENAI_API_KEY: {'✅ SET' if openai_key and openai_key != 'YOUR_API_KEY_HERE' else '❌ NOT SET'}")
    
    if etherscan_key and etherscan_key != 'YOUR_ETHERSCAN_API_KEY_HERE':
        print(f"Etherscan Key (first 8 chars): {etherscan_key[:8]}...")
        return True
    else:
        print("\n❌ ETHERSCAN_API_KEY is not properly configured!")
        print("To fix this:")
        print("1. Get a free API key from https://etherscan.io/apis")
        print("2. Open your .env file")
        print("3. Replace 'YOUR_ETHERSCAN_API_KEY_HERE' with your actual key")
        print("4. Restart the application")
        return False

async def test_etherscan_direct():
    """Test Etherscan API directly"""
    print("\n🔌 Direct Etherscan API Test")
    print("=" * 50)
    
    try:
        from blockchain_api import EtherscanAPI
        
        api_key = os.getenv('ETHERSCAN_API_KEY')
        if not api_key or api_key == 'YOUR_ETHERSCAN_API_KEY_HERE':
            print("❌ No valid API key found")
            return False
        
        async with EtherscanAPI(api_key) as etherscan:
            # Test with Vitalik's address
            test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
            print(f"Testing with address: {test_address}")
            
            # Test balance fetch
            balance = await etherscan.get_account_balance(test_address)
            print(f"✅ Balance fetched: {balance:.4f} ETH")
            
            # Test transaction fetch
            transactions = await etherscan.get_transaction_list(test_address, limit=5)
            print(f"✅ Transactions fetched: {len(transactions)} transactions")
            
            if transactions:
                latest_tx = transactions[0]
                print(f"   Latest TX: {latest_tx.hash[:10]}... ({latest_tx.value:.4f} ETH)")
            
            return True
            
    except Exception as e:
        print(f"❌ Direct API test failed: {str(e)}")
        return False

async def test_scoring_integration():
    """Test the scoring system integration"""
    print("\n🎯 Scoring System Integration Test")
    print("=" * 50)
    
    try:
        from scoring import analyze_wallet
        
        # Test with a known address
        test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        print(f"Analyzing: {test_address}")
        
        result = await analyze_wallet(test_address)
        
        # Check if we got real data
        raw_metrics = result.get('raw_metrics', {})
        is_real_data = raw_metrics.get('is_real_data', False)
        data_freshness = raw_metrics.get('data_freshness', 0.0)
        
        print(f"Data Source: {'✅ REAL BLOCKCHAIN DATA' if is_real_data else '❌ SIMULATED DATA'}")
        print(f"Data Freshness: {data_freshness:.1%}")
        print(f"Trust Score: {result['analysis']['trust_score']}/100")
        
        if 'balance_eth' in raw_metrics:
            print(f"Balance: {raw_metrics['balance_eth']:.4f} ETH")
        if 'tx_count' in raw_metrics:
            print(f"Transactions: {raw_metrics['tx_count']:,}")
        if 'age_days' in raw_metrics:
            print(f"Age: {raw_metrics['age_days']} days")
        
        return is_real_data
        
    except Exception as e:
        print(f"❌ Scoring integration test failed: {str(e)}")
        return False

async def main():
    """Main debug function"""
    print("🚀 TrustLens.AI API Debug Tool")
    print("=" * 60)
    
    # Step 1: Check environment configuration
    env_ok = check_env_config()
    
    if not env_ok:
        print("\n🛑 Cannot proceed without proper API configuration")
        return
    
    # Step 2: Test direct API access
    api_ok = await test_etherscan_direct()
    
    if not api_ok:
        print("\n🛑 Direct API test failed")
        return
    
    # Step 3: Test scoring integration
    integration_ok = await test_scoring_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 DEBUG SUMMARY")
    print("=" * 60)
    print(f"Environment Config: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"Direct API Test: {'✅ PASS' if api_ok else '❌ FAIL'}")
    print(f"Integration Test: {'✅ PASS' if integration_ok else '❌ FAIL'}")
    
    if env_ok and api_ok and integration_ok:
        print("\n🎉 ALL TESTS PASSED! Your system is using REAL blockchain data!")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    asyncio.run(main())
