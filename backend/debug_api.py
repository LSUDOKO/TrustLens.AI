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
        
        api_key = os.getenv('ETHERSCAN_API_KEY')
        
        # Directly call with the new signature
        result = await analyze_wallet(test_address, api_key=api_key)
        
        # Check the result structure
        trust_score = result.get('trust_score', 0)
        risk_level = result.get('risk_level', 'unknown')
        confidence = result.get('confidence', 0.0)
        raw_metrics = result.get('raw_metrics', {})
        data_source = raw_metrics.get('data_source', 'unknown')
        component_scores = result.get('component_scores', {})
        
        print(f"✅ Analysis completed successfully!")
        print(f"Data Source: {'🔗 REAL BLOCKCHAIN DATA' if data_source == 'real' else '🎭 SIMULATED DATA'}")
        print(f"Trust Score: {trust_score}/100")
        print(f"Risk Level: {risk_level}")
        print(f"Confidence: {confidence:.3f}")
        
        # Show component scores
        print("Component Scores:")
        for component, score in component_scores.items():
            print(f"  {component.capitalize()}: {score}/100")
        
        # Show key metrics
        if 'current_balance' in raw_metrics:
            print(f"Balance: {raw_metrics['current_balance']:.4f} ETH")
        if 'total_transactions' in raw_metrics:
            print(f"Transactions: {raw_metrics['total_transactions']}")
        if 'wallet_age' in raw_metrics:
            print(f"Age: {raw_metrics['wallet_age']} days")
        if 'unique_counterparties' in raw_metrics:
            print(f"Unique Addresses: {raw_metrics['unique_counterparties']}")
        
        # Show risk factors if any
        risk_factors = result.get('risk_factors', [])
        if risk_factors:
            print(f"\nRisk Factors: {len(risk_factors)} identified")
            for rf in risk_factors[:3]:  # Show first 3
                severity = rf.get('severity', 'unknown')
                description = rf.get('description', 'Unknown risk')
                print(f"  • [{severity.upper()}] {description}")
        else:
            print("\nRisk Factors: None identified")
        
        return data_source == 'real'
        
    except Exception as e:
        print(f"❌ Scoring integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_multiple_addresses():
    """Test multiple addresses to verify consistency"""
    print("\n🔍 Multiple Address Test")
    print("=" * 50)
    
    test_addresses = [
        ("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "Vitalik Buterin"),
        ("0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE", "Binance Hot Wallet"),
        ("0x742d35Cc6634C0532925a3b8D400B7fb56AE0D9C", "Null Address")
    ]
    
    results = []
    api_key = os.getenv('ETHERSCAN_API_KEY')
    
    try:
        from scoring import analyze_wallet
        
        for address, name in test_addresses:
            print(f"\nTesting {name}: {address[:10]}...")
            try:
                result = await analyze_wallet(address, api_key=api_key)
                
                score = result.get('trust_score', 0)
                risk_level = result.get('risk_level', 'unknown')
                data_source = result.get('raw_metrics', {}).get('data_source', 'unknown')
                
                print(f"  Score: {score}/100 | Risk: {risk_level} | Source: {data_source}")
                results.append((name, score, data_source == 'real'))
                
            except Exception as e:
                print(f"  ❌ Failed: {str(e)}")
                results.append((name, 0, False))
        
        # Summary
        real_data_count = sum(1 for _, _, is_real in results if is_real)
        print(f"\nSummary: {real_data_count}/{len(results)} addresses used real data")
        
        return real_data_count > 0
        
    except Exception as e:
        print(f"❌ Multiple address test failed: {str(e)}")
        return False

async def benchmark_performance():
    """Benchmark the scoring system performance"""
    print("\n⚡ Performance Benchmark")
    print("=" * 50)
    
    try:
        import time
        from scoring import analyze_wallet
        
        test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        api_key = os.getenv('ETHERSCAN_API_KEY')
        
        print("Running performance test...")
        start_time = time.time()
        
        # Directly call with the new signature
        result = await analyze_wallet(test_address, api_key=api_key)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Analysis completed in {duration:.2f} seconds")
        
        # Performance thresholds
        if duration < 5.0:
            print("🚀 Excellent performance!")
            return True
        elif duration < 10.0:
            print("✅ Good performance")
            return True
        elif duration < 20.0:
            print("⚠️  Acceptable performance")
            return True
        else:
            print("❌ Slow performance - may need optimization")
            return False
            
    except Exception as e:
        print(f"❌ Performance test failed: {str(e)}")
        return False

async def main():
    """Main debug function"""
    print("🚀 TrustLens.AI Enhanced API Debug Tool")
    print("=" * 60)
    
    # Step 1: Check environment configuration
    env_ok = check_env_config()
    
    if not env_ok:
        print("\n🛑 Cannot proceed without proper API configuration")
        return
    
    # Step 2: Test direct API access
    api_ok = await test_etherscan_direct()
    
    if not api_ok:
        print("\n🛑 Direct API test failed - but continuing with integration tests")
        # Don't return here - let's see if integration still works
    
    # Step 3: Test scoring integration
    integration_ok = await test_scoring_integration()
    
    # Step 4: Test multiple addresses
    multiple_ok = await test_multiple_addresses()
    
    # Step 5: Performance benchmark
    perf_ok = await benchmark_performance()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 COMPREHENSIVE DEBUG SUMMARY")
    print("=" * 60)
    print(f"Environment Config: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"Direct API Test: {'✅ PASS' if api_ok else '❌ FAIL'}")
    print(f"Integration Test: {'✅ PASS' if integration_ok else '❌ FAIL'}")
    print(f"Multiple Address Test: {'✅ PASS' if multiple_ok else '❌ FAIL'}")
    print(f"Performance Test: {'✅ PASS' if perf_ok else '❌ FAIL'}")
    
    if env_ok and integration_ok:
        print("\n🎉 CORE FUNCTIONALITY WORKING!")
        if api_ok and multiple_ok and perf_ok:
            print("🌟 EXCELLENT - ALL SYSTEMS OPERATIONAL WITH REAL DATA!")
        else:
            print("⚠️  Some advanced features need attention, but basic scoring works.")
        
        print("\n🔧 Next Steps:")
        print("1. Your scoring system is now properly integrated")
        print("2. WalletMetrics class has been defined and implemented")
        print("3. Real blockchain data is being fetched and processed")
        print("4. You can now run your main application!")
        
    else:
        print("\n❌ CRITICAL ISSUES DETECTED")
        print("Please fix the issues above before proceeding.")

if __name__ == "__main__":
    asyncio.run(main())