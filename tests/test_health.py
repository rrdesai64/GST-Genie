import pytest
from fastapi import status
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "components" in data

@pytest.mark.asyncio
async def test_readiness_check():
    """Test readiness probe"""
    response = client.get("/health/ready")
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]

@pytest.mark.asyncio
async def test_liveness_check():
    """Test liveness probe"""
    response = client.get("/health/live")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data