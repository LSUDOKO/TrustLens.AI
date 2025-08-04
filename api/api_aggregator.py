import asyncio
from typing import Any, Dict, List

import aiohttp

from .clients.base import BaseAPIClient
from .clients.bitscrunch import BitsCrunchClient
from .clients.contractscan import ContractScanClient


class APIAggregator:
    """Aggregates data from multiple API clients."""

    def __init__(self, api_keys: Dict[str, str], session: aiohttp.ClientSession):
        self.clients: List[BaseAPIClient] = [
            BitsCrunchClient(api_keys.get("BITSCRUNCH_API_KEY", ""), session),
            ContractScanClient(api_keys.get("CONTRACTSCAN_API_KEY", ""), session),
            # Add other clients here as they are created
        ]

    async def fetch_all_wallet_data(self, address: str) -> List[Dict[str, Any]]:
        """
        Fetches wallet data from all supported clients concurrently.

        Args:
            address (str): The wallet address.

        Returns:
            List[Dict[str, Any]]: A list of normalized data from all sources.
        """
        tasks = [client.get_wallet_data(address) for client in self.clients]
        results = await asyncio.gather(*tasks)
        return [res for res in results if not res.get("error")]

    async def fetch_all_contract_data(self, address: str) -> List[Dict[str, Any]]:
        """
        Fetches contract data from all supported clients concurrently.

        Args:
            address (str): The contract address.

        Returns:
            List[Dict[str, Any]]: A list of normalized data from all sources.
        """
        tasks = [client.get_contract_data(address) for client in self.clients]
        results = await asyncio.gather(*tasks)
        return [res for res in results if not res.get("error")]

    async def fetch_all_social_data(self, handle: str) -> List[Dict[str, Any]]:
        """
        Fetches social data from all supported clients concurrently.

        Args:
            handle (str): The social media handle.

        Returns:
            List[Dict[str, Any]]: A list of normalized data from all sources.
        """
        tasks = [client.get_social_data(handle) for client in self.clients]
        results = await asyncio.gather(*tasks)
        return [res for res in results if not res.get("error")]

    async def get_wallet_transactions(self, wallet_address: str) -> List[Dict[str, Any]]:
        """
        Fetches wallet transaction history from the first available client.

        Args:
            wallet_address (str): The wallet address.

        Returns:
            List[Dict[str, Any]]: A list of transactions.
        """
        for client in self.clients:
            transactions = await client.get_wallet_transactions(wallet_address)
            if transactions:  # Return the first non-empty list of transactions
                return transactions
        return []
