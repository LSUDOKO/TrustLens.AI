import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
from functools import lru_cache
from alith import Agent  # Import the Alith Agent
import numpy as np
from collections import defaultdict
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    HIGH_TRUST = "high_trust"
    MEDIUM_TRUST = "medium_trust"
    LOW_TRUST = "low_trust"
    HIGH_RISK = "high_risk"

class RiskCategory(Enum):
    TEMPORAL = "temporal"
    BEHAVIORAL = "behavioral"
    IDENTITY = "identity"
    FINANCIAL = "financial"
    NETWORK = "network"

@dataclass
class RiskFactor:
    category: RiskCategory
    severity: float  # -100 to +100
    confidence: float  # 0 to 1
    description: str
    weight: float = 1.0

@dataclass
class WalletMetrics:
    # Basic metrics
    address: str
    tx_count: int = 0
    age_days: int = 0
    balance_eth: float = 0.0
    balance_usd: float = 0.0
    
    # Advanced behavioral metrics
    unique_contracts: int = 0
    contract_interactions: int = 0
    defi_protocols: int = 0
    nft_collections: int = 0
    bridge_usage: int = 0
    
    # Temporal patterns
    avg_tx_per_day: float = 0.0
    peak_activity_day: int = 0
    dormant_periods: int = 0
    last_activity_days: int = 0
    
    # Financial patterns
    total_volume_eth: float = 0.0
    avg_tx_value: float = 0.0
    max_tx_value: float = 0.0
    gas_efficiency_score: float = 0.0
    
    # Identity and social
    has_ens: bool = False
    ens_domains: int = 0
    has_github: bool = False
    has_farcaster: bool = False
    has_lens: bool = False
    has_twitter: bool = False
    verified_credentials: int = 0
    
    # Risk indicators
    flagged_interactions: int = 0
    blacklisted_interactions: int = 0
    wash_trading_score: float = 0.0
    mev_involvement: float = 0.0
    sandwich_attacks: int = 0
    flashloan_usage: int = 0
    
    # Network analysis
    clustering_coefficient: float = 0.0
    betweenness_centrality: float = 0.0
    connected_known_addresses: int = 0
    suspicious_patterns: List[str] = field(default_factory=list)
    
    # Reputation scores from external sources
    chainalysis_score: Optional[float] = None
    elliptic_score: Optional[float] = None
    crystal_score: Optional[float] = None


