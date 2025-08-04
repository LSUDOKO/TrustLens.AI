import asyncio
import logging
from typing import List, Dict, Any

from web3 import Web3
from web3.providers.async_rpc import AsyncHTTPProvider

logger = logging.getLogger(__name__)

class HyperionClient:
    """Client for interacting with the Hyperion testnet to fetch on-chain event logs."""

    def __init__(self, rpc_url: str):
        self.w3 = Web3(AsyncHTTPProvider(rpc_url))

    async def get_event_logs(self, address: str) -> List[Dict[str, Any]]:
        """Fetches event logs for a given address using parallel execution."""
        if not self.w3.is_address(address):
            logger.error(f"Invalid address provided: {address}")
            return []

        # Define common event topics (keccak256 hashes)
        transfer_topic = self.w3.keccak(text="Transfer(address,address,uint256)").hex()
        approval_topic = self.w3.keccak(text="Approval(address,address,uint256)").hex()

        # Create filters for events where the address is either the source or destination
        filter_params = [
            {"fromBlock": "earliest", "toBlock": "latest", "topics": [transfer_topic, None, self.w3.to_checksum_address(address)]},
            {"fromBlock": "earliest", "toBlock": "latest", "topics": [transfer_topic, self.w3.to_checksum_address(address)]},
            {"fromBlock": "earliest", "toBlock": "latest", "topics": [approval_topic, self.w3.to_checksum_address(address)]}
        ]

        try:
            tasks = [self.w3.eth.get_logs(params) for params in filter_params]
            log_groups = await asyncio.gather(*tasks, return_exceptions=True)

            all_logs = []
            for result in log_groups:
                if isinstance(result, Exception):
                    logger.error(f"Error fetching logs: {result}", exc_info=True)
                    continue
                all_logs.extend(result)

            # Process logs into a more readable format
            processed_logs = [dict(log) for log in all_logs]
            logger.info(f"Found {len(processed_logs)} event logs for address {address}")
            return processed_logs

        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching logs for {address}: {e}", exc_info=True)
            return []
