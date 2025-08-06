import sys
import uvicorn
import redis.asyncio as redis
import time
import json
import asyncio
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException, Depends, Request, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, ConfigDict, validator
import logging

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.settings import settings
from backend.scoring import analyze_wallet
from backend.alith_agent import create_agent, get_trustlens_agent, is_agent_healthy, validate_wallet_address

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")

# --- API Security & Rate Limiting ---
limiter = Limiter(key_func=get_remote_address)
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify the API key provided in the request header."""
    if not settings.api_key:
        logger.warning("API key not configured on server, access is open.")
        return True
    if api_key == settings.api_key:
        return True
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key"
    )

# --- Global Variables ---
redis_client: redis.Redis | None = None
trustlens_agent = None

# --- Caching Functions ---
async def get_cache_key(address: str, blockchain: str) -> str:
    return f"analysis:{blockchain}:{address.lower()}"

async def get_cached_analysis(key: str) -> Optional[dict]:
    if not redis_client:
        return None
    try:
        cached = await redis_client.get(key)
        return json.loads(cached) if cached else None
    except Exception as e:
        logger.warning(f"Redis GET failed for key {key}: {e}")
        return None

async def cache_analysis(key: str, data: dict, ttl: int):
    if not redis_client:
        return
    try:
        await redis_client.setex(key, ttl, json.dumps(data))
    except Exception as e:
        logger.warning(f"Redis SETEX failed for key {key}: {e}")

# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global redis_client, trustlens_agent
    
    logger.info(f"Starting TrustLens.AI API in {settings.environment} mode")
    
    # Initialize Redis connection
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30
        )
        await redis_client.ping()
        logger.info("Redis connection established successfully")
    except Exception as e:
        logger.warning(f"Redis connection failed, running without cache. Error: {e}")
        redis_client = None
    
    # Initialize TrustLens AI Agent
    if settings.enable_ai_analysis:
        trustlens_agent = create_agent()
        if trustlens_agent:
            logger.info("TrustLens AI Agent initialized successfully")
        else:
            logger.warning("TrustLens AI Agent initialization failed. Check API keys.")
    else:
        logger.info("AI analysis is disabled by configuration.")
    
    yield
    
    # Shutdown logic
    logger.info("Shutting down TrustLens.AI API")
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed.")
    trustlens_agent = None

app = FastAPI(
    title="TrustLens.AI API",
    description="API for TrustLens.AI wallet scoring and analysis",
    version="2.0.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class RiskFactor(BaseModel):
    type: str
    severity: str
    confidence: float
    description: str

class WalletMetadata(BaseModel):
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    transaction_count: int = 0
    balance_usd: float = 0.0

class WalletAnalysisRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    address: str = Field(..., min_length=26, max_length=62, description="Blockchain wallet address")
    blockchain: Optional[str] = Field(default="ethereum", pattern="^(ethereum|bitcoin|polygon|bsc|avalanche)$", description="Blockchain network")
    include_metadata: bool = Field(default=True, description="Include additional wallet metadata in response")
    include_ai_insights: bool = Field(default=False, description="Include AI-generated insights and explanations")

    @validator('address')
    def validate_address_format(cls, v):
        if not v or not validate_wallet_address(v.strip()):
            raise ValueError("Invalid wallet address format")
        return v.strip().lower() if v.startswith('0x') else v.strip()

class WalletAnalysisResponse(BaseModel):
    address: str
    blockchain: str
    trust_score: int = Field(..., ge=0, le=100)
    risk_category: str
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    explanation: str
    ai_insights: Optional[str] = None
    metadata: Optional[WalletMetadata] = None
    analysis_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_time_ms: Optional[float] = None
    cached: bool = False
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    checks: Dict[str, bool]

class ChatRequest(BaseModel):
    """Request model for AI chat"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User message for the AI agent"
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional conversation ID for context"
    )

