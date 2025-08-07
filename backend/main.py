import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union
import os
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator, ValidationError
from pydantic.config import ConfigDict
from prometheus_fastapi_instrumentator import Instrumentator
import redis.asyncio as redis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import structlog

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Configuration
class Settings:
    """Application settings with validation"""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = self.environment == "development"
        self.frontend_origins = self._parse_origins()
        self.trusted_hosts = self._parse_hosts()
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.rate_limit = os.getenv("RATE_LIMIT", "100/minute")
        self.api_key = os.getenv("API_KEY")
        self.max_workers = int(os.getenv("MAX_WORKERS", "4"))
        self.cache_ttl = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        
    def _parse_origins(self) -> List[str]:
        origins = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://localhost:3000")
        parsed_origins = [origin.strip() for origin in origins.split(",")]
        print(f"DEBUG: Loaded CORS origins: {parsed_origins}")
        return parsed_origins
    
    def _parse_hosts(self) -> List[str]:
        hosts = os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1")
        return [host.strip() for host in hosts.split(",")]

settings = Settings()

# Redis connection pool
redis_client: Optional[redis.Redis] = None

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Security
security = HTTPBearer(auto_error=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global redis_client
    
    # Startup
    logger.info("Starting TrustLens.AI API", version="2.0.0", environment=settings.environment)
    
    try:
        # Initialize Redis connection
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30,
            retry_on_timeout=True,
            max_connections=20
        )
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning("Redis connection failed, running without cache", error=str(e))
        redis_client = None
    
    # Validate scoring module
    try:
        from scoring import analyze_wallet
        logger.info("Scoring module loaded successfully")
    except ImportError as e:
        logger.error("Failed to import scoring module", error=str(e))
        sys.exit(1)
    
    yield
    
    # Shutdown
    logger.info("Shutting down TrustLens.AI API")
    if redis_client:
        await redis_client.close()

# Initialize FastAPI app
app = FastAPI(
    title="TrustLens.AI API",
    description="Advanced blockchain wallet trust scoring and risk analysis platform",
    version="2.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
    openapi_url="/openapi.json" if settings.debug else None,
)

# Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=86400,  # Cache preflight requests for 24 hours
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_hosts + ["testserver"]
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SlowAPIMiddleware)

# Add Prometheus metrics
if not settings.debug:
    instrumentator = Instrumentator()
    instrumentator.instrument(app).expose(app)

# Rate limiting error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enhanced Pydantic models
class WalletAnalysisRequest(BaseModel):
    """Request model for wallet analysis with validation"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    address: str = Field(
        ...,
        min_length=26,
        max_length=62,
        description="Blockchain wallet address (Bitcoin, Ethereum, etc.)"
    )
    blockchain: Optional[str] = Field(
        default="ethereum",
        pattern="^(ethereum|bitcoin|polygon|bsc|avalanche)$",
        description="Blockchain network"
    )
    include_metadata: bool = Field(
        default=True,
        description="Include additional wallet metadata in response"
    )
    
    @validator('address')
    def validate_address(cls, v):
        """Validate wallet address format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Address cannot be empty")
        
        v = v.strip()
        
        # Basic format validation (can be enhanced per blockchain)
        if v.startswith('0x') and len(v) == 42:  # Ethereum
            return v.lower()
        elif len(v) >= 26 and len(v) <= 35:  # Bitcoin
            return v
        elif len(v) == 44:  # Solana
            return v
        else:
            raise ValueError("Invalid wallet address format")

class RiskFactor(BaseModel):
    """Risk factor with severity and confidence"""
    type: str = Field(..., description="Risk factor type")
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    description: str = Field(..., description="Human-readable description")
    evidence: Optional[Dict] = Field(default=None, description="Supporting evidence")

class WalletMetadata(BaseModel):
    """Extended wallet metadata"""
    age_days: Optional[int] = Field(default=None, ge=0)
    transaction_count: Optional[int] = Field(default=None, ge=0)
    contract_interactions: Optional[int] = Field(default=None, ge=0)
    balance_usd: Optional[float] = Field(default=None, ge=0)
    token_count: Optional[int] = Field(default=None, ge=0)
    last_activity: Optional[datetime] = None
    creation_date: Optional[datetime] = None
    labels: Optional[List[str]] = Field(default_factory=list)

