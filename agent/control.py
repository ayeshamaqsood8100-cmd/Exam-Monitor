import threading
from collections.abc import Callable

from .auth import build_auth_headers
from .config import settings
from .http_client import get_http_client


class SessionControlManager:
    def __init__(self, session_id: str, on_status_change: Callable[[str], None], poll_interval_seconds: float = 10.0) -> None:
        self.session_id = session_id
        self._on_status_change = on_status_change
        self._poll_interval_seconds = poll_interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_status: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=2.5)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            status = self._fetch_status()
            if status and status != self._last_status:
                self._last_status = status
                self._on_status_change(status)
            self._stop_event.wait(self._poll_interval_seconds)

    def _fetch_status(self) -> str | None:
        url = f"{settings.BACKEND_URL.rstrip('/')}/session/status"
        headers = build_auth_headers()

        try:
            response = get_http_client().post(
                url,
                headers=headers,
                json={"session_id": self.session_id},
                timeout=5.0,
            )
            response.raise_for_status()
            data = response.json()
            return str(data.get("status", "")).lower()
        except Exception as e:
            print(f"[CONTROL] Warning: status poll failed - {e}")
            return None
