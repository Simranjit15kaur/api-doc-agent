"""
Database connection pool management using asyncpg.

Gracefully handles missing DATABASE_URL — the app runs without persistence.
"""

import asyncpg
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def init_pool():
    """Initialize the asyncpg connection pool."""
    global _pool
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        logger.warning("DATABASE_URL not set — running without database persistence")
        return

    # asyncpg expects postgresql:// not postgresql+asyncpg://
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")

    _pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=1,
        max_size=5,
        command_timeout=30,
    )
    logger.info("Database connection pool established")


async def close_pool():
    """Close the connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def get_pool() -> Optional[asyncpg.Pool]:
    """Get the current connection pool (may be None if DB is unavailable)."""
    return _pool
