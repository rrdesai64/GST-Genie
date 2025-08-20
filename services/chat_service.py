from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import uuid
import logging
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models import ChatSession, ChatMessage, User
from schemas import MessageType

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_session(self, user: User, title: Optional[str] = None) -> ChatSession:
        """Create a new chat session"""
        session = ChatSession(
            user_id=user.id,
            title=title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        logger.info(f"Created new session {session.id} for user {user.id}")
        return session
    
    async def add_message(
        self,
        session_id: str,
        user_id: str,
        message_type: MessageType,
        content: str,
        metadata: Optional[Dict] = None,
        response_time: Optional[float] = None
    ) -> ChatMessage:
        """Add a message to a session"""
        message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            message_type=message_type.value,
            content=content,
            metadata=json.dumps(metadata) if metadata else None,
            response_time=response_time
        )
        
        self.db.add(message)
        
        # Update session activity and message count
        result = await self.db.execute(
            select(ChatSession).filter(ChatSession.id == session_id)
        )
        session = result.scalar_one()
        session.last_activity = datetime.now()
        session.message_count += 1
        
        await self.db.commit()
        await self.db.refresh(message)
        
        logger.debug(f"Added message {message.id} to session {session_id}")
        return message
    
    async def get_session_messages(
        self, 
        session_id: str, 
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatMessage]:
        """Get messages from a session"""
        result = await self.db.execute(
            select(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.timestamp.asc())
            .limit(limit)
            .offset(offset)
        )
        
        return result.scalars().all()
    
    async def get_user_sessions(
        self, 
        user_id: str, 
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatSession]:
        """Get user's chat sessions"""
        result = await self.db.execute(
            select(ChatSession)
            .filter(ChatSession.user_id == user_id, ChatSession.is_active == True)
            .order_by(ChatSession.last_activity.desc())
            .limit(limit)
            .offset(offset)
        )
        
        return result.scalars().all()
    
    async def verify_session_ownership(self, session_id: str, user_id: str) -> bool:
        """Verify that a session belongs to a user"""
        result = await self.db.execute(
            select(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
                ChatSession.is_active == True
            )
        )
        
        return result.scalar_one_or_none() is not None
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session (soft delete)"""
        result = await self.db.execute(
            select(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            )
        )
        
        session = result.scalar_one_or_none()
        if not session:
            return False
        
        session.is_active = False
        await self.db.commit()
        
        logger.info(f"Deleted session {session_id} for user {user_id}")
        return True