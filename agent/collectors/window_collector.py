"""
Window monitoring collector.
Polls the active foreground window and buffers changes thread-safely.
"""
import threading
from datetime import datetime, timezone
from urllib.parse import urlparse
from .. import platform_compat  # noqa: F401
import pygetwindow


def _pick_title(active_win, fallback_title: str) -> str:
    """Prefer focused page metadata on macOS when it is available."""
    tab_title = getattr(active_win, "tab_title", None) if active_win is not None else None
    tab_url = getattr(active_win, "tab_url", None) if active_win is not None else None
    app_name = getattr(active_win, "app_name", None) if active_win is not None else None

    if tab_title:
        return str(tab_title).strip()

    if tab_url:
        parsed = urlparse(str(tab_url).strip())
        compact_url = parsed.netloc + parsed.path if parsed.netloc else parsed.path or str(tab_url).strip()
        compact_url = compact_url[:140]
        if app_name:
            return f"{compact_url} - {app_name}"
        return compact_url

    return fallback_title

class WindowCollector:
    """
    Monitors the active foreground window every 2 seconds and buffers changes.
    """
    def __init__(self) -> None:
        self._buffer: list[dict] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_window: str = ""
        
    def start(self) -> None:
        """Starts the background window polling loop."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        
    def stop(self) -> None:
        """Signals the background polling loop to stop and exit cleanly."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=2.5)
        
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
                app_name = "Unknown"
                if active_win is not None:
                    fallback_title = active_win.title
                    current_title = _pick_title(active_win, fallback_title)
                    explicit_app_name = getattr(active_win, "app_name", None)
                    if explicit_app_name:
                        app_name = explicit_app_name
                else:
                    current_title = "Unknown"
                    
                # Only record if the window actually changed from the last polled state
                if current_title != self._last_window:
                    self._last_window = current_title
                    
                    # Fall back to a title split only when the window shim did not provide an app name.
                    if app_name == "Unknown" and " - " in current_title:
                        app_name = current_title.split(" - ")[-1].strip()
                    elif app_name == "Unknown" and current_title:
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
