"""
Middleware configuration utilities for the chat application.
"""

from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from config import settings, EnvironmentEnum
from .logging import LoggingMiddleware, SecurityHeadersMiddleware, RateLimitHeadersMiddleware

def setup_middleware(app: FastAPI):
    """
    Configure all middleware for the application with proper ordering.
    
    Middleware order matters! They execute from bottom to top (last to first added).
    """
    
    # 1. CORS - Should be first to handle cross-origin requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 2. Trusted Hosts - Security for production
    if settings.environment == EnvironmentEnum.PRODUCTION:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=get_production_hosts()
        )
    
    # 3. GZip Compression - Reduce bandwidth
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # 4. Custom Security Headers - OWASP best practices
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 5. Rate Limit Headers - API rate limiting information
    app.add_middleware(RateLimitHeadersMiddleware)
    
    # 6. Request Logging - Application-level logging
    app.add_middleware(
        LoggingMiddleware,
        exclude_paths=get_excluded_log_paths()
    )
    
    # 7. Additional production-only middleware
    if settings.environment == EnvironmentEnum.PRODUCTION:
        setup_production_middleware(app)

def get_excluded_log_paths() -> List[str]:
    """Get list of paths to exclude from detailed logging"""
    return [
        "/health",
        "/health/ready", 
        "/health/live",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
        "/metrics"  # If you add metrics endpoint later
    ]

def get_production_hosts() -> List[str]:
    """Get allowed hosts for production environment"""
    return [
        "localhost",
        "127.0.0.1",
        "*.your-domain.com", 
        "your-domain.com",
        # Add your actual production domains here
        "your-app.herokuapp.com",
        "your-app.azurewebsites.net",
        # etc.
    ]

def setup_production_middleware(app: FastAPI):
    """Setup middleware specific to production environment"""
    # Add any production-specific middleware here
    pass

def get_middleware_order() -> List[str]:
    """Return the order of middleware execution for documentation"""
    return [
        "1. CORSMiddleware",
        "2. TrustedHostMiddleware (production only)",
        "3. GZipMiddleware", 
        "4. SecurityHeadersMiddleware",
        "5. RateLimitHeadersMiddleware",
        "6. LoggingMiddleware",
        "7. Application Routes"
    ]