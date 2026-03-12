"""
Clipboard monitoring collector.
Polls the system clipboard for text changes and buffers them thread-safely.
"""
import threading
import time
from datetime import datetime, timezone
from .. import platform_compat  # noqa: F401
import pyperclip
import pygetwindow

class ClipboardCollector:
    """
    Monitors the system clipboard every 1 second and buffers new text copies.
    """
    def __init__(self) -> None:
        self._buffer: list[dict] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_content: str = ""
        self._last_activity_monotonic: float | None = None
        
    def start(self) -> None:
        """Starts the background clipboard polling loop."""
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

    def get_last_activity_monotonic(self) -> float | None:
        return self._last_activity_monotonic
            
    def _loop(self) -> None:
        """Continuously polls the clipboard every 1 second until stopped."""
        # Initialize baseline immediately to avoid triggering a "false" copy event on startup
        try:
            self._last_content = pyperclip.paste()
        except Exception:
            pass

        while not self._stop_event.is_set():
            try:
                current_content = pyperclip.paste()
                
                if current_content and current_content != self._last_content:
                    self._last_content = current_content
                    
                    # Attempt to grab the active window where the copy occurred
                    source_app = "Unknown"
                    try:
                        active_win = pygetwindow.getActiveWindow()
                        if active_win:
                            source_app = active_win.title
                    except Exception:
                        pass
                    
                    # Truncate clipboard content to maximum 500 characters
                    truncated_content = current_content
                    if len(truncated_content) > 500:
                        truncated_content = truncated_content[:497] + "..."

                    event = {
                        "event_type": "copy",
                        "content": truncated_content,
                        "source_application": source_app,
                        "destination_application": None,
                        "captured_at": datetime.now(timezone.utc).isoformat()
                    }

                    self._last_activity_monotonic = time.monotonic()

                    with self._lock:
                        self._buffer.append(event)
                        
            except pyperclip.PyperclipException:
                # E.g., clipboard is locked by another process or holds non-text (image) data
                pass
            except Exception:
                # Catch-all to ensure the daemon never dies
                pass
                
            self._stop_event.wait(1.0)
