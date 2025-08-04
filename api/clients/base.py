import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential


class BaseAPIClient(ABC):
    """Abstract base class for API clients."""

    def __init__(self, api_key: str, base_url: str, session: aiohttp.ClientSession):
        self.api_key = api_key
        self.base_url = base_url
        self.session = session

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Makes an asynchronous HTTP request to the specified endpoint.

        Args:
            method (str): The HTTP method to use (e.g., 'GET', 'POST').
            endpoint (str): The API endpoint to request.
            params (Optional[Dict[str, Any]]): A dictionary of query parameters.
            headers (Optional[Dict[str, str]]): A dictionary of request headers.

        Returns:
            Dict[str, Any]: The JSON response from the API.
        
        Raises:
            aiohttp.ClientResponseError: If the request fails.
        """
        url = f"{self.base_url}{endpoint}"
        async with self.session.request(method, url, params=params, headers=headers) as response:
            response.raise_for_status()
            return await response.json()

    @abstractmethod
    async def get_wallet_data(self, address: str) -> Dict[str, Any]:
        """
        Fetches and normalizes wallet data from the API.

        Args:
            address (str): The wallet address.

        Returns:
            Dict[str, Any]: The normalized wallet data.
        """
        pass

    @abstractmethod
    async def get_contract_data(self, address: str) -> Dict[str, Any]:
        """
        Fetches and normalizes smart contract data from the API.

        Args:
            address (str): The contract address.

        Returns:
            Dict[str, Any]: The normalized contract data.
        """
        pass

    @abstractmethod
    async def get_social_data(self, social_handle: str) -> Dict[str, Any]:
        """Fetches social profile data and normalizes it."""
        pass

    @abstractmethod
    async def get_wallet_transactions(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Fetches wallet transaction history for graph analysis."""
        pass
