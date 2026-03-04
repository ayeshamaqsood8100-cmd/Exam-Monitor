"""
Window monitoring collector.
Polls the active foreground window and buffers changes thread-safely.
"""
import threading
from datetime import datetime, timezone
import pygetwindow

class WindowCollector:
    """
    Monitors the active foreground window every 2 seconds and buffers changes.
    """
    def __init__(self) -> None:
        self._buffer: list[dict] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._last_window: str = ""
        
    def start(self) -> None:
        """Starts the background window polling loop."""
        self._stop_event.clear()
        self._thread.start()
        
    def stop(self) -> None:
        """Signals the background polling loop to stop and exit cleanly."""
        self._stop_event.set()
        
    def peek(self, limit: int = 500) -> list[dict]:
        """Atomically returns up to `limit` items from the front of the buffer."""
        with self._lock:
            return self._buffer[:limit]
        
    def pop(self, count: int) -> None:
        """Atomically removes `count` items from the front of the buffer."""
        with self._lock:
            del self._buffer[:count]
            
    def _loop(self) -> None:
        """Continuously polls the active window every 2 seconds until stopped."""
        while not self._stop_event.is_set():
            try:
                active_win = pygetwindow.getActiveWindow()
                if active_win is not None:
                    current_title = active_win.title
                else:
                    current_title = "Unknown"
                    
                # Only record if the window actually changed from the last polled state
                if current_title != self._last_window:
                    self._last_window = current_title
                    
                    # Attempt crude extraction of application name (often after final dash in Windows)
                    app_name = "Unknown"
                    if " - " in current_title:
                        app_name = current_title.split(" - ")[-1].strip()
                    elif current_title:
                        app_name = current_title

                    event = {
                        "window_title": current_title,
                        "application_name": app_name,
                        "switched_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    with self._lock:
                        self._buffer.append(event)
                        
            except Exception:
                # Do not crash the daemon thread if pygetwindow encounters an OS permissions error
                pass
                
            self._stop_event.wait(2.0)
