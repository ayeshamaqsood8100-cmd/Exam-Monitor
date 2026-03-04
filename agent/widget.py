"""
agent/widget.py
On-screen monitoring widget that displays student info and allows ending the session safely.
"""
import tkinter as tk
import threading
from typing import Callable

class MonitoringWidget:
    def __init__(self, student_name: str, erp: str, access_code: str, on_end_session: Callable[[], None]) -> None:
        self.student_name = student_name
        self.erp = erp
        self.access_code = access_code
        self.on_end_session = on_end_session
        self.root = None
        self._thread = None
        
        # Dragging state coordinates
        self._start_x = 0
        self._start_y = 0
        self._start_win_x = 0
        self._start_win_y = 0

    def start(self) -> None:
        """Starts the tkinter mainloop on a separate background daemon thread."""
        self._thread = threading.Thread(target=self._run_app, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Safely destroys the widget from outside the main thread."""
        if self.root:
            try:
                self.root.after(0, self.root.destroy)
            except Exception:
                pass

    def _run_app(self) -> None:
        self.root = tk.Tk()
        self.root.title("Markaz Sentinel")
        
        # Remove all window manager controls (close, minimize, maximize buttons)
        self.root.overrideredirect(True)
        
        # Force float on top of all other windows
        self.root.wm_attributes("-topmost", True)
        
        # Styling frame
        frame = tk.Frame(self.root, padx=15, pady=15, bg="#f8f9fa", highlightbackground="#ced4da", highlightthickness=1)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="Markaz Exam Active", font=("Helvetica", 10, "bold"), bg="#f8f9fa", fg="#dc3545").pack(pady=(0, 10))
        tk.Label(frame, text=f"Student: {self.student_name}", font=("Helvetica", 9), bg="#f8f9fa").pack(anchor=tk.W)
        tk.Label(frame, text=f"ERP: {self.erp}", font=("Helvetica", 9), bg="#f8f9fa").pack(anchor=tk.W)
        tk.Label(frame, text=f"Code: {self.access_code}", font=("Courier", 11, "bold"), bg="#f8f9fa", fg="#0d6efd").pack(anchor=tk.W, pady=(5, 15))
        
        tk.Button(frame, text="End Session", bg="#dc3545", fg="white", font=("Helvetica", 9, "bold"), relief=tk.FLAT, cursor="hand2", command=self._prompt_end_session).pack(fill=tk.X)
        
        # Bind dragging to all components so clicking anywhere on the widget works
        for widget in [frame] + frame.winfo_children():
            widget.bind("<ButtonPress-1>", self._on_drag_start)
            widget.bind("<B1-Motion>", self._on_drag_motion)
            widget.bind("<ButtonRelease-1>", self._on_drag_release)
            
        # Initialize rendering so measurements are accurate
        self.root.update_idletasks()
        
        # Position in top-right corner safely
        sw = self.root.winfo_screenwidth()
        ww = self.root.winfo_width()
        self.root.geometry(f"+{sw - ww - 20}+20")
        
        # Block this daemon thread in the GUI event loop indefinitely
        self.root.mainloop()

    def _on_drag_start(self, event) -> None:
        """Records initial absolute mouse and window coordinates upon click."""
        self._start_x = event.x_root
        self._start_y = event.y_root
        self._start_win_x = self.root.winfo_x()
        self._start_win_y = self.root.winfo_y()

    def _on_drag_motion(self, event) -> None:
        """Calculates delta and strictly clamps the widget inside physical screen bounds during drag."""
        dx = event.x_root - self._start_x
        dy = event.y_root - self._start_y
        new_x = self._start_win_x + dx
        new_y = self._start_win_y + dy
        
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        ww = self.root.winfo_width()
        wh = self.root.winfo_height()
        
        # Clamp coordinates tightly within the physical screen boundaries
        new_x = max(0, min(new_x, sw - ww))
        new_y = max(0, min(new_y, sh - wh))
        
        self.root.geometry(f"+{new_x}+{new_y}")

    def _on_drag_release(self, event) -> None:
        """Redundant safety snap when the user releases the mouse."""
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        ww = self.root.winfo_width()
        wh = self.root.winfo_height()
        
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        
        new_x = max(0, min(x, sw - ww))
        new_y = max(0, min(y, sh - wh))
        
        if x != new_x or y != new_y:
            self.root.geometry(f"+{new_x}+{new_y}")

    def _prompt_end_session(self) -> None:
        """Spawns an always-on-top passcode modal locking out the background."""
        dialog = tk.Toplevel(self.root)
        dialog.overrideredirect(True)
        dialog.wm_attributes("-topmost", True)
        
        frame = tk.Frame(dialog, padx=15, pady=15, bg="#ffffff", highlightbackground="#ced4da", highlightthickness=1)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="Authorize Shutdown", font=("Helvetica", 10, "bold"), bg="#ffffff").pack(pady=(0, 10))
        tk.Label(frame, text="Passcode (Access Code):", font=("Helvetica", 9), bg="#ffffff").pack(anchor=tk.W)
        
        # Mask the access code input natively
        entry = tk.Entry(frame, justify="center", font=("Courier", 10), show="*")
        entry.pack(fill=tk.X, pady=(5, 5))
        entry.focus_set()
        
        error_label = tk.Label(frame, text="", bg="#ffffff", fg="#dc3545", font=("Helvetica", 8))
        error_label.pack(pady=(0, 10))
        
        def on_submit(e=None) -> None:
            if not self.access_code or self.access_code.strip() == "":
                error_label.config(text="Session code unavailable — contact invigilator")
                entry.delete(0, tk.END)
                return
                
            if entry.get().strip() == self.access_code:
                dialog.destroy()
                # Run the provided callback asynchronously to prevent locking the GUI thread
                if self.on_end_session:
                    threading.Thread(target=self.on_end_session, daemon=True).start()
            else:
                error_label.config(text="Incorrect passcode!")
                entry.delete(0, tk.END)
                
        def on_cancel(e=None) -> None:
            dialog.destroy()
            
        btn_frame = tk.Frame(frame, bg="#ffffff")
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="Cancel", relief=tk.FLAT, bg="#e9ecef", command=on_cancel).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        tk.Button(btn_frame, text="Confirm", relief=tk.FLAT, bg="#dc3545", fg="white", command=on_submit).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0))
        
        dialog.bind("<Return>", on_submit)
        dialog.bind("<Escape>", on_cancel)
        
        # Snap dialog near main widget securely
        dialog.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        dw = dialog.winfo_width()
        dh = dialog.winfo_height()
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        
        # Center X relative to main widget, clamping horizontally
        new_x = rx + (rw - dw) // 2
        new_x = max(0, min(new_x, sw - dw))
        
        # Try spawning below first
        new_y = ry + rh + 10
        
        # If spawning below pushes it off the bottom screen edge, spawn it *above* the widget instead
        if new_y + dh > sh:
            new_y = ry - dh - 10
            
        # Final vertical clamp just in case monitor is bizarrely tiny
        new_y = max(0, min(new_y, sh - dh))
        
        dialog.geometry(f"+{new_x}+{new_y}")
        
        # Grab modal focus solidly to prevent interacting with the main widget underneath
        dialog.grab_set()
