from typing import Any, Dict, Optional

import aiohttp

from .base import BaseAPIClient


class BitsCrunchClient(BaseAPIClient):
    """API client for bitsCrunch (UnleashNFTs)."""

    def __init__(self, api_key: str, session: aiohttp.ClientSession):
        super().__init__(api_key, "https://api.unleashnfts.com/api/v1", session)

    async def get_wallet_data(self, address: str) -> Dict[str, Any]:
        """
        Fetches and normalizes wallet data from the bitsCrunch API.

        Args:
            address (str): The wallet address.

        Returns:
            Dict[str, Any]: The normalized wallet data.
        """
        headers = {"x-api-key": self.api_key}
        params = {"wallet_address": address, "chain_id": "1"}

        try:
            portfolio_data = await self._request("GET", "/wallet/portfolio", params=params, headers=headers)
            
            # For this example, we'll assume the portfolio data is sufficient.
            # In a real-world scenario, you might fetch from multiple endpoints.

            return self._normalize_wallet_data(portfolio_data)
        except aiohttp.ClientResponseError as e:
            # Handle API errors gracefully
            return {
                "error": True,
                "status_code": e.status,
                "message": f"Failed to fetch data from bitsCrunch: {e.message}"
            }

    def _normalize_wallet_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes raw API data into a standardized format.

        Args:
            data (Dict[str, Any]): The raw data from the API.

        Returns:
            Dict[str, Any]: The normalized data.
        """
        # This is an example normalization. You would adapt this to the actual API response.
        assets = data.get("assets", [])
        scam_count = sum(1 for asset in assets if asset.get("is_scam", False))

        return {
            "source": "bitsCrunch",
            "scam_flags": {
                "count": scam_count,
                "details": [asset for asset in assets if asset.get("is_scam")]
            },
            "tx_behavior": {
                "total_transactions": data.get("total_transactions", 0),
                "first_activity_date": data.get("first_activity_date")
            },
            "asset_summary": {
                "total_nfts": len(assets),
                "portfolio_value_usd": data.get("total_portfolio_value_usd", 0)
            }
        }

    async def get_contract_data(self, address: str) -> Dict[str, Any]:
        """
        Placeholder for fetching contract data. bitsCrunch is more wallet-focused.
        """
        return {
            "source": "bitsCrunch",
            "contract_vulnerabilities": "Not supported"
        }

    async def get_social_data(self, social_handle: str) -> Dict[str, Any]:
        """Social data not available from this client."""
        return {"error": "Social data not available from bitsCrunch"}

    async def get_wallet_transactions(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Fetches the last 100 transactions for a wallet for graph analysis."""
        endpoint = f"/nfts?owner_address={wallet_address}&chain_id=1&offset=0&limit=100"
        data = await self._make_request(endpoint)

        if not data or 'data' not in data or not data['data']:
            return []

        transactions = []
        for nft in data['data']:
            # We need a clear source and destination for graph edges.
            # 'last_sale' provides a clear buyer and seller.
            if 'last_sale' in nft and nft['last_sale']:
                transactions.append({
                    "from_address": nft['last_sale'].get('seller_address'),
                    "to_address": nft['last_sale'].get('buyer_address'),
                    "value": nft['last_sale'].get('payment_amount_usd', 0)
                })
        return transactions
