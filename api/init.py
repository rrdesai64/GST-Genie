"""
API package for the Advanced Gemini Chat Application.

This package contains all API endpoints, routes, and dependency injections
for the chat application. It follows a modular structure with separate
modules for different functional areas.

Structure:
api/
├── __init__.py          (this file)
├── dependencies.py      - Dependency injection setup
└── endpoints/           - API route handlers
    ├── __init__.py      - Endpoints package
    ├── auth.py          - Authentication endpoints
    ├── chat.py          - Chat functionality endpoints  
    ├── sessions.py      - Session management endpoints
    └── health.py        - Health check endpoints
"""

from . import endpoints
from .dependencies import (
    get_redis,
    get_chat_service,
    get_gemini_service,
    get_analytics,
    get_rate_limiter,
    get_current_user
)

__version__ = "1.0.0"
__author__ = "Chat Application Team"
__description__ = "API layer for FastAPI chat application"

# Export all dependencies and routers
__all__ = [
    # Sub-packages
    'endpoints',
    
    # Dependencies
    'get_redis',
    'get_chat_service', 
    'get_gemini_service',
    'get_analytics',
    'get_rate_limiter',
    'get_current_user',
    
    # Routers (from endpoints)
    'auth_router',
    'chat_router',
    'sessions_router',
    'health_router'
]

# Import routers from endpoints for easy access
from .endpoints import (
    auth_router,
    chat_router,
    sessions_router,
    health_router
)

# Re-export for convenience
auth_router = auth_router
chat_router = chat_router
sessions_router = sessions_router
health_router = health_router

# Package metadata
__package_metadata__ = {
    "version": __version__,
    "author": __author__,
    "description": __description__,
    "modules": {
        "endpoints": {
            "description": "API route handlers organized by functionality",
            "components": [
                "auth.py - User authentication and registration",
                "chat.py - AI chat functionality and WebSocket",
                "sessions.py - Chat session management", 
                "health.py - Health checks and monitoring"
            ]
        },
        "dependencies": {
            "description": "Dependency injection for services and utilities",
            "components": [
                "Database sessions",
                "Redis connections", 
                "AI services",
                "Analytics tracking",
                "Rate limiting",
                "Authentication"
            ]
        }
    }
}

def get_api_info() -> dict:
    """
    Get comprehensive information about the API package structure.
    
    Returns:
        dict: Metadata about API modules and components
    """
    return __package_metadata__

# Type annotations for better IDE support
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fastapi import APIRouter
    from redis.asyncio import Redis
    from services.chat_service import ChatService
    from services.gemini_service import StreamingGeminiService
    from services.analytics import ChatAnalytics
    from services.rate_limiter import RateLimiter
    from models import User
    
    # Router types
    auth_router: APIRouter
    chat_router: APIRouter
    sessions_router: APIRouter
    health_router: APIRouter
    
    # Dependency types
    def get_redis() -> Redis: ...
    def get_chat_service() -> ChatService: ...
    def get_gemini_service() -> StreamingGeminiService: ...
    def get_analytics() -> ChatAnalytics: ...
    def get_rate_limiter() -> RateLimiter: ...
    def get_current_user() -> User: ...

# Compatibility information
__compatibility__ = {
    "fastapi": ">=0.104.0",
    "python": ">=3.8"
}

def setup_api_routes(app):
    """
    Helper function to setup all API routes with proper prefixes.
    
    Args:
        app: FastAPI application instance
    """
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])
    app.include_router(sessions_router, prefix="/api/v1", tags=["Sessions"])
    app.include_router(health_router, prefix="/api/v1", tags=["Health"])