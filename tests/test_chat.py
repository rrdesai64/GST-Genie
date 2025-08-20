import pytest
import json
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from models import User, ChatSession
from auth import create_access_token

client = TestClient(app)

@pytest.fixture
def auth_token():
    """Create a test auth token"""
    return create_access_token({"sub": "test-user-id"})

@pytest.mark.asyncio
async def test_chat_endpoint_requires_auth():
    """Test that chat endpoint requires authentication"""
    response = client.post("/api/v1/chat", json={"message": "Hello"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_chat_with_new_session(auth_token, db_session: AsyncSession):
    """Test chat with new session creation"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    chat_data = {"message": "Hello, how are you?"}
    
    response = client.post("/api/v1/chat", json=chat_data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "response" in data
    assert "session_id" in data
    assert "message_id" in data

@pytest.mark.asyncio
async def test_chat_with_existing_session(auth_token, db_session: AsyncSession):
    """Test chat with existing session"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # First message to create session
    first_response = client.post("/api/v1/chat", 
        json={"message": "First message"}, 
        headers=headers
    )
    session_id = first_response.json()["session_id"]
    
    # Second message using same session
    second_response = client.post("/api/v1/chat", 
        json={"message": "Second message", "session_id": session_id}, 
        headers=headers
    )
    
    assert second_response.status_code == status.HTTP_200_OK
    assert second_response.json()["session_id"] == session_id

@pytest.mark.asyncio
async def test_chat_rate_limiting(auth_token, db_session: AsyncSession):
    """Test chat rate limiting"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Make multiple requests quickly
    responses = []
    for i in range(35):  # Limit is 30 requests per minute
        response = client.post("/api/v1/chat", 
            json={"message": f"Message {i}"}, 
            headers=headers
        )
        responses.append(response)
    
    # Check if any were rate limited
    rate_limited = any(r.status_code == status.HTTP_429_TOO_MANY_REQUESTS for r in responses)
    assert rate_limited, "Expected at least one rate limited response"

@pytest.mark.asyncio
async def test_get_sessions(auth_token, db_session: AsyncSession):
    """Test getting user sessions"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Create some sessions first
    for i in range(3):
        client.post("/api/v1/chat", 
            json={"message": f"Test message {i}"}, 
            headers=headers
        )
    
    response = client.get("/api/v1/sessions", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) <= data["total"]