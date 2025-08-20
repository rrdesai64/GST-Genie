import logging
import time
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request logging with performance monitoring.
    
    Logs:
    - Request method and path
    - Response status code
    - Processing time
    - Client IP address
    - User agent
    - Request ID for tracing
    """
    
    def __init__(self, app: ASGIApp, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health", 
            "/health/ready", 
            "/health/live",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Generate request ID for tracing
        request_id = request.headers.get('X-Request-ID') or self._generate_request_id()
        request.state.request_id = request_id
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log successful request
            self._log_request(
                request=request,
                response=response,
                process_time=process_time,
                request_id=request_id,
                error=None
            )
            
            # Add headers for monitoring
            response.headers["X-Process-Time"] = f"{process_time:.4f}"
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            # Log error with stack trace
            self._log_request(
                request=request,
                response=None,
                process_time=process_time,
                request_id=request_id,
                error=e
            )
            
            # Re-raise the exception for proper error handling
            raise
    
    def _log_request(self, request: Request, response: Optional[Response], 
                    process_time: float, request_id: str, error: Optional[Exception] = None):
        """Log request details in a structured format"""
        
        log_data: Dict[str, Any] = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "process_time": f"{process_time:.4f}s",
            "timestamp": time.time()
        }
        
        if error:
            log_data.update({
                "status": "error",
                "error_type": error.__class__.__name__,
                "error_message": str(error)
            })
            logger.error(json.dumps(log_data), exc_info=error)
        else:
            log_data.update({
                "status": "success",
                "status_code": response.status_code if response else 500,
                "content_type": response.headers.get("content-type", "") if response else ""
            })
            logger.info(json.dumps(log_data))
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request headers"""
        if request.client is None:
            return "unknown"
        
        # Check for forwarded headers (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        return request.client.host
    
    def _generate_request_id(self) -> str:
        """Generate a unique request ID"""
        import uuid
        return str(uuid.uuid4())

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers to all responses.
    
    Implements OWASP security best practices for HTTP headers.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'",
        }
        
        for header, value in security_headers.items():
            if header not in response.headers:
                response.headers[header] = value
        
        return response

class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding rate limit headers to responses.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add rate limit headers if they exist in response state
        rate_limit_info = getattr(request.state, 'rate_limit_info', None)
        if rate_limit_info:
            response.headers["X-RateLimit-Limit"] = str(rate_limit_info.get("max_requests", 0))
            response.headers["X-RateLimit-Remaining"] = str(
                rate_limit_info.get("max_requests", 0) - rate_limit_info.get("requests_made", 0)
            )
            response.headers["X-RateLimit-Reset"] = str(rate_limit_info.get("window_seconds", 0))
        
        return response