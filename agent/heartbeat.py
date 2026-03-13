"""
Heartbeat management module for the Markaz Exam Monitor agent.
Handles background pinging to prove the agent is alive.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Callable

from .auth import build_auth_headers
from .config import settings
from .http_client import get_http_client


class HeartbeatManager:
    """
    Manages the background heartbeat thread that periodically pings the backend.
    """

    def __init__(
        self,
        session_id: str,
        on_force_stop: Callable[[], None] | None = None,
        on_connectivity_change: Callable[[bool, str | None], None] | None = None,
    ) -> None:
        self.session_id = session_id
        self._on_force_stop = on_force_stop
        self._on_connectivity_change = on_connectivity_change
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._is_connected: bool | None = None

    def start(self) -> None:
        """Starts the background heartbeat loop."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signals the background heartbeat loop to stop and exit cleanly."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=2.5)
        self._thread = None

    def _loop(self) -> None:
        """Continuously pings the backend every 5 seconds until stopped."""
        while not self._stop_event.is_set():
            self._ping()
            self._stop_event.wait(5.0)

    def _ping(self) -> None:
        """Performs a single synchronous HTTP POST heartbeat ping."""
        url = f"{settings.BACKEND_URL.rstrip('/')}/heartbeat"
        headers = build_auth_headers()
        timestamp = datetime.now(timezone.utc).isoformat()

        payload = {
            "session_id": self.session_id,
            "timestamp": timestamp,
        }

        try:
            response = get_http_client().post(url, headers=headers, json=payload, timeout=10.0)
            response.raise_for_status()
            self._emit_connectivity_change(True, None)

            data = response.json()
            if data.get("force_stop", False) is True and self._on_force_stop:
                self._on_force_stop()
        except Exception as e:
            self._emit_connectivity_change(False, str(e))
            print(f"[HEARTBEAT] Warning: ping failed - {e}")

    def _emit_connectivity_change(self, is_connected: bool, detail: str | None) -> None:
        if self._is_connected is is_connected:
            return

        self._is_connected = is_connected
        if self._on_connectivity_change:
            try:
                self._on_connectivity_change(is_connected, detail)
            except Exception as e:
                print(f"[HEARTBEAT] Warning: connectivity callback failed - {e}")
