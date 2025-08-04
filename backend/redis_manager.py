import redis.asyncio as redis
import os
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class RedisManager:
    """Manages Redis connections, caching, and stream logging for the bot."""

    def __init__(self):
        """Initializes the Redis connection pool."""
        self.pool = None

    async def initialize(
        self,
        host: str = os.getenv("REDIS_HOST", "localhost"),
        port: int = int(os.getenv("REDIS_PORT", 6379)),
        password: Optional[str] = os.getenv("REDIS_PASSWORD"),
    ):
        """Creates the connection pool to Redis."""
        try:
            self.pool = redis.ConnectionPool(host=host, port=port, password=password, db=0, decode_responses=True)
            logger.info(f"Successfully connected to Redis at {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.pool = None

    async def close(self):
        """Closes the Redis connection pool."""
        if self.pool:
            await self.pool.disconnect()
            logger.info("Redis connection pool closed.")

    async def get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Gets a JSON value from the Redis cache."""
        if not self.pool:
            return None
        try:
            r = redis.Redis(connection_pool=self.pool)
            cached_data = await r.get(key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Redis GET failed for key '{key}': {e}")
        return None

    async def set_cache(self, key: str, value: Dict[str, Any], ttl_seconds: int = 1800):
        """Sets a JSON value in the Redis cache with a TTL (default 30 mins)."""
        if not self.pool:
            return
        try:
            r = redis.Redis(connection_pool=self.pool)
            await r.set(key, json.dumps(value), ex=ttl_seconds)
        except Exception as e:
            logger.error(f"Redis SET failed for key '{key}': {e}")

    async def log_event(self, stream_name: str, event_data: Dict[str, Any]):
        """Logs an event to a Redis Stream."""
        if not self.pool:
            return
        try:
            r = redis.Redis(connection_pool=self.pool)
            # Flatten dict values to strings for the stream
            flat_data = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in event_data.items()}
            await r.xadd(stream_name, flat_data)
            logger.info(f"Logged event to Redis Stream '{stream_name}'.")
        except Exception as e:
            logger.error(f"Redis XADD failed for stream '{stream_name}': {e}")
