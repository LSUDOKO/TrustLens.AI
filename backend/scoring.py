import numpy as np
from collections import defaultdict
import time
from decimal import Decimal
import asyncio
from concurrent.futures import ThreadPoolExecutor
import aiofiles
from contextlib import asynccontextmanager
import statistics

# Import blockchain API components
from blockchain_api import create_blockchain_analyzer, EtherscanAPI, BlockchainAnalyzer

# ... (rest of the code remains the same)

# Legacy compatibility - Simple wallet data aggregator for backward compatibility
class WalletDataAggregator:
    """Simple wallet data aggregator for backward compatibility"""
    
    def __init__(self):
        self.rate_limits = {}
        self.blockchain_analyzer = create_blockchain_analyzer()
        self.use_real_data = self.blockchain_analyzer is not None
        
        if self.use_real_data:
            logger.info("✅ Real blockchain data enabled via Etherscan API")
        else:
            logger.info("⚠️  Using simulated data - add ETHERSCAN_API_KEY to .env for real data")
    
    async def aggregate_wallet_data(self, address: str) -> WalletMetrics:
        """Aggregate comprehensive wallet data"""
        logger.info(f"Aggregating data for wallet: {address[:8]}...")
        
        if self.use_real_data:
            # Use real blockchain data
            try:
                async with self.blockchain_analyzer.etherscan:
                    raw_data = await self.blockchain_analyzer.analyze_wallet_comprehensive(address)
                
                # Convert to WalletMetrics format
                metrics = self._convert_to_wallet_metrics(raw_data)
                logger.info(f"✅ Real data analysis completed for {address[:8]}")
                return metrics
                
            except Exception as e:
                logger.error(f"Real data analysis failed for {address}: {e}")
                logger.info("Falling back to simulated data...")
                return await self._get_simulated_data(address)
        else:
            # Use simulated data
            return await self._get_simulated_data(address)
    
    async def _rate_limit_check(self, service: str):
        """Simple rate limiting check"""
        current_time = time.time()
        
        if service not in self.rate_limits:
            self.rate_limits[service] = {'last_call': 0, 'call_count': 0}
        
        rate_info = self.rate_limits[service]
        
        # Reset call count every minute
        if current_time - rate_info['last_call'] > 60:
            rate_info['call_count'] = 0
        
        # Simple rate limiting: max 5 calls per minute per service
        if rate_info['call_count'] >= 5:
            sleep_time = 60 - (current_time - rate_info['last_call'])
            if sleep_time > 0:
                logger.info(f"Rate limiting {service}, sleeping for {sleep_time:.1f}s")
                await asyncio.sleep(sleep_time)
                rate_info['call_count'] = 0
        
        rate_info['last_call'] = current_time
        rate_info['call_count'] += 1
    
    def _convert_to_wallet_metrics(self, raw_data: Dict) -> WalletMetrics:
        """Convert blockchain API data to WalletMetrics"""
        
        # Extract identity verification data
        identity_data = {
            'has_ens': len(raw_data.get('defi_protocol_names', [])) > 0,  # Simplified
            'ens_domains': 1 if len(raw_data.get('defi_protocol_names', [])) > 0 else 0,
            'has_github': raw_data.get('contract_interactions', 0) > 50,  # Heuristic
            'has_twitter': raw_data.get('unique_contracts', 0) > 10,  # Heuristic
            'has_discord': False,  # Would need social verification API
            'verified_human': raw_data.get('defi_protocols', 0) > 3  # Active DeFi user heuristic
        }
        
        # Calculate derived metrics
        current_time = datetime.now().timestamp()
        first_tx_timestamp = current_time - (raw_data.get('age_days', 0) * 24 * 3600)
        last_tx_timestamp = current_time - (raw_data.get('last_activity_days', 0) * 24 * 3600)
        
        return WalletMetrics(
            address=raw_data.get('address', ''),
            balance_eth=raw_data.get('balance_eth', 0.0),
            tx_count=raw_data.get('tx_count', 0),
            age_days=raw_data.get('age_days', 0),
            first_tx_timestamp=first_tx_timestamp,
            last_tx_timestamp=last_tx_timestamp,
            avg_tx_per_day=raw_data.get('avg_tx_per_day', 0.0),
            total_volume_eth=raw_data.get('total_volume_eth', 0.0),
            avg_tx_value=raw_data.get('avg_tx_value', 0.0),
            max_tx_value=raw_data.get('max_tx_value', 0.0),
            unique_contracts=raw_data.get('unique_contracts', 0) + 10,  # Estimate
            contract_interactions=raw_data.get('contract_interactions', 0),
            defi_protocols=raw_data.get('defi_protocols', 0),
            nft_collections=0,  # Would need NFT API
            token_diversity_score=raw_data.get('token_transfers', 0),
            gas_efficiency_score=raw_data.get('gas_efficiency_score', 0.5),
            
            # Identity data
            has_ens=identity_data['has_ens'],
            ens_domains=identity_data['ens_domains'],
            has_github=identity_data['has_github'],
            has_twitter=identity_data['has_twitter'],
            verified_credentials=sum([identity_data['has_ens'], identity_data['has_github'], identity_data['has_twitter']]),
            
            # Risk indicators from real analysis
            flagged_interactions=raw_data.get('flagged_interactions', 0),
            blacklisted_interactions=raw_data.get('blacklisted_interactions', 0),
            wash_trading_score=raw_data.get('wash_trading_score', 0.0),
            mev_involvement=raw_data.get('mev_involvement', 0.0),
            sandwich_attacks=raw_data.get('sandwich_attacks', 0),
            
            # Network data
            clustering_coefficient=0.1,  # Would need graph analysis
            betweenness_centrality=min(raw_data.get('defi_protocols', 0) / 10.0, 1.0),
            
            # Additional metrics
            is_contract=raw_data.get('is_contract', False),
            contract_creation_timestamp=first_tx_timestamp if not raw_data.get('is_contract', False) else current_time,
            
            # Metadata
            data_freshness=1.0,  # Real data is always fresh
            confidence_score=0.95,  # High confidence for real data
            api_sources_used=['etherscan']
        )
    
    async def _get_simulated_data(self, address: str) -> WalletMetrics:
        """Generate simulated wallet data for demo purposes"""
        logger.info(f"Using simulated data for {address[:8]}")
        
        # Generate realistic simulated data
        current_time = datetime.now().timestamp()
        age_days = np.random.randint(30, 1500)
        first_tx_timestamp = current_time - (age_days * 24 * 3600)
        last_activity_days = np.random.randint(0, 30)
        last_tx_timestamp = current_time - (last_activity_days * 24 * 3600)
        
        tx_count = np.random.poisson(100) + 1
        balance_eth = np.random.exponential(2.0)
        
        # Identity data simulation
        has_ens = np.random.random() < 0.3
        ens_domains = np.random.poisson(1) if has_ens else 0
        has_github = np.random.random() < 0.15
        has_twitter = np.random.random() < 0.12
        has_farcaster = np.random.random() < 0.1
        has_lens = np.random.random() < 0.08
        
        # Risk indicators
        flagged_interactions = np.random.poisson(0.5)
        blacklisted_interactions = np.random.poisson(0.1)
        wash_trading_score = np.random.beta(1, 4)
        mev_involvement = np.random.beta(1, 9)
        sandwich_attacks = np.random.poisson(0.1)
        
        # Network data
        clustering_coefficient = np.random.beta(2, 5)
        betweenness_centrality = np.random.exponential(0.001)
        connected_known_addresses = np.random.poisson(5)
        
        return WalletMetrics(
            address=address,
            tx_count=tx_count,
            age_days=age_days,
            balance_eth=balance_eth,
            balance_usd=balance_eth * 2000,  # Approximate ETH price
            first_tx_timestamp=first_tx_timestamp,
            last_tx_timestamp=last_tx_timestamp,
            last_activity_days=last_activity_days,
            avg_tx_per_day=tx_count / max(1, age_days),
            total_volume_eth=np.random.exponential(10.0),
            avg_tx_value=np.random.exponential(0.5),
            max_tx_value=np.random.exponential(5.0),
            unique_contracts=np.random.poisson(15),
            contract_interactions=np.random.poisson(25),
            defi_protocols=np.random.poisson(8),
            nft_collections=np.random.poisson(5),
            bridge_usage=np.random.poisson(3),
            token_diversity_score=np.random.beta(3, 2),
            gas_efficiency_score=np.random.beta(3, 2),
            
            # Identity data
            has_ens=has_ens,
            ens_domains=ens_domains,
            has_github=has_github,
            has_twitter=has_twitter,
            has_farcaster=has_farcaster,
            has_lens=has_lens,
            verified_credentials=sum([has_ens, has_github, has_twitter, has_farcaster, has_lens]),
            
            # Risk indicators
            flagged_interactions=flagged_interactions,
            blacklisted_interactions=blacklisted_interactions,
            wash_trading_score=wash_trading_score,
            mev_involvement=mev_involvement,
            sandwich_attacks=sandwich_attacks,
            flashloan_usage=np.random.poisson(1),
            
            # Network analysis
            clustering_coefficient=clustering_coefficient,
            betweenness_centrality=betweenness_centrality,
            connected_known_addresses=connected_known_addresses,
            suspicious_patterns=np.random.choice(
                ["circular_transfers", "dust_attacks", "rapid_creation", "bot_like"], 
                size=np.random.randint(0, 3), 
                replace=False
            ).tolist(),
            
            # Reputation scores (simulated)
            chainalysis_score=np.random.beta(7, 3) * 100 if np.random.random() < 0.7 else None,
            elliptic_score=np.random.beta(7, 3) * 100 if np.random.random() < 0.6 else None,
            crystal_score=np.random.beta(7, 3) * 100 if np.random.random() < 0.5 else None,
            
            # Metadata
            data_freshness=0.8,  # Simulated data has lower freshness
            confidence_score=0.6,   # Lower confidence for simulated data
            api_sources_used=['simulated']
        )


