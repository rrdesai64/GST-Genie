from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException  # Added HTTPException
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from typing import AsyncGenerator
import time
import logging
from logging.config import dictConfig
from datetime import datetime
from config import settings, EnvironmentEnum
from database import db_manager

# Configure logging
dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": settings.log_level,
            "class": "logging.StreamHandler",
            "formatter": "default" if settings.environment == EnvironmentEnum.DEVELOPMENT else "json",
        }
    },
    "root": {
        "level": settings.log_level,
        "handlers": ["console"],
    }
})

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown"""
    startup_success = False
    
    try:
        # Startup
        logger.info("Starting Advanced Gemini Chat Application...")
        
        # Validate environment configuration
        if settings.environment == EnvironmentEnum.PRODUCTION:
            logger.info("Running in PRODUCTION mode")
            if settings.jwt_secret_key == "your-secret-key-here":
                logger.error("JWT secret key must be changed in production!")
                raise ValueError("Invalid JWT secret key for production")
        else:
            logger.info("Running in DEVELOPMENT mode")
        
        # Initialize database
        await db_manager.initialize()
        
        # Initialize Redis (simplified - remove problematic imports)
        try:
            import redis.asyncio as redis
            redis_client = redis.from_url(str(settings.redis_url))
            await redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
        
        startup_success = True
        logger.info("Application started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}", exc_info=True)
        startup_success = False
        raise
        
    finally:
        # Shutdown
        logger.info("Shutting down application...")
        try:
            await db_manager.close()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        if startup_success:
            logger.info("Application shutdown completed successfully")

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Advanced Gemini Chat API",
        version="1.0.0",
        description="Production-ready chat application with Gemini AI",
        routes=app.routes,
    )
    
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    for path_name, path_item in openapi_schema["paths"].items():
        for method_name, method_item in path_item.items():
            if method_name in ["get", "post", "put", "delete", "patch"]:
                if not path_name.startswith("/auth/"):
                    method_item["security"] = [{"BearerAuth": []}]
    
    openapi_schema["tags"] = [
        {"name": "Authentication", "description": "User authentication"},
        {"name": "Chat", "description": "AI chat functionality"},
        {"name": "Sessions", "description": "Chat session management"},
        {"name": "Health", "description": "Health checks"}
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Create FastAPI app
app = FastAPI(
    title="Advanced Gemini Chat API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.openapi = custom_openapi

# Basic middleware setup (simplified)
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.3f}"
    return response

# Include routers (commented out until files exist)
 from api.endpoints.auth import router as auth_router
 from api.endpoints.chat import router as chat_router
 from api.endpoints.sessions import router as sessions_router
 from api.endpoints.health import router as health_router

 app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
 app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])
 app.include_router(sessions_router, prefix="/api/v1", tags=["Sessions"])
 app.include_router(health_router, prefix="/api/v1", tags=["Health"])

# Basic endpoints for testing
@app.get("/")
async def root():
    return {"message": "API is running", "status": "ok"}

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

if __name__ == "__main__":
    import uvicorn
    import os
    os.makedirs("logs", exist_ok=True)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )