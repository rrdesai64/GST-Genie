import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from models import ChatSession
from auth import create_access_token

client = TestClient(app)

@pytest.fixture
def auth_token():
    """Create a test auth token"""
    return create_access_token({"sub": "test-user-id"})

@pytest.mark.asyncio
async def test_get_sessions_empty(auth_token, db_session: AsyncSession):
    """Test getting sessions when user has none"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    response = client.get("/api/v1/sessions", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0
    assert data["has_more"] == False

@pytest.mark.asyncio
async def test_get_sessions_with_data(auth_token, db_session: AsyncSession):
    """Test getting sessions with existing data"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Create some sessions first
    for i in range(5):
        client.post("/api/v1/chat", 
            json={"message": f"Test message {i}"}, 
            headers=headers
        )
    
    response = client.get("/api/v1/sessions", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 5
    assert data["has_more"] == False

@pytest.mark.asyncio
async def test_get_sessions_pagination(auth_token, db_session: AsyncSession):
    """Test session pagination"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Create more sessions than page size
    for i in range(15):
        client.post("/api/v1/chat", 
            json={"message": f"Test message {i}"}, 
            headers=headers
        )
    
    # First page
    response = client.get("/api/v1/sessions?page=1&size=10", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["total"] == 15
    assert len(data["items"]) == 10
    assert data["has_more"] == True
    assert data["page"] == 1
    assert data["size"] == 10

@pytest.mark.asyncio
async def test_get_session_messages(auth_token, db_session: AsyncSession):
    """Test getting messages from a session"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Create a session with messages
    chat_response = client.post("/api/v1/chat", 
        json={"message": "First message"}, 
        headers=headers
    )
    session_id = chat_response.json()["session_id"]
    
    # Add more messages
    for i in range(3):
        client.post("/api/v1/chat", 
            json={"message": f"Message {i}", "session_id": session_id}, 
            headers=headers
        )
    
    # Get messages
    response = client.get(f"/api/v1/sessions/{session_id}/messages", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    messages = response.json()
    assert len(messages) == 4  # Initial + 3 additional messages

@pytest.mark.asyncio
async def test_get_session_messages_unauthorized(auth_token, db_session: AsyncSession):
    """Test getting messages from another user's session"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Create a session
    chat_response = client.post("/api/v1/chat", 
        json={"message": "Test message"}, 
        headers=headers
    )
    session_id = chat_response.json()["session_id"]
    
    # Try to access with different user token
    other_token = create_access_token({"sub": "other-user-id"})
    other_headers = {"Authorization": f"Bearer {other_token}"}
    
    response = client.get(f"/api/v1/sessions/{session_id}/messages", headers=other_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_delete_session(auth_token, db_session: AsyncSession):
    """Test deleting a session"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Create a session
    chat_response = client.post("/api/v1/chat", 
        json={"message": "Test message"}, 
        headers=headers
    )
    session_id = chat_response.json()["session_id"]
    
    # Delete the session
    response = client.delete(f"/api/v1/sessions/{session_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    # Verify session is gone from list
    list_response = client.get("/api/v1/sessions", headers=headers)
    assert list_response.json()["total"] == 0

@pytest.mark.asyncio
async def test_delete_nonexistent_session(auth_token, db_session: AsyncSession):
    """Test deleting a session that doesn't exist"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    response = client.delete("/api/v1/sessions/nonexistent-session", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_delete_other_users_session(auth_token, db_session: AsyncSession):
    """Test deleting another user's session"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Create a session
    chat_response = client.post("/api/v1/chat", 
        json={"message": "Test message"}, 
        headers=headers
    )
    session_id = chat_response.json()["session_id"]
    
    # Try to delete with different user token
    other_token = create_access_token({"sub": "other-user-id"})
    other_headers = {"Authorization": f"Bearer {other_token}"}
    
    response = client.delete(f"/api/v1/sessions/{session_id}", headers=other_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND