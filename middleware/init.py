"""
Middleware package for the Advanced Gemini Chat Application.

This package contains custom middleware components that process requests and responses
before they reach the application handlers or after they leave them.

Middleware execution order (from first to last):
1. CORS Middleware - Handles cross-origin requests
2. TrustedHost Middleware - Validates host headers (production only)
3. GZip Middleware - Response compression
4. SecurityHeaders Middleware - Security headers (OWASP best practices)
5. RateLimitHeaders Middleware - Rate limit information headers
6. Logging Middleware - Request/response logging and monitoring
7. Application Routes - Your actual business logic

Each middleware component can be used independently or together through the setup_middleware() function.
"""

from .logging import (
    LoggingMiddleware, 
    SecurityHeadersMiddleware, 
    RateLimitHeadersMiddleware
)

from .config import (
    setup_middleware,
    get_middleware_order,
    get_excluded_log_paths,
    get_production_hosts,
    setup_production_middleware
)

__version__ = "1.0.0"
__author__ = "Chat Application Team"
__description__ = "Middleware components for FastAPI chat application"

# Export all middleware components and utilities
__all__ = [
    # Core middleware classes
    'LoggingMiddleware',
    'SecurityHeadersMiddleware', 
    'RateLimitHeadersMiddleware',
    
    # Configuration utilities
    'setup_middleware',
    'get_middleware_order', 
    'get_excluded_log_paths',
    'get_production_hosts',
    'setup_production_middleware'
]

# Type annotations for better IDE support
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fastapi import FastAPI
    from typing import List
    
    def setup_middleware(app: FastAPI) -> None: ...
    def get_middleware_order() -> List[str]: ...
    def get_excluded_log_paths() -> List[str]: ...
    def get_production_hosts() -> List[str]: ...
    def setup_production_middleware(app: FastAPI) -> None: ...

# Package metadata
__package_metadata__ = {
    "version": __version__,
    "author": __author__,
    "description": __description__,
    "components": [
        {
            "name": "LoggingMiddleware",
            "description": "Comprehensive request logging with performance monitoring and structured JSON output",
            "features": [
                "Request/response logging",
                "Performance timing",
                "Error tracking",
                "Request ID generation",
                "Structured JSON logging"
            ]
        },
        {
            "name": "SecurityHeadersMiddleware", 
            "description": "OWASP security best practices implementation with comprehensive security headers",
            "features": [
                "X-Content-Type-Options",
                "X-Frame-Options", 
                "X-XSS-Protection",
                "Strict-Transport-Security",
                "Referrer-Policy",
                "Permissions-Policy",
                "Content-Security-Policy"
            ]
        },
        {
            "name": "RateLimitHeadersMiddleware",
            "description": "Rate limiting information headers for API consumers",
            "features": [
                "X-RateLimit-Limit header",
                "X-RateLimit-Remaining header", 
                "X-RateLimit-Reset header",
                "Integration with rate limiting service"
            ]
        },
        {
            "name": "setup_middleware",
            "description": "Centralized middleware configuration with proper ordering",
            "features": [
                "Automatic middleware ordering",
                "Environment-specific configuration",
                "Production readiness checks",
                "CORS configuration"
            ]
        }
    ]
}

def get_middleware_info() -> dict:
    """
    Get comprehensive information about available middleware components.
    
    Returns:
        dict: Metadata about all middleware components and their features
    """
    return __package_metadata__

def print_middleware_order() -> None:
    """
    Print the middleware execution order for debugging and documentation purposes.
    """
    order = get_middleware_order()
    print("Middleware Execution Order:")
    print("=" * 40)
    for item in order:
        print(f"• {item}")
    print("=" * 40)
    print("Note: Middleware executes from first to last in this order")

# Example usage documentation
__usage_examples__ = """
# Basic usage
from middleware import setup_middleware
from fastapi import FastAPI

app = FastAPI()
setup_middleware(app)

# Individual middleware usage
from middleware import LoggingMiddleware, SecurityHeadersMiddleware

app.add_middleware(LoggingMiddleware, exclude_paths=["/health"])
app.add_middleware(SecurityHeadersMiddleware)

# Configuration inspection
from middleware import get_middleware_order, get_excluded_log_paths

print("Middleware order:", get_middleware_order())
print("Excluded log paths:", get_excluded_log_paths())
"""

# Version compatibility information
__compatibility__ = {
    "fastapi": ">=0.104.0",
    "python": ">=3.8",
    "redis": ">=5.0.0",
    "sqlalchemy": ">=2.0.0"
}

def check_compatibility() -> dict:
    """
    Check if the current environment meets the middleware compatibility requirements.
    
    Returns:
        dict: Compatibility check results with version information
    """
    import importlib.metadata
    results = {}
    
    for package, required_version in __compatibility__.items():
        try:
            installed_version = importlib.metadata.version(package)
            results[package] = {
                "required": required_version,
                "installed": installed_version,
                "compatible": True  # Simple check - in real implementation, use packaging.version
            }
        except importlib.metadata.PackageNotFoundError:
            results[package] = {
                "required": required_version,
                "installed": "Not installed",
                "compatible": False
            }
    
    return results