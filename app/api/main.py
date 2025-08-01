from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.api.routes import accounts, tasks, settings, proxies, workers
from app.database.db_session import async_session_factory, init_models

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/api.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="NexusCore API",
    description="API for managing NexusCore Telegram operations",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get database session
async def get_db():
    db = async_session_factory()
    try:
        yield db
    finally:
        await db.close()

# Include routers
app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(proxies.router, prefix="/api/proxies", tags=["proxies"])
app.include_router(workers.router, prefix="/api/workers", tags=["workers"])

@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "version": app.version}

@app.on_event("startup")
async def startup_event():
    """Initialize database models and other startup tasks"""
    logger.info("Starting API server")
    await init_models()
    logger.info("Database models initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown tasks"""
    logger.info("Shutting down API server")