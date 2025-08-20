"""
API endpoints package for the Advanced Gemini Chat Application.

This package contains all the route handlers organized by functionality.
Each module corresponds to a specific area of the application's API.

Endpoints are organized as follows:
- auth.py: Authentication and user management
- chat.py: AI chat functionality and WebSocket connections  
- sessions.py: Chat session management
- health.py: Health checks and monitoring

Each endpoint module exports an APIRouter instance that can be included
in the main FastAPI application.
"""

from .auth import router as auth_router
from .chat import router as chat_router
from .sessions import router as sessions_router
from .health import router as health_router

__version__ = "1.0.0"
__author__ = "Chat Application Team"
__description__ = "API endpoint handlers for chat application"

# Export all routers
__all__ = [
    'auth_router',
    'chat_router',
    'sessions_router',
    'health_router'
]

# Package metadata
__package_metadata__ = {
    "version": __version__,
    "author": __author__,
    "description": __description__,
    "endpoints": {
        "auth_router": {
            "path_prefix": "/api/v1/auth",
            "tags": ["Authentication"],
            "description": "User registration, login, and authentication endpoints",
            "routes": [
                "POST /register - Register new user",
                "POST /login - User login and token generation"
            ]
        },
        "chat_router": {
            "path_prefix": "/api/v1",
            "tags": ["Chat"],
            "description": "AI chat functionality and real-time WebSocket connections",
            "routes": [
                "POST /chat - Send message and get AI response",
                "WS /ws/chat/{session_id} - WebSocket for real-time chat"
            ]
        },
        "sessions_router": {
            "path_prefix": "/api/v1",
            "tags": ["Sessions"],
            "description": "Chat session management and message retrieval",
            "routes": [
                "GET /sessions - List user's chat sessions",
                "GET /sessions/{session_id}/messages - Get session messages",
                "DELETE /sessions/{session_id} - Delete chat session"
            ]
        },
        "health_router": {
            "path_prefix": "/api/v1",
            "tags": ["Health"],
            "description": "Health checks and system monitoring",
            "routes": [
                "GET /health - Comprehensive health check",
                "GET /health/ready - Readiness probe",
                "GET /health/live - Liveness probe",
                "GET /health/services - Detailed services health check"
            ]
        }
    }
}

def get_endpoints_info() -> dict:
    """
    Get comprehensive information about all API endpoints.
    
    Returns:
        dict: Metadata about all endpoint routers and their routes
    """
    return __package_metadata__

def get_all_routers():
    """
    Get all API router instances.
    
    Returns:
        list: List of all APIRouter instances
    """
    return [auth_router, chat_router, sessions_router, health_router]

def get_router_by_tag(tag: str):
    """
    Get router by tag name.
    
    Args:
        tag: Tag name to search for (e.g., "Authentication", "Chat")
    
    Returns:
        APIRouter: Router instance or None if not found
    """
    routers = {
        "Authentication": auth_router,
        "Chat": chat_router,
        "Sessions": sessions_router,
        "Health": health_router
    }
    return routers.get(tag)

# Type annotations for better IDE support
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fastapi import APIRouter
    
    auth_router: APIRouter
    chat_router: APIRouter
    sessions_router: APIRouter
    health_router: APIRouter

# Route statistics (can be used for monitoring)
def get_route_statistics():
    """
    Get statistics about all registered routes.
    
    Returns:
        dict: Route count and information by method and tag
    """
    stats = {
        "total_routes": 0,
        "by_method": {"GET": 0, "POST": 0, "PUT": 0, "DELETE": 0, "WS": 0},
        "by_tag": {},
        "routes": []
    }
    
    for router in get_all_routers():
        for route in router.routes:
            stats["total_routes"] += 1
            method = getattr(route, "methods", ["WS"])[0] if hasattr(route, "methods") else "WS"
            stats["by_method"][method] = stats["by_method"].get(method, 0) + 1
            
            # Extract tags
            tags = getattr(route, "tags", ["untagged"])
            for tag in tags:
                stats["by_tag"][tag] = stats["by_tag"].get(tag, 0) + 1
            
            stats["routes"].append({
                "path": getattr(route, "path", "unknown"),
                "method": method,
                "tags": tags
            })
    
    return stats

# WebSocket connection statistics
def get_websocket_stats():
    """
    Get WebSocket connection statistics.
    
    Returns:
        dict: WebSocket connection information
    """
    from .chat import manager
    return {
        "active_connections": len(manager.active_connections),
        "connections": list(manager.active_connections.keys())
    }

# Example usage
__usage_examples__ = """
# Import all routers
from api.endpoints import auth_router, chat_router, sessions_router, health_router

# Include in FastAPI app
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])
app.include_router(sessions_router, prefix="/api/v1", tags=["Sessions"])
app.include_router(health_router, prefix="/api/v1", tags=["Health"])

# Get endpoint information
from api.endpoints import get_endpoints_info
print(get_endpoints_info())

# Get route statistics
from api.endpoints import get_route_statistics
stats = get_route_statistics()
print(f"Total routes: {stats['total_routes']}")

# Get WebSocket stats
from api.endpoints import get_websocket_stats
ws_stats = get_websocket_stats()
print(f"Active WebSocket connections: {ws_stats['active_connections']}")
"""