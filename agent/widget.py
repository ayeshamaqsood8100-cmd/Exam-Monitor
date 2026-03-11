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
        self._thread: threading.Thread | None = None
        self._ready_event = threading.Event()
        
        # Dragging state coordinates
        self._start_x = 0
        self._start_y = 0
        self._start_win_x = 0
        self._start_win_y = 0

    def _create_round_rect(self, cvs, x1, y1, x2, y2, r, **kwargs):
        pts = [
            x1+r, y1,  x1+r, y1,  x2-r, y1,  x2-r, y1,  x2, y1,  x2, y1+r,  x2, y1+r,
            x2, y2-r,  x2, y2-r,  x2, y2,  x2-r, y2,  x2-r, y2,  x1+r, y2,  x1+r, y2,
            x1, y2,  x1, y2-r,  x1, y2-r,  x1, y1+r,  x1, y1+r,  x1, y1
        ]
        return cvs.create_polygon(pts, smooth=True, **kwargs)

    def start(self) -> None:
        """Starts the widget in its own UI thread if it is not already running."""
        if self._thread and self._thread.is_alive():
            self.show()
            return

        self._ready_event.clear()
        self._thread = threading.Thread(target=self._run_app, daemon=True)
        self._thread.start()
        self._ready_event.wait(timeout=5.0)

    def show(self) -> None:
        """Shows the widget again after a remote resume."""
        if self.root:
            try:
                self.root.after(0, self.root.deiconify)
            except Exception:
                pass

    def hide(self) -> None:
        """Hides the widget without tearing down the whole agent."""
        if self.root:
            try:
                self.root.after(0, self.root.withdraw)
            except Exception:
                pass

    def stop(self) -> None:
        """Safely destroys the widget from outside the main thread."""
        if self.root:
            try:
                self.root.after(0, self.root.destroy)
            except Exception:
                pass
        if self._thread and self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=2.5)

    def _run_app(self) -> None:
        self.root = tk.Tk()
        self.root.title("Markaz Sentinel")
        
        # Remove all window manager controls (close, minimize, maximize buttons)
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        
        bg_main = "#2a2a2c"
        bg_box = "#3D3D3F"
        
        # Reduced master outer padding
        frame = tk.Frame(self.root, padx=6, pady=6, bg=bg_main, highlightbackground="#404040", highlightthickness=1)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Info (Name & ERP) - Constrained width
        info_frame = tk.Frame(frame, bg=bg_main)
        info_frame.pack(fill=tk.X, pady=(0, 4))
        
        # Use wraplength to ensure long names don't stretch the window box
        name_label = tk.Label(info_frame, text=self.student_name, font=("Segoe UI", 10, "bold"), bg=bg_main, fg="#ffffff", wraplength=140, justify=tk.CENTER)
        name_label.pack(anchor=tk.CENTER, pady=(0,1))
        
        tk.Label(info_frame, text=f"ERP: {self.erp}", font=("Segoe UI", 8), bg=bg_main, fg="#b3b3b3").pack(anchor=tk.CENTER)
        
        # Access Code Panel
        code_frame = tk.Frame(frame, bg=bg_box, padx=4, pady=6)
        code_frame.pack(fill=tk.X, pady=(0, 6))
        tk.Label(code_frame, text="CODE", font=("Segoe UI", 8, "bold"), bg=bg_box, fg="#d1d1d1").pack(anchor=tk.CENTER, pady=(0, 2))
        tk.Label(code_frame, text=self.access_code, font=("Consolas", 16, "bold"), bg=bg_box, fg="#ffffff").pack(anchor=tk.CENTER)
        
        # End & Remove Action Area
        btn_canvas = tk.Canvas(frame, bg=bg_main, highlightthickness=0, height=36, cursor="hand2")
        btn_canvas.pack(fill=tk.X, pady=(4, 0))

        def _draw_main_btn(w, h, hover=False):
            if w < 10 or h < 10: return
            btn_canvas.delete("all")
            # Image 2 has significantly squarer corners (rounded rectangle) rather than a full pill
            r = 6 
            
            # Simple soft drop shadow (darker)
            self._create_round_rect(btn_canvas, 1, 3, w-1, h, r, fill="#040710", tags="btn")
            
            # Main red surface
            fill_color = "#D02046" if hover else "#B81537"
            self._create_round_rect(btn_canvas, 0, 0, w, h-2, r, fill=fill_color, tags="btn")
            
            # Subtle top-edge highlight for that "glassy/shiny" 3D pop seen in Image 2
            highlight_color = "#E62F56" if hover else "#D12146"
            self._create_round_rect(btn_canvas, 1, 1, w-1, h-4, r-1, fill=highlight_color, tags="btn")
            
            btn_canvas.create_text(w/2, (h-2)/2, text="End Session", font=("Segoe UI", 10, "bold"), fill="#ffffff", tags="btn")

        btn_canvas.bind("<Configure>", lambda e: _draw_main_btn(e.width, e.height))
        btn_canvas.bind("<Enter>", lambda e: _draw_main_btn(btn_canvas.winfo_width(), btn_canvas.winfo_height(), hover=True))
        btn_canvas.bind("<Leave>", lambda e: _draw_main_btn(btn_canvas.winfo_width(), btn_canvas.winfo_height(), hover=False))
        btn_canvas.tag_bind("btn", "<ButtonRelease-1>", lambda e: self._prompt_end_session())
        
        # Bind dragging to all components securely recursively
        def _bind_drag_recursive(w):
            w.bind("<ButtonPress-1>", self._on_drag_start)
            w.bind("<B1-Motion>", self._on_drag_motion)
            w.bind("<ButtonRelease-1>", self._on_drag_release)
            for child in w.winfo_children():
                _bind_drag_recursive(child)
                
        _bind_drag_recursive(frame)
            
        # Initialize rendering so measurements are accurate
        self.root.update_idletasks()
        
        # Force a very tight, half-width compact box size (approx 160px instead of 220px)
        target_width = 160
        target_height = self.root.winfo_reqheight()
        
        # Position in top-right corner safely
        sw = self.root.winfo_screenwidth()
        self.root.geometry(f"{target_width}x{target_height}+{sw - target_width - 20}+20")
        self._ready_event.set()
        
        # Block this daemon thread in the GUI event loop indefinitely
        self.root.mainloop()
        self.root = None

    def _on_drag_start(self, event) -> None:
        self._start_x = event.x_root
        self._start_y = event.y_root
        self._start_win_x = self.root.winfo_x()
        self._start_win_y = self.root.winfo_y()

    def _on_drag_motion(self, event) -> None:
        dx = event.x_root - self._start_x
        dy = event.y_root - self._start_y
        new_x = self._start_win_x + dx
        new_y = self._start_win_y + dy
        
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        ww = self.root.winfo_width()
        wh = self.root.winfo_height()
        
        new_x = max(0, min(new_x, sw - ww))
        new_y = max(0, min(new_y, sh - wh))
        
        self.root.geometry(f"+{new_x}+{new_y}")

    def _on_drag_release(self, event) -> None:
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
        # Full-screen dimmed overlay
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.wm_attributes("-topmost", True)
        overlay.wm_attributes("-alpha", 0.6)
        overlay.configure(bg="black")
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        overlay.geometry(f"{sw}x{sh}+0+0")

        # Main centered dialog
        dialog = tk.Toplevel(self.root)
        dialog.overrideredirect(True)
        dialog.wm_attributes("-topmost", True)
        
        bg_modal = "#212121"
        bg_input = "#333333"
        
        # Substantially shrunk modal master padding
        frame = tk.Frame(dialog, padx=24, pady=24, bg=bg_modal, highlightbackground="#404040", highlightthickness=1)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="End Session?", font=("Segoe UI", 16, "bold"), bg=bg_modal, fg="#ffffff").pack(anchor=tk.W, pady=(0, 6))
        
        # Squeeze horizontal text explicitly
        msg = "This will end monitoring and remove the agent from this device. This action cannot be undone."
        tk.Label(frame, text=msg, font=("Segoe UI", 9), bg=bg_modal, fg="#d1d1d1", justify=tk.LEFT, wraplength=260).pack(anchor=tk.W, pady=(0, 16))
        
        tk.Label(frame, text="CONFIRM WITH CODE", font=("Segoe UI", 8, "bold"), bg=bg_modal, fg="#b3b3b3").pack(anchor=tk.W, pady=(0, 4))
        
        # Mask the access code input natively with a thinner rounded canvas box
        input_cvs = tk.Canvas(frame, bg=bg_modal, highlightthickness=0, height=44)
        input_cvs.pack(fill=tk.X, pady=(0, 6))
        
        entry = tk.Entry(input_cvs, justify="center", font=("Consolas", 18, "bold"), show="•", bg=bg_input, fg="#ffffff", insertbackground="#ffffff", relief=tk.FLAT, bd=0, highlightthickness=0)
        
        def _draw_input(cvs, w, h):
            if w < 10 or h < 10: return
            cvs.delete("all")
            self._create_round_rect(cvs, 0, 0, w, h, 28, fill=bg_input, tags="bg")
            cvs.create_window(w/2, h/2, window=entry, width=w-30, height=h-20)
            
        input_cvs.bind("<Configure>", lambda e: _draw_input(input_cvs, e.width, e.height))
        entry.focus_set()
        
        error_label = tk.Label(frame, text="", bg=bg_modal, fg="#ff4d60", font=("Segoe UI", 11, "bold"))
        error_label.pack(pady=(0, 15))
        
        def on_submit(e=None) -> None:
            if not self.access_code or self.access_code.strip() == "":
                error_label.config(text="Session code unavailable")
                entry.delete(0, tk.END)
                return
                
            if entry.get().strip() == self.access_code:
                dialog.destroy()
                overlay.destroy()
                if self.on_end_session:
                    threading.Thread(target=self.on_end_session, daemon=True).start()
            else:
                error_label.config(text="Incorrect passcode. Access denied.")
                entry.delete(0, tk.END)
                
        def on_cancel(e=None) -> None:
            dialog.destroy()
            overlay.destroy()
            
        btn_frame = tk.Frame(frame, bg=bg_modal)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        cancel_cvs = tk.Canvas(btn_frame, bg=bg_modal, highlightthickness=0, height=44, cursor="hand2")
        cancel_cvs.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        
        confirm_cvs = tk.Canvas(btn_frame, bg=bg_modal, highlightthickness=0, height=44, cursor="hand2")
        confirm_cvs.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0))
        
        def _draw_dialog_btn(cvs, w, h, text, color_bg, color_hover, hover=False):
            if w < 10 or h < 10: return
            cvs.delete("all")
            r = 20
            current_bg = color_hover if hover else color_bg
            self._create_round_rect(cvs, 1, 1, w-2, h-2, r, fill=current_bg, outline="#555555" if color_bg=="#333333" else "", width=1, tags="btn")
            cvs.create_text(w/2, h/2, text=text, font=("Segoe UI", 14, "bold"), fill="#ffffff", tags="btn")

        cancel_cvs.bind("<Configure>", lambda e: _draw_dialog_btn(cancel_cvs, e.width, e.height, "Cancel", "#333333", "#4d4d4d"))
        cancel_cvs.bind("<Enter>", lambda e: _draw_dialog_btn(cancel_cvs, cancel_cvs.winfo_width(), cancel_cvs.winfo_height(), "Cancel", "#333333", "#4d4d4d", True))
        cancel_cvs.bind("<Leave>", lambda e: _draw_dialog_btn(cancel_cvs, cancel_cvs.winfo_width(), cancel_cvs.winfo_height(), "Cancel", "#333333", "#4d4d4d", False))
        cancel_cvs.tag_bind("btn", "<ButtonRelease-1>", on_cancel)

        confirm_cvs.bind("<Configure>", lambda e: _draw_dialog_btn(confirm_cvs, e.width, e.height, "Confirm End", "#b0243b", "#c22a42"))
        confirm_cvs.bind("<Enter>", lambda e: _draw_dialog_btn(confirm_cvs, confirm_cvs.winfo_width(), confirm_cvs.winfo_height(), "Confirm End", "#b0243b", "#c22a42", True))
        confirm_cvs.bind("<Leave>", lambda e: _draw_dialog_btn(confirm_cvs, confirm_cvs.winfo_width(), confirm_cvs.winfo_height(), "Confirm End", "#b0243b", "#c22a42", False))
        confirm_cvs.tag_bind("btn", "<ButtonRelease-1>", on_submit)
        
        dialog.bind("<Return>", on_submit)
        dialog.bind("<Escape>", on_cancel)
        
        dialog.update_idletasks()
        
        # Force a hard horizontal limit across the tk root
        target_dw = 320
        dh = dialog.winfo_reqheight()
        
        # Center the dialog precisely in the middle of the screen
        new_x = (sw - target_dw) // 2
        new_y = (sh - dh) // 2
        
        dialog.geometry(f"{target_dw}x{dh}+{new_x}+{new_y}")
        dialog.grab_set()