class WalletDataAggregator:
    """Aggregates wallet data from multiple sources efficiently"""
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self.session = session or aiohttp.ClientSession()
        self.cache = {}
        self.rate_limits = defaultdict(lambda: {"calls": 0, "reset_time": time.time()})
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _cache_key(self, address: str, data_type: str) -> str:
        return hashlib.md5(f"{address}_{data_type}".encode()).hexdigest()
    
    async def _rate_limit_check(self, service: str, limit: int = 100, window: int = 3600):
        """Check and enforce rate limits per service"""
        current_time = time.time()
        rate_info = self.rate_limits[service]
        
        if current_time - rate_info["reset_time"] > window:
            rate_info["calls"] = 0
            rate_info["reset_time"] = current_time
        
        if rate_info["calls"] >= limit:
            sleep_time = window - (current_time - rate_info["reset_time"])
            logger.warning(f"Rate limit reached for {service}, sleeping {sleep_time}s")
            await asyncio.sleep(sleep_time)
            rate_info["calls"] = 0
            rate_info["reset_time"] = time.time()
        
        rate_info["calls"] += 1
    
    async def get_wallet_data(self, address: str) -> WalletMetrics:
        """Enhanced wallet data fetching with parallel API calls"""
        cache_key = self._cache_key(address, "full_metrics")
        
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < 300:  # 5 minute cache
                return cached_data
        
        logger.info(f"Fetching comprehensive data for {address[:8]}...")
        
        # Parallel data fetching
        tasks = [
            self._fetch_basic_metrics(address),
            self._fetch_defi_metrics(address),
            self._fetch_identity_data(address),
            self._fetch_risk_indicators(address),
            self._fetch_network_analysis(address),
            self._fetch_reputation_scores(address)
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine all metrics
            wallet_metrics = WalletMetrics(address=address)
            for result in results:
                if not isinstance(result, Exception):
                    self._merge_metrics(wallet_metrics, result)
                else:
                    logger.warning(f"Failed to fetch data: {result}")
            
            # Calculate derived metrics
            self._calculate_derived_metrics(wallet_metrics)
            
            # Cache the result
            self.cache[cache_key] = (wallet_metrics, time.time())
            
            return wallet_metrics
            
        except Exception as e:
            logger.error(f"Error fetching wallet data: {e}")
            return WalletMetrics(address=address)
    
    async def _fetch_basic_metrics(self, address: str) -> Dict:
        """Fetch basic wallet metrics (transactions, balance, age)"""
        await self._rate_limit_check("etherscan")
        
        # In production, replace with actual Etherscan/Alchemy API calls
        # Simulated enhanced data for demo
        first_tx_timestamp = int(datetime.now().timestamp()) - (np.random.randint(30, 1500) * 24 * 3600)
        tx_count = np.random.poisson(100) + 1
        
        return {
            "tx_count": tx_count,
            "age_days": (datetime.now().timestamp() - first_tx_timestamp) // (24 * 3600),
            "balance_eth": np.random.exponential(2.0),
            "balance_usd": 0,  # Would be calculated from ETH price
            "total_volume_eth": np.random.exponential(10.0),
            "avg_tx_value": np.random.exponential(0.5),
            "max_tx_value": np.random.exponential(5.0),
            "last_activity_days": np.random.randint(0, 30),
            "gas_efficiency_score": np.random.beta(3, 2),
        }
    
    async def _fetch_defi_metrics(self, address: str) -> Dict:
        """Fetch DeFi interaction metrics"""
        await self._rate_limit_check("defi_pulse")
        
        return {
            "contract_interactions": np.random.poisson(25),
            "unique_contracts": np.random.poisson(15),
            "defi_protocols": np.random.poisson(8),
            "nft_collections": np.random.poisson(5),
            "bridge_usage": np.random.poisson(3),
            "flashloan_usage": np.random.poisson(1),
        }
    
    async def _fetch_identity_data(self, address: str) -> Dict:
        """Fetch identity and social verification data"""
        await self._rate_limit_check("ens")
        
        has_ens = np.random.random() < 0.3
        return {
            "has_ens": has_ens,
            "ens_domains": np.random.poisson(1) if has_ens else 0,
            "has_github": np.random.random() < 0.15,
            "has_farcaster": np.random.random() < 0.1,
            "has_lens": np.random.random() < 0.08,
            "has_twitter": np.random.random() < 0.12,
            "verified_credentials": np.random.poisson(0.5),
        }
    
    async def _fetch_risk_indicators(self, address: str) -> Dict:
        """Fetch risk and suspicious activity indicators"""
        await self._rate_limit_check("risk_analysis")
        
        return {
            "flagged_interactions": np.random.poisson(0.5),
            "blacklisted_interactions": np.random.poisson(0.1),
            "wash_trading_score": np.random.beta(1, 4),
            "mev_involvement": np.random.beta(1, 9),
            "sandwich_attacks": np.random.poisson(0.1),
            "suspicious_patterns": np.random.choice(
                ["circular_transfers", "dust_attacks", "rapid_creation", "bot_like"], 
                size=np.random.randint(0, 3), 
                replace=False
            ).tolist()
        }
    
    async def _fetch_network_analysis(self, address: str) -> Dict:
        """Fetch network topology metrics"""
        await self._rate_limit_check("graph_analysis")
        
        return {
            "clustering_coefficient": np.random.beta(2, 5),
            "betweenness_centrality": np.random.exponential(0.001),
            "connected_known_addresses": np.random.poisson(5),
        }
    
    async def _fetch_reputation_scores(self, address: str) -> Dict:
        """Fetch external reputation scores"""
        scores = {}
        for service in ["chainalysis", "elliptic", "crystal"]:
            await self._rate_limit_check(service)
            if np.random.random() < 0.7:  # 70% chance of having a score
                scores[f"{service}_score"] = np.random.beta(7, 3) * 100
        
        return scores
    
    def _merge_metrics(self, wallet_metrics: WalletMetrics, data: Dict):
        """Merge fetched data into WalletMetrics object"""
        for key, value in data.items():
            if hasattr(wallet_metrics, key):
                setattr(wallet_metrics, key, value)
    
    def _calculate_derived_metrics(self, metrics: WalletMetrics):
        """Calculate derived metrics from raw data"""
        if metrics.age_days > 0:
            metrics.avg_tx_per_day = metrics.tx_count / metrics.age_days
        
        # Calculate dormant periods based on activity patterns (simplified)
        metrics.dormant_periods = max(0, metrics.age_days // 30 - max(1, metrics.tx_count // 10))
        
        # Peak activity estimation
        metrics.peak_activity_day = int(metrics.avg_tx_per_day * np.random.uniform(2, 5))


class AdvancedTrustScorer:
    """Advanced trust scoring system with machine learning-like scoring"""
    
    def __init__(self):
        self.feature_weights = self._initialize_weights()
        self.risk_thresholds = {
            RiskLevel.HIGH_TRUST: 80,
            RiskLevel.MEDIUM_TRUST: 60,
            RiskLevel.LOW_TRUST: 40,
            RiskLevel.HIGH_RISK: 0
        }
    
    def _initialize_weights(self) -> Dict[str, float]:
        """Initialize feature weights based on empirical analysis"""
        return {
            # Temporal factors
            "age_factor": 15.0,
            "activity_consistency": 12.0,
            "recency_factor": 8.0,
            
            # Behavioral factors
            "transaction_patterns": 18.0,
            "defi_engagement": 10.0,
            "network_diversity": 8.0,
            
            # Identity factors
            "verification_level": 15.0,
            "social_presence": 7.0,
            
            # Risk factors
            "suspicious_activity": -25.0,
            "blacklist_exposure": -30.0,
            "wash_trading": -20.0,
            
            # Financial factors
            "balance_stability": 6.0,
            "volume_patterns": 8.0,
            
            # Network factors
            "reputation_scores": 12.0,
            "network_position": 5.0,
        }
    
    async def calculate_trust_score(self, metrics: WalletMetrics) -> Dict:
        """Calculate comprehensive trust score"""
        logger.info(f"Calculating trust score for {metrics.address[:8]}...")
        
        # Extract features and calculate sub-scores
        features = self._extract_features(metrics)
        risk_factors = self._identify_risk_factors(metrics, features)
        
        # Calculate weighted score
        base_score = self._calculate_base_score(features)
        risk_adjusted_score = self._apply_risk_adjustments(base_score, risk_factors)
        
        # Apply confidence weighting
        confidence_score = self._calculate_confidence(metrics, risk_factors)
        final_score = self._apply_confidence_weighting(risk_adjusted_score, confidence_score)
        
        # Determine risk level and generate explanation
        risk_level = self._determine_risk_level(final_score)
        explanation = await self._generate_explanation(metrics, risk_factors, final_score, risk_level)
        
        return {
            "score": int(np.clip(final_score, 0, 100)),
            "risk_level": risk_level.value,
            "confidence": confidence_score,
            "risk_factors": [
                {
                    "category": rf.category.value,
                    "severity": rf.severity,
                    "description": rf.description,
                    "confidence": rf.confidence
                } for rf in risk_factors
            ],
            "explanation": explanation,
            "feature_contributions": self._get_feature_contributions(features),
            "timestamp": datetime.now().isoformat()
        }
    
    def _extract_features(self, metrics: WalletMetrics) -> Dict[str, float]:
        """Extract and normalize features for scoring"""
        features = {}
        
        # Temporal features
        features["age_factor"] = min(1.0, metrics.age_days / 365)
        features["activity_consistency"] = min(1.0, metrics.avg_tx_per_day / 5)
        features["recency_factor"] = max(0, 1 - metrics.last_activity_days / 90)
        
        # Behavioral features
        features["transaction_patterns"] = min(1.0, np.log1p(metrics.tx_count) / np.log(1000))
        features["defi_engagement"] = min(1.0, metrics.defi_protocols / 20)
        features["network_diversity"] = min(1.0, metrics.unique_contracts / 50)
        
        # Identity features
        identity_score = (
            int(metrics.has_ens) * 0.3 +
            int(metrics.has_github) * 0.2 +
            int(metrics.has_farcaster) * 0.15 +
            int(metrics.has_lens) * 0.15 +
            int(metrics.has_twitter) * 0.1 +
            min(0.1, metrics.verified_credentials * 0.05)
        )
        features["verification_level"] = min(1.0, identity_score)
        features["social_presence"] = min(1.0, (metrics.ens_domains + metrics.verified_credentials) / 5)
        
        # Risk features (inverted - higher values mean more risk)
        features["suspicious_activity"] = min(1.0, (
            metrics.flagged_interactions * 0.1 +
            len(metrics.suspicious_patterns) * 0.05 +
            metrics.sandwich_attacks * 0.2
        ))
        features["blacklist_exposure"] = min(1.0, metrics.blacklisted_interactions * 0.5)
        features["wash_trading"] = metrics.wash_trading_score
        
        # Financial features
        features["balance_stability"] = min(1.0, np.log1p(metrics.balance_eth) / np.log(100))
        features["volume_patterns"] = min(1.0, np.log1p(metrics.total_volume_eth) / np.log(1000))
        
        # Network features
        reputation_scores = [
            s for s in [metrics.chainalysis_score, metrics.elliptic_score, metrics.crystal_score]
            if s is not None
        ]
        features["reputation_scores"] = np.mean(reputation_scores) / 100 if reputation_scores else 0.5
        features["network_position"] = min(1.0, metrics.connected_known_addresses / 20)
        
        return features
    
    def _identify_risk_factors(self, metrics: WalletMetrics, features: Dict[str, float]) -> List[RiskFactor]:
        """Identify specific risk factors"""
        risk_factors = []
        
        # Age-based risks
        if metrics.age_days < 7:
            risk_factors.append(RiskFactor(
                RiskCategory.TEMPORAL, -30, 0.9,
                "Extremely new wallet (< 1 week old)"
            ))
        elif metrics.age_days < 30:
            risk_factors.append(RiskFactor(
                RiskCategory.TEMPORAL, -15, 0.8,
                "New wallet (< 1 month old)"
            ))
        
        # Activity-based risks
        if metrics.tx_count < 5:
            risk_factors.append(RiskFactor(
                RiskCategory.BEHAVIORAL, -25, 0.9,
                "Very low transaction count"
            ))
        elif metrics.avg_tx_per_day > 50:
            risk_factors.append(RiskFactor(
                RiskCategory.BEHAVIORAL, -15, 0.7,
                "Extremely high activity (potential bot)"
            ))
        
        # Identity bonuses
        if metrics.has_ens:
            risk_factors.append(RiskFactor(
                RiskCategory.IDENTITY, 20, 0.8,
                "ENS domain ownership"
            ))
        
        if metrics.verified_credentials > 2:
            risk_factors.append(RiskFactor(
                RiskCategory.IDENTITY, 15, 0.9,
                "Multiple verified credentials"
            ))
        
        # Financial risks
        if metrics.wash_trading_score > 0.8:
            risk_factors.append(RiskFactor(
                RiskCategory.FINANCIAL, -35, 0.85,
                "High wash trading probability"
            ))
        
        if metrics.blacklisted_interactions > 0:
            risk_factors.append(RiskFactor(
                RiskCategory.NETWORK, -50, 0.95,
                f"Interactions with {metrics.blacklisted_interactions} blacklisted addresses"
            ))
        
        # Network analysis
        if metrics.clustering_coefficient > 0.8:
            risk_factors.append(RiskFactor(
                RiskCategory.NETWORK, -20, 0.7,
                "High clustering (potential coordinated activity)"
            ))
        
        return risk_factors
    
    def _calculate_base_score(self, features: Dict[str, float]) -> float:
        """Calculate base score using weighted features"""
        score = 50  # Start with neutral score
        
        for feature_name, value in features.items():
            if feature_name in self.feature_weights:
                weight = self.feature_weights[feature_name]
                contribution = value * weight
                score += contribution
        
        return score
    
    def _apply_risk_adjustments(self, base_score: float, risk_factors: List[RiskFactor]) -> float:
        """Apply risk factor adjustments to base score"""
        adjusted_score = base_score
        
        for risk_factor in risk_factors:
            # Apply confidence-weighted adjustment
            adjustment = risk_factor.severity * risk_factor.confidence * risk_factor.weight
            adjusted_score += adjustment
        
        return adjusted_score
    
    def _calculate_confidence(self, metrics: WalletMetrics, risk_factors: List[RiskFactor]) -> float:
        """Calculate confidence in the score based on data quality"""
        confidence_factors = []
        
        # Data completeness
        total_fields = len(metrics.__dict__)
        non_zero_fields = sum(1 for v in metrics.__dict__.values() if v not in [0, 0.0, False, None, []])
        data_completeness = non_zero_fields / total_fields
        confidence_factors.append(data_completeness)
        
        # Age factor (older wallets = more confident)
        age_confidence = min(1.0, metrics.age_days / 180)
        confidence_factors.append(age_confidence)
        
        # Activity factor (more activity = more confident)
        activity_confidence = min(1.0, metrics.tx_count / 100)
        confidence_factors.append(activity_confidence)
        
        # Risk factor confidence
        if risk_factors:
            avg_risk_confidence = np.mean([rf.confidence for rf in risk_factors])
            confidence_factors.append(avg_risk_confidence)
        
        return np.mean(confidence_factors)
    
    def _apply_confidence_weighting(self, score: float, confidence: float) -> float:
        """Apply confidence weighting to final score"""
        # Lower confidence pushes score toward neutral (50)
        neutral_score = 50
        return score * confidence + neutral_score * (1 - confidence)
    
    def _determine_risk_level(self, score: float) -> RiskLevel:
        """Determine risk level based on score"""
        if score >= self.risk_thresholds[RiskLevel.HIGH_TRUST]:
            return RiskLevel.HIGH_TRUST
        elif score >= self.risk_thresholds[RiskLevel.MEDIUM_TRUST]:
            return RiskLevel.MEDIUM_TRUST
        elif score >= self.risk_thresholds[RiskLevel.LOW_TRUST]:
            return RiskLevel.LOW_TRUST
        else:
            return RiskLevel.HIGH_RISK
    
    async def _generate_explanation(self, metrics: WalletMetrics, risk_factors: List[RiskFactor], 
                                  score: float, risk_level: RiskLevel) -> str:
        """Generate natural language explanation using the Alith AI Agent."""
        logger.info(f"Generating explanation for {metrics.address[:8]} using Alith Agent...")

        # NOTE: Alith Agent requires an underlying LLM API key.
        # Ensure OPENAI_API_KEY (or other provider) is set in your environment.
        try:
            agent = Agent(
                model="gpt-4",  # Or another powerful model like 'claude-3-opus-20240229'
                preamble="You are an expert Web3 risk analyst for a service called TrustLens. Your role is to provide a clear, concise, and insightful trust analysis of an Ethereum wallet based on the data provided. Structure your response in three parts: 1. A one-sentence summary of the wallet's risk profile. 2. A brief explanation of the key positive indicators. 3. A brief explanation of the key negative risk factors. Be professional and objective."
            )

            positive_indicators = [rf.description for rf in risk_factors if rf.severity > 0]
            negative_indicators = [rf.description for rf in risk_factors if rf.severity < 0]

            prompt = (
                f"Please provide a trust analysis for a wallet with the following characteristics:\n\n"
                f"- Final Trust Score: {int(score)}/100\n"
                f"- Assessed Risk Level: {risk_level.value}\n"
                f"- Wallet Age: {metrics.age_days} days\n"
                f"- Total Transactions: {metrics.tx_count}\n"
                f"- DeFi Protocol Interactions: {metrics.defi_protocols}\n"
                f"- Key Positive Indicators: {positive_indicators or 'None'}\n"
                f"- Key Negative Indicators: {negative_indicators or 'None'}\n"
            )

            # Run the synchronous Alith prompt in a separate thread to avoid blocking the asyncio event loop.
            explanation = await asyncio.to_thread(agent.prompt, prompt)
            logger.info(f"Successfully generated explanation for {metrics.address[:8]}")
            return explanation

        except Exception as e:
            logger.error(f"Failed to generate explanation using Alith Agent for {metrics.address[:8]}: {e}")
            return "AI-powered explanation is currently unavailable due to a configuration issue. Please ensure your API key is set correctly."
    
    def _get_feature_contributions(self, features: Dict[str, float]) -> Dict[str, float]:
        """Get feature contributions to final score"""
        contributions = {}
        for feature_name, value in features.items():
            if feature_name in self.feature_weights:
                contributions[feature_name] = value * self.feature_weights[feature_name]
        return contributions


# Main API functions
async def analyze_wallet(address: str) -> Dict:
    """Main function to analyze a wallet and return trust score"""
    async with WalletDataAggregator() as aggregator:
        # Fetch comprehensive wallet data
        wallet_metrics = await aggregator.get_wallet_data(address)
        
        # Calculate trust score
        scorer = AdvancedTrustScorer()
        trust_analysis = await scorer.calculate_trust_score(wallet_metrics)
        
        # Format wallet age
        age_days = wallet_metrics.age_days
        if age_days >= 365:
            years = age_days // 365
            remaining_days = age_days % 365
            months = remaining_days // 30
            age_text = f"{years} year{'s' if years > 1 else ''}"
            if months > 0:
                age_text += f" {months} month{'s' if months > 1 else ''}"
        elif age_days >= 30:
            months = age_days // 30
            age_text = f"{months} month{'s' if months > 1 else ''}"
        else:
            age_text = f"{age_days} day{'s' if age_days > 1 else ''}"
        
        # Format last activity
        last_activity_days = wallet_metrics.last_activity_days
        if last_activity_days == 0:
            last_activity_text = "Today"
        elif last_activity_days == 1:
            last_activity_text = "1 day ago"
        elif last_activity_days < 7:
            last_activity_text = f"{last_activity_days} days ago"
        elif last_activity_days < 30:
            weeks = last_activity_days // 7
            last_activity_text = f"{weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            months = last_activity_days // 30
            last_activity_text = f"{months} month{'s' if months > 1 else ''} ago"
        
        # Generate DeFi protocol list
        defi_protocols = []
        if wallet_metrics.defi_protocols > 0:
            # Mock protocol names based on activity level
            all_protocols = ['Uniswap', 'Aave', 'Compound', 'MakerDAO', 'Curve', 'SushiSwap', 'Balancer', 'Yearn']
            protocol_count = min(wallet_metrics.defi_protocols, len(all_protocols))
            defi_protocols = all_protocols[:protocol_count]
        
        # Generate identity tags
        identity_tags = []
        if wallet_metrics.has_ens:
            identity_tags.append("ENS Domain")
        if wallet_metrics.has_github:
            identity_tags.append("GitHub Linked")
        if wallet_metrics.has_farcaster:
            identity_tags.append("Farcaster")
        if wallet_metrics.has_lens:
            identity_tags.append("Lens Protocol")
        if wallet_metrics.has_twitter:
            identity_tags.append("Twitter Verified")
        if wallet_metrics.verified_credentials > 0:
            identity_tags.append("Verified")
        
        # Generate risk tags based on analysis
        risk_tags = []
        if trust_analysis["score"] >= 80:
            risk_tags.extend(["Clean History", "Established"])
        elif trust_analysis["score"] >= 60:
            risk_tags.extend(["Moderate Risk", "Active"])
        else:
            risk_tags.extend(["High Risk", "Caution Advised"])
            
        if wallet_metrics.flagged_interactions > 0:
            risk_tags.append("Flagged Interactions")
        if wallet_metrics.wash_trading_score > 0.5:
            risk_tags.append("Wash Trading")
        
        return {
            "address": address,
            "analysis": {
                **trust_analysis,
                "identity_analysis": f"Wallet has {len(identity_tags)} identity verification{'s' if len(identity_tags) != 1 else ''} " +
                                   f"and {wallet_metrics.defi_protocols} DeFi protocol interaction{'s' if wallet_metrics.defi_protocols != 1 else ''}.",
                "risk_factors": "No significant risk factors detected." if trust_analysis["score"] >= 80 
                              else f"Risk factors detected: {', '.join(risk_tags[:3])}. Exercise appropriate caution."
            },
            "wallet_metrics": {
                "wallet_age": age_text,
                "current_balance": f"{round(wallet_metrics.balance_eth, 4)} ETH",
                "total_transactions": wallet_metrics.tx_count,
                "last_activity": last_activity_text,
                "avg_daily_tx": round(wallet_metrics.avg_tx_per_day, 1),
                "defi_protocols": ", ".join(defi_protocols) if defi_protocols else "None detected"
            },
            "identity_tags": identity_tags if identity_tags else ["No Verification"],
            "risk_tags": risk_tags if risk_tags else ["Clean History"],
            "raw_metrics": {
                "basic": {
                    "age_days": wallet_metrics.age_days,
                    "tx_count": wallet_metrics.tx_count,
                    "balance_eth": round(wallet_metrics.balance_eth, 4),
                    "avg_tx_per_day": round(wallet_metrics.avg_tx_per_day, 2),
                    "last_activity_days": wallet_metrics.last_activity_days
                },
                "defi": {
                    "protocols": wallet_metrics.defi_protocols,
                    "contracts": wallet_metrics.unique_contracts,
                    "nft_collections": wallet_metrics.nft_collections,
                    "bridge_usage": wallet_metrics.bridge_usage
                },
                "identity": {
                    "has_ens": wallet_metrics.has_ens,
                    "verified_credentials": wallet_metrics.verified_credentials,
                    "social_connections": sum([
                        wallet_metrics.has_github,
                        wallet_metrics.has_farcaster,
                        wallet_metrics.has_lens,
                        wallet_metrics.has_twitter
                    ])
                },
                "risk": {
                    "flagged_interactions": wallet_metrics.flagged_interactions,
                    "blacklisted_interactions": wallet_metrics.blacklisted_interactions,
                    "wash_trading_score": wallet_metrics.wash_trading_score,
                    "suspicious_patterns": wallet_metrics.suspicious_patterns
                }
            }
        }


async def batch_analyze_wallets(addresses: List[str], max_concurrent: int = 5) -> List[Dict]:
    """Analyze multiple wallets concurrently"""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def analyze_with_semaphore(address: str):
        async with semaphore:
            return await analyze_wallet(address)
    
    tasks = [analyze_with_semaphore(addr) for addr in addresses]
    return await asyncio.gather(*tasks, return_exceptions=True)


# Example usage
if __name__ == "__main__":
    async def main():
        # Single wallet analysis
        test_address = "0x742d35Cc6634C0532925a3b8D0A4E89C6aa9b02A"
        result = await analyze_wallet(test_address)
        
        print(f"Trust Score: {result['analysis']['score']}")
        print(f"Risk Level: {result['analysis']['risk_level']}")
        print(f"Confidence: {result['analysis']['confidence']:.2f}")
        print(f"Explanation: {result['analysis']['explanation']}")
        
        # Batch analysis example
        test_addresses = [
            "0x742d35Cc6634C0532925a3b8D0A4E89C6aa9b02A",
            "0x8ba1f109551bD432803012645Hac136c2132415a",
            "0x123d35Cc6634C0532925a3b8D0A4E89C6aa9b456"
        ]
        
        batch_results = await batch_analyze_wallets(test_addresses)
        print(f"\nBatch analysis completed for {len(batch_results)} wallets")
    
    # Run the example
    asyncio.run(main())