import sys
import uvicorn
import redis.asyncio as redis
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

from backend.settings import settings
from backend.scoring import analyze_wallet
from backend.alith_agent import create_agent, get_trustlens_agent, is_agent_healthy

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")

# --- Global Variables ---
redis_client: redis.Redis | None = None
trustlens_agent = None

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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
)

# --- Pydantic Models ---
class ScoreRequest(BaseModel):
    address: str

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

# --- API Endpoints --- #
@app.get("/")
def read_root():
    """Root endpoint with a welcome message."""
    return {"message": "Welcome to the TrustLens.AI API. Use /api/score or /api/chat."}

@app.get("/api/health")
async def health_check():
    """Check the health of the API and its components"""
    agent_health = is_agent_healthy()
    redis_status = "connected" if redis_client and await redis_client.ping() else "disconnected"
    return {
        "status": "healthy" if agent_health["status"] == "healthy" and redis_status == "connected" else "degraded",
        "redis_status": redis_status,
        "ai_agent_status": agent_health
    }

@app.post("/api/score")
async def get_wallet_score(request: ScoreRequest):
    """
    Analyzes a wallet address and returns a comprehensive trust score and analysis.
    This is the primary data endpoint.
    """
    if not request.address:
        raise HTTPException(status_code=400, detail="Wallet address is required.")

    try:
        api_key = os.getenv("ETHERSCAN_API_KEY")
        analysis_result = await analyze_wallet(request.address, api_key=api_key)
        return analysis_result
    except Exception as e:
        print(f"Error in /api/score: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

@app.post("/api/chat")
async def chat_with_agent(request: ChatRequest):
    """
    Handles conversational queries with the Alith AI agent.
    """
    if not trustlens_agent:
        raise HTTPException(
            status_code=503,
            detail="AI Agent is not available. Check server configuration."
        )
    
    try:
        # Get the AI's reply using the agent's chat method
        response = await trustlens_agent.chat_async(request.message)
        return ChatResponse(reply=response)
    except Exception as e:
        logger.error(f"Error during chat processing: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred with the AI agent."
        )

# --- Uvicorn Runner ---
if __name__ == "__main__":
    # To run this application from the root directory:
    # uvicorn main:app --reload
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
