"""
CRUD operations for the messages table.

Messages store chat conversation history for long-term persistence.
"""

import logging
from typing import List
from app.db.connection import get_pool

logger = logging.getLogger(__name__)


async def save_message(session_id: str, role: str, content: str) -> None:
    """Insert a single chat message."""
    pool = await get_pool()
    if not pool:
        return

    try:
        await pool.execute(
            "INSERT INTO messages (session_id, role, content) VALUES ($1::uuid, $2, $3)",
            session_id, role, content
        )
    except Exception as e:
        logger.error(f"Error saving message: {e}")


async def get_messages(session_id: str, limit: int = 50) -> List[dict]:
    """Retrieve chat messages for a session, ordered by creation time."""
    pool = await get_pool()
    if not pool:
        return []

    try:
        rows = await pool.fetch(
            "SELECT role, content, created_at FROM messages "
            "WHERE session_id = $1::uuid "
            "ORDER BY created_at ASC "
            "LIMIT $2",
            session_id, limit
        )
        return [
            {"role": row["role"], "content": row["content"], "created_at": str(row["created_at"])}
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return []