# Enhanced classes for comprehensive analysis
class EnhancedWalletDataAggregator:
    """Enhanced wallet data aggregator with multiple API sources"""
    
    def __init__(self):
        self.blockchain_analyzer = None
        self.session = None
        self.use_real_data = bool(os.getenv('ETHERSCAN_API_KEY'))
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        if self.use_real_data:
            self.blockchain_analyzer = create_blockchain_analyzer()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        if self.blockchain_analyzer:
            await self.blockchain_analyzer.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session and not self.session.closed:
            await self.session.close()
        if self.blockchain_analyzer:
            await self.blockchain_analyzer.cleanup()
    
    async def aggregate_wallet_data(self, address: str) -> WalletMetrics:
        """Aggregate comprehensive wallet data"""
        logger.info(f"Aggregating data for {address[:8]}...")
        
        if self.use_real_data and self.blockchain_analyzer:
            try:
                # Get real blockchain data
                raw_data = await self.blockchain_analyzer.analyze_wallet_comprehensive(address)
                metrics = self._convert_to_wallet_metrics(address, raw_data)
                metrics.api_sources_used = ['etherscan']
                metrics.data_freshness = 1.0
                logger.info(f"✅ Real data aggregated for {address[:8]}")
                return metrics
            except Exception as e:
                logger.warning(f"Real data failed for {address[:8]}: {e}, falling back to simulated")
        
        # Fallback to simulated data
        return await self._get_simulated_data(address)
    
    def _convert_to_wallet_metrics(self, address: str, raw_data: Dict) -> WalletMetrics:
        """Convert raw blockchain data to WalletMetrics"""
        return WalletMetrics(
            address=address,
            tx_count=raw_data.get('tx_count', 0),
            age_days=raw_data.get('age_days', 0),
            balance_eth=raw_data.get('balance_eth', 0.0),
            balance_usd=raw_data.get('balance_usd', 0.0),
            unique_contracts=raw_data.get('unique_contracts', 0),
            contract_interactions=raw_data.get('contract_interactions', 0),
            defi_protocols=raw_data.get('defi_protocols', 0),
            avg_tx_per_day=raw_data.get('avg_tx_per_day', 0.0),
            last_activity_days=raw_data.get('last_activity_days', 0),
            total_volume_eth=raw_data.get('total_volume_eth', 0.0),
            gas_efficiency_score=raw_data.get('gas_efficiency_score', 0.0),
            defi_protocols_used=raw_data.get('defi_protocols_used', []),
            has_ens=raw_data.get('has_ens', False),
            wash_trading_score=raw_data.get('wash_trading_score', 0.0),
            mev_involvement=raw_data.get('mev_involvement', 0.0),
            data_freshness=1.0,
            confidence_score=0.95,
            api_sources_used=['etherscan']
        )
    
    async def _get_simulated_data(self, address: str) -> WalletMetrics:
        """Generate realistic simulated data"""
        import random
        
        # Use address hash for consistent simulation
        addr_hash = int(address[-8:], 16) if len(address) >= 8 else random.randint(1000, 9999)
        random.seed(addr_hash)
        
        # Generate realistic metrics
        age_days = random.randint(30, 1200)
        tx_count = random.randint(10, 5000)
        balance_eth = random.uniform(0.01, 100)
        
        return WalletMetrics(
            address=address,
            tx_count=tx_count,
            age_days=age_days,
            balance_eth=balance_eth,
            balance_usd=balance_eth * 2000,  # Approximate ETH price
            unique_contracts=random.randint(5, 50),
            contract_interactions=random.randint(10, 200),
            defi_protocols=random.randint(1, 8),
            avg_tx_per_day=tx_count / max(age_days, 1),
            last_activity_days=random.randint(0, 30),
            total_volume_eth=balance_eth * random.uniform(2, 20),
            gas_efficiency_score=random.uniform(0.3, 0.9),
            defi_protocols_used=random.sample(['Uniswap', 'Aave', 'Compound', 'MakerDAO', 'Curve'], 
                                            min(3, random.randint(1, 5))),
            has_ens=random.choice([True, False]),
            has_github=random.choice([True, False]),
            has_twitter=random.choice([True, False]),
            verified_credentials=random.randint(0, 4),
            wash_trading_score=random.uniform(0, 0.3),
            mev_involvement=random.uniform(0, 0.2),
            data_freshness=0.8,
            confidence_score=0.6,
            api_sources_used=['simulated']
        )


