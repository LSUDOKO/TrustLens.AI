#!/usr/bin/env python3
"""
Debug the scoring system to see why it's returning 0
"""
import asyncio
import os
from dotenv import load_dotenv
from scoring import analyze_wallet

async def debug_scoring():
    load_dotenv()
    api_key = os.getenv("ETHERSCAN_API_KEY")
    
    test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    
    print(f"🔍 Debugging scoring for {test_address}")
    print("=" * 60)
    
    try:
        result = await analyze_wallet(test_address, api_key)
        
        print("📊 Full Analysis Result:")
        print(f"   Trust Score: {result.get('trust_score', 'NOT FOUND')}")
        print(f"   Risk Level: {result.get('risk_level', 'NOT FOUND')}")
        print(f"   Confidence: {result.get('confidence', 'NOT FOUND')}")
        
        print("\n🔧 Component Scores:")
        components = result.get('component_scores', {})
        for component, score in components.items():
            print(f"   {component}: {score}")
        
        print("\n📈 Raw Metrics:")
        raw_metrics = result.get('raw_metrics', {})
        for key, value in raw_metrics.items():
            if key != 'address':
                print(f"   {key}: {value}")
        
        print("\n⚠️ Risk Factors:")
        risk_factors = result.get('risk_factors', [])
        for factor in risk_factors:
            print(f"   - {factor}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_scoring())