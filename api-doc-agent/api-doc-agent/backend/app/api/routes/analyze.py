"""
POST /analyze — Main analysis endpoint.

Flow:
  1. Hash the URL
  2. Check cache (sessions table)
  3. If cached → return immediately with from_cache: true
  4. If not cached → run LangGraph pipeline → cache result → return
"""

import hashlib
import uuid
import logging

from fastapi import APIRouter, Request, HTTPException
from app.schemas.models import AnalyzeRequest, AnalyzeResponse, EndpointInfo
from app.api.deps import get_gemini_key
from app.graphs.api_doc_graph import api_doc_graph
from app.db.sessions import get_session_by_hash, upsert_session

logger = logging.getLogger(__name__)
router = APIRouter()


def compute_url_hash(url: str) -> str:
    """SHA256 hash of the URL, first 16 chars."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


@router.post("", response_model=AnalyzeResponse)
async def analyze_doc(body: AnalyzeRequest, request: Request):
    """Analyse an API documentation page and return structured results."""

    # 1. Extract Gemini key from header
    gemini_key = get_gemini_key(request)

    # 2. Check cache
    url_hash = compute_url_hash(body.page_url)

    # Only check cache if no error_message (error traces are always fresh)
    if not body.error_message:
        try:
            cached = await get_session_by_hash(url_hash)
            if cached and cached.get("result_json"):
                result = cached["result_json"]
                result["from_cache"] = True
                result["session_id"] = cached["id"]
                return AnalyzeResponse(**result)
        except Exception as e:
            logger.warning(f"Cache lookup failed (continuing without cache): {e}")

    # 3. Run LangGraph pipeline
    try:
        initial_state = {
            "page_text": body.page_text,
            "page_url": body.page_url,
            "page_title": body.page_title,
            "language": body.language,
            "error_message": body.error_message,
            "gemini_key": gemini_key,
        }

        result_state = await api_doc_graph.ainvoke(initial_state)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"LangGraph pipeline error: {error_msg}")

        # Detect specific Gemini errors
        if "PERMISSION_DENIED" in error_msg or "API_KEY_INVALID" in error_msg or "INVALID_ARGUMENT" in error_msg or "401" in error_msg:
            raise HTTPException(status_code=401, detail="Invalid Gemini API key.")
        if "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
            raise HTTPException(status_code=429, detail="Gemini API rate limit exceeded. Please wait and try again.")

        raise HTTPException(status_code=500, detail=f"Analysis failed: {error_msg}")

    # 4. Build response
    response_data = {
        "session_id": "",  # Will be set after DB upsert
        "doc_type": result_state.get("doc_type"),
        "endpoint": EndpointInfo(
            method=result_state.get("endpoint_method"),
            url=result_state.get("endpoint_url"),
            auth=result_state.get("auth_type"),
        ),
        "code_snippet": result_state.get("code_snippet"),
        "postman_payload": result_state.get("postman_payload"),
        "plain_english": result_state.get("plain_english"),
        "error_analysis": result_state.get("error_analysis"),
        "from_cache": False,
    }

    # 5. Cache the result (best-effort)
    try:
        # Convert EndpointInfo to dict for storage
        cache_data = {**response_data}
        cache_data["endpoint"] = {
            "method": response_data["endpoint"].method,
            "url": response_data["endpoint"].url,
            "auth": response_data["endpoint"].auth,
        }

        session_id = await upsert_session(
            url_hash=url_hash,
            url=body.page_url,
            page_title=body.page_title,
            language=body.language,
            result_json=cache_data,
        )

        if session_id:
            response_data["session_id"] = session_id
        else:
            response_data["session_id"] = str(uuid.uuid4())

    except Exception as e:
        logger.warning(f"Failed to cache result (returning anyway): {e}")
        response_data["session_id"] = str(uuid.uuid4())

    return AnalyzeResponse(**response_data)
