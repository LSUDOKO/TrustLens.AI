#!/usr/bin/env python3
"""
Test script to verify Etherscan API connectivity
"""
import asyncio
import os
from dotenv import load_dotenv
from blockchain_api import EtherscanAPI

async def test_etherscan():
    load_dotenv()
    api_key = os.getenv("ETHERSCAN_API_KEY")
    
    if not api_key:
        print("❌ No ETHERSCAN_API_KEY found in .env file")
        return
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    try:
        async with EtherscanAPI(api_key) as etherscan:
            print("🔍 Testing API connection...")
            
            # Test with a known wallet address
            test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
            
            # Get balance
            balance = await etherscan.get_account_balance(test_address)
            print(f"💰 Balance: {balance} ETH")
            
            # Get transactions
            transactions = await etherscan.get_transaction_list(test_address, limit=5)
            print(f"📊 Found {len(transactions)} transactions")
            
            if transactions:
                print("✅ Etherscan API is working correctly!")
                print(f"   Latest transaction: {transactions[0].hash}")
            else:
                print("⚠️ No transactions found, but API is responding")
                
    except Exception as e:
        print(f"❌ Etherscan API error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_etherscan())