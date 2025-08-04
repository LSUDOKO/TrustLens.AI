import asyncio
import logging
from typing import Dict, Any, List

from .base_analyzer import BaseAnalyzer, AnalysisResult
from ...api.clients.hyperion import HyperionClient

logger = logging.getLogger(__name__)

class HyperionAnalyzer(BaseAnalyzer):
    """Analyzes on-chain event logs from Hyperion for risk signals."""

    def __init__(self, hyperion_client: HyperionClient):
        super().__init__(None)  # BaseAnalyzer expects a session, but we don't need one
        self.hyperion_client = hyperion_client
        # Keccak256 hashes for common events, pre-calculated for efficiency
        self.transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        self.approval_topic = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"

    async def analyze(self, address: str) -> AnalysisResult:
        """Analyzes event logs for a given address and returns a risk score."""
        logs = await self.hyperion_client.get_event_logs(address)
        if not logs:
            return AnalysisResult(score=0, risk_level="NO_DATA", details={"message": "No event logs found for this address on the Metis network."}, recommendations=["Could not retrieve on-chain event history."])

        score = 0
        recommendations = []
        event_counts = {"transfers": 0, "approvals": 0}

        for log in logs:
            if not log.get('topics'):
                continue
            
            topic_hex = log['topics'][0].hex() if hasattr(log['topics'][0], 'hex') else log['topics'][0]
            if topic_hex == self.transfer_topic:
                event_counts["transfers"] += 1
            elif topic_hex == self.approval_topic:
                event_counts["approvals"] += 1

        # Score based on transfer volume
        if event_counts["transfers"] > 200:
            score += 30
            recommendations.append("Wallet has a very high number of transfers, suggesting potential bot activity. Investigate further.")
        elif event_counts["transfers"] > 50:
            score += 15
            recommendations.append("Wallet has a high number of transfers. Verify the nature of these transactions.")

        # Score based on approval count
        if event_counts["approvals"] > 20:
            score += 40
            recommendations.append("Wallet has approved a very high number of contracts. Review and revoke unnecessary approvals immediately.")
        elif event_counts["approvals"] > 5:
            score += 20
            recommendations.append("Wallet has several active approvals. Periodically review and revoke unused contract permissions.")

        # Determine risk level
        if score >= 50:
            risk_level = "HIGH"
        elif score >= 25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        details = {
            "message": f"Analyzed {len(logs)} on-chain events.",
            "total_transfers": event_counts["transfers"],
            "total_approvals": event_counts["approvals"],
        }

        return AnalysisResult(score=min(score, 100), risk_level=risk_level, details=details, recommendations=recommendations)
