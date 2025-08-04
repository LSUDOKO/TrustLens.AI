from typing import Dict, Any, List

from .base_analyzer import BaseAnalyzer, AnalysisResult
from ....api.api_aggregator import APIAggregator


class ContractAnalyzer(BaseAnalyzer):
    """Analyzes smart contract data using multiple API sources."""

    def __init__(self, api_aggregator: APIAggregator):
        self.api_aggregator = api_aggregator

    async def analyze(self, contract_address: str) -> AnalysisResult:
        """
        Fetches contract data from multiple sources via the APIAggregator,
        analyzes it, and returns a comprehensive risk analysis.
        """
        aggregated_data = await self.api_aggregator.fetch_all_contract_data(contract_address)

        if not aggregated_data:
            return AnalysisResult(
                score=0,
                risk_level="NO_DATA",
                details={"error": "Could not fetch contract data from any source."},
                recommendations=["Ensure the contract address is correct and try again."]
            )

        # Combine data and calculate score
        score = 0
        details = {"sources": []}
        recommendations = set()

        for data in aggregated_data:
            source = data.get("source", "Unknown")
            details["sources"].append(source)
            
            if "contract_vulnerabilities" in data:
                vulnerabilities = data["contract_vulnerabilities"].get("details", [])
                if vulnerabilities:
                    score += len(vulnerabilities) * 25 # Add 25 points per vulnerability
                    recommendations.add(f"Address the {len(vulnerabilities)} vulnerabilities found by {source}.")
                details[f"{source}_vulnerabilities"] = vulnerabilities

            if "is_verified" in data:
                details[f"{source}_is_verified"] = data["is_verified"]
                if not data["is_verified"]:
                    score += 20
                    recommendations.add(f"Contract source code is not verified on {source}.")

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
