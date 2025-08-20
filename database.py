from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from config import settings, EnvironmentEnum  # Added EnvironmentEnum

logger = logging.getLogger(__name__)

Base = declarative_base()

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.async_session_factory = None
    
    async def initialize(self):
        """Initialize database engine and session factory"""
        try:
            self.engine = create_async_engine(
                str(settings.database_url),
                echo=settings.environment == EnvironmentEnum.DEVELOPMENT,
                poolclass=NullPool,
                future=True
            )
            
            self.async_session_factory = sessionmaker(
                self.engine, 
                class_=AsyncSession, 
                expire_on_commit=False,
                autoflush=False
            )
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        """Close database engine"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")
    
    @asynccontextmanager
    async def get_session_dependency(self) -> AsyncGenerator[AsyncSession, None]:
        """FastAPI dependency for database sessions"""
        if not self.async_session_factory:
            raise RuntimeError("Database not initialized")
        
        session = self.async_session_factory()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Global database manager
db_manager.get_session_dependency = lambda: db_manager.get_session_dependency()