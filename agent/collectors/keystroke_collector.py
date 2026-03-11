"""
Keystroke monitoring collector.
Hooks the system keyboard to record keystrokes and buffers them thread-safely.
"""
import threading
import time
from datetime import datetime, timezone
from .. import platform_compat  # noqa: F401
from pynput import keyboard
import pygetwindow

class KeystrokeCollector:
    """
    Hooks the system keyboard using pynput and buffers keystrokes.
    """
    def __init__(self) -> None:
        self._buffer: list[dict] = []
        self._lock = threading.Lock()
        self._listener: keyboard.Listener | None = None
        self._last_keypress_monotonic: float | None = None
        self._listener_started_monotonic: float | None = None
        
    def start(self) -> None:
        """Starts the background keyboard listener daemon thread."""
        if self._listener is not None and self._listener.is_alive():
            return
        # pynput Listener is naturally a daemon thread.
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.start()
        self._listener_started_monotonic = time.monotonic()
        
    def stop(self) -> None:
        """Stops the underlying keyboard listener correctly."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def restart(self) -> None:
        """Recreate the pynput listener if it becomes stale or dies silently."""
        self.stop()
        self.start()

    def is_listener_alive(self) -> bool:
        return bool(self._listener is not None and self._listener.is_alive())

    def get_health_snapshot(self) -> dict[str, float | bool | None]:
        now = time.monotonic()
        return {
            "listener_alive": self.is_listener_alive(),
            "listener_started_monotonic": self._listener_started_monotonic,
            "listener_uptime_seconds": None if self._listener_started_monotonic is None else now - self._listener_started_monotonic,
            "seconds_since_last_keypress": None if self._last_keypress_monotonic is None else now - self._last_keypress_monotonic,
            "last_keypress_monotonic": self._last_keypress_monotonic,
        }
            
    def peek(self, limit: int = 500) -> list[dict]:
        """Atomically returns up to `limit` items from the front of the buffer."""
        with self._lock:
            return self._buffer[:limit]
            
    def pop(self, count: int) -> None:
        """Atomically removes `count` items from the front of the buffer."""
        with self._lock:
            del self._buffer[:count]
            
    def _on_press(self, key) -> None:
        """Callback fired by pynput synchronously upon every physical keystroke."""
        # Isolate window title lookup in its own try/except completely separate
        # from the event creation and buffer append logic.
        app_name = "Unknown"
        try:
            active_win = pygetwindow.getActiveWindow()
            if active_win and hasattr(active_win, 'title') and active_win.title:
                app_name = active_win.title
        except Exception:
            app_name = "Unknown"

        try:
            # Handle standard character keys vs special keys (like space, enter, shift)
            try:
                key_data = key.char
            except AttributeError:
                key_data = str(key)
                
            if key_data is None:
                key_data = "Unknown"
                
            event = {
                "application": app_name,
                "key_data": key_data,
                "captured_at": datetime.now(timezone.utc).isoformat()
            }

            self._last_keypress_monotonic = time.monotonic()

            with self._lock:
                self._buffer.append(event)
                
        except Exception:
            # Catch entirely so a listener callback crash doesn't murder the pynput thread
            pass
