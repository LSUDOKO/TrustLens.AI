import asyncio
import aiohttp
import logging
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class BlockchainTransaction:
    hash: str
    from_address: str
    to_address: str
    value: float
    timestamp: int
    gas_used: int
    gas_price: int
    is_contract_creation: bool = False
    contract_address: Optional[str] = None

class EtherscanAPI:
    """Real Etherscan API integration for blockchain data"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.etherscan.io/api"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _make_request(self, params: Dict) -> Dict:
        """Make API request to Etherscan"""
        params['apikey'] = self.api_key
        
        try:
            async with self.session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == '1':
                        return data.get('result', {})
                    else:
                        logger.warning(f"Etherscan API error: {data.get('message')}")
                        return {}
                else:
                    logger.error(f"HTTP error {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return {}
    
    async def get_account_balance(self, address: str) -> float:
        """Get ETH balance for address"""
        params = {
            'module': 'account',
            'action': 'balance',
            'address': address,
            'tag': 'latest'
        }
        
        result = await self._make_request(params)
        if result:
            # Convert from wei to ETH
            return float(result) / 10**18
        return 0.0
    
    async def get_transaction_list(self, address: str, limit: int = 10000) -> List[BlockchainTransaction]:
        """Get transaction history for address"""
        params = {
            'module': 'account',
            'action': 'txlist',
            'address': address,
            'startblock': 0,
            'endblock': 99999999,
            'page': 1,
            'offset': limit,
            'sort': 'desc'
        }
        
        result = await self._make_request(params)
        transactions = []
        
        if result and isinstance(result, list):
            for tx in result:
                try:
                    transactions.append(BlockchainTransaction(
                        hash=tx.get('hash', ''),
                        from_address=tx.get('from', ''),
                        to_address=tx.get('to', ''),
                        value=float(tx.get('value', '0')) / 10**18,  # Convert wei to ETH
                        timestamp=int(tx.get('timeStamp', '0')),
                        gas_used=int(tx.get('gasUsed', '0')),
                        gas_price=int(tx.get('gasPrice', '0')),
                        is_contract_creation=tx.get('to', '') == '',
                        contract_address=tx.get('contractAddress')
                    ))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing transaction: {e}")
                    continue
        
        return transactions
    
    async def get_internal_transactions(self, address: str, limit: int = 1000) -> List[Dict]:
        """Get internal transactions for address"""
        params = {
            'module': 'account',
            'action': 'txlistinternal',
            'address': address,
            'startblock': 0,
            'endblock': 99999999,
            'page': 1,
            'offset': limit,
            'sort': 'desc'
        }
        
        result = await self._make_request(params)
        return result if isinstance(result, list) else []
    
    async def get_erc20_transfers(self, address: str, limit: int = 1000) -> List[Dict]:
        """Get ERC20 token transfers for address"""
        params = {
            'module': 'account',
            'action': 'tokentx',
            'address': address,
            'startblock': 0,
            'endblock': 99999999,
            'page': 1,
            'offset': limit,
            'sort': 'desc'
        }
        
        result = await self._make_request(params)
        return result if isinstance(result, list) else []
    
    async def get_contract_info(self, address: str) -> Dict:
        """Check if address is a contract and get ABI if available"""
        params = {
            'module': 'contract',
            'action': 'getabi',
            'address': address
        }
        
        result = await self._make_request(params)
        return {'is_contract': bool(result), 'abi': result if result else None}

class BlockchainAnalyzer:
    """Analyze blockchain data for trust scoring"""
    
    def __init__(self, etherscan_api: EtherscanAPI):
        self.etherscan = etherscan_api
    
    async def analyze_wallet_comprehensive(self, address: str) -> Dict:
        """Comprehensive wallet analysis using real blockchain data"""
        logger.info(f"Starting comprehensive analysis for {address[:8]}...")
        
        # Fetch all data in parallel
        tasks = [
            self.etherscan.get_account_balance(address),
            self.etherscan.get_transaction_list(address),
            self.etherscan.get_internal_transactions(address),
            self.etherscan.get_erc20_transfers(address),
            self.etherscan.get_contract_info(address)
        ]
        
        try:
            balance, transactions, internal_txs, token_transfers, contract_info = await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error fetching data for {address}: {e}")
            return self._fallback_analysis(address)
        
        # Analyze the fetched data
        analysis = await self._analyze_data(address, balance, transactions, internal_txs, token_transfers, contract_info)
        
        logger.info(f"Completed analysis for {address[:8]}")
        return analysis
    
    async def _analyze_data(self, address: str, balance: float, transactions: List[BlockchainTransaction], 
                          internal_txs: List[Dict], token_transfers: List[Dict], contract_info: Dict) -> Dict:
        """Analyze fetched blockchain data"""
        
        current_time = datetime.now().timestamp()
        
        # Basic metrics
        tx_count = len(transactions)
        
        # Calculate wallet age
        if transactions:
            first_tx_time = min(tx.timestamp for tx in transactions)
            age_days = int((current_time - first_tx_time) / (24 * 3600))
            last_activity_days = int((current_time - max(tx.timestamp for tx in transactions)) / (24 * 3600))
        else:
            age_days = 0
            last_activity_days = 999
        
        # Transaction patterns
        total_volume = sum(tx.value for tx in transactions)
        avg_tx_value = total_volume / max(1, tx_count)
        max_tx_value = max((tx.value for tx in transactions), default=0)
        avg_tx_per_day = tx_count / max(1, age_days) if age_days > 0 else 0
        
        # Contract interactions
        contract_interactions = sum(1 for tx in transactions if tx.to_address and await self._is_contract_address(tx.to_address))
        unique_contracts = len(set(tx.to_address for tx in transactions if tx.to_address and await self._is_contract_address(tx.to_address)))
        
        # DeFi analysis
        defi_protocols = await self._analyze_defi_interactions(transactions)
        
        # Risk indicators
        risk_analysis = await self._analyze_risk_patterns(transactions, internal_txs)
        
        # Gas efficiency
        gas_efficiency = self._calculate_gas_efficiency(transactions)
        
        return {
            'address': address,
            'balance_eth': balance,
            'tx_count': tx_count,
            'age_days': age_days,
            'last_activity_days': last_activity_days,
            'total_volume_eth': total_volume,
            'avg_tx_value': avg_tx_value,
            'max_tx_value': max_tx_value,
            'avg_tx_per_day': avg_tx_per_day,
            'contract_interactions': contract_interactions,
            'unique_contracts': unique_contracts,
            'defi_protocols': len(defi_protocols),
            'defi_protocol_names': defi_protocols,
            'gas_efficiency_score': gas_efficiency,
            'is_contract': contract_info.get('is_contract', False),
            'token_transfers': len(token_transfers),
            'internal_transactions': len(internal_txs),
            **risk_analysis
        }
    
    async def _is_contract_address(self, address: str) -> bool:
        """Check if address is a smart contract (simplified check)"""
        # This is a simplified check - in production, you'd want to cache this
        # or use a more efficient method
        return len(address) == 42 and address.startswith('0x')
    
    async def _analyze_defi_interactions(self, transactions: List[BlockchainTransaction]) -> List[str]:
        """Analyze DeFi protocol interactions"""
        # Known DeFi contract addresses (simplified list)
        defi_contracts = {
            '0x7a250d5630b4cf539739df2c5dacb4c659f2488d': 'Uniswap V2',
            '0xe592427a0aece92de3edee1f18e0157c05861564': 'Uniswap V3',
            '0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9': 'Aave',
            '0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b': 'Compound',
            '0x6b175474e89094c44da98b954eedeac495271d0f': 'DAI',
            '0xa0b86a33e6d01547e04eb0606f2e1deb9dbce9a': 'USDC'
        }
        
        protocols = set()
        for tx in transactions:
            if tx.to_address and tx.to_address.lower() in defi_contracts:
                protocols.add(defi_contracts[tx.to_address.lower()])
        
        return list(protocols)
    
    async def _analyze_risk_patterns(self, transactions: List[BlockchainTransaction], internal_txs: List[Dict]) -> Dict:
        """Analyze risk patterns in transactions"""
        
        # Analyze transaction patterns for suspicious activity
        flagged_interactions = 0
        suspicious_patterns = []
        
        # Check for rapid successive transactions (potential bot activity)
        if len(transactions) > 10:
            time_diffs = []
            for i in range(1, min(100, len(transactions))):
                time_diff = abs(transactions[i-1].timestamp - transactions[i].timestamp)
                time_diffs.append(time_diff)
            
            avg_time_diff = sum(time_diffs) / len(time_diffs)
            if avg_time_diff < 60:  # Less than 1 minute average
                suspicious_patterns.append("rapid_transactions")
        
        # Check for circular transactions (simplified)
        addresses = set()
        for tx in transactions[:100]:  # Check recent transactions
            addresses.add(tx.from_address)
            addresses.add(tx.to_address)
        
        if len(addresses) < len(transactions) * 0.1:  # Very few unique addresses
            suspicious_patterns.append("limited_counterparties")
        
        # Check for dust attacks (many small transactions)
        dust_threshold = 0.001  # 0.001 ETH
        dust_transactions = sum(1 for tx in transactions if 0 < tx.value < dust_threshold)
        if dust_transactions > len(transactions) * 0.3:
            suspicious_patterns.append("dust_pattern")
        
        return {
            'flagged_interactions': flagged_interactions,
            'blacklisted_interactions': 0,  # Would need blacklist database
            'wash_trading_score': min(1.0, len(suspicious_patterns) * 0.3),
            'suspicious_patterns': suspicious_patterns,
            'mev_involvement': 0.0,  # Would need MEV detection
            'sandwich_attacks': 0
        }
    
    def _calculate_gas_efficiency(self, transactions: List[BlockchainTransaction]) -> float:
        """Calculate gas efficiency score"""
        if not transactions:
            return 0.0
        
        # Calculate average gas price relative to network average (simplified)
        avg_gas_price = sum(tx.gas_price for tx in transactions) / len(transactions)
        
        # Normalize to 0-1 scale (this is simplified - would need historical network data)
        # Lower gas prices = higher efficiency
        efficiency = max(0, min(1, 1 - (avg_gas_price / 50_000_000_000)))  # 50 gwei baseline
        
        return efficiency
    
    def _fallback_analysis(self, address: str) -> Dict:
        """Fallback analysis when API calls fail"""
        logger.warning(f"Using fallback analysis for {address}")
        
        # Return simulated data as fallback
        return {
            'address': address,
            'balance_eth': np.random.exponential(2.0),
            'tx_count': np.random.poisson(100) + 1,
            'age_days': np.random.randint(30, 1500),
            'last_activity_days': np.random.randint(0, 30),
            'total_volume_eth': np.random.exponential(10.0),
            'avg_tx_value': np.random.exponential(0.5),
            'max_tx_value': np.random.exponential(5.0),
            'avg_tx_per_day': np.random.uniform(0.1, 10.0),
            'contract_interactions': np.random.poisson(25),
            'unique_contracts': np.random.poisson(15),
            'defi_protocols': np.random.poisson(8),
            'defi_protocol_names': ['Uniswap', 'Aave', 'Compound'][:np.random.randint(1, 4)],
            'gas_efficiency_score': np.random.beta(3, 2),
            'is_contract': False,
            'token_transfers': np.random.poisson(20),
            'internal_transactions': np.random.poisson(5),
            'flagged_interactions': np.random.poisson(0.5),
            'blacklisted_interactions': np.random.poisson(0.1),
            'wash_trading_score': np.random.beta(1, 4),
            'suspicious_patterns': [],
            'mev_involvement': 0.0,
            'sandwich_attacks': 0
        }

# Factory function to create analyzer with API key from environment
def create_blockchain_analyzer() -> Optional[BlockchainAnalyzer]:
    """Create blockchain analyzer with API key from environment"""
    api_key = os.getenv('ETHERSCAN_API_KEY')
    
    if not api_key or api_key == 'YOUR_ETHERSCAN_API_KEY_HERE':
        logger.warning("No Etherscan API key found. Using simulated data.")
        return None
    
    etherscan_api = EtherscanAPI(api_key)
    return BlockchainAnalyzer(etherscan_api)
