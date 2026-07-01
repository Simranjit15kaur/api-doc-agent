"""
Pydantic models for API request/response schemas and LangGraph state.
"""

from pydantic import BaseModel
from typing import Optional, List, Any
from typing_extensions import TypedDict


# ═══════════════════════════════════════════════════════════════
# LangGraph State
# ═══════════════════════════════════════════════════════════════

class ApiDocState(TypedDict, total=False):
    """Shared state object passed between every LangGraph node."""

    # ── Inputs (set before the graph runs) ────────────────────
    page_text: str
    page_url: str
    page_title: str
    language: str              # "python" | "javascript" | "curl"
    error_message: Optional[str]
    gemini_key: str            # forwarded from the request header

    # ── Set by classify_doc_node ──────────────────────────────
    doc_type: Optional[str]   # "REST endpoint" | "GraphQL" | "Webhook" | "SDK method" | "Unknown"

    # ── Set by extract_endpoint_node ──────────────────────────
    endpoint_method: Optional[str]     # GET | POST | PUT | DELETE | PATCH
    endpoint_url: Optional[str]        # /v1/charges
    endpoint_params: Optional[dict]    # { "amount": "integer, required", ... }
    auth_type: Optional[str]           # "Bearer token" | "API key" | "OAuth2" | "Basic auth"
    error_codes: Optional[list]        # [{ "code": 400, "meaning": "Invalid request" }]
    base_url: Optional[str]            # https://api.stripe.com

    # ── Set by generate_outputs_node ──────────────────────────
    code_snippet: Optional[str]
    postman_payload: Optional[dict]
    plain_english: Optional[str]

    # ── Set by error_trace_node (only if error present) ───────
    error_analysis: Optional[str]


# ═══════════════════════════════════════════════════════════════
# Analyze Endpoint
# ═══════════════════════════════════════════════════════════════

class AnalyzeRequest(BaseModel):
    page_text: str
    page_url: str
    page_title: str
    language: str = "python"  # "python" | "javascript" | "curl"
    error_message: Optional[str] = None


class EndpointInfo(BaseModel):
    method: Optional[str] = None
    url: Optional[str] = None
    auth: Optional[str] = None


class AnalyzeResponse(BaseModel):
    session_id: str
    doc_type: Optional[str] = None
    endpoint: Optional[EndpointInfo] = None
    code_snippet: Optional[str] = None
    postman_payload: Optional[Any] = None
    plain_english: Optional[str] = None
    error_analysis: Optional[str] = None
    from_cache: bool = False


# ═══════════════════════════════════════════════════════════════
# Chat Endpoint
# ═══════════════════════════════════════════════════════════════

class ChatMessage(BaseModel):
    role: str  # "user" or "agent"
    content: str


class ChatRequest(BaseModel):
    session_id: str
    question: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    session_id: str
