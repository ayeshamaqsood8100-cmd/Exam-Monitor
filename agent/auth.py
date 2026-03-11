from __future__ import annotations

import threading

from .config import settings


_session_token_lock = threading.Lock()
_session_token: str | None = None


def set_session_token(token: str | None) -> None:
    global _session_token
    with _session_token_lock:
        _session_token = token or None


def get_session_token() -> str | None:
    with _session_token_lock:
        return _session_token


def clear_session_token() -> None:
    set_session_token(None)


def build_auth_headers(*, session_token: str | None = None, content_type: str | None = "application/json") -> dict[str, str]:
    headers: dict[str, str] = {}
    token = session_token or get_session_token()

    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif settings.BACKEND_API_KEY:
        headers["X-API-Key"] = str(settings.BACKEND_API_KEY)
    else:
        raise RuntimeError("No backend authorization is available for the agent.")

    if content_type:
        headers["Content-Type"] = content_type

    return headers
