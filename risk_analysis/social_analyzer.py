from typing import Dict, Any, List

from .base_analyzer import BaseAnalyzer, AnalysisResult
from ....api.api_aggregator import APIAggregator


class SocialAnalyzer(BaseAnalyzer):
    """Analyzes off-chain social profile data using multiple API sources."""

    def __init__(self, api_aggregator: APIAggregator):
        self.api_aggregator = api_aggregator

    async def analyze(self, social_handle: str) -> AnalysisResult:
        """
        Fetches social data from multiple sources via the APIAggregator,
        analyzes it, and returns a comprehensive risk analysis.
        """
        aggregated_data = await self.api_aggregator.fetch_all_social_data(social_handle)

        if not aggregated_data:
            return AnalysisResult(
                score=0,
                risk_level="NO_DATA",
                details={"info": "Social media analysis is not yet supported or no data was found."},
                recommendations=[]
            )

        # Combine data and calculate score
        score = 0
        details = {"sources": []}
        recommendations = set()

        # This part is ready for when social clients are added
        for data in aggregated_data:
            source = data.get("source", "Unknown")
            details["sources"].append(source)
            
            # Example scoring logic for a hypothetical social data point
            if "follower_ratio" in data and data["follower_ratio"] < 0.5:
                score += 40
                recommendations.add("Account has a low follower/following ratio, indicating potential inauthenticity.")

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
