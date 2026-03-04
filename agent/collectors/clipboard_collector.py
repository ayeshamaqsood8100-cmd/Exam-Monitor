"""
Clipboard monitoring collector.
Polls the system clipboard for text changes and buffers them thread-safely.
"""
import threading
from datetime import datetime, timezone
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
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._last_content: str = ""
        
    def start(self) -> None:
        """Starts the background clipboard polling loop."""
        self._stop_event.clear()
        self._thread.start()
        
    def stop(self) -> None:
        """Signals the background polling loop to stop and exit cleanly."""
        self._stop_event.set()
        
    def flush(self) -> list[dict]:
        """Atomically returns and clears the current buffer."""
        with self._lock:
            data = self._buffer.copy()
            self._buffer.clear()
            return data
            
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
                    
                    with self._lock:
                        self._buffer.append(event)
                        
            except pyperclip.PyperclipException:
                # E.g., clipboard is locked by another process or holds non-text (image) data
                pass
            except Exception:
                # Catch-all to ensure the daemon never dies
                pass
                
            self._stop_event.wait(1.0)
