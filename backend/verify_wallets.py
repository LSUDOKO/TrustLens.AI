#!/usr/bin/env python3
"""
Verify wallet data accuracy by checking multiple addresses
"""
import asyncio
import os
from dotenv import load_dotenv
from blockchain_api import EtherscanAPI

async def verify_wallet_data():
    load_dotenv()
    api_key = os.getenv("ETHERSCAN_API_KEY")
    
    # Wallet addresses from your tests
    test_wallets = [
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        "0xa0D53dE6f036D8cffB7168e68b9D5dd0550ee650", 
        "0xDB65702A9b26f8a643a31a4c84b9392589e03D7c"
    ]
    
    async with EtherscanAPI(api_key) as etherscan:
        for address in test_wallets:
            print(f"\n🔍 Checking {address}")
            print("-" * 60)
            
            try:
                # Get balance
                balance = await etherscan.get_account_balance(address)
                print(f"💰 Balance: {balance:.4f} ETH")
                
                # Get transactions
                transactions = await etherscan.get_transaction_list(address, limit=100)
                print(f"📊 Total Transactions: {len(transactions)}")
                
                if transactions:
                    # Calculate wallet age
                    oldest_tx = min(transactions, key=lambda tx: tx.timestamp)
                    newest_tx = max(transactions, key=lambda tx: tx.timestamp)
                    
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)
                    wallet_age = (now - oldest_tx.timestamp).days
                    last_activity = (now - newest_tx.timestamp).days
                    
                    print(f"⏰ Wallet Age: {wallet_age} days")
                    print(f"📅 Last Activity: {last_activity} days ago")
                    
                    # Count unique counterparties
                    counterparties = set()
                    for tx in transactions:
                        if tx.from_address.lower() != address.lower():
                            counterparties.add(tx.from_address.lower())
                        if tx.to_address.lower() != address.lower():
                            counterparties.add(tx.to_address.lower())
                    
                    print(f"👥 Unique Counterparties: {len(counterparties)}")
                    print(f"🔗 Latest TX: {transactions[0].hash}")
                else:
                    print("📭 No transactions found")
                    
            except Exception as e:
                print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(verify_wallet_data())