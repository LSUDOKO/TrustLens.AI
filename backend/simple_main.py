from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="TrustLens.AI API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class WalletAnalysisRequest(BaseModel):
    address: str

class WalletAnalysisResponse(BaseModel):
    address: str
    trust_score: int
    risk_tags: List[str]
    explanation: str

@app.get("/")
def read_root():
    return {"message": "TrustLens.AI API", "version": "1.0.0", "status": "operational"}

@app.post("/api/score", response_model=WalletAnalysisResponse)
async def analyze_wallet(request: WalletAnalysisRequest):
    """Analyze a wallet address and return trust score with risk factors"""
    try:
        # Import scoring logic
        from scoring import calculate_trust_score, get_wallet_data
        
        # Get wallet data
        wallet_data = await get_wallet_data(request.address)
        
        # Calculate trust score
        analysis = calculate_trust_score(wallet_data)
        
        return WalletAnalysisResponse(
            address=request.address,
            trust_score=analysis["score"],
            risk_tags=analysis["risk_tags"],
            explanation=analysis["explanation"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
