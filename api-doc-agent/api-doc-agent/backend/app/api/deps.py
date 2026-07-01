"""
Shared FastAPI dependencies.

Provides Gemini key extraction from request headers
and database pool access.
"""

from fastapi import Request, HTTPException


def get_gemini_key(request: Request) -> str:
    """Extract the Gemini API key from the X-Gemini-Key header."""
    key = request.headers.get("X-Gemini-Key") or request.headers.get("x-gemini-key")
    if not key:
        raise HTTPException(
            status_code=401,
            detail="Missing Gemini API key. Set it in the extension's Settings page."
        )
    return key
