"""
The 4-node LangGraph analysis pipeline.

Graph flow:
  classify_doc → extract_endpoint → generate_outputs → [conditional] → error_trace → END
                                                      └─────────────────────────────→ END

Each node is a focused LLM call with a specific job.
The conditional edge after generate_outputs routes to error_trace
only if the user provided an error_message.
"""

import json
import logging
from typing import Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage

from app.schemas.models import ApiDocState
from app.core.gemini_factory import create_gemini_client

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def extract_json_text(text: str) -> str:
    """Strip markdown code fences from LLM JSON output."""
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence (```json or ```)
        text = text[text.find("\n") + 1:]
        # Remove closing fence
        if "```" in text:
            text = text[:text.rfind("```")]
    return text.strip()


def safe_parse_json(text: str) -> Optional[dict]:
    """Attempt to parse JSON from LLM output, stripping code fences first."""
    cleaned = extract_json_text(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning(f"JSON parse failed on: {cleaned[:200]}...")
        return None


def is_auth_error(error: Exception) -> bool:
    """Check if an error is a critical Gemini auth/quota error that should be propagated."""
    error_str = str(error)
    return any(marker in error_str for marker in [
        "API_KEY_INVALID", "PERMISSION_DENIED", "RESOURCE_EXHAUSTED",
        "INVALID_ARGUMENT",
    ])


# ═══════════════════════════════════════════════════════════════
# Node 1: classify_doc_node
# ═══════════════════════════════════════════════════════════════

async def classify_doc_node(state: ApiDocState) -> dict:
    """Determine what kind of API documentation this page is."""
    llm = create_gemini_client(state["gemini_key"])

    prompt = (
        "You are an API documentation classifier. Given the text of an API documentation page, "
        "identify the documentation type. Respond with ONLY one of these exact strings:\n"
        "REST endpoint | GraphQL | Webhook | SDK method | Unknown\n\n"
        f"Page title: {state.get('page_title', '')}\n\n"
        f"Page text:\n{state['page_text'][:3000]}"
    )

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        doc_type = response.content.strip()
        # Validate the response
        valid_types = ["REST endpoint", "GraphQL", "Webhook", "SDK method", "Unknown"]
        if doc_type not in valid_types:
            doc_type = "REST endpoint"  # Default to most common
    except Exception as e:
        logger.error(f"classify_doc_node error: {e}")
        if is_auth_error(e):
            raise  # Let the route handler catch this and return 401/429
        doc_type = "Unknown"

    return {"doc_type": doc_type}


# ═══════════════════════════════════════════════════════════════
# Node 2: extract_endpoint_node
# ═══════════════════════════════════════════════════════════════

async def extract_endpoint_node(state: ApiDocState) -> dict:
    """Extract structured endpoint details from the documentation."""
    llm = create_gemini_client(state["gemini_key"])

    prompt = (
        "You are an API documentation parser. Extract the following from the documentation below.\n"
        "Respond ONLY with a valid JSON object. No markdown, no backticks, just raw JSON.\n\n"
        "Extract:\n"
        '- method: HTTP method (GET/POST/PUT/DELETE/PATCH) or null\n'
        '- url: the endpoint path, e.g. /v1/charges\n'
        '- base_url: the full base URL, e.g. https://api.stripe.com\n'
        '- auth_type: authentication method description or null\n'
        '- params: object where keys are param names and values describe type + required status\n'
        '- error_codes: array of objects with "code" and "meaning" fields\n\n'
        f"Documentation type: {state.get('doc_type', 'Unknown')}\n\n"
        f"Documentation:\n{state['page_text'][:8000]}"
    )

    defaults = {
        "endpoint_method": None,
        "endpoint_url": None,
        "endpoint_params": None,
        "auth_type": None,
        "error_codes": None,
        "base_url": None,
    }

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        parsed = safe_parse_json(response.content)

        if parsed:
            return {
                "endpoint_method": parsed.get("method"),
                "endpoint_url": parsed.get("url"),
                "endpoint_params": parsed.get("params"),
                "auth_type": parsed.get("auth_type"),
                "error_codes": parsed.get("error_codes"),
                "base_url": parsed.get("base_url"),
            }
        else:
            # Retry once
            logger.info("Retrying extract_endpoint_node after JSON parse failure")
            response = await llm.ainvoke([HumanMessage(content=prompt + "\n\nIMPORTANT: Respond with valid JSON only. No markdown.")])
            parsed = safe_parse_json(response.content)
            if parsed:
                return {
                    "endpoint_method": parsed.get("method"),
                    "endpoint_url": parsed.get("url"),
                    "endpoint_params": parsed.get("params"),
                    "auth_type": parsed.get("auth_type"),
                    "error_codes": parsed.get("error_codes"),
                    "base_url": parsed.get("base_url"),
                }

    except Exception as e:
        logger.error(f"extract_endpoint_node error: {e}")
        if is_auth_error(e):
            raise

    return defaults


# ═══════════════════════════════════════════════════════════════
# Node 3: generate_outputs_node
# ═══════════════════════════════════════════════════════════════

async def generate_outputs_node(state: ApiDocState) -> dict:
    """Generate the three main outputs: code snippet, Postman payload, plain English."""
    llm = create_gemini_client(state["gemini_key"])

    language = state.get("language", "python")
    method = state.get("endpoint_method", "GET")
    url = state.get("endpoint_url", "/unknown")
    base_url = state.get("base_url", "https://api.example.com")
    params = state.get("endpoint_params", {})
    auth_type = state.get("auth_type", "Bearer token")
    full_url = f"{base_url}{url}" if base_url and url else url

    # Build language-specific instructions
    lang_instructions = {
        "python": (
            "For code_snippet: Use the `requests` library. Include imports, "
            "include headers with auth, include a sample body with realistic placeholder values, "
            "add a comment showing how to handle the response."
        ),
        "javascript": (
            "For code_snippet: Use `fetch()` with async/await. "
            "Include error handling with try/catch. Include headers and body."
        ),
        "curl": (
            "For code_snippet: Write a full curl command with -X, -H, -d flags. "
            "Make it copy-pasteable."
        ),
    }

    prompt = f"""You are an API code generator. Generate three outputs based on the API endpoint details below.
Respond ONLY with a valid JSON object. No markdown, no backticks, just raw JSON.

API Details:
- Method: {method}
- Endpoint: {url}
- Base URL: {base_url}
- Full URL: {full_url}
- Authentication: {auth_type}
- Parameters: {json.dumps(params) if params else "None specified"}
- Language preference: {language}

Generate a JSON object with exactly these three keys:

1. "code_snippet": A ready-to-run code example in {language}.
   {lang_instructions.get(language, lang_instructions["python"])}

2. "postman_payload": A Postman-importable JSON object with keys: method, url (full URL), headers (object), body (object with realistic sample values).

3. "plain_english": 2-4 sentences explaining when and why to use this endpoint. Mention required params and what the response contains. Note any common gotchas.

Respond with valid JSON only."""

    defaults = {
        "code_snippet": None,
        "postman_payload": None,
        "plain_english": None,
    }

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        parsed = safe_parse_json(response.content)

        if parsed:
            return {
                "code_snippet": parsed.get("code_snippet"),
                "postman_payload": parsed.get("postman_payload"),
                "plain_english": parsed.get("plain_english"),
            }
        else:
            # Retry once
            logger.info("Retrying generate_outputs_node after JSON parse failure")
            response = await llm.ainvoke([HumanMessage(content=prompt + "\n\nCRITICAL: Output valid JSON only.")])
            parsed = safe_parse_json(response.content)
            if parsed:
                return {
                    "code_snippet": parsed.get("code_snippet"),
                    "postman_payload": parsed.get("postman_payload"),
                    "plain_english": parsed.get("plain_english"),
                }

    except Exception as e:
        logger.error(f"generate_outputs_node error: {e}")
        if is_auth_error(e):
            raise

    return defaults


# ═══════════════════════════════════════════════════════════════
# Node 4: error_trace_node (conditional)
# ═══════════════════════════════════════════════════════════════

async def error_trace_node(state: ApiDocState) -> dict:
    """Analyse the user's error message in context of the documentation."""
    llm = create_gemini_client(state["gemini_key"])

    method = state.get("endpoint_method", "")
    url = state.get("endpoint_url", "")
    error_msg = state.get("error_message", "")
    page_text = state.get("page_text", "")

    prompt = f"""A developer is using the following API endpoint:
{method} {url}

They received this error:
{error_msg}

The API documentation says:
{page_text[:5000]}

Explain in plain English:
1. Why this error occurred
2. Which specific part of the documentation they missed or misunderstood
3. The exact fix they need to make to their code

Be specific and actionable. If the error code is documented, reference the exact section."""

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return {"error_analysis": response.content.strip()}
    except Exception as e:
        logger.error(f"error_trace_node error: {e}")
        return {"error_analysis": f"Error analysis failed: {str(e)}"}


# ═══════════════════════════════════════════════════════════════
# Conditional Router
# ═══════════════════════════════════════════════════════════════

def should_trace_error(state: ApiDocState) -> str:
    """Route to error_trace if user provided an error message, else END."""
    if state.get("error_message"):
        return "error_trace"
    return END


# ═══════════════════════════════════════════════════════════════
# Graph Assembly
# ═══════════════════════════════════════════════════════════════

def build_api_doc_graph():
    """Build and compile the 4-node analysis pipeline."""
    graph = StateGraph(ApiDocState)

    # Add nodes
    graph.add_node("classify_doc", classify_doc_node)
    graph.add_node("extract_endpoint", extract_endpoint_node)
    graph.add_node("generate_outputs", generate_outputs_node)
    graph.add_node("error_trace", error_trace_node)

    # Set entry point
    graph.set_entry_point("classify_doc")

    # Linear edges
    graph.add_edge("classify_doc", "extract_endpoint")
    graph.add_edge("extract_endpoint", "generate_outputs")

    # Conditional edge: after generate_outputs, check if error tracing is needed
    graph.add_conditional_edges(
        "generate_outputs",
        should_trace_error,
        {
            "error_trace": "error_trace",
            END: END,
        }
    )

    # error_trace always ends
    graph.add_edge("error_trace", END)

    return graph.compile()


# Pre-compile the graph (it's stateless — safe to reuse)
api_doc_graph = build_api_doc_graph()
