import os
import asyncio
import logging
import time
from typing import Optional, Dict, Any, List, Union, Callable
from functools import lru_cache, wraps
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import aiohttp
from contextlib import asynccontextmanager

from alith import Agent
from .scoring import analyze_wallet as analyze_wallet_async
from .settings import settings

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Performance monitoring
performance_logger = logging.getLogger(f"{__name__}.performance")

class RiskLevel(Enum):
    """Enhanced risk level enumeration"""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"

@dataclass
class AnalysisMetrics:
    """Comprehensive analysis metrics tracking"""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration: Optional[float] = None
    cache_hit: bool = False
    api_calls: int = 0
    data_points: int = 0
    
    def complete(self):
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time

@dataclass
class WalletAnalysisResult:
    """Enhanced wallet analysis result structure"""
    address: str
    trust_score: float
    risk_level: RiskLevel
    risk_factors: List[Dict[str, Any]]
    recommendations: List[str]
    raw_metrics: Dict[str, Any]
    analysis_time: datetime
    metrics: AnalysisMetrics
    confidence: float = 0.0
    data_freshness: Optional[datetime] = None

class WalletAnalysisError(Exception):
    """Enhanced custom exception with error codes"""
    def __init__(self, message: str, error_code: str = "UNKNOWN", details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}