class WalletAnalysisResponse(BaseModel):
    """Enhanced response model with detailed analysis"""
    address: str
    blockchain: str
    trust_score: int = Field(..., ge=0, le=100, description="Trust score (0-100)")
    risk_category: str = Field(..., pattern="^(very_low|low|medium|high|very_high)$")
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    explanation: str = Field(..., description="Detailed explanation of the score")
    metadata: Optional[WalletMetadata] = None
    analysis_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_time_ms: Optional[float] = None
    cached: bool = False
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence")

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    redis_connected: bool
    checks: Dict[str, bool]

class ErrorResponse(BaseModel):
    """Standardized error response"""
    error: str
    message: str
    timestamp: datetime
    request_id: Optional[str] = None

class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., min_length=1, max_length=1000, description="User message")

class ChatResponse(BaseModel):
    """Chat response model"""
    response: str = Field(..., description="AI agent response")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TransactionSimulationRequest(BaseModel):
    """Transaction simulation request"""
    from_address: str = Field(..., description="Sender wallet address")
    to_address: str = Field(..., description="Recipient address")
    amount_eth: float = Field(..., gt=0, description="Transaction amount in ETH")
    transaction_type: str = Field(default="transfer", description="Type of transaction")

class TransactionSimulationResponse(BaseModel):
    """Transaction simulation response"""
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str
    warnings: List[str]
    recommendations: List[str]
    estimated_loss_probability: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Dependency functions
async def get_redis() -> Optional[redis.Redis]:
    """Get Redis client dependency"""
    return redis_client

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """Verify API key for protected endpoints"""
    if not settings.api_key:
        return True  # No auth required if not configured
    
    if not credentials or credentials.credentials != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True

# Utility functions
async def get_cache_key(address: str, blockchain: str) -> str:
    """Generate cache key for wallet analysis"""
    return f"wallet_analysis:{blockchain}:{address.lower()}"

async def cache_analysis(key: str, analysis: Dict, ttl: int = None) -> None:
    """Cache analysis result"""
    if not redis_client:
        return
    
    try:
        await redis_client.setex(
            key,
            ttl or settings.cache_ttl,
            analysis.model_dump_json() if hasattr(analysis, 'model_dump_json') else str(analysis)
        )
    except Exception as e:
        logger.warning("Failed to cache analysis", error=str(e), key=key)

async def get_cached_analysis(key: str) -> Optional[Dict]:
    """Retrieve cached analysis"""
    if not redis_client:
        return None
    
    try:
        cached = await redis_client.get(key)
        if cached:
            import json
            return json.loads(cached)
    except Exception as e:
        logger.warning("Failed to retrieve cached analysis", error=str(e), key=key)
    
    return None

# Error handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="validation_error",
            message=f"Invalid request data: {exc.errors()}",
            timestamp=datetime.now(timezone.utc)
        ).model_dump()
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="http_error",
            message=exc.detail,
            timestamp=datetime.now(timezone.utc)
        ).model_dump()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="internal_error",
            message="An unexpected error occurred" if not settings.debug else str(exc),
            timestamp=datetime.now(timezone.utc)
        ).model_dump()
    )

# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()
    
    # Generate request ID
    request_id = f"{int(start_time * 1000)}-{hash(str(request.url)) % 10000}"
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        path=request.url.path,
        client_ip=get_remote_address(request),
        request_id=request_id
    )
    
    try:
        response = await call_next(request)
        
        # Calculate processing time
        process_time = (time.time() - start_time) * 1000
        
        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            processing_time_ms=round(process_time, 2),
            request_id=request_id
        )
        
        response.headers["X-Process-Time"] = str(round(process_time, 2))
        response.headers["X-Request-ID"] = request_id
        
        return response
        
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        logger.error(
            "Request failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            processing_time_ms=round(process_time, 2),
            request_id=request_id
        )
        raise

