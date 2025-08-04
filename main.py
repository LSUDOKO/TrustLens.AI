import os
import logging
import aiohttp
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from cogs.risk_analysis.risk_orchestrator import RiskOrchestrator
from database.redis_manager import RedisManager

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App state to hold singletons
app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize and store clients
    logger.info("Application startup: Initializing clients...")
    app_state['http_session'] = aiohttp.ClientSession()
    app_state['redis_manager'] = RedisManager(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379))
    )
    api_keys = {
        "BITSCRUNCH_API_KEY": os.getenv("BITSCRUNCH_API_KEY"),
        "BITQUERY_API_KEY": os.getenv("BITQUERY_API_KEY"),
    }
    app_state['risk_orchestrator'] = RiskOrchestrator(
        api_keys=api_keys,
        session=app_state['http_session'],
        redis_manager=app_state['redis_manager']
    )
    logger.info("Clients initialized successfully.")
    yield
    # Shutdown: Clean up resources
    logger.info("Application shutdown: Closing clients...")
    await app_state['http_session'].close()
    await app_state['redis_manager'].close()
    logger.info("Clients closed successfully.")

app = FastAPI(lifespan=lifespan, title="TrustLens.AI API", version="1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now, restrict in production
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Dependency to get the risk orchestrator
def get_orchestrator():
    return app_state['risk_orchestrator']

@app.post("/api/score")
async def get_score(address: str, orchestrator: RiskOrchestrator = Depends(get_orchestrator)):
    """Analyzes a wallet address and returns a comprehensive risk score."""
    if not address:
        raise HTTPException(status_code=400, detail="Wallet address is required.")
    
    try:
        logger.info(f"Analyzing address: {address}")
        analysis_result = await orchestrator.analyze_all(wallet_address=address)
        return analysis_result
    except Exception as e:
        logger.error(f"An error occurred during analysis for {address}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during analysis.")

@app.get("/")
def read_root():
    return {"message": "Welcome to the TrustLens.AI API. Use the /api/score endpoint to analyze a wallet."}

# To run this application:
# uvicorn main:app --reload