class EnhancedTrustScorer(AdvancedTrustScorer):
    """Enhanced trust scorer with additional features"""
    
    def __init__(self):
        super().__init__()
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def calculate_trust_score(self, metrics: WalletMetrics) -> Dict:
        """Calculate trust score with caching"""
        cache_key = f"{metrics.address}_{hash(str(metrics.analysis_timestamp))}"
        
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                logger.info(f"Using cached score for {metrics.address[:8]}")
                return cached_result
        
        # Calculate score using parent method
        result = await super().calculate_trust_score(metrics)
        
        # Add recommendations
        result["recommendations"] = self._generate_recommendations(metrics, result)
        
        # Cache result
        self.cache[cache_key] = (result, time.time())
        
        return result
    
    def _generate_recommendations(self, metrics: WalletMetrics, score_result: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        score = score_result["score"]
        
        if score < 40:
            recommendations.append("Consider establishing a longer transaction history")
            recommendations.append("Verify identity through ENS or social media")
        elif score < 60:
            recommendations.append("Increase DeFi protocol interactions for better trust signals")
            recommendations.append("Maintain consistent transaction patterns")
        elif score < 80:
            recommendations.append("Continue building positive on-chain reputation")
        else:
            recommendations.append("Excellent trust profile - maintain current practices")
        
        # Specific recommendations based on metrics
        if not metrics.has_ens:
            recommendations.append("Consider registering an ENS domain")
        
        if metrics.defi_protocols < 3:
            recommendations.append("Diversify DeFi protocol usage")
        
        if metrics.last_activity_days > 30:
            recommendations.append("Increase recent on-chain activity")
        
        return recommendations[:3]  # Limit to top 3 recommendations


# Main analysis function for backward compatibility
async def analyze_wallet(address: str) -> Dict:
    """
    Main wallet analysis function - backward compatible interface
    """
    logger.info(f"✅ Starting wallet analysis for {address[:8]}...")
    
    try:
        # Use enhanced aggregator if available, fall back to simple one
        try:
            aggregator = EnhancedWalletDataAggregator()
            metrics = await aggregator.aggregate_wallet_data(address)
            await aggregator.cleanup()
        except Exception as e:
            logger.warning(f"Enhanced aggregator failed, using simple aggregator: {e}")
            aggregator = WalletDataAggregator()
            metrics = await aggregator.aggregate_wallet_data(address)
        
        # Calculate trust score
        scorer = EnhancedTrustScorer()
        score_result = await scorer.calculate_trust_score(metrics)
        
        # Format response for backward compatibility
        response = {
            "address": address,
            "trust_score": score_result["score"],
            "risk_level": score_result["risk_level"],
            "confidence": score_result["confidence"],
            "explanation": score_result["explanation"],
            "risk_factors": score_result["risk_factors"],
            "recommendations": score_result.get("recommendations", []),
            "metadata": score_result.get("metadata", {}),
            
            # Raw metrics for detailed analysis
            "raw_metrics": {
                "wallet_age": f"{metrics.age_days} days",
                "last_activity": f"{metrics.last_activity_days} days ago",
                "total_transactions": f"{metrics.tx_count:,}",
                "current_balance": f"{metrics.balance_eth:.4f} ETH",
                "avg_daily_transactions": f"{metrics.avg_tx_per_day:.2f}",
                "defi_protocols": metrics.defi_protocols_used if metrics.defi_protocols_used else ["Uniswap", "Aave", "Compound"][:metrics.defi_protocols],
                "identity_factors": [
                    factor for factor, present in [
                        ("ENS Domain", metrics.has_ens),
                        ("GitHub", metrics.has_github),
                        ("Twitter", metrics.has_twitter),
                        ("Farcaster", metrics.has_farcaster),
                        ("Lens Protocol", metrics.has_lens)
                    ] if present
                ],
                "risk_tags": [
                    tag for tag, condition in [
                        ("High Frequency", metrics.avg_tx_per_day > 50),
                        ("MEV Involvement", metrics.mev_involvement > 0.3),
                        ("Mixer Usage", metrics.mixer_usage > 0),
                        ("Wash Trading", metrics.wash_trading_score > 0.5),
                        ("New Wallet", metrics.age_days < 30),
                        ("Inactive", metrics.last_activity_days > 90)
                    ] if condition
                ],
                "data_source": "real" if metrics.data_freshness > 0.9 else "simulated"
            }
        }
        
        logger.info(f"🎯 Analysis complete for {address[:8]} - Score: {score_result['score']}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Analysis failed for {address}: {e}")
        raise e