class ChatResponse(BaseModel):
    """Response model for AI chat"""
    response: str = Field(..., description="AI agent response")
    conversation_id: str = Field(..., description="Conversation identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_time_ms: Optional[float] = None

# --- API Endpoints --- #
@app.get("/", tags=["General"])
async def read_root():
    """Root endpoint providing basic API information"""
    return {"message": "Welcome to the TrustLens.AI API"}

@app.get("/health", response_model=HealthResponse, tags=["System"])
@limiter.limit("1000/minute")
async def health_check(request: Request):
    """Comprehensive health check endpoint"""
    start_time = time.time()
    
    redis_connected = False
    if redis_client:
        try:
            await redis_client.ping()
            redis_connected = True
        except Exception:
            pass
    
    scoring_available = False
    try:
        from backend.scoring import analyze_wallet
        scoring_available = True
    except ImportError:
        pass
    
    ai_agent_available = trustlens_agent is not None
    gemini_configured = bool(settings.gemini_api_key)
    etherscan_configured = bool(settings.etherscan_api_key)
    
    all_systems_healthy = all([
        redis_connected,
        scoring_available,
        etherscan_configured
    ])
    
    return HealthResponse(
        status="healthy" if all_systems_healthy else "degraded",
        timestamp=datetime.now(timezone.utc),
        version="2.0.0",
        environment=settings.environment,
        uptime_seconds=time.time() - start_time,
        checks={
            "redis": redis_connected,
            "scoring_module": scoring_available,
            "ai_agent": ai_agent_available,
            "gemini_api": gemini_configured,
            "etherscan_api": etherscan_configured,
            "ai_analysis_enabled": settings.enable_ai_analysis,
        }
    )

@app.post("/api/v2/analyze", response_model=WalletAnalysisResponse, tags=["Analysis"])
@limiter.limit(settings.rate_limit)
async def analyze_wallet_v2(
    request: Request,
    wallet_request: WalletAnalysisRequest,
    background_tasks: BackgroundTasks,
    authenticated: bool = Depends(verify_api_key)
):
    """Enhanced wallet analysis endpoint with optional AI insights"""
    start_time = time.time()
    logger.info("Received wallet analysis request", address=wallet_request.address, blockchain=wallet_request.blockchain)

    cache_key = await get_cache_key(wallet_request.address, wallet_request.blockchain + ("_ai" if wallet_request.include_ai_insights else ""))
    cached_result = await get_cached_analysis(cache_key)
    if cached_result:
        cached_result["cached"] = True
        cached_result["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        logger.info("Returning cached analysis", address=wallet_request.address)
        return WalletAnalysisResponse(**cached_result)

    try:
        logger.info("Performing new analysis", address=wallet_request.address)
        full_analysis = await asyncio.wait_for(analyze_wallet(wallet_request.address), timeout=float(settings.request_timeout))
        analysis = full_analysis['analysis']
        
        ai_insights = None
        if wallet_request.include_ai_insights and settings.enable_ai_analysis and trustlens_agent:
            try:
                ai_prompt = f"Provide additional insights for wallet {wallet_request.address} with trust score {analysis['score']} and risk level {analysis.get('risk_level', 'unknown')}. Focus on what this means for users."
                ai_insights = await asyncio.wait_for(trustlens_agent.run_async(ai_prompt), timeout=10)
            except Exception as e:
                logger.warning(f"AI insights failed: {e}")
                ai_insights = "AI insights temporarily unavailable."

        processing_time = round((time.time() - start_time) * 1000, 2)

        risk_factors_formatted = [RiskFactor(**rf) if isinstance(rf, dict) else RiskFactor(type="general_risk", severity="medium", confidence=0.7, description=str(rf)) for rf in analysis.get('risk_factors', [])]

        response_data = WalletAnalysisResponse(
            address=wallet_request.address,
            blockchain=wallet_request.blockchain,
            trust_score=analysis['score'],
            risk_category=analysis.get('risk_level', 'unknown'),
            risk_factors=risk_factors_formatted,
            explanation=analysis.get('explanation', 'Analysis completed.'),
            ai_insights=ai_insights,
            metadata=WalletMetadata(**full_analysis.get("raw_metrics", {}).get("basic", {})) if wallet_request.include_metadata else None,
            processing_time_ms=processing_time,
            cached=False,
            confidence_score=analysis.get('confidence', 0.8)
        )

        background_tasks.add_task(cache_analysis, cache_key, response_data.model_dump(mode='json'), settings.cache_ttl)
        logger.info("Wallet analysis completed", address=wallet_request.address, trust_score=analysis["score"], processing_time_ms=processing_time)
        return response_data

    except asyncio.TimeoutError:
        logger.error("Wallet analysis timed out", address=wallet_request.address)
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail="Wallet analysis timed out")
    except Exception as e:
        logger.error("Wallet analysis failed", address=wallet_request.address, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analysis failed: {str(e)}")

@app.post("/api/v2/chat", response_model=ChatResponse, tags=["AI Chat"])
@limiter.limit(settings.rate_limit)
async def chat_with_ai(
    request: Request, # Required for rate limiting
    chat_request: ChatRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """Chat with TrustLens AI for wallet analysis and crypto insights"""
    start_time = time.time()
    
    if not settings.enable_ai_analysis or not trustlens_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analysis is currently unavailable"
        )
    
    conversation_id = chat_request.conversation_id or f"chat_{int(time.time() * 1000)}"
    
    logger.info(
        "AI chat request received",
        message_preview=chat_request.message[:50],
        conversation_id=conversation_id
    )
    
    try:
        ai_response = await asyncio.wait_for(
            trustlens_agent.run_async(chat_request.message),
            timeout=float(settings.request_timeout)
        )
        
        processing_time = round((time.time() - start_time) * 1000, 2)
        
        logger.info(
            "AI chat completed",
            conversation_id=conversation_id,
            processing_time_ms=processing_time
        )
        
        return ChatResponse(
            response=ai_response,
            conversation_id=conversation_id,
            processing_time_ms=processing_time
        )
        
    except asyncio.TimeoutError:
        logger.error("AI chat timed out", conversation_id=conversation_id)
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="AI response timed out"
        )
    except Exception as e:
        logger.error(
            "AI chat failed",
            error=str(e),
            conversation_id=conversation_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI chat failed: {str(e)}"
        )

# --- Uvicorn Runner ---
if __name__ == "__main__":
    # To run this application from the root directory:
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
