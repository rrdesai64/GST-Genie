from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from database import db_manager
from auth import authenticate_user, create_user, create_access_token, get_password_hash
from schemas import UserCreate, UserResponse, Token, ErrorResponse
from services.rate_limiter import RateLimiter
from .dependencies import get_rate_limiter
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "User already exists"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
async def register(
    user_data: UserCreate,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Register a new user"""
    # Rate limiting for registration endpoint
    is_limited, rate_info = await rate_limiter.is_rate_limited(
        f"register:{user_data.username}", "register", max_requests=3, window_seconds=3600
    )
    
    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many registration attempts. Try again in {rate_info['retry_after']} seconds"
        )
    
    try:
        user = await create_user(db, user_data)
        logger.info(f"User registered successfully: {user.username}")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed for {user_data.username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

@router.post(
    "/login",
    response_model=Token,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Login user and get access token"""
    # Rate limiting for login attempts
    is_limited, rate_info = await rate_limiter.is_rate_limited(
        f"login:{form_data.username}", "login", max_requests=5, window_seconds=300
    )
    
    if is_limited:
        logger.warning(f"Rate limited login attempt for: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {rate_info['retry_after']} seconds"
        )
    
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.now()
    await db.commit()
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    logger.info(f"User logged in successfully: {user.username}")
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60
    )