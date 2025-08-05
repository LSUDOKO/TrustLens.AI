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
        return [origin.strip() for origin in origins.split(",")]
    
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
        full_analysis = await asyncio.wait_for(
            analyze_wallet(wallet_request.address),
            timeout=settings.request_timeout
        )
        analysis = full_analysis['analysis']
        processing_time = round((time.time() - start_time) * 1000, 2)

        response_data = WalletAnalysisResponse(
            address=wallet_request.address,
            blockchain=wallet_request.blockchain,
            trust_score=analysis['score'],
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
            trust_score=analysis["score"],
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