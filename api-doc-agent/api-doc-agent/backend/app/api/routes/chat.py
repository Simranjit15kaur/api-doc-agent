"""
POST /chat — Follow-up chat endpoint.

Flow:
  1. Load the original analysis from sessions table using session_id
  2. Run the chat graph with the question + history + analysis context
  3. Persist both user message and agent reply to messages table
  4. Return the reply
"""

import logging

from fastapi import APIRouter, Request, HTTPException
from app.schemas.models import ChatRequest, ChatResponse
from app.api.deps import get_gemini_key
from app.graphs.chat_graph import chat_graph
from app.db.sessions import get_session_by_id
from app.db.messages import save_message

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    """Handle a follow-up chat question grounded in the original analysis."""

    # 1. Extract Gemini key
    gemini_key = get_gemini_key(request)

    # 2. Load original analysis for context
    original_analysis = {}
    try:
        session = await get_session_by_id(body.session_id)
        if session and session.get("result_json"):
            original_analysis = session["result_json"]
    except Exception as e:
        logger.warning(f"Could not load session context: {e}")
        # Continue without context — still useful

    # 3. Run chat graph
    try:
        chat_state = {
            "gemini_key": gemini_key,
            "question": body.question,
            "history": [msg.model_dump() for msg in body.history],
            "original_analysis": original_analysis,
        }

        result = await chat_graph.ainvoke(chat_state)
        reply = result.get("reply", "Sorry, I could not generate a response.")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Chat graph error: {error_msg}")

        if "PERMISSION_DENIED" in error_msg or "API_KEY_INVALID" in error_msg:
            raise HTTPException(status_code=401, detail="Invalid Gemini API key.")
        if "RESOURCE_EXHAUSTED" in error_msg:
            raise HTTPException(status_code=429, detail="Rate limit exceeded.")

        raise HTTPException(status_code=500, detail=f"Chat failed: {error_msg}")

    # 4. Persist messages (best-effort)
    try:
        await save_message(body.session_id, "user", body.question)
        await save_message(body.session_id, "agent", reply)
    except Exception as e:
        logger.warning(f"Failed to persist chat messages: {e}")

    return ChatResponse(reply=reply, session_id=body.session_id)
