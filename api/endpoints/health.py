from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from datetime import datetime
import logging
import asyncio

from database import db_manager
from schemas import HealthResponse, ErrorResponse
from .dependencies import get_redis

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/health",
    response_model=HealthResponse,
    responses={500: {"model": ErrorResponse, "description": "Health check failed"}}
)
async def health_check(redis_client: redis.Redis = Depends(get_redis)):
    """Comprehensive health check endpoint"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(),
            "components": {},
            "response_time": {}
        }
        
        # Check Redis with timeout
        try:
            start_time = datetime.now()
            await asyncio.wait_for(redis_client.ping(), timeout=2.0)
            response_time = (datetime.now() - start_time).total_seconds()
            health_status["components"]["redis"] = {"status": "healthy", "response_time": response_time}
        except asyncio.TimeoutError:
            health_status["components"]["redis"] = {"status": "unhealthy", "error": "Timeout"}
            health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["redis"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "degraded"
        
        # Check Database with timeout
        try:
            start_time = datetime.now()
            async with db_manager.get_session() as db:
                await asyncio.wait_for(db.execute("SELECT 1"), timeout=3.0)
                response_time = (datetime.now() - start_time).total_seconds()
                health_status["components"]["database"] = {"status": "healthy", "response_time": response_time}
        except asyncio.TimeoutError:
            health_status["components"]["database"] = {"status": "unhealthy", "error": "Timeout"}
            health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["database"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "degraded"
        
        return HealthResponse(**health_status)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Health check failed"
        )

@router.get("/health/ready")
async def readiness_check(redis_client: redis.Redis = Depends(get_redis)):
    """Kubernetes/Docker readiness probe"""
    try:
        # Quick checks for readiness with timeouts
        await asyncio.wait_for(redis_client.ping(), timeout=1.0)
        
        async with db_manager.get_session() as db:
            await asyncio.wait_for(db.execute("SELECT 1"), timeout=2.0)
        
        return {"status": "ready", "timestamp": datetime.now().isoformat()}
        
    except asyncio.TimeoutError:
        logger.warning("Readiness check timeout")
        raise HTTPException(status_code=503, detail="Service not ready - timeout")
    except Exception as e:
        logger.warning(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")

@router.get("/health/live")
async def liveness_check():
    """Kubernetes/Docker liveness probe"""
    return {"status": "alive", "timestamp": datetime.now().isoformat()}

@router.get("/health/services")
async def services_health_check(redis_client: redis.Redis = Depends(get_redis)):
    """Detailed services health check"""
    services = {
        "redis": False,
        "database": False,
        "overall": False
    }
    
    try:
        # Redis health
        try:
            await redis_client.ping()
            services["redis"] = True
        except:
            services["redis"] = False
        
        # Database health
        try:
            async with db_manager.get_session() as db:
                await db.execute("SELECT 1")
                services["database"] = True
        except:
            services["database"] = False
        
        services["overall"] = services["redis"] and services["database"]
        
        return {
            "services": services,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Services health check failed: {e}")
        return {
            "services": services,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }