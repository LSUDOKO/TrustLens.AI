import os
from dotenv import load_dotenv
from pathlib import Path

# Explicitly load the .env file from the project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Settings:
    """Centralized application settings"""
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
        self.enable_ai_analysis = os.getenv("ENABLE_AI_ANALYSIS", "true").lower() == "true"
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.environment = os.getenv("ENVIRONMENT", "development")

# Create a single, global instance of the settings
settings = Settings()
