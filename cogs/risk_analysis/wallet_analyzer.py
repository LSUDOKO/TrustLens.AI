from typing import Dict, Any, List

from .base_analyzer import BaseAnalyzer, AnalysisResult
from ....api.api_aggregator import APIAggregator


class WalletAnalyzer(BaseAnalyzer):
    """Analyzes on-chain wallet data using multiple API sources."""

    def __init__(self, api_aggregator: APIAggregator):
        self.api_aggregator = api_aggregator

    async def analyze(self, wallet_address: str) -> AnalysisResult:
        """
        Fetches wallet data from multiple sources via the APIAggregator,
        analyzes it, and returns a comprehensive risk analysis.
        """
        aggregated_data = await self.api_aggregator.fetch_all_wallet_data(wallet_address)

        if not aggregated_data:
            return AnalysisResult(
                score=0,
                risk_level="NO_DATA",
                details={"error": "Could not fetch wallet data from any source."},
                recommendations=["Ensure the wallet address is correct and try again."]
            )

        # Combine data and calculate score
        score = 0
        details = {"sources": []}
        recommendations = set()

        for data in aggregated_data:
            source = data.get("source", "Unknown")
            details["sources"].append(source)
            
            if "scam_flags" in data:
                scam_count = data["scam_flags"].get("count", 0)
                if scam_count > 0:
                    score += scam_count * 20  # Add 20 points per scam asset
                    recommendations.add(f"Review the {scam_count} suspicious assets reported by {source}.")
            
            if "asset_summary" in data:
                details[f"{source}_asset_summary"] = data["asset_summary"]
        
        # Normalize score to be within 0-100
        score = min(score, 100)

        risk_level = self.get_risk_level(score)

        return AnalysisResult(
            score=score,
            risk_level=risk_level,
            details=details,
            recommendations=list(recommendations)
        )

    def get_risk_level(self, score: int) -> str:
        if score > 75:
            return "CRITICAL"
        if score > 50:
            return "HIGH"
        if score > 25:
            return "MEDIUM"
        return "LOW"
