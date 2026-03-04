"""
Heartbeat management module for the Markaz Exam Monitor agent.
Handles background pinging to prove the agent is alive.
"""
import threading
import httpx
from datetime import datetime, timezone
from .config import settings

class HeartbeatManager:
    """
    Manages the background heartbeat thread that periodically pings the backend.
    """
    def __init__(self, session_id: str, on_force_stop: callable = None) -> None:
        self.session_id = session_id
        self._on_force_stop = on_force_stop
        self._stop_event = threading.Event()
        self._thread = None
        
    def start(self) -> None:
        """Starts the background heartbeat loop."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        
    def stop(self) -> None:
        """Signals the background heartbeat loop to stop and exit cleanly."""
        self._stop_event.set()
        
    def _loop(self) -> None:
        """Continuously pings the backend every 30 seconds until stopped."""
        while not self._stop_event.is_set():
            self._ping()
            # Wait for 30 seconds; will exit wait early if stop() is called.
            self._stop_event.wait(30.0)
            
    def _ping(self) -> None:
        """Performs a single synchronous HTTP POST heartbeat ping."""
        url = f"{settings.BACKEND_URL.rstrip('/')}/heartbeat"
        
        headers = {
            "X-API-Key": settings.API_KEY,
            "Content-Type": "application/json"
        }
        
        # Ensure timestamp is explicit timezone-aware UTC inside Python, formatted as ISO 8601 string
        timestamp = datetime.now(timezone.utc).isoformat()
        
        payload = {
            "session_id": self.session_id,
            "timestamp": timestamp
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            # Safe JSON parse after confirming 200 HTTP success
            data = response.json()
            if data.get("force_stop", False) is True:
                if self._on_force_stop:
                    self._on_force_stop()
                    
        except Exception as e:
            # Silent failure for the daemon, so it never crashes the main agent loop.
            print(f"[HEARTBEAT] Warning: ping failed — {str(e)}")
