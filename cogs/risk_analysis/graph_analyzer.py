import networkx as nx
from typing import List, Dict, Any
from .analyzer_interface import AnalyzerInterface
from .analysis_result import AnalysisResult
import logging

logger = logging.getLogger(__name__)

class GraphAnalyzer(AnalyzerInterface):
    """Analyzes wallet-to-wallet interactions using a graph-based trust propagation model."""

    def __init__(self, transactions: List[Dict[str, Any]]):
        self.transactions = transactions
        self.graph = nx.DiGraph()

    def analyze(self) -> AnalysisResult:
        """Builds the transaction graph, runs PageRank, and calculates a risk score."""
        if not self.transactions:
            return AnalysisResult(score=0, risk_level="NO_DATA", details={"message": "No transaction data for graph analysis."})

        self._build_graph()
        
        if self.graph.number_of_nodes() == 0:
            return AnalysisResult(score=0, risk_level="NO_DATA", details={"message": "Transaction data did not yield a valid graph."})

        try:
            pagerank_scores = nx.pagerank(self.graph, alpha=0.85)
        except Exception as e:
            logger.error(f"PageRank calculation failed: {e}")
            return AnalysisResult(score=0, risk_level="NO_DATA", details={"message": "Graph analysis failed during PageRank calculation."})

        # Identify the top 5 most influential nodes (hubs)
        top_nodes = sorted(pagerank_scores.items(), key=lambda item: item[1], reverse=True)[:5]

        # Basic risk scoring based on influence concentration
        # High concentration in a few nodes can be risky
        total_pagerank = sum(pagerank_scores.values())
        top_5_pagerank_concentration = sum(score for _, score in top_nodes) / total_pagerank if total_pagerank > 0 else 0
        
        risk_score = 0
        if top_5_pagerank_concentration > 0.8:
            risk_score += 40  # Very high concentration
        elif top_5_pagerank_concentration > 0.5:
            risk_score += 20  # Moderate concentration

        # For now, we'll keep the details simple
        details = {
            "total_wallets_in_graph": self.graph.number_of_nodes(),
            "total_transactions_in_graph": self.graph.number_of_edges(),
            "influence_concentration_top_5": f"{top_5_pagerank_concentration:.2%}",
            "most_influential_wallets": [f"{node[:6]}...{node[-4:]}" for node, score in top_nodes]
        }

        risk_level = self._get_risk_level(risk_score)
        return AnalysisResult(score=risk_score, risk_level=risk_level, details=details)

    def _build_graph(self):
        """Constructs a directed graph from transaction data."""
        for tx in self.transactions:
            sender = tx.get('from_address')
            receiver = tx.get('to_address')
            value = float(tx.get('value', 0))

            if sender and receiver and sender != receiver:
                # Add nodes and a weighted edge
                self.graph.add_edge(sender, receiver, weight=value)

    def _get_risk_level(self, score: int) -> str:
        if score >= 75:
            return "CRITICAL"
        elif score >= 50:
            return "HIGH"
        elif score >= 25:
            return "MEDIUM"
        else:
            return "LOW"
