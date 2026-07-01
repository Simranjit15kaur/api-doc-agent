"""
Gemini LLM factory — creates a ChatGoogleGenerativeAI instance per request
using the caller's API key (BYOK pattern).
"""

from langchain_google_genai import ChatGoogleGenerativeAI


def create_gemini_client(api_key: str, temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    """
    Build a Gemini LLM client with the user-provided API key.
    
    Uses gemini-2.5-flash for best speed/quality tradeoff on structured tasks.
    Temperature is kept low for deterministic structured output.
    """
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=api_key,
        temperature=temperature,
        max_output_tokens=4096,
        convert_system_message_to_human=False,
    )
