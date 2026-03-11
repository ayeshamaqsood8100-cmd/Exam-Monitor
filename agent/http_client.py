"""
Shared HTTP client utilities for the Markaz agent.

The agent performs a high volume of short backend calls during exams.
Reusing one keep-alive client avoids repeated TCP/TLS setup on every request.
"""
from __future__ import annotations

import threading

import httpx


_client_lock = threading.Lock()
_shared_client: httpx.Client | None = None


def get_http_client() -> httpx.Client:
    global _shared_client

    with _client_lock:
        if _shared_client is None:
            _shared_client = httpx.Client(
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return _shared_client


def close_http_client() -> None:
    global _shared_client

    with _client_lock:
        if _shared_client is not None:
            _shared_client.close()
            _shared_client = None
