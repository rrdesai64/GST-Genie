from typing import AsyncGenerator
import redis.asyncio as redis
from fastapi import Depends

from database import db_manager
from config import settings
from services.chat_service import ChatService
from services.gemini_service import StreamingGeminiService
from services.analytics import ChatAnalytics
from services.rate_limiter import RateLimiter
from auth import get_current_active_user

# Redis connection pool
redis_pool = None

async def get_redis() -> redis.Redis:
    """Get Redis connection"""
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.from_url(
            str(settings.redis_url),
            password=settings.redis_password,
            decode_responses=False,
            socket_connect_timeout=5,
            socket_keepalive=True,
            max_connections=20,
            health_check_interval=30,
        )
    return redis_pool

async def get_chat_service(db: AsyncSession = Depends(db_manager.get_session_dependency)) -> ChatService:
    return ChatService(db)

async def get_gemini_service() -> StreamingGeminiService:
    """Get Gemini service dependency"""
    return StreamingGeminiService()

async def get_analytics() -> ChatAnalytics:
    """Get analytics service dependency"""
    redis_client = await get_redis()
    return ChatAnalytics(redis_client)

async def get_rate_limiter() -> RateLimiter:
    """Get rate limiter dependency"""
    redis_client = await get_redis()
    return RateLimiter(redis_client)

# Re-export auth dependencies
get_current_user = get_current_active_user