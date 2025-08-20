import json
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPBearer

from database import db_manager
from auth import get_current_user, decode_access_token, get_user_by_id
from models import User, MessageType
from schemas import ChatRequest, ChatResponse, ErrorResponse, RateLimitResponse
from services.chat_service import ChatService
from services.gemini_service import StreamingGeminiService
from services.analytics import ChatAnalytics
from services.rate_limiter import RateLimiter
from .dependencies import get_redis
from .dependencies import get_chat_service, get_gemini_service, get_analytics, get_rate_limiter

logger = logging.getLogger(__name__)
router = APIRouter()

# WebSocket connection manager for better connection management
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        await websocket.accept()
        connection_id = f"{user_id}_{session_id}"
        self.active_connections[connection_id] = websocket
        logger.info(f"WebSocket connected: {connection_id}")
    
    async def disconnect(self, session_id: str, user_id: str):
        connection_id = f"{user_id}_{session_id}"
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_message(self, session_id: str, user_id: str, message: dict):
        connection_id = f"{user_id}_{session_id}"
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {e}")

manager = ConnectionManager()

@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        429: {"model": RateLimitResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def chat_endpoint(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    gemini_service: StreamingGeminiService = Depends(get_gemini_service),
    analytics: ChatAnalytics = Depends(get_analytics),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
):
    """Chat endpoint with comprehensive error handling"""
    # Rate limiting
    try:
        is_limited, rate_info = await rate_limiter.is_rate_limited(
            user.id, "chat", max_requests=30, window_seconds=60
        )
        
        if is_limited:
            logger.warning(f"Rate limit exceeded for user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=rate_info
            )
    except Exception as e:
        logger.error(f"Rate limiter error for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )
    
    try:
        # Validate and get session
        if not request.session_id:
            session = await chat_service.create_session(user)
            session_id = session.id
            logger.info(f"Created new session {session_id} for user {user.id}")
        else:
            session_id = request.session_id
            if not await chat_service.verify_session_ownership(session_id, user.id):
                logger.warning(f"Session access denied: {session_id} for user {user.id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found or access denied"
                )
        
        # Get conversation history
        messages = await chat_service.get_session_messages(session_id)
        
        # Generate response
        try:
            response_text, response_time = await gemini_service.generate_response(
                request.message, messages
            )
        except Exception as e:
            logger.error(f"Gemini service error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service temporarily unavailable"
            )
        
        # Store messages
        try:
            user_message = await chat_service.add_message(
                session_id=session_id,
                user_id=user.id,
                message_type=MessageType.USER,
                content=request.message,
                metadata=request.metadata
            )
            
            assistant_message = await chat_service.add_message(
                session_id=session_id,
                user_id=user.id,
                message_type=MessageType.ASSISTANT,
                content=response_text,
                response_time=response_time
            )
        except Exception as e:
            logger.error(f"Failed to store messages: {e}")
            # Continue even if storage fails, but log the error
        
        # Track analytics in background
        try:
            background_tasks.add_task(
                analytics.track_message,
                user.id, len(request.message), response_time, session_id
            )
        except Exception as e:
            logger.warning(f"Analytics tracking failed: {e}")
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            message_id=assistant_message.id if assistant_message else None,
            response_time=response_time,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )

@router.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket, 
    session_id: str,
    token: Optional[str] = None
):
    """WebSocket chat with proper connection management and authentication"""
    try:
        # Extract token from query parameters
        if not token:
            token = websocket.query_params.get("token")
        
        if not token:
            logger.warning("WebSocket connection attempt without token")
            await websocket.close(code=4003, reason="Authentication token required")
            return
        
        # Authenticate user
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            if not user_id:
                logger.warning("Invalid token payload")
                await websocket.close(code=4003, reason="Invalid token")
                return
            
            # Get user from database
            async with db_manager.get_session() as db:
                user = await get_user_by_id(db, user_id)
                if not user:
                    logger.warning(f"User not found: {user_id}")
                    await websocket.close(code=4003, reason="User not found")
                    return
        except Exception as e:
            logger.error(f"WebSocket authentication error: {e}")
            await websocket.close(code=4003, reason="Authentication failed")
            return
        
        # Verify session ownership
        try:
            async with db_manager.get_session() as db:
                chat_service = ChatService(db)
                if not await chat_service.verify_session_ownership(session_id, user.id):
                    logger.warning(f"Session access denied: {session_id} for user {user.id}")
                    await websocket.close(code=4004, reason="Session not found or access denied")
                    return
        except Exception as e:
            logger.error(f"Session verification error: {e}")
            await websocket.close(code=4005, reason="Session verification failed")
            return
        
        # Connect WebSocket
        await manager.connect(websocket, session_id, user.id)
        
        # Get services
        try:
            gemini_service = StreamingGeminiService()
            analytics = ChatAnalytics(await get_redis())
            rate_limiter = RateLimiter(await get_redis())
        except Exception as e:
            logger.error(f"Service initialization error: {e}")
            await websocket.close(code=4006, reason="Service initialization failed")
            return
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "data": {"session_id": session_id, "user_id": user.id, "timestamp": datetime.now().isoformat()}
        })
        
        logger.info(f"WebSocket session started: user={user.id}, session={session_id}")
        
        while True:
            try:
                # Receive message with timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=300.0)
                message_data = json.loads(data)
                message = message_data.get("message", "").strip()
                
                if not message:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Empty message not allowed", "error_code": "EMPTY_MESSAGE"}
                    })
                    continue
                
                # Rate limiting
                try:
                    is_limited, rate_info = await rate_limiter.is_rate_limited(
                        user.id, "websocket", max_requests=20, window_seconds=60
                    )
                    
                    if is_limited:
                        await websocket.send_json({
                            "type": "rate_limit",
                            "data": rate_info
                        })
                        continue
                except Exception as e:
                    logger.error(f"Rate limiter error: {e}")
                    # Continue without rate limiting if service fails
                
                # Process message
                try:
                    async with db_manager.get_session() as db:
                        chat_service = ChatService(db)
                        messages = await chat_service.get_session_messages(session_id)
                        
                        start_time = datetime.now()
                        response_text = await gemini_service.stream_response(
                            message, messages, websocket
                        )
                        response_time = (datetime.now() - start_time).total_seconds()
                        
                        # Store messages
                        await chat_service.add_message(
                            session_id=session_id,
                            user_id=user.id,
                            message_type=MessageType.USER,
                            content=message
                        )
                        
                        await chat_service.add_message(
                            session_id=session_id,
                            user_id=user.id,
                            message_type=MessageType.ASSISTANT,
                            content=response_text,
                            response_time=response_time
                        )
                        
                        # Track analytics
                        try:
                            await analytics.track_message(user.id, len(message), response_time, session_id)
                        except Exception as e:
                            logger.warning(f"Analytics tracking failed: {e}")
                            
                except Exception as e:
                    logger.error(f"Message processing error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Failed to process message", "error_code": "PROCESSING_ERROR"}
                    })
                    
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "timeout",
                    "data": {"message": "Connection timeout - please send a message"}
                })
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected normally: user={user.id}, session={session_id}")
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON format", "error_code": "INVALID_JSON"}
                })
            except Exception as e:
                logger.error(f"WebSocket processing error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "An error occurred", "error_code": "INTERNAL_ERROR"}
                })
                
    except Exception as e:
        logger.error(f"WebSocket endpoint error: {e}")
    finally:
        await manager.disconnect(session_id, user.id if 'user' in locals() else None)
        await websocket.close()