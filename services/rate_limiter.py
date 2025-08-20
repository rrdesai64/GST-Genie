import logging
from typing import Dict, Any, Tuple
from datetime import datetime
import uuid

import redis.asyncio as redis

logger = logging.getLogger(__name__)

class RateLimiter:
    """Enhanced rate limiting with user tiers"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def is_rate_limited(
        self, 
        user_id: str, 
        endpoint: str, 
        max_requests: int = 60, 
        window_seconds: int = 60
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit with sliding window"""
        try:
            key = f"rate_limit:{endpoint}:{user_id}"
            current_time = datetime.now().timestamp()
            window_start = current_time - window_seconds
            
            # Clean old entries and count current
            async with self.redis.pipeline() as pipe:
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zcard(key)
                pipe.expire(key, window_seconds)
                results = await pipe.execute()
            
            current_requests = results[1]
            
            if current_requests >= max_requests:
                return True, {
                    "rate_limited": True,
                    "requests_made": current_requests,
                    "max_requests": max_requests,
                    "window_seconds": window_seconds,
                    "retry_after": window_seconds
                }
            
            # Add current request
            await self.redis.zadd(key, {str(uuid.uuid4()): current_time})
            
            return False, {
                "rate_limited": False,
                "requests_made": current_requests + 1,
                "max_requests": max_requests,
                "window_seconds": window_seconds
            }
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # Fail open - don't block on rate limiter errors
            return False, {"error": str(e)}