import os
import asyncio
import logging
from typing import Optional, Dict, Any
from functools import lru_cache

from alith import Agent
from .scoring import analyze_wallet as analyze_wallet_async

from .settings import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WalletAnalysisError(Exception):
    """Custom exception for wallet analysis errors"""
    pass

def validate_wallet_address(address: str) -> bool:
    """Validate Ethereum wallet address format"""
    if not address:
        return False
    
    # Basic validation for hex address (0x followed by 40 hex chars)
    if address.startswith('0x') and len(address) == 42:
        try:
            int(address[2:], 16)  # Check if valid hex
            return True
        except ValueError:
            return False
    
    # ENS name validation (basic check)
    if address.endswith('.eth') and len(address) > 4:
        return True
    return False

# --- Alith Agent Tool --- #
async def get_wallet_analysis_tool(wallet_address: str) -> str:
    """Analyzes an Ethereum wallet address using the scoring module"""
    if not wallet_address:
        return "❌ Please provide a wallet address or ENS name."
    if not validate_wallet_address(wallet_address.strip()):
        return "❌ Invalid wallet address format. Please provide a valid Ethereum address (0x...) or ENS name (.eth)."
    if not settings.etherscan_api_key:
        return "⚠️ Etherscan API key not configured. Cannot perform analysis."
    
    try:
        from .scoring import analyze_wallet
        result = await analyze_wallet(wallet_address.strip())
        analysis = result.get('analysis', {})
        raw_metrics = result.get('raw_metrics', {})
        risk_level = analysis.get('risk_level', 'UNKNOWN')
        trust_score = analysis.get('score', 0)
        risk_factors = analysis.get('risk_factors', [])
        
        response = f"""
📊 **Wallet Analysis Complete**
🔍 **Address**: `{wallet_address}`

**Trust Score**: {trust_score}/100
**Risk Level**: {risk_level}
**Data Source**: {raw_metrics.get('data_source', 'Etherscan')}

**Risk Factors**:"""
        
        if risk_factors:
            for i, factor in enumerate(risk_factors, 1):
                if isinstance(factor, dict):
                    response += f"\n{i}. {factor.get('description', factor.get('type', str(factor)))}"
                else:
                    response += f"\n{i}. {factor}"
        else:
            response += "\n✅ No significant risk factors detected."
        
        # Add recommendations based on trust score
        trust_score = result['trust_score']
        if trust_score >= 80:
            response += "\n\n💡 **Recommendation**: This wallet appears to have a good track record."
        elif trust_score >= 60:
            response += "\n\n💡 **Recommendation**: Proceed with normal caution when interacting."
        elif trust_score >= 40:
            response += "\n\n⚠️ **Recommendation**: Exercise increased caution with this wallet."
        else:
            response += "\n\n🚨 **Recommendation**: High risk - avoid interactions if possible."
        
        return response.strip()
        
    except asyncio.TimeoutError:
        logger.error(f"Timeout analyzing wallet {wallet_address}")
        return "⏱️ Analysis timed out. The wallet might have too much activity to analyze quickly."
    
    except Exception as e:
        logger.error(f"Error analyzing wallet {wallet_address}: {e}")
        return f"❌ Sorry, I couldn't analyze that address. Error: {str(e)[:100]}..."

@lru_cache(maxsize=1)
def create_agent() -> Optional[Agent]:
    """Initialize the Alith Agent with caching to prevent multiple instances"""
    if not settings.gemini_api_key:
        logger.warning("⚠️ GEMINI_API_KEY not found. Alith Agent is disabled.")
        logger.info("💡 To enable AI chat, add GEMINI_API_KEY to your .env file")
        return None
    if not settings.etherscan_api_key:
        logger.warning("⚠️ ETHERSCAN_API_KEY not found. Wallet analysis will be limited.")
    
    try:
        # Debug: Check what's available in the Agent class
        logger.info("Attempting to create Alith Agent...")
        
        # Try to import and inspect Alith to understand supported models
        from alith import Agent
        logger.info(f"Alith Agent class available: {Agent}")
        
        # Initialize Agent with correct model name for Alith
        # Based on Alith documentation, try common model names
        model_names_to_try = [
            "deepseek-chat",
            "gpt-4", 
            "gpt-3.5-turbo",
            "claude-3-sonnet",
            "gemini-pro",
            "gemini"
        ]
        
        agent = None
        for model_name in model_names_to_try:
            try:
                logger.info(f"Trying model: {model_name}")
                agent = Agent(
                    model=model_name,
                    tools=[get_wallet_analysis_tool],
                    api_key=settings.gemini_api_key,
                )
                logger.info(f"✅ Successfully created agent with model: {model_name}")
                break
            except Exception as model_error:
                logger.warning(f"Failed with model {model_name}: {model_error}")
                continue
        
        if not agent:
            raise Exception("Failed to create agent with any supported model")
        
        logger.info("✅ TrustLens AI Agent (Gemini-powered) initialized successfully.")
        return agent
        
    except Exception as e:
        logger.error(f"Failed to initialize Alith Agent: {e}")
        return None

# Singleton pattern for agent instance
_agent_instance = None

def get_trustlens_agent() -> Optional[Agent]:
    """Get the TrustLens agent instance (singleton pattern)"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = create_agent()
    return _agent_instance

# For backward compatibility
trustlens_agent = get_trustlens_agent()

# Health check function
def is_agent_healthy() -> Dict[str, Any]:
    """Check if the agent and its dependencies are properly configured"""
    return {
        "agent_initialized": trustlens_agent is not None,
        "gemini_api_configured": bool(settings.gemini_api_key),
        "etherscan_api_configured": bool(settings.etherscan_api_key),
        "status": "healthy" if (trustlens_agent and settings.gemini_api_key and settings.etherscan_api_key) else "degraded"
    }