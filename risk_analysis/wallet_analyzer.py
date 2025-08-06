import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import statistics

from .base_analyzer import BaseAnalyzer, AnalysisResult
from ....api.api_aggregator import APIAggregator


@dataclass
class WalletMetrics:
    """Comprehensive wallet metrics for analysis."""
    transaction_count: int = 0
    total_value: float = 0.0
    unique_contracts: int = 0
    suspicious_transactions: int = 0
    age_days: int = 0
    activity_score: float = 0.0
    diversity_score: float = 0.0
    risk_indicators: List[str] = field(default_factory=list)


@dataclass
class RiskWeights:
    """Configurable risk scoring weights."""
    scam_multiplier: float = 25.0
    suspicious_tx_weight: float = 0.5
    new_wallet_penalty: float = 10.0
    low_activity_penalty: float = 5.0
    high_risk_contract_weight: float = 15.0
    unusual_pattern_weight: float = 10.0


class WalletAnalyzer(BaseAnalyzer):
    """
    Advanced on-chain wallet analyzer with comprehensive risk assessment,
    performance optimization, and multi-source data aggregation.
    """

    def __init__(
        self, 
        api_aggregator: APIAggregator,
        risk_weights: Optional[RiskWeights] = None,
        cache_ttl: int = 300,  # 5 minutes cache
        max_concurrent_requests: int = 10
    ):
        self.api_aggregator = api_aggregator
        self.risk_weights = risk_weights or RiskWeights()
        self.cache_ttl = cache_ttl
        self.max_concurrent_requests = max_concurrent_requests
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self._analysis_times: List[float] = []

    async def analyze(self, wallet_address: str, deep_analysis: bool = True) -> AnalysisResult:
        """
        Performs comprehensive wallet analysis with optional deep scanning.
        
        Args:
            wallet_address: The wallet address to analyze
            deep_analysis: Whether to perform detailed transaction analysis
            
        Returns:
            Comprehensive analysis result with risk scoring and recommendations
        """
        start_time = datetime.now()
        
        try:
            # Validate wallet address format
            if not self._is_valid_address(wallet_address):
                return self._create_error_result("Invalid wallet address format")

            # Check cache first
            cached_result = self._get_cached_result(wallet_address)
            if cached_result:
                self.logger.info(f"Returning cached result for {wallet_address[:10]}...")
                return cached_result

            # Fetch data with timeout and error handling
            aggregated_data = await self._fetch_data_with_retry(wallet_address)
            
            if not aggregated_data:
                return self._create_error_result("Could not fetch wallet data from any source")

            # Perform analysis
            metrics = await self._calculate_wallet_metrics(aggregated_data, deep_analysis)
            risk_score = self._calculate_risk_score(metrics)
            risk_level = self._get_risk_level(risk_score)
            
            # Generate detailed analysis
            details = self._generate_detailed_analysis(aggregated_data, metrics)
            recommendations = self._generate_recommendations(metrics, risk_level)

            result = AnalysisResult(
                score=risk_score,
                risk_level=risk_level,
                details=details,
                recommendations=recommendations
            )

            # Cache the result
            self._cache_result(wallet_address, result)
            
            # Track performance
            analysis_time = (datetime.now() - start_time).total_seconds()
            self._analysis_times.append(analysis_time)
            self.logger.info(f"Analysis completed in {analysis_time:.2f}s")

            return result

        except Exception as e:
            self.logger.error(f"Analysis failed for {wallet_address}: {str(e)}")
            return self._create_error_result(f"Analysis failed: {str(e)}")

    async def _fetch_data_with_retry(
        self, 
        wallet_address: str, 
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """Fetch data with retry logic and timeout handling."""
        for attempt in range(max_retries):
            try:
                # Use asyncio.wait_for to add timeout
                aggregated_data = await asyncio.wait_for(
                    self.api_aggregator.fetch_all_wallet_data(wallet_address),
                    timeout=30.0  # 30 second timeout
                )
                return aggregated_data
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout on attempt {attempt + 1} for {wallet_address}")
                if attempt == max_retries - 1:
                    return []
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                self.logger.error(f"Error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    return []
                await asyncio.sleep(1)
        return []

    async def _calculate_wallet_metrics(
        self, 
        aggregated_data: List[Dict[str, Any]], 
        deep_analysis: bool
    ) -> WalletMetrics:
        """Calculate comprehensive wallet metrics from aggregated data."""
        metrics = WalletMetrics()
        
        # Process data from all sources concurrently
        tasks = [
            self._process_source_data(data, metrics, deep_analysis) 
            for data in aggregated_data
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate derived metrics
        metrics.activity_score = self._calculate_activity_score(metrics)
        metrics.diversity_score = self._calculate_diversity_score(metrics)
        
        return metrics

    async def _process_source_data(
        self, 
        data: Dict[str, Any], 
        metrics: WalletMetrics, 
        deep_analysis: bool
    ) -> None:
        """Process data from a single API source."""
        source = data.get("source", "Unknown")
        
        try:
            # Process scam flags
            if "scam_flags" in data:
                scam_data = data["scam_flags"]
                scam_count = scam_data.get("count", 0)
                if scam_count > 0:
                    metrics.risk_indicators.extend([
                        f"Scam assets detected by {source}: {scam_count}",
                        *scam_data.get("details", [])
                    ])

            # Process transaction data
            if "transactions" in data:
                tx_data = data["transactions"]
                metrics.transaction_count += tx_data.get("count", 0)
                metrics.suspicious_transactions += tx_data.get("suspicious_count", 0)
                
                # Calculate wallet age
                if "first_transaction" in tx_data:
                    first_tx = datetime.fromisoformat(tx_data["first_transaction"])
                    metrics.age_days = max(metrics.age_days, (datetime.now() - first_tx).days)

            # Process asset data
            if "asset_summary" in data:
                asset_data = data["asset_summary"]
                metrics.total_value += asset_data.get("total_value_usd", 0)
                metrics.unique_contracts += asset_data.get("unique_tokens", 0)

            # Deep analysis for transaction patterns
            if deep_analysis and "transaction_patterns" in data:
                await self._analyze_transaction_patterns(data["transaction_patterns"], metrics)

        except Exception as e:
            self.logger.error(f"Error processing {source} data: {str(e)}")

    async def _analyze_transaction_patterns(
        self, 
        patterns: Dict[str, Any], 
        metrics: WalletMetrics
    ) -> None:
        """Analyze transaction patterns for suspicious activity."""
        # Check for unusual patterns
        if patterns.get("rapid_transactions", 0) > 100:
            metrics.risk_indicators.append("High frequency trading detected")
        
        if patterns.get("round_number_frequency", 0) > 0.8:
            metrics.risk_indicators.append("Unusual round number transaction pattern")
        
        if patterns.get("same_amount_frequency", 0) > 0.5:
            metrics.risk_indicators.append("Repetitive transaction amounts detected")

    def _calculate_activity_score(self, metrics: WalletMetrics) -> float:
        """Calculate wallet activity score (0-100)."""
        if metrics.age_days == 0:
            return 0.0
            
        # Transactions per day with logarithmic scaling
        tx_per_day = metrics.transaction_count / max(metrics.age_days, 1)
        activity_score = min(100, tx_per_day * 10)
        
        return activity_score

    def _calculate_diversity_score(self, metrics: WalletMetrics) -> float:
        """Calculate portfolio diversity score (0-100)."""
        if metrics.unique_contracts == 0:
            return 0.0
            
        # Logarithmic scaling for diversity
        diversity_score = min(100, metrics.unique_contracts * 5)
        return diversity_score

    def _calculate_risk_score(self, metrics: WalletMetrics) -> int:
        """Calculate comprehensive risk score using weighted factors."""
        score = 0.0
        weights = self.risk_weights

        # Scam-related risks
        scam_indicators = len([r for r in metrics.risk_indicators if "scam" in r.lower()])
        score += scam_indicators * weights.scam_multiplier

        # Suspicious transaction ratio
        if metrics.transaction_count > 0:
            suspicious_ratio = metrics.suspicious_transactions / metrics.transaction_count
            score += suspicious_ratio * 100 * weights.suspicious_tx_weight

        # New wallet penalty
        if metrics.age_days < 30:
            score += weights.new_wallet_penalty

        # Low activity penalty
        if metrics.activity_score < 10:
            score += weights.low_activity_penalty

        # High-risk contract interactions
        high_risk_contracts = len([r for r in metrics.risk_indicators if "contract" in r.lower()])
        score += high_risk_contracts * weights.high_risk_contract_weight

        # Unusual patterns
        pattern_indicators = len([r for r in metrics.risk_indicators if "pattern" in r.lower()])
        score += pattern_indicators * weights.unusual_pattern_weight

        return min(int(score), 100)

    def _generate_detailed_analysis(
        self, 
        aggregated_data: List[Dict[str, Any]], 
        metrics: WalletMetrics
    ) -> Dict[str, Any]:
        """Generate detailed analysis report."""
        return {
            "sources_analyzed": [data.get("source", "Unknown") for data in aggregated_data],
            "wallet_metrics": {
                "transaction_count": metrics.transaction_count,
                "total_value_usd": round(metrics.total_value, 2),
                "unique_contracts": metrics.unique_contracts,
                "wallet_age_days": metrics.age_days,
                "activity_score": round(metrics.activity_score, 2),
                "diversity_score": round(metrics.diversity_score, 2)
            },
            "risk_indicators": metrics.risk_indicators,
            "suspicious_transactions": metrics.suspicious_transactions,
            "analysis_timestamp": datetime.now().isoformat(),
            "performance_stats": {
                "avg_analysis_time": round(statistics.mean(self._analysis_times), 2) if self._analysis_times else 0,
                "cache_hit_rate": self._get_cache_hit_rate()
            }
        }

    def _generate_recommendations(
        self, 
        metrics: WalletMetrics, 
        risk_level: str
    ) -> List[str]:
        """Generate contextual recommendations based on analysis."""
        recommendations = []

        if risk_level == "CRITICAL":
            recommendations.extend([
                "⚠️ CRITICAL: This wallet shows multiple high-risk indicators",
                "Avoid any transactions with this wallet",
                "Report this wallet if suspected of fraudulent activity"
            ])
        elif risk_level == "HIGH":
            recommendations.extend([
                "⚠️ HIGH RISK: Exercise extreme caution",
                "Verify the legitimacy of this wallet through multiple sources",
                "Consider smaller test transactions first"
            ])

        # Specific recommendations based on metrics
        if metrics.age_days < 7:
            recommendations.append("🆕 Very new wallet - proceed with extra caution")

        if metrics.activity_score < 5:
            recommendations.append("📊 Low activity wallet - verify authenticity")

        if len(metrics.risk_indicators) > 3:
            recommendations.append("🔍 Multiple risk factors detected - thorough verification recommended")

        if metrics.suspicious_transactions > 0:
            recommendations.append(f"⚠️ {metrics.suspicious_transactions} suspicious transactions detected")

        # Default recommendations for low-risk wallets
        if risk_level == "LOW" and not recommendations:
            recommendations.extend([
                "✅ Wallet appears to have low risk profile",
                "Standard due diligence still recommended",
                "Monitor for any changes in activity patterns"
            ])

        return recommendations

    def _get_risk_level(self, score: int) -> str:
        """Determine risk level based on score with more granular thresholds."""
        if score >= 80:
            return "CRITICAL"
        elif score >= 60:
            return "HIGH"
        elif score >= 30:
            return "MEDIUM"
        elif score >= 10:
            return "LOW"
        else:
            return "MINIMAL"

    def _is_valid_address(self, address: str) -> bool:
        """Validate wallet address format for common blockchain formats."""
        if not address or not isinstance(address, str):
            return False
            
        # Remove whitespace
        address = address.strip()
        
        # Basic validation for common formats
        # Ethereum: 42 characters starting with 0x
        if address.startswith('0x') and len(address) == 42:
            return all(c in '0123456789abcdefABCDEF' for c in address[2:])
        
        # Bitcoin: 26-35 characters
        if 26 <= len(address) <= 35:
            return True
            
        # Add more validation as needed for other chains
        return False

    def _get_cached_result(self, wallet_address: str) -> Optional[AnalysisResult]:
        """Retrieve cached analysis result if still valid."""
        if wallet_address in self._cache:
            result, timestamp = self._cache[wallet_address]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return result
            else:
                del self._cache[wallet_address]
        return None

    def _cache_result(self, wallet_address: str, result: AnalysisResult) -> None:
        """Cache analysis result with timestamp."""
        self._cache[wallet_address] = (result, datetime.now())
        
        # Cleanup old cache entries (keep last 1000)
        if len(self._cache) > 1000:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

    def _get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate for performance monitoring."""
        # This would need to be implemented with proper tracking
        return 0.0  # Placeholder

    def _create_error_result(self, error_message: str) -> AnalysisResult:
        """Create standardized error result."""
        return AnalysisResult(
            score=0,
            risk_level="ERROR",
            details={"error": error_message, "timestamp": datetime.now().isoformat()},
            recommendations=[
                "Verify the wallet address format is correct",
                "Check network connectivity and try again",
                "Contact support if the issue persists"
            ]
        )

    async def analyze_multiple(
        self, 
        wallet_addresses: List[str], 
        deep_analysis: bool = False
    ) -> Dict[str, AnalysisResult]:
        """Analyze multiple wallets concurrently for batch processing."""
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        async def analyze_single(address: str) -> Tuple[str, AnalysisResult]:
            async with semaphore:
                result = await self.analyze(address, deep_analysis)
                return address, result
        
        tasks = [analyze_single(addr) for addr in wallet_addresses]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            addr: result for addr, result in results 
            if not isinstance(result, Exception)
        }

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get analyzer performance statistics."""
        return {
            "total_analyses": len(self._analysis_times),
            "average_time": statistics.mean(self._analysis_times) if self._analysis_times else 0,
            "cache_size": len(self._cache),
            "cache_hit_rate": self._get_cache_hit_rate()
        }