# API Routes
@app.get("/", tags=["Root"])
@limiter.limit(settings.rate_limit)
async def read_root(request: Request):
    """Root endpoint with API information"""
    return {
        "name": "TrustLens.AI API",
        "version": "2.0.0",
        "description": "Advanced blockchain wallet trust scoring and risk analysis platform",
        "environment": settings.environment,
        "docs_url": "/docs" if settings.debug else None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/v2/analyze", response_model=WalletAnalysisResponse, tags=["Analysis"])
@limiter.limit(settings.rate_limit)
async def analyze_wallet_v2(
    request: Request,
    wallet_request: WalletAnalysisRequest,
    background_tasks: BackgroundTasks,
    authenticated: bool = Depends(verify_api_key)
):
    """Enhanced wallet analysis endpoint with caching"""
    start_time = time.time()
    request_id = request.state.request_id

    logger.info(
        "Received wallet analysis request",
        address=wallet_request.address,
        blockchain=wallet_request.blockchain,
        request_id=request_id
    )

    # Check cache first
    cache_key = await get_cache_key(wallet_request.address, wallet_request.blockchain)
    cached_result = await get_cached_analysis(cache_key)
    if cached_result:
        cached_result["cached"] = True
        cached_result["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        logger.info("Returning cached analysis", address=wallet_request.address)
        return WalletAnalysisResponse(**cached_result)

    try:
        from scoring import analyze_wallet

        logger.info("Performing new analysis", address=wallet_request.address)

        # Use asyncio.wait_for to enforce a timeout on the analysis
        api_key = os.getenv("ETHERSCAN_API_KEY")
        full_analysis = await asyncio.wait_for(
            analyze_wallet(wallet_request.address, api_key, include_ai_features=True),
            timeout=settings.request_timeout
        )
        # analyze_wallet returns the analysis directly
        analysis = full_analysis
        processing_time = round((time.time() - start_time) * 1000, 2)

        response_data = WalletAnalysisResponse(
            address=wallet_request.address,
            blockchain=wallet_request.blockchain,
            trust_score=analysis['trust_score'],
            risk_level=analysis['risk_level'].value if hasattr(analysis['risk_level'], 'value') else analysis['risk_level'],
            risk_factors=[RiskFactor(**rf) for rf in analysis['risk_factors']],
            explanation=analysis['explanation'],
            metadata=WalletMetadata(**full_analysis.get("raw_metrics", {}).get("basic", {})),
            processing_time_ms=processing_time,
            cached=False,
            confidence_score=analysis.get('confidence', 0.8)
        )

        # Cache result in background
        background_tasks.add_task(
            cache_analysis,
            cache_key,
            response_data.model_dump(),
            settings.cache_ttl
        )

        logger.info(
            "Wallet analysis completed",
            address=wallet_request.address,
            trust_score=analysis["trust_score"],
            processing_time_ms=processing_time
        )

        return response_data

    except asyncio.TimeoutError:
        logger.error("Wallet analysis timed out", address=wallet_request.address)
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Wallet analysis timed out"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Wallet analysis failed",
            address=wallet_request.address,
            error=str(e),
            processing_time_ms=round((time.time() - start_time) * 1000, 2)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )

# Legacy endpoint for backward compatibility
@app.post("/api/score", response_model=WalletAnalysisResponse, tags=["Legacy"])
@limiter.limit(settings.rate_limit)
async def analyze_wallet_legacy(
    request: Request,
    wallet_request: WalletAnalysisRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """Legacy wallet analysis endpoint (deprecated)"""
    logger.warning("Legacy endpoint used", path="/api/score", address=wallet_request.address)
    
    # Convert to new format and call v2 endpoint
    new_request = WalletAnalysisRequest(
        address=wallet_request.address,
        blockchain="ethereum",  # Default for legacy
        include_metadata=True
    )
    
    background_tasks = BackgroundTasks()
    return await analyze_wallet_v2(request, new_request, background_tasks)

@app.get("/health", response_model=HealthResponse, tags=["System"])
@limiter.limit("1000/minute")  # Higher limit for health checks
async def health_check(request: Request):
    """Comprehensive health check endpoint"""
    start_time = time.time()
    
    # Check Redis connection
    redis_connected = False
    if redis_client:
        try:
            await redis_client.ping()
            redis_connected = True
        except Exception:
            pass
    
    # Check scoring module
    scoring_available = False
    try:
        from scoring import analyze_wallet
        scoring_available = True
    except ImportError:
        pass
    
    return HealthResponse(
        status="healthy" if redis_connected and scoring_available else "degraded",
        timestamp=datetime.now(timezone.utc),
        version="2.0.0",
        environment=settings.environment,
        uptime_seconds=time.time() - start_time,
        redis_connected=redis_connected,
        checks={
            "redis": redis_connected,
            "scoring_module": scoring_available,
            "database": True,  # Add actual DB check if needed
        }
    )

@app.post("/api/v2/chat", response_model=ChatResponse, tags=["AI Agent"])
@limiter.limit(settings.rate_limit)
async def chat_with_ai(
    request: Request,
    chat_request: ChatRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """AI chat endpoint for wallet analysis queries"""
    start_time = time.time()
    
    logger.info(
        "Received chat request",
        message=chat_request.message[:100] + "..." if len(chat_request.message) > 100 else chat_request.message
    )
    
    try:
        # Simple pattern matching for wallet analysis
        message = chat_request.message.lower().strip()
        
        # Extract wallet address from message
        import re
        
        # Look for Ethereum addresses (0x followed by 40 hex characters)
        eth_pattern = r'0x[a-fA-F0-9]{40}'
        eth_matches = re.findall(eth_pattern, chat_request.message)
        
        # Look for ENS domains
        ens_pattern = r'\b\w+\.eth\b'
        ens_matches = re.findall(ens_pattern, chat_request.message)
        
        wallet_address = None
        if eth_matches:
            wallet_address = eth_matches[0]
        elif ens_matches:
            wallet_address = ens_matches[0]
        
        if wallet_address:
            # Perform wallet analysis
            try:
                from scoring import analyze_wallet
                
                logger.info("Analyzing wallet for chat", address=wallet_address)
                
                # Use asyncio.wait_for to enforce timeout
                api_key = os.getenv("ETHERSCAN_API_KEY")
                gemini_api_key = os.getenv("GEMINI_API_KEY")
                full_analysis = await asyncio.wait_for(
                    analyze_wallet(wallet_address, api_key, include_ai_features=True),
                    timeout=settings.request_timeout
                )
                
                # analyze_wallet returns the analysis directly
                analysis = full_analysis
                raw_metrics = full_analysis.get('raw_metrics', {})
                
                # Debug logging
                logger.info(f"Chat analysis result: trust_score={analysis.get('trust_score', 'NOT_FOUND')}, risk_level={analysis.get('risk_level', 'NOT_FOUND')}")
                
                # Generate natural language response
                trust_score = analysis.get('trust_score', 0)
                risk_level = analysis.get('risk_level', 'unknown')
                if hasattr(risk_level, 'value'):
                    risk_level = risk_level.value
                
                # Format response based on trust score
                if trust_score >= 80:
                    trust_desc = "highly trustworthy"
                    emoji = "✅"
                elif trust_score >= 60:
                    trust_desc = "moderately trustworthy"
                    emoji = "⚠️"
                elif trust_score >= 40:
                    trust_desc = "somewhat risky"
                    emoji = "🔶"
                else:
                    trust_desc = "high risk"
                    emoji = "🚨"
                
                # Build organized response with HTML formatting
                response_parts = [
                    f"{emoji} <b>WALLET ANALYSIS REPORT</b>",
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    f"",
                    f"📍 <b>Address:</b> {wallet_address}",
                    f"",
                    f"🎯 <b>TRUST ASSESSMENT</b>",
                    f"   • <b>Score:</b> {trust_score}/100",
                    f"   • <b>Rating:</b> {trust_desc.title()}",
                    f"   • <b>Risk Level:</b> {risk_level.replace('_', ' ').title()}",
                    f"",
                    f"📊 <b>WALLET METRICS</b>"
                ]
                
                # Add AI-powered behavioral clustering
                behavioral_clusters = analysis.get('behavioral_clusters', [])
                if behavioral_clusters:
                    response_parts.append(f"")
                    response_parts.append(f"🧠 <b>AI BEHAVIORAL ANALYSIS</b>")
                    for cluster in behavioral_clusters[:2]:  # Show top 2 clusters
                        response_parts.append(f"   🎯 <b>{cluster['cluster_type'].replace('_', ' ').title()}:</b> {cluster['description']}")
                        response_parts.append(f"      Similarity: {cluster['similarity_score']*100:.0f}%")
                
                # Add wallet metrics in organized sections
                if raw_metrics:
                    # Basic Info
                    if raw_metrics.get('current_balance') is not None:
                        balance = raw_metrics['current_balance']
                        response_parts.append(f"   💰 <b>Balance:</b> {balance:.4f} ETH (${balance * 2500:.0f} USD)")
                    
                    if raw_metrics.get('wallet_age'):
                        age_days = raw_metrics['wallet_age']
                        if age_days >= 365:
                            age_str = f"{age_days // 365} year(s), {age_days % 365} days"
                        else:
                            age_str = f"{age_days} days"
                        response_parts.append(f"   ⏰ <b>Age:</b> {age_str}")
                    
                    # Activity Metrics
                    response_parts.append(f"")
                    response_parts.append(f"📈 <b>ACTIVITY ANALYSIS</b>")
                    
                    if raw_metrics.get('total_transactions'):
                        response_parts.append(f"   🔄 <b>Total Transactions:</b> {raw_metrics['total_transactions']:,}")
                    
                    if raw_metrics.get('unique_counterparties'):
                        response_parts.append(f"   👥 <b>Unique Counterparties:</b> {raw_metrics['unique_counterparties']:,}")
                    
                    if raw_metrics.get('last_activity_days') is not None:
                        last_activity = raw_metrics['last_activity_days']
                        if last_activity == 0:
                            activity_str = "Today"
                        elif last_activity == 1:
                            activity_str = "Yesterday"
                        else:
                            activity_str = f"{last_activity} days ago"
                        response_parts.append(f"   📅 <b>Last Activity:</b> {activity_str}")
                    
                    # Transaction Patterns
                    if raw_metrics.get('average_transaction_value') or raw_metrics.get('contract_interactions'):
                        response_parts.append(f"")
                        response_parts.append(f"🔍 <b>TRANSACTION PATTERNS</b>")
                        
                        if raw_metrics.get('average_transaction_value'):
                            avg_value = raw_metrics['average_transaction_value']
                            response_parts.append(f"   💸 <b>Average Transaction:</b> {avg_value:.4f} ETH")
                        
                        if raw_metrics.get('contract_interactions'):
                            contracts = raw_metrics['contract_interactions']
                            total_tx = raw_metrics.get('total_transactions', 1)
                            contract_pct = (contracts / total_tx) * 100
                            response_parts.append(f"   🤖 <b>Smart Contract Usage:</b> {contracts:,} transactions ({contract_pct:.1f}%)")
                
                # Component Scores
                component_scores = analysis.get('component_scores', {})
                if component_scores:
                    response_parts.append(f"")
                    response_parts.append(f"⚡ <b>DETAILED SCORES</b>")
                    score_items = [
                        ('balance', '💰 Balance', component_scores.get('balance', 0)),
                        ('activity', '📈 Activity', component_scores.get('activity', 0)),
                        ('age', '⏰ Age', component_scores.get('age', 0)),
                        ('transactions', '🔄 Transactions', component_scores.get('transactions', 0)),
                        ('network', '🌐 Network', component_scores.get('network', 0)),
                        ('risk', '🛡️ Risk Factors', component_scores.get('risk', 0))
                    ]
                    
                    for key, label, score in score_items:
                        bar = "█" * (score // 10) + "░" * (10 - score // 10)
                        response_parts.append(f"   {label}: <b>{score:2d}/100</b> [{bar}]")
                
                # Enhanced explainable risk factors
                explainable_risks = analysis.get('explainable_risks', [])
                if explainable_risks:
                    response_parts.append(f"")
                    response_parts.append(f"🔍 <b>EXPLAINABLE RISK ANALYSIS</b>")
                    for i, risk in enumerate(explainable_risks[:2], 1):  # Show top 2 risks
                        severity_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(risk['severity'], "⚪")
                        response_parts.append(f"   <b>{i}. {risk['title']}</b> {severity_emoji}")
                        response_parts.append(f"      {risk['explanation'][:100]}...")
                        response_parts.append(f"      <i>Recommendation: {risk['recommendation'][:80]}...</i>")
                
                # Fallback to basic risk factors if no explainable risks
                elif analysis.get('risk_factors', []):
                    risk_factors = analysis.get('risk_factors', [])
                    response_parts.append(f"")
                    response_parts.append(f"⚠️ <b>RISK FACTORS</b>")
                    for i, factor in enumerate(risk_factors[:3], 1):  # Limit to top 3
                        if isinstance(factor, dict):
                            factor_text = factor.get('description', 'Unknown risk factor')
                        else:
                            factor_text = str(factor)
                        response_parts.append(f"   <b>{i}.</b> {factor_text}")
                
                # Data source with better formatting
                data_source = raw_metrics.get('data_source', 'unknown')
                response_parts.append(f"")
                response_parts.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                if data_source == 'simulated':
                    response_parts.append("⚠️ <i>This analysis uses simulated data for demonstration purposes.</i>")
                elif data_source == 'real':
                    response_parts.append("✅ <i>Analysis powered by real blockchain data from Etherscan API</i>")
                else:
                    response_parts.append(f"ℹ️ <i>Data source: {data_source}</i>")
                
                response_text = "\n".join(response_parts)
                
            except asyncio.TimeoutError:
                response_text = f"⏱️ Analysis of {wallet_address} timed out. Please try again later."
            except Exception as e:
                logger.error("Chat wallet analysis failed", error=str(e), address=wallet_address)
                response_text = f"❌ Sorry, I couldn't analyze {wallet_address}. Error: {str(e)}"
        
        else:
            # Check if this is a follow-up question about previous analysis
            if any(word in message for word in ['why', 'explain', 'how', 'what does', 'tell me more', 'details']):
                try:
                    from ai_features import GeminiAIIntegration
                    gemini_api_key = os.getenv("GEMINI_API_KEY")
                    
                    if gemini_api_key:
                        gemini_ai = GeminiAIIntegration(gemini_api_key)
                        # For now, provide a general response since we don't have context storage
                        response_text = await gemini_ai.answer_followup_question(
                            message, 
                            {"context": "General blockchain wallet analysis question"}
                        )
                    else:
                        response_text = """🤖 <b>AI Assistant Unavailable</b>
                        
I'd love to provide detailed explanations, but the AI assistant requires a Gemini API key to be configured.

For now, I can help you with:
• Wallet address analysis
• Basic risk assessment
• Transaction pattern analysis

Try asking me to analyze a specific wallet address!"""
                        
                except Exception as e:
                    logger.error(f"Gemini AI error: {str(e)}")
                    response_text = f"Sorry, I couldn't process your question. Please try analyzing a wallet address instead."
            
            # No wallet address found, provide general help
            elif any(word in message for word in ['help', 'how', 'what', 'guide']):
                response_text = """🔍 <b>TrustLens AI Agent Help</b>

I can analyze Ethereum wallet addresses and ENS domains to provide trust scores and risk assessments.

<b>How to use:</b>
• Send me a wallet address like: 0x1234...abcd
• Or an ENS domain like: vitalik.eth
• Ask me to "analyze [address]" or just paste the address

<b>What I analyze:</b>
• Trust score (0-100)
• Risk level assessment
• Transaction patterns
• Wallet age and activity
• Security indicators

<b>Example queries:</b>
• "analyze 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
• "what's the trust score for vitalik.eth?"
• "check this wallet: 0x1234..."

Try sending me a wallet address to get started! 🚀"""
            
            elif any(word in message for word in ['hello', 'hi', 'hey', 'start']):
                response_text = """👋 Hello! I'm the TrustLens AI agent.

I can analyze any Ethereum wallet address or ENS name to provide:
• <b>Trust scores and risk assessments</b>
• <b>Transaction pattern analysis</b>
• <b>Security insights</b>
• <b>Wallet activity metrics</b>

Just send me a wallet address (0x...) or ENS domain (.eth) and I'll analyze it for you!

Need help? Just ask "help" or "how to use"."""
            
            else:
                response_text = """🤔 I didn't find a wallet address in your message.

To analyze a wallet, please provide:
• <b>An Ethereum address</b> (starts with 0x, 42 characters)
• <b>An ENS domain</b> (ends with .eth)

<b>Examples:</b>
• 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
• vitalik.eth

You can also ask for "help" to learn more about what I can do!"""
        
        processing_time = round((time.time() - start_time) * 1000, 2)
        
        logger.info(
            "Chat request completed",
            processing_time_ms=processing_time,
            response_length=len(response_text)
        )
        
        return ChatResponse(response=response_text)
        
    except Exception as e:
        logger.error("Chat request failed", error=str(e))
        return ChatResponse(
            response="❌ Sorry, I encountered an error processing your request. Please try again."
        )

@app.post("/api/v2/simulate-transaction", response_model=TransactionSimulationResponse, tags=["AI Features"])
@limiter.limit(settings.rate_limit)
async def simulate_transaction(
    request: Request,
    sim_request: TransactionSimulationRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """Simulate transaction risk assessment"""
    start_time = time.time()
    
    try:
        from ai_features import TransactionSimulator
        from scoring import analyze_wallet
        
        # Analyze the sender wallet first
        api_key = os.getenv("ETHERSCAN_API_KEY")
        sender_analysis = await asyncio.wait_for(
            analyze_wallet(sim_request.from_address, api_key, include_ai_features=False),
            timeout=settings.request_timeout
        )
        
        # Extract wallet metrics
        sender_metrics_data = sender_analysis.get('raw_metrics', {})
        
        # Create a simplified WalletMetrics object for simulation
        from scoring import WalletMetrics
        sender_metrics = WalletMetrics(
            address=sim_request.from_address,
            current_balance=sender_metrics_data.get('current_balance', 0),
            total_transactions=sender_metrics_data.get('total_transactions', 0),
            wallet_age=sender_metrics_data.get('wallet_age', 0),
            average_transaction_value=sender_metrics_data.get('average_transaction_value', 0),
            max_transaction_value=sender_metrics_data.get('max_transaction_value', 0),
            unique_counterparties=sender_metrics_data.get('unique_counterparties', 0),
            gas_efficiency_score=sender_metrics_data.get('gas_efficiency_score', 50),
            activity_frequency=sender_metrics_data.get('activity_frequency', 0),
            last_activity_days=sender_metrics_data.get('last_activity_days', 999),
            incoming_volume=sender_metrics_data.get('incoming_volume', 0),
            outgoing_volume=sender_metrics_data.get('outgoing_volume', 0),
            net_flow=sender_metrics_data.get('net_flow', 0),
            contract_interactions=sender_metrics_data.get('contract_interactions', 0),
            failed_transactions=sender_metrics_data.get('failed_transactions', 0),
            data_source=sender_metrics_data.get('data_source', 'unknown')
        )
        
        # Perform transaction simulation
        simulator = TransactionSimulator()
        risk_assessment = await simulator.assess_transaction_risk(
            sender_metrics,
            sim_request.to_address,
            sim_request.amount_eth,
            sim_request.transaction_type
        )
        
        processing_time = round((time.time() - start_time) * 1000, 2)
        
        logger.info(
            "Transaction simulation completed",
            from_address=sim_request.from_address,
            to_address=sim_request.to_address,
            risk_score=risk_assessment.risk_score,
            processing_time_ms=processing_time
        )
        
        return TransactionSimulationResponse(
            risk_score=risk_assessment.risk_score,
            risk_level=risk_assessment.risk_level,
            warnings=risk_assessment.warnings,
            recommendations=risk_assessment.recommendations,
            estimated_loss_probability=risk_assessment.estimated_loss_probability
        )
        
    except Exception as e:
        logger.error("Transaction simulation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {str(e)}"
        )

@app.get("/metrics", tags=["System"])
async def get_metrics():
    """Application metrics endpoint"""
    if settings.debug:
        return {"message": "Metrics available at /metrics in production"}
    
    # Prometheus metrics are automatically exposed by instrumentator
    return {"message": "Metrics endpoint"}

# Development routes
if settings.debug:
    @app.get("/debug/cache/{address}", tags=["Debug"])
    async def debug_cache(address: str, blockchain: str = "ethereum"):
        """Debug cache contents (development only)"""
        cache_key = await get_cache_key(address, blockchain)
        cached = await get_cached_analysis(cache_key)
        return {"cache_key": cache_key, "cached_data": cached}

# Application startup
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=settings.debug,
        workers=1 if settings.debug else settings.max_workers,
        log_config=None,  # Use structlog instead
        access_log=False,  # Custom logging middleware
    )