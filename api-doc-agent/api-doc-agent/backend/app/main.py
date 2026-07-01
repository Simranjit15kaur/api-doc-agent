"""
FastAPI application entry point.

Sets up CORS, includes route modules, and initializes the database
connection pool on startup.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging

from app.api.routes import analyze, chat
from app.db.connection import init_pool, close_pool

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the application lifecycle — DB pool startup/shutdown."""
    try:
        await init_pool()
        logger.info("Database pool initialized")
    except Exception as e:
        logger.warning(f"Database pool initialization failed (running without persistence): {e}")
    yield
    try:
        await close_pool()
        logger.info("Database pool closed")
    except Exception:
        pass


app = FastAPI(
    title="API Doc Agent Backend",
    description="AI agent backend that analyses API documentation and generates code snippets, Postman payloads, and explanations.",
    version="1.0.0",
    lifespan=lifespan
)

# ── CORS ──────────────────────────────────────────────────────
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────
app.include_router(analyze.router, prefix="/analyze", tags=["analyze"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])


@app.get("/health")
async def health():
    return {"status": "ok"}
