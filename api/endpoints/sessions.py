from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from database import db_manager
from auth import get_current_user
from models import User, ChatSession
from schemas import SessionResponse, MessageResponse, PaginatedResponse, ErrorResponse
from services.chat_service import ChatService
from .dependencies import get_chat_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/sessions",
    response_model=PaginatedResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def list_sessions(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """List user's chat sessions with pagination"""
    try:
        sessions = await chat_service.get_user_sessions(user.id, limit=size, offset=(page-1)*size)
        
        # Get total count for pagination
        total = await chat_service.get_user_session_count(user.id)
        
        session_responses = [
            SessionResponse(
                session_id=session.id,
                title=session.title,
                created_at=session.created_at,
                last_activity=session.last_activity,
                message_count=session.message_count
            )
            for session in sessions
        ]
        
        logger.info(f"Retrieved {len(session_responses)} sessions for user {user.id}")
        
        return PaginatedResponse(
            items=session_responses,
            total=total,
            page=page,
            size=size,
            has_more=(page * size) < total
        )
        
    except Exception as e:
        logger.error(f"Failed to retrieve sessions for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions"
        )

@router.get(
    "/sessions/{session_id}/messages",
    response_model=List[MessageResponse],
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_session_messages(
    session_id: str,
    limit: int = Query(50, ge=1, le=100, description="Number of messages to retrieve"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get messages from a specific session"""
    try:
        # Verify session ownership
        if not await chat_service.verify_session_ownership(session_id, user.id):
            logger.warning(f"Session access denied: {session_id} for user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied"
            )
        
        messages = await chat_service.get_session_messages(session_id, limit=limit, offset=offset)
        
        logger.info(f"Retrieved {len(messages)} messages from session {session_id}")
        
        return [
            MessageResponse(
                id=message.id,
                message_type=message.message_type,
                content=message.content,
                timestamp=message.timestamp,
                response_time=message.response_time
            )
            for message in messages
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve messages from session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages"
        )

@router.delete(
    "/sessions/{session_id}",
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Delete a chat session (soft delete)"""
    try:
        success = await chat_service.delete_session(session_id, user.id)
        
        if not success:
            logger.warning(f"Session not found for deletion: {session_id} by user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied"
            )
        
        logger.info(f"Session deleted successfully: {session_id} by user {user.id}")
        return {"message": "Session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete session"
        )