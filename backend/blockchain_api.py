import asyncio
import aiohttp
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Transaction:
    """Data class representing a blockchain transaction"""
    hash: str
    block_number: int
    timestamp: datetime
    from_address: str
    to_address: str
    value: float  # in ETH
    gas_used: int
    gas_price: int
    input_data: str
    is_error: bool = False
    
    @classmethod
    def from_etherscan_data(cls, data: Dict[str, Any]) -> 'Transaction':
        """Create Transaction from Etherscan API response"""
        return cls(
            hash=data.get('hash', ''),
            block_number=int(data.get('blockNumber', 0)),
            timestamp=datetime.fromtimestamp(int(data.get('timeStamp', 0)), timezone.utc),
            from_address=data.get('from', ''),
            to_address=data.get('to', ''),
            value=float(data.get('value', 0)) / 1e18,  # Convert wei to ETH
            gas_used=int(data.get('gasUsed', 0)),
            gas_price=int(data.get('gasPrice', 0)),
            input_data=data.get('input', ''),
            is_error=data.get('isError', '0') == '1'
        )

class EtherscanAPI:
    """Ethereum blockchain data provider using Etherscan API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.etherscan.io/api"
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_delay = 0.2  # 5 requests per second limit
        self.last_request_time = 0
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'TrustLens.AI/1.0'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _rate_limit(self):
        """Implement rate limiting to respect API limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        
        self.last_request_time = time.time()
    
    async def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to Etherscan API with rate limiting and error handling"""
        await self._rate_limit()
        
        # Add API key to params
        params['apikey'] = self.api_key
        
        if not self.session:
            raise RuntimeError("API session not initialized. Use async context manager.")
        
        try:
            async with self.session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {await response.text()}")
                
                data = await response.json()
                
                if data.get('status') != '1':
                    error_msg = data.get('message', 'Unknown error')
                    if error_msg == 'No transactions found':
                        # This is not an error, just empty result
                        return {'status': '1', 'result': []}
                    raise Exception(f"API Error: {error_msg}")
                
                return data
                
        except aiohttp.ClientError as e:
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            raise
    
    async def get_account_balance(self, address: str) -> float:
        """Get the current ETH balance of an address"""
        params = {
            'module': 'account',
            'action': 'balance',
            'address': address,
            'tag': 'latest'
        }
        
        try:
            data = await self._make_request(params)
            balance_wei = int(data['result'])
            balance_eth = balance_wei / 1e18
            
            logger.info(f"Balance for {address}: {balance_eth:.6f} ETH")
            return balance_eth
            
        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {str(e)}")
            raise
    
    async def get_transaction_list(self, address: str, limit: int = 100, 
                                   start_block: int = 0, end_block: int = 99999999) -> List[Transaction]:
        """Get list of transactions for an address"""
        params = {
            'module': 'account',
            'action': 'txlist',
            'address': address,
            'startblock': start_block,
            'endblock': end_block,
            'page': 1,
            'offset': min(limit, 10000),  # Etherscan max is 10,000
            'sort': 'desc'  # Most recent first
        }
        
        try:
            data = await self._make_request(params)
            transactions = []
            
            for tx_data in data.get('result', []):
                try:
                    tx = Transaction.from_etherscan_data(tx_data)
                    transactions.append(tx)
                except Exception as e:
                    logger.warning(f"Failed to parse transaction {tx_data.get('hash', 'unknown')}: {str(e)}")
                    continue
            
            logger.info(f"Retrieved {len(transactions)} transactions for {address}")
            return transactions
            
        except Exception as e:
            logger.error(f"Failed to get transactions for {address}: {str(e)}")
            raise
    
    async def get_internal_transactions(self, address: str, limit: int = 100) -> List[Transaction]:
        """Get internal transactions (contract interactions)"""
        params = {
            'module': 'account',
            'action': 'txlistinternal',
            'address': address,
            'page': 1,
            'offset': min(limit, 10000),
            'sort': 'desc'
        }
        
        try:
            data = await self._make_request(params)
            transactions = []
            
            for tx_data in data.get('result', []):
                try:
                    tx = Transaction.from_etherscan_data(tx_data)
                    transactions.append(tx)
                except Exception as e:
                    logger.warning(f"Failed to parse internal transaction: {str(e)}")
                    continue
            
            logger.info(f"Retrieved {len(transactions)} internal transactions for {address}")
            return transactions
            
        except Exception as e:
            logger.error(f"Failed to get internal transactions for {address}: {str(e)}")
            # Don't raise for internal transactions - they're optional
            return []
    
    async def get_erc20_transfers(self, address: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get ERC-20 token transfers"""
        params = {
            'module': 'account',
            'action': 'tokentx',
            'address': address,
            'page': 1,
            'offset': min(limit, 10000),
            'sort': 'desc'
        }
        
        try:
            data = await self._make_request(params)
            transfers = data.get('result', [])
            
            logger.info(f"Retrieved {len(transfers)} ERC-20 transfers for {address}")
            return transfers
            
        except Exception as e:
            logger.error(f"Failed to get ERC-20 transfers for {address}: {str(e)}")
            # Don't raise for token transfers - they're optional
            return []
    
    async def get_contract_info(self, address: str) -> Optional[Dict[str, Any]]:
        """Check if address is a contract and get basic info"""
        params = {
            'module': 'contract',
            'action': 'getsourcecode',
            'address': address
        }
        
        try:
            data = await self._make_request(params)
            result = data.get('result', [])
            
            if result and result[0].get('SourceCode'):
                return {
                    'is_contract': True,
                    'name': result[0].get('ContractName', ''),
                    'compiler': result[0].get('CompilerVersion', ''),
                    'verified': True
                }
            else:
                # Check if it's an unverified contract by looking at code
                code_params = {
                    'module': 'proxy',
                    'action': 'eth_getCode',
                    'address': address,
                    'tag': 'latest'
                }
                
                code_data = await self._make_request(code_params)
                code = code_data.get('result', '0x')
                
                return {
                    'is_contract': code != '0x' and len(code) > 2,
                    'name': '',
                    'compiler': '',
                    'verified': False
                }
                
        except Exception as e:
            logger.error(f"Failed to get contract info for {address}: {str(e)}")
            return None

