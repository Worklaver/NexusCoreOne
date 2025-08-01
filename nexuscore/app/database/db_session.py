from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://nexususer:password@postgres/nexuscore")

# Create async engine
async_engine = create_async_engine(DATABASE_URL, echo=True)

# Create async sessionmaker
async_session_factory = sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Sync engine for migrations and sync operations
sync_engine = create_engine(DATABASE_URL.replace("+asyncpg", ""))
SyncSession = sessionmaker(bind=sync_engine)

@contextmanager
def get_sync_session():
    """Context manager for handling synchronous database sessions"""
    session = SyncSession()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

async def init_models():
    """Initialize database models"""
    from app.database.models import Base
    async with async_engine.begin() as conn:
        # Uncomment to drop all tables (DANGEROUS in production!)
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)