import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from models import User
from auth import get_password_hash

client = TestClient(app)

@pytest.mark.asyncio
async def test_register_user(db_session: AsyncSession):
    """Test user registration"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "SecurePass123!"
    }
    
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == status.HTTP_201_CREATED
    
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "password" not in data

@pytest.mark.asyncio
async def test_register_duplicate_username(db_session: AsyncSession):
    """Test duplicate username registration"""
    # Create first user
    user_data = {
        "username": "duplicate",
        "email": "test1@example.com",
        "password": "SecurePass123!"
    }
    client.post("/api/v1/auth/register", json=user_data)
    
    # Try to create user with same username
    duplicate_data = {
        "username": "duplicate",
        "email": "test2@example.com",
        "password": "SecurePass123!"
    }
    
    response = client.post("/api/v1/auth/register", json=duplicate_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.asyncio
async def test_login_success(db_session: AsyncSession):
    """Test successful login"""
    # First register
    user_data = {
        "username": "loginuser",
        "email": "login@example.com",
        "password": "SecurePass123!"
    }
    client.post("/api/v1/auth/register", json=user_data)
    
    # Then login
    login_data = {
        "username": "loginuser",
        "password": "SecurePass123!"
    }
    
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(db_session: AsyncSession):
    """Test login with invalid credentials"""
    login_data = {
        "username": "nonexistent",
        "password": "wrongpassword"
    }
    
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_rate_limiting(db_session: AsyncSession):
    """Test rate limiting on login"""
    login_data = {
        "username": "ratelimited",
        "password": "wrongpassword"
    }
    
    # Make multiple failed attempts
    for i in range(6):  # Limit is 5 attempts per 5 minutes
        response = client.post("/api/v1/auth/login", data=login_data)
    
    # Last attempt should be rate limited
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS