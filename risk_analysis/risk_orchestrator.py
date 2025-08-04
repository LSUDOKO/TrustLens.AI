import asyncio
import aiohttp
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from .wallet_analyzer import WalletAnalyzer
from .contract_analyzer import ContractAnalyzer
from .social_analyzer import SocialAnalyzer
from .graph_analyzer import GraphAnalyzer
from .hyperion_analyzer import HyperionAnalyzer
from .base_analyzer import AnalysisResult
from ....api.api_aggregator import APIAggregator
from ....api.clients.hyperion import HyperionClient
from ....database.redis_manager import RedisManager

logger = logging.getLogger(__name__)

class RiskOrchestrator:
    """Orchestrates parallel risk analysis across different domains."""

    def __init__(self, api_keys: Dict[str, str], session: aiohttp.ClientSession, redis_manager: RedisManager):
        self.api_aggregator = APIAggregator(api_keys, session)
        self.redis_manager = redis_manager
        self.wallet_analyzer = WalletAnalyzer(self.api_aggregator)
        self.contract_analyzer = ContractAnalyzer(self.api_aggregator)
        self.social_analyzer = SocialAnalyzer(self.api_aggregator)

        # Initialize Hyperion client and analyzer for on-chain analysis
        metis_rpc_url = os.getenv("METIS_RPC_URL")
        if not metis_rpc_url:
            raise ValueError("METIS_RPC_URL environment variable not set.")
        self.hyperion_client = HyperionClient(rpc_url=metis_rpc_url, session=session)
        self.hyperion_analyzer = HyperionAnalyzer(self.hyperion_client)

    async def analyze_all(
        self,
        wallet_address: str,
        contract_address: Optional[str] = None,
        social_handle: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run all relevant analyzers in parallel and aggregate the results."""
        analysis_tasks = {
            "wallet_analysis": self.wallet_analyzer.analyze(wallet_address),
            "hyperion_analysis": self.hyperion_analyzer.analyze(wallet_address)
        }
        if contract_address:
            analysis_tasks["contract_analysis"] = self.contract_analyzer.analyze(contract_address)
        if social_handle:
            analysis_tasks["social_analysis"] = self.social_analyzer.analyze(social_handle)

        # Run primary analyses in parallel
        results_list = await asyncio.gather(*analysis_tasks.values())
        final_results = dict(zip(analysis_tasks.keys(), results_list))

        # Now, fetch data for and run the graph analysis
        graph_res = await self._fetch_and_run_graph_analysis(wallet_address)
        final_results["graph_analysis"] = graph_res

        # Calculate final score and recommendations
        final_results['overall_score'] = self._calculate_overall_score(final_results)
        final_results['overall_recommendations'] = self._generate_overall_recommendations(final_results)

        # Log the complete event to Redis Stream
        if self.redis_manager:
            # Prepare data for logging (convert AnalysisResult objects to dicts)
            log_data = {
                "wallet_address": wallet_address,
                "contract_address": contract_address,
                "social_handle": social_handle,
                "timestamp": datetime.utcnow().isoformat()
            }
            for key, value in final_results.items():
                if isinstance(value, AnalysisResult):
                    log_data[key] = {
                        "score": value.score,
                        "risk_level": value.risk_level,
                        "details": value.details,
                        "recommendations": value.recommendations
                    }
                else:
                    log_data[key] = value
            
            await self.redis_manager.log_event("trustlens:events", log_data)

        return final_results

    async def _fetch_and_run_graph_analysis(self, wallet_address: str) -> AnalysisResult:
        """Fetches transaction data and runs the graph analyzer."""
        try:
            transactions = await self.api_aggregator.get_wallet_transactions(wallet_address)
            if not transactions:
                return AnalysisResult(score=0, risk_level="NO_DATA", details={"message": "No transactions found for graph analysis."})

            analyzer = GraphAnalyzer(transactions)
            return analyzer.analyze()
        except Exception as e:
            logger.error(f"Graph analysis failed for {wallet_address}: {e}", exc_info=True)
            return AnalysisResult(score=0, risk_level="ERROR", details={"message": "An unexpected error occurred during graph analysis."})

    def _calculate_overall_score(self, results: Dict[str, AnalysisResult]) -> int:
        """Calculates a weighted average score from all analysis results."""
        scores, weights = [], []
        # New weights for TrustLens.AI, focusing on on-chain activity
        weight_map = {
            'wallet_analysis': 0.30,      # General wallet stats (bitsCrunch)
            'hyperion_analysis': 0.35,    # On-chain event analysis (Hyperion)
            'contract_analysis': 0.15,    # Contract-specific risks
            'social_analysis': 0.05,      # Social presence (optional)
            'graph_analysis': 0.15,       # Transaction graph patterns
        }

        for key, result in results.items():
            if key in weight_map and isinstance(result, AnalysisResult):
                scores.append(result.score)
                weights.append(weight_map[key])
        
        if not weights:
            return 0

        total_score = sum(s * w for s, w in zip(scores, weights))
        total_weight = sum(weights)
        return int(total_score / total_weight) if total_weight > 0 else 0

    def _generate_overall_recommendations(self, results: Dict[str, AnalysisResult]) -> List[str]:
        """Generate a summary of recommendations from all analyses."""
        all_recs = []
        for result in results.values():
            if isinstance(result, AnalysisResult) and result.recommendations:
                all_recs.extend(result.recommendations)
        return list(set(all_recs))
