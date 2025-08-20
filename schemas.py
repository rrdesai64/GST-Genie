from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    user_id: Optional[str] = None

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator('message')
    def validate_message(cls, v):
        # Basic sanitization
        v = v.strip()
        if not v:
            raise ValueError('Message cannot be empty')
        return v

class ChatResponse(BaseModel):
    response: str
    session_id: str
    message_id: str
    response_time: float
    timestamp: datetime

class SessionResponse(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    last_activity: datetime
    message_count: int

class MessageResponse(BaseModel):
    id: str
    message_type: MessageType
    content: str
    timestamp: datetime
    response_time: Optional[float] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    components: Dict[str, Any]

class AnalyticsResponse(BaseModel):
    date: str
    total_messages: int
    total_characters: int
    total_response_time: float
    avg_message_length: float
    avg_response_time: float

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None

class RateLimitResponse(BaseModel):
    detail: str = "Rate limit exceeded"
    retry_after: int
    limit: int
    window: int

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    has_more: bool