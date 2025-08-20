import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from main import app
from database import Base, db_manager
from config import settings

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost/test_gemini_chat"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db():
    """Create test database and tables"""
    # Create test engine
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
        future=True
    )
    
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    test_async_session_factory = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    yield test_async_session_factory
    
    # Drop tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await test_engine.dispose()

@pytest.fixture
async def db_session(test_db):
    """Create a clean database session for each test"""
    async with test_db() as session:
        yield session
        
        # Rollback any changes
        await session.rollback()

@pytest.fixture
def client():
    """Create a test client"""
    from fastapi.testclient import TestClient
    return TestClient(app)

@pytest.fixture(autouse=True)
async def cleanup_test_data(db_session: AsyncSession):
    """Clean up test data after each test"""
    yield
    # Clean up all test data
    try:
        await db_session.execute("DELETE FROM chat_messages")
        await db_session.execute("DELETE FROM chat_sessions")
        await db_session.execute("DELETE FROM users")
        await db_session.commit()
    except:
        await db_session.rollback()