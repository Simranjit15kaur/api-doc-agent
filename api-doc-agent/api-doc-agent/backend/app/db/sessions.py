"""
CRUD operations for the sessions table.

Sessions store cached analysis results keyed by URL hash.
"""

import json
import logging
from typing import Optional
from app.db.connection import get_pool

logger = logging.getLogger(__name__)


async def get_session_by_hash(url_hash: str) -> Optional[dict]:
    """Look up a cached analysis by URL hash."""
    pool = await get_pool()
    if not pool:
        return None

    try:
        row = await pool.fetchrow(
            "SELECT id, url_hash, url, page_title, language, result_json, created_at, last_accessed_at "
            "FROM sessions WHERE url_hash = $1",
            url_hash
        )
        if row:
            # Update last_accessed_at
            await pool.execute(
                "UPDATE sessions SET last_accessed_at = NOW() WHERE url_hash = $1",
                url_hash
            )
            return {
                "id": str(row["id"]),
                "url_hash": row["url_hash"],
                "url": row["url"],
                "page_title": row["page_title"],
                "language": row["language"],
                "result_json": json.loads(row["result_json"]) if isinstance(row["result_json"], str) else row["result_json"],
                "created_at": str(row["created_at"]),
                "last_accessed_at": str(row["last_accessed_at"]),
            }
        return None
    except Exception as e:
        logger.error(f"Error fetching session by hash: {e}")
        return None


async def upsert_session(url_hash: str, url: str, page_title: str, language: str, result_json: dict) -> Optional[str]:
    """Insert or update a session. Returns the session ID."""
    pool = await get_pool()
    if not pool:
        return None

    try:
        result_str = json.dumps(result_json)
        row = await pool.fetchrow(
            """
            INSERT INTO sessions (url_hash, url, page_title, language, result_json)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            ON CONFLICT (url_hash)
            DO UPDATE SET 
                result_json = EXCLUDED.result_json,
                language = EXCLUDED.language,
                last_accessed_at = NOW()
            RETURNING id
            """,
            url_hash, url, page_title, language, result_str
        )
        return str(row["id"]) if row else None
    except Exception as e:
        logger.error(f"Error upserting session: {e}")
        return None


async def get_session_by_id(session_id: str) -> Optional[dict]:
    """Retrieve a session by its UUID."""
    pool = await get_pool()
    if not pool:
        return None

    try:
        row = await pool.fetchrow(
            "SELECT id, url_hash, url, page_title, language, result_json "
            "FROM sessions WHERE id = $1::uuid",
            session_id
        )
        if row:
            return {
                "id": str(row["id"]),
                "url": row["url"],
                "page_title": row["page_title"],
                "language": row["language"],
                "result_json": json.loads(row["result_json"]) if isinstance(row["result_json"], str) else row["result_json"],
            }
        return None
    except Exception as e:
        logger.error(f"Error fetching session by id: {e}")
        return None
