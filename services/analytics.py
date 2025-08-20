import logging
from datetime import datetime
from typing import Dict, Any, Optional

import redis.asyncio as redis

from config import settings

logger = logging.getLogger(__name__)

class ChatAnalytics:
    """Production analytics with error isolation"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def track_message(
        self, 
        user_id: str, 
        message_length: int, 
        response_time: float, 
        session_id: str
    ):
        """Track message analytics with error isolation"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Use pipeline for atomic operations
            async with self.redis.pipeline() as pipe:
                # Daily stats
                pipe.hincrby(f"daily_stats:{today}", "total_messages", 1)
                pipe.hincrby(f"daily_stats:{today}", "total_characters", message_length)
                pipe.hincrbyfloat(f"daily_stats:{today}", "total_response_time", response_time)
                pipe.expire(f"daily_stats:{today}", 30 * 24 * 3600)
                
                # User stats
                pipe.hincrby(f"user_stats:{user_id}", "message_count", 1)
                pipe.hset(f"user_stats:{user_id}", "last_seen", datetime.now().isoformat())
                
                # Session stats
                pipe.hincrby(f"session_stats:{session_id}", "message_count", 1)
                pipe.hincrbyfloat(f"session_stats:{session_id}", "total_response_time", response_time)
                pipe.expire(f"session_stats:{session_id}", 7 * 24 * 3600)
                
                await pipe.execute()
            
        except Exception as e:
            # Analytics failures shouldn't break the main flow
            logger.error(f"Analytics tracking failed (non-critical): {e}")

    async def get_daily_stats(self, date: str = None) -> Dict[str, Any]:
        """Get daily statistics with error handling"""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            
            stats = await self.redis.hgetall(f"daily_stats:{date}")
            
            if not stats:
                return {"date": date, "no_data": True}
            
            total_messages = int(stats.get(b"total_messages", 0))
            total_characters = int(stats.get(b"total_characters", 0))
            total_response_time = float(stats.get(b"total_response_time", 0))
            
            result = {
                "date": date,
                "total_messages": total_messages,
                "total_characters": total_characters,
                "total_response_time": total_response_time,
                "avg_message_length": total_characters / max(total_messages, 1),
                "avg_response_time": total_response_time / max(total_messages, 1)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}")
            return {"date": date or "unknown", "error": str(e)}