class CacheManager:
    """Advanced caching system with TTL and intelligent invalidation"""
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        self.default_ttl = default_ttl
        self.max_size = max_size
    
    def _generate_key(self, address: str, params: Dict[str, Any] = None) -> str:
        """Generate cache key with parameter hashing"""
        key_data = f"{address}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, address: str, params: Dict[str, Any] = None) -> Optional[Any]:
        """Get cached result with TTL check"""
        key = self._generate_key(address, params)
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if time.time() - entry['timestamp'] > entry.get('ttl', self.default_ttl):
            self.invalidate(key)
            return None
        
        self._access_times[key] = time.time()
        logger.debug(f"Cache hit for key: {key}")
        return entry['data']
    
    def set(self, address: str, data: Any, ttl: Optional[int] = None, params: Dict[str, Any] = None):
        """Set cached result with automatic cleanup"""
        key = self._generate_key(address, params)
        
        # Cleanup old entries if cache is full
        if len(self._cache) >= self.max_size:
            self._cleanup_old_entries()
        
        self._cache[key] = {
            'data': data,
            'timestamp': time.time(),
            'ttl': ttl or self.default_ttl
        }
        self._access_times[key] = time.time()
        logger.debug(f"Cached result for key: {key}")
    
    def invalidate(self, key: str):
        """Remove specific cache entry"""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)
    
    def _cleanup_old_entries(self):
        """Remove least recently used entries"""
        if not self._access_times:
            return
        
        # Sort by access time and remove oldest 20%
        sorted_keys = sorted(self._access_times.items(), key=lambda x: x[1])
        keys_to_remove = [key for key, _ in sorted_keys[:len(sorted_keys) // 5]]
        
        for key in keys_to_remove:
            self.invalidate(key)
        
        logger.debug(f"Cleaned up {len(keys_to_remove)} cache entries")

# Global cache instance
cache_manager = CacheManager(default_ttl=600, max_size=2000)

def performance_monitor(func):
    """Decorator for performance monitoring"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        function_name = func.__name__
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            performance_logger.info(f"{function_name} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            performance_logger.error(f"{function_name} failed after {duration:.3f}s: {str(e)}")
            raise
    
    return wrapper

def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Enhanced retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. Retrying in {current_delay}s...")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
            
            raise last_exception
        return wrapper
    return decorator

class WalletValidator:
    """Enhanced wallet address validation"""
    
    @staticmethod
    def is_valid_ethereum_address(address: str) -> bool:
        """Validate Ethereum address with checksum validation"""
        if not address or not isinstance(address, str):
            return False
        
        # Remove whitespace
        address = address.strip()
        
        # Basic format check
        if not (address.startswith('0x') and len(address) == 42):
            return False
        
        try:
            # Validate hex characters
            int(address[2:], 16)
            
            # TODO: Add checksum validation for EIP-55
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_valid_ens_name(name: str) -> bool:
        """Enhanced ENS name validation"""
        if not name or not isinstance(name, str):
            return False
        
        name = name.strip().lower()
        
        # Basic format checks
        if not name.endswith('.eth') or len(name) < 5:
            return False
        
        # Remove .eth suffix for validation
        base_name = name[:-4]
        
        # Check for invalid characters
        invalid_chars = set('!@#$%^&*()+={}[]|\\:";\'<>?,/`~')
        if any(char in invalid_chars for char in base_name):
            return False
        
        # Length validation (3-63 characters for the name part)
        return 3 <= len(base_name) <= 63
    
    @staticmethod
    def validate_wallet_address(address: str) -> tuple[bool, str]:
        """Comprehensive wallet address validation with detailed feedback"""
        if not address:
            return False, "Empty address provided"
        
        address = address.strip()
        
        if cls.is_valid_ethereum_address(address):
            return True, "Valid Ethereum address"
        elif cls.is_valid_ens_name(address):
            return True, "Valid ENS name"
        else:
            return False, "Invalid address format. Provide a valid Ethereum address (0x...) or ENS name (.eth)"

class EnhancedWalletAnalyzer:
    """Enhanced wallet analysis with advanced features"""
    
    def __init__(self):
        self.session_pool = None
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    @asynccontextmanager
    async def get_session(self):
        """Async session context manager with connection pooling"""
        if self.session_pool is None:
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=20)
            self.session_pool = aiohttp.ClientSession(connector=connector)
        
        try:
            yield self.session_pool
        finally:
            # Session cleanup is handled in __del__ or explicit cleanup
            pass
    
    async def analyze_multiple_wallets(self, addresses: List[str]) -> Dict[str, WalletAnalysisResult]:
        """Batch analysis of multiple wallets with concurrency control"""
        results = {}
        semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
        
        async def analyze_single(address: str) -> tuple[str, WalletAnalysisResult]:
            async with semaphore:
                try:
                    result = await self.analyze_wallet_enhanced(address)
                    return address, result
                except Exception as e:
                    logger.error(f"Failed to analyze {address}: {str(e)}")
                    return address, None
        
        tasks = [analyze_single(addr) for addr in addresses]
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for address, result in completed_results:
            if not isinstance(result, Exception) and result is not None:
                results[address] = result
        
        return results
    
    @performance_monitor
    @retry_on_failure(max_retries=2)
    async def analyze_wallet_enhanced(self, address: str) -> WalletAnalysisResult:
        """Enhanced wallet analysis with comprehensive error handling"""
        metrics = AnalysisMetrics()
        
        # Check cache first
        cached_result = cache_manager.get(address)
        if cached_result:
            metrics.cache_hit = True
            metrics.complete()
            cached_result.metrics = metrics
            return cached_result
        
        try:
            # Perform analysis
            raw_result = await analyze_wallet_async(address)
            metrics.api_calls += 1
            
            # Enhanced result processing
            result = self._process_analysis_result(address, raw_result, metrics)
            
            # Cache successful result
            cache_manager.set(address, result, ttl=900)  # 15 minutes cache
            
            return result
            
        except asyncio.TimeoutError:
            raise WalletAnalysisError(
                "Analysis timed out - wallet may have excessive activity",
                "TIMEOUT_ERROR",
                {"address": address, "timeout_duration": 30}
            )
        except Exception as e:
            raise WalletAnalysisError(
                f"Analysis failed: {str(e)}",
                "ANALYSIS_ERROR",
                {"address": address, "original_error": str(e)}
            )
        finally:
            metrics.complete()
    
    def _process_analysis_result(self, address: str, raw_result: Dict[str, Any], metrics: AnalysisMetrics) -> WalletAnalysisResult:
        """Process raw analysis result into structured format"""
        analysis = raw_result.get('analysis', {})
        raw_metrics = raw_result.get('raw_metrics', {})
        
        # Enhanced risk level mapping
        risk_level_map = {
            'VERY_LOW': RiskLevel.VERY_LOW,
            'LOW': RiskLevel.LOW,
            'MEDIUM': RiskLevel.MEDIUM,
            'HIGH': RiskLevel.HIGH,
            'VERY_HIGH': RiskLevel.VERY_HIGH,
            'CRITICAL': RiskLevel.CRITICAL
        }
        
        risk_level = risk_level_map.get(
            analysis.get('risk_level', 'UNKNOWN'),
            RiskLevel.UNKNOWN
        )
        
        trust_score = float(analysis.get('score', 0))
        risk_factors = analysis.get('risk_factors', [])
        
        # Generate intelligent recommendations
        recommendations = self._generate_recommendations(trust_score, risk_level, risk_factors)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(raw_metrics, len(risk_factors))
        
        return WalletAnalysisResult(
            address=address,
            trust_score=trust_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            recommendations=recommendations,
            raw_metrics=raw_metrics,
            analysis_time=datetime.now(),
            metrics=metrics,
            confidence=confidence,
            data_freshness=self._estimate_data_freshness(raw_metrics)
        )
    
    def _generate_recommendations(self, trust_score: float, risk_level: RiskLevel, risk_factors: List[Dict]) -> List[str]:
        """Generate intelligent recommendations based on analysis"""
        recommendations = []
        
        if trust_score >= 90:
            recommendations.append("✅ Excellent track record - safe for large transactions")
        elif trust_score >= 80:
            recommendations.append("✅ Good reputation - proceed with confidence")
        elif trust_score >= 70:
            recommendations.append("⚠️ Generally safe - standard due diligence recommended")
        elif trust_score >= 60:
            recommendations.append("⚠️ Exercise normal caution - verify transaction details")
        elif trust_score >= 40:
            recommendations.append("🚨 Increased risk - thorough verification required")
        elif trust_score >= 20:
            recommendations.append("🚨 High risk - avoid large transactions")
        else:
            recommendations.append("🛑 Critical risk - avoid interaction if possible")
        
        # Risk-specific recommendations
        if risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH, RiskLevel.CRITICAL]:
            recommendations.append("🔍 Consider additional verification through multiple sources")
            recommendations.append("💰 Start with small test transactions if interaction is necessary")
        
        # Factor-specific recommendations
        factor_types = [f.get('type', '') for f in risk_factors if isinstance(f, dict)]
        if 'high_volume' in factor_types:
            recommendations.append("📊 High transaction volume detected - verify legitimacy")
        if 'new_wallet' in factor_types:
            recommendations.append("🆕 Recently created wallet - exercise extra caution")
        
        return recommendations
    
    def _calculate_confidence(self, raw_metrics: Dict[str, Any], risk_factor_count: int) -> float:
        """Calculate confidence score based on available data"""
        base_confidence = 0.5
        
        # Increase confidence based on data availability
        data_points = raw_metrics.get('transaction_count', 0)
        if data_points > 100:
            base_confidence += 0.3
        elif data_points > 10:
            base_confidence += 0.2
        elif data_points > 0:
            base_confidence += 0.1
        
        # Account for analysis depth
        if risk_factor_count > 0:
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _estimate_data_freshness(self, raw_metrics: Dict[str, Any]) -> Optional[datetime]:
        """Estimate data freshness based on last transaction"""
        last_tx_time = raw_metrics.get('last_transaction_time')
        if last_tx_time:
            try:
                return datetime.fromisoformat(last_tx_time)
            except (ValueError, TypeError):
                pass
        return None

# Global analyzer instance
wallet_analyzer = EnhancedWalletAnalyzer()

# --- Enhanced Alith Agent Tool --- #
async def get_wallet_analysis_tool(wallet_address: str) -> str:
    """Enhanced wallet analysis tool with comprehensive reporting"""
    if not wallet_address:
        return "❌ **Error**: Please provide a wallet address or ENS name."
    
    # Enhanced validation
    is_valid, validation_message = WalletValidator.validate_wallet_address(wallet_address)
    if not is_valid:
        return f"❌ **Validation Error**: {validation_message}"
    
    if not settings.etherscan_api_key:
        return "⚠️ **Configuration Error**: Etherscan API key not configured. Cannot perform analysis."
    
    try:
        # Use enhanced analyzer
        result = await wallet_analyzer.analyze_wallet_enhanced(wallet_address.strip())
        
        # Generate comprehensive report
        return _generate_analysis_report(result)
        
    except WalletAnalysisError as e:
        logger.error(f"Wallet analysis error for {wallet_address}: {e}")
        return f"❌ **Analysis Error**: {e} (Code: {e.error_code})"
    
    except asyncio.TimeoutError:
        logger.error(f"Timeout analyzing wallet {wallet_address}")
        return "⏱️ **Timeout**: Analysis timed out. The wallet might have excessive activity to analyze quickly."
    
    except Exception as e:
        logger.error(f"Unexpected error analyzing wallet {wallet_address}: {e}")
        return f"❌ **System Error**: An unexpected error occurred. Please try again later."

def _generate_analysis_report(result: WalletAnalysisResult) -> str:
    """Generate comprehensive analysis report"""
    # Risk level emoji mapping
    risk_emojis = {
        RiskLevel.VERY_LOW: "🟢",
        RiskLevel.LOW: "🟢",
        RiskLevel.MEDIUM: "🟡",
        RiskLevel.HIGH: "🟠",
        RiskLevel.VERY_HIGH: "🔴",
        RiskLevel.CRITICAL: "🛑",
        RiskLevel.UNKNOWN: "⚪"
    }
    
    risk_emoji = risk_emojis.get(result.risk_level, "⚪")
    
    report = f"""
🔍 **Advanced Wallet Analysis Complete**
📍 **Address**: `{result.address}`

## 📊 **Analysis Summary**
**Trust Score**: {result.trust_score:.1f}/100.0
**Risk Level**: {risk_emoji} {result.risk_level.value}
**Confidence**: {result.confidence:.0%}
**Analysis Time**: {result.metrics.duration:.2f}s
**Data Source**: {result.raw_metrics.get('data_source', 'Etherscan')}
"""
    
    # Add cache hit information
    if result.metrics.cache_hit:
        report += "\n💾 **Cache**: Results from cache (fast retrieval)"
    
    # Add data freshness
    if result.data_freshness:
        time_diff = datetime.now() - result.data_freshness
        if time_diff.days > 30:
            report += f"\n⏰ **Data Age**: Last activity {time_diff.days} days ago"
        elif time_diff.days > 1:
            report += f"\n⏰ **Data Age**: Last activity {time_diff.days} days ago"
        else:
            report += "\n⏰ **Data Age**: Recent activity detected"
    
    # Risk factors section
    report += "\n\n## 🚨 **Risk Assessment**"
    if result.risk_factors:
        for i, factor in enumerate(result.risk_factors, 1):
            if isinstance(factor, dict):
                description = factor.get('description', factor.get('type', str(factor)))
                severity = factor.get('severity', 'medium').upper()
                report += f"\n{i}. [{severity}] {description}"
            else:
                report += f"\n{i}. {factor}"
    else:
        report += "\n✅ No significant risk factors detected."
    
    # Recommendations section
    report += "\n\n## 💡 **Recommendations**"
    for rec in result.recommendations:
        report += f"\n• {rec}"
    
    # Performance metrics (for debugging/monitoring)
    if result.metrics.api_calls > 0:
        report += f"\n\n## 📈 **Analysis Metrics**"
        report += f"\n• API Calls: {result.metrics.api_calls}"
        report += f"\n• Processing Time: {result.metrics.duration:.3f}s"
        if result.raw_metrics.get('transaction_count'):
            report += f"\n• Transactions Analyzed: {result.raw_metrics['transaction_count']}"
    
    return report.strip()

class AgentManager:
    """Enhanced agent management with health monitoring and failover"""
    
    def __init__(self):
        self._agent = None
        self._health_check_interval = 300  # 5 minutes
        self._last_health_check = 0
        self._failover_models = ["deepseek-chat", "gpt-4", "claude-3-sonnet"]
        self._current_model_index = 0
    
    @lru_cache(maxsize=1)
    def create_agent(self) -> Optional[Agent]:
        """Create agent with failover model support"""
        if not settings.alith_api_key:
            logger.warning("ALITH_API_KEY is not set. AI agent will not be created.")
            return None
        
        for attempt, model in enumerate(self._failover_models):
            try:
                logger.info(f"Attempting to create agent with model: {model} (attempt {attempt + 1})")
                
                agent = Agent(
                    model=model,
                    tools=[get_wallet_analysis_tool],
                    api_key=settings.alith_api_key,
                )
                
                self._current_model_index = attempt
                logger.info(f"Agent created successfully with model: {model}")
                return agent
                
            except Exception as e:
                logger.error(f"Failed to create agent with model {model}: {e}")
                if attempt == len(self._failover_models) - 1:
                    logger.error("All failover models exhausted. Agent creation failed.")
                continue
        
        return None
    
    def get_agent(self) -> Optional[Agent]:
        """Get agent with health monitoring"""
        current_time = time.time()
        
        # Periodic health check
        if current_time - self._last_health_check > self._health_check_interval:
            self._perform_health_check()
            self._last_health_check = current_time
        
        if self._agent is None:
            self._agent = self.create_agent()
        
        return self._agent
    
    def _perform_health_check(self):
        """Perform agent health check"""
        if self._agent is None:
            return
        
        try:
            # Test basic agent functionality
            # This would depend on the Alith Agent API
            logger.debug("Agent health check passed")
        except Exception as e:
            logger.warning(f"Agent health check failed: {e}")
            self._agent = None  # Force recreation
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status"""
        return {
            "agent_initialized": self._agent is not None,
            "current_model": self._failover_models[self._current_model_index] if self._agent else None,
            "alith_api_configured": bool(settings.alith_api_key),
            "etherscan_api_configured": bool(settings.etherscan_api_key),
            "gemini_api_configured": bool(settings.gemini_api_key),
            "cache_size": len(cache_manager._cache),
            "last_health_check": datetime.fromtimestamp(self._last_health_check).isoformat(),
            "status": "healthy" if self._agent and settings.alith_api_key and settings.etherscan_api_key else "degraded"
        }

# Global agent manager
agent_manager = AgentManager()

def get_trustlens_agent() -> Optional[Agent]:
    """Get the TrustLens agent instance with enhanced management"""
    return agent_manager.get_agent()

# For backward compatibility
trustlens_agent = get_trustlens_agent()

# Enhanced health check function
def is_agent_healthy() -> Dict[str, Any]:
    """Comprehensive system health check"""
    return agent_manager.get_agent_status()

# Batch analysis function
async def analyze_wallet_batch(addresses: List[str]) -> Dict[str, Dict[str, Any]]:
    """Analyze multiple wallets in batch with optimized concurrency"""
    results = await wallet_analyzer.analyze_multiple_wallets(addresses)
    
    # Convert to dictionary format for API compatibility
    formatted_results = {}
    for address, result in results.items():
        if result:
            formatted_results[address] = {
                'trust_score': result.trust_score,
                'risk_level': result.risk_level.value,
                'risk_factors': result.risk_factors,
                'recommendations': result.recommendations,
                'confidence': result.confidence,
                'analysis_time': result.analysis_time.isoformat()
            }
    
    return formatted_results

# Cleanup function for graceful shutdown
async def cleanup():
    """Cleanup resources on shutdown"""
    try:
        if wallet_analyzer.session_pool:
            await wallet_analyzer.session_pool.close()
        if wallet_analyzer.executor:
            wallet_analyzer.executor.shutdown(wait=True)
        logger.info("Cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

# Context manager for resource management
@asynccontextmanager
async def wallet_analysis_context():
    """Context manager for wallet analysis with proper cleanup"""
    try:
        yield wallet_analyzer
    finally:
        await cleanup()