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
        self.google_cloud_project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        self.google_cloud_location = os.getenv("GOOGLE_CLOUD_LOCATION")
        self.enable_ai_analysis = os.getenv("ENABLE_AI_ANALYSIS", "true").lower() == "true"
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.rate_limit = os.getenv("RATE_LIMIT", "10/minute")
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        self.api_key = os.getenv("API_KEY", "").strip()
        self.cache_ttl = int(os.getenv("CACHE_TTL", "3600")) # Cache for 1 hour by default

# Create a single, global instance of the settings
settings = Settings()

# Debugging: Print loaded API key to verify it's loaded correctly
print(f"--- Loaded API key from .env: {settings.api_key[:4]}... ---" if settings.api_key else "--- No API key loaded from .env ---")