# Utility functions
async def validate_ethereum_address(address: str) -> bool:
    """Validate if address is a valid Ethereum address"""
    if not address or not isinstance(address, str):
        return False
    
    # Remove 0x prefix if present
    if address.startswith('0x'):
        address = address[2:]
    
    # Check length (40 hex characters)
    if len(address) != 40:
        return False
    
    # Check if all characters are hex
    try:
        int(address, 16)
        return True
    except ValueError:
        return False

async def get_address_summary(api_key: str, address: str) -> Dict[str, Any]:
    """Get a comprehensive summary of an address"""
    if not await validate_ethereum_address(address):
        raise ValueError(f"Invalid Ethereum address: {address}")
    
    async with EtherscanAPI(api_key) as etherscan:
        # Get basic data
        balance = await etherscan.get_account_balance(address)
        transactions = await etherscan.get_transaction_list(address, limit=50)
        
        # Optional data (don't fail if these don't work)
        internal_txs = []
        erc20_transfers = []
        contract_info = None
        
        try:
            internal_txs = await etherscan.get_internal_transactions(address, limit=50)
        except:
            pass
        
        try:
            erc20_transfers = await etherscan.get_erc20_transfers(address, limit=50)
        except:
            pass
        
        try:
            contract_info = await etherscan.get_contract_info(address)
        except:
            pass
        
        return {
            'address': address,
            'balance': balance,
            'transaction_count': len(transactions),
            'transactions': transactions,
            'internal_transactions': internal_txs,
            'erc20_transfers': erc20_transfers,
            'contract_info': contract_info,
            'is_contract': contract_info.get('is_contract', False) if contract_info else False
        }

# Test function
async def test_api():
    """Test the API functionality"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv('ETHERSCAN_API_KEY')
    
    if not api_key:
        print("❌ No API key found in environment variables")
        return
    
    test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"  # Vitalik's address
    
    try:
        async with EtherscanAPI(api_key) as etherscan:
            print(f"Testing API with address: {test_address}")
            
            # Test balance
            balance = await etherscan.get_account_balance(test_address)
            print(f"✅ Balance: {balance:.4f} ETH")
            
            # Test transactions
            txs = await etherscan.get_transaction_list(test_address, limit=5)
            print(f"✅ Transactions: {len(txs)} found")
            
            if txs:
                latest = txs[0]
                print(f"   Latest: {latest.hash[:10]}... ({latest.value:.4f} ETH)")
                print(f"   Date: {latest.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            print("🎉 API test successful!")
            
    except Exception as e:
        print(f"❌ API test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_api())
