#!/usr/bin/env python3
"""
Test script for TrustLens.AI blockchain integration
Tests both real API and fallback modes
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scoring import analyze_wallet
from blockchain_api import create_blockchain_analyzer

async def test_wallet_analysis():
    """Test wallet analysis with different scenarios"""
    
    print("🔍 TrustLens.AI Integration Test")
    print("=" * 50)
    
    # Test addresses (well-known Ethereum addresses)
    test_addresses = [
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",  # Vitalik Buterin
        "0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE",  # Binance hot wallet
        "0x742d35Cc6634C0532925a3b8D4C4C6E4e7c8c9B2"   # Random address for testing
    ]
    
    # Check if we have real API access
    analyzer = create_blockchain_analyzer()
    if analyzer:
        print("✅ Etherscan API key found - testing with REAL data")
        data_mode = "REAL"
    else:
        print("⚠️  No Etherscan API key - testing with SIMULATED data")
        data_mode = "SIMULATED"
    
    print(f"🌐 Data Mode: {data_mode}")
    print("-" * 50)
    
    for i, address in enumerate(test_addresses, 1):
        print(f"\n🔎 Test {i}: Analyzing {address[:8]}...")
        
        try:
            # Analyze the wallet
            result = await analyze_wallet(address)
            
            # Extract key information
            trust_score = result['analysis']['trust_score']
            risk_level = result['analysis']['risk_level']
            confidence = result['analysis']['confidence']
            
            # Check data source
            raw_metrics = result.get('raw_metrics', {})
            is_real_data = raw_metrics.get('is_real_data', False)
            data_freshness = raw_metrics.get('data_freshness', 0.0)
            
            # Display results
            print(f"   📊 Trust Score: {trust_score}/100")
            print(f"   ⚠️  Risk Level: {risk_level}")
            print(f"   🎯 Confidence: {confidence:.1%}")
            print(f"   📡 Data Source: {'Real Blockchain' if is_real_data else 'Simulated'}")
            print(f"   🔄 Data Freshness: {data_freshness:.1%}")
            
            # Show some key metrics
            if 'balance_eth' in raw_metrics:
                print(f"   💰 Balance: {raw_metrics['balance_eth']:.4f} ETH")
            if 'tx_count' in raw_metrics:
                print(f"   📈 Transactions: {raw_metrics['tx_count']:,}")
            if 'age_days' in raw_metrics:
                print(f"   📅 Wallet Age: {raw_metrics['age_days']} days")
            
            # Show identity and risk tags
            identity_tags = result.get('identity_tags', [])
            risk_tags = result.get('risk_tags', [])
            
            if identity_tags:
                print(f"   🆔 Identity: {', '.join(identity_tags[:3])}")
            if risk_tags:
                print(f"   🚨 Risk Factors: {', '.join(risk_tags[:3])}")
            
            print(f"   ✅ Analysis completed successfully")
            
        except Exception as e:
            print(f"   ❌ Error analyzing {address[:8]}: {str(e)}")
            continue
    
    print("\n" + "=" * 50)
    print("🎉 Integration test completed!")
    
    # Summary
    print(f"\n📋 Summary:")
    print(f"   • Data Mode: {data_mode}")
    print(f"   • API Integration: {'Working' if analyzer else 'Fallback Mode'}")
    print(f"   • Test Addresses: {len(test_addresses)}")
    
    if data_mode == "SIMULATED":
        print(f"\n💡 To enable real data:")
        print(f"   1. Get free API key from https://etherscan.io/apis")
        print(f"   2. Add to .env: ETHERSCAN_API_KEY=your_key_here")
        print(f"   3. Restart the application")

async def test_api_connectivity():
    """Test direct API connectivity"""
    print("\n🔌 Testing API Connectivity")
    print("-" * 30)
    
    analyzer = create_blockchain_analyzer()
    if not analyzer:
        print("❌ No API key configured")
        return
    
    try:
        # Test with a simple API call
        async with analyzer.etherscan:
            balance = await analyzer.etherscan.get_account_balance("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
            print(f"✅ API connectivity test passed")
            print(f"   Sample balance query: {balance:.4f} ETH")
    except Exception as e:
        print(f"❌ API connectivity test failed: {e}")

if __name__ == "__main__":
    print("Starting TrustLens.AI integration tests...\n")
    
    # Run the tests
    asyncio.run(test_wallet_analysis())
    asyncio.run(test_api_connectivity())
    
    print("\n🏁 All tests completed!")
