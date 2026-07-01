"""
Lightweight follow-up chat graph.

Single-node graph that loads the original analysis as context,
appends conversation history, and returns a grounded answer.
"""

import logging
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from typing import Optional, List

from app.core.gemini_factory import create_gemini_client

logger = logging.getLogger(__name__)


# ── Chat State ────────────────────────────────────────────────

class ChatState(TypedDict, total=False):
    gemini_key: str
    question: str
    history: List[dict]           # [{ "role": "user"|"agent", "content": "..." }]
    original_analysis: dict       # The full analysis result JSON for context
    reply: Optional[str]


# ── Chat Node ─────────────────────────────────────────────────

async def chat_node(state: ChatState) -> dict:
    """Answer a follow-up question grounded in the original analysis."""
    llm = create_gemini_client(state["gemini_key"], temperature=0.3)

    analysis = state.get("original_analysis", {})

    # Build system context from the original analysis
    context_parts = []
    if analysis.get("doc_type"):
        context_parts.append(f"Documentation type: {analysis['doc_type']}")
    if analysis.get("endpoint"):
        ep = analysis["endpoint"]
        context_parts.append(f"Endpoint: {ep.get('method', '')} {ep.get('url', '')}")
        if ep.get("auth"):
            context_parts.append(f"Authentication: {ep['auth']}")
    if analysis.get("code_snippet"):
        context_parts.append(f"Generated code:\n{analysis['code_snippet']}")
    if analysis.get("plain_english"):
        context_parts.append(f"Explanation: {analysis['plain_english']}")

    context_str = "\n".join(context_parts) if context_parts else "No previous analysis available."

    system_prompt = (
        "You are an API documentation assistant. A developer has already analysed an API endpoint "
        "and is now asking follow-up questions. Use the analysis context below to give specific, "
        "actionable answers. If the question is about code, include code examples.\n\n"
        f"=== Analysis Context ===\n{context_str}\n=== End Context ==="
    )

    # Build message history
    messages = [SystemMessage(content=system_prompt)]

    for msg in state.get("history", []):
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    # Add the current question
    messages.append(HumanMessage(content=state["question"]))

    try:
        response = await llm.ainvoke(messages)
        return {"reply": response.content.strip()}
    except Exception as e:
        logger.error(f"chat_node error: {e}")
        return {"reply": f"Sorry, I encountered an error: {str(e)}"}


# ── Graph Assembly ────────────────────────────────────────────

def build_chat_graph():
    """Build the simple single-node chat graph."""
    graph = StateGraph(ChatState)
    graph.add_node("chat", chat_node)
    graph.set_entry_point("chat")
    graph.add_edge("chat", END)
    return graph.compile()


chat_graph = build_chat_graph()
