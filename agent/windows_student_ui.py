from __future__ import annotations

import platform
import sys
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Any


_BG_BASE = "#000000"
_BG_SURFACE = "#000000"
_BG_INPUT = "#000000"
_BORDER_SUBTLE = "#111111"

_NEON_CYAN = "#00B8D9"
_NEON_ROSE = "#FF3366"
_REQUEST_TIMEOUT_MS = 15000
_TEXT_STATUS = "#FFD166"

_TEXT_PRIMARY = "#FFFFFF"
_TEXT_MUTED = "#888888"
_TEXT_SUBTITLE = "#AAAAAA"
_TEXT_ERROR = "#FF3366"


def is_windows_packaged_runtime() -> bool:
    return platform.system() == "Windows" and bool(getattr(sys, "frozen", False))

def is_gui_mode() -> bool:
    return True


def show_error_dialog(title: str, message: str) -> None:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    messagebox.showerror(title, message, parent=root)
    root.destroy()


def _add_close_button(parent: tk.Widget, cancel_cmd: Callable[[], None]) -> None:
    btn = tk.Label(
        parent,
        text="×",
        bg=_BG_BASE,
        fg=_TEXT_MUTED,
        font=("Segoe UI", 16),
        cursor="hand2",
    )
    btn.place(relx=0.0, rely=0.0, anchor="nw", x=15, y=10)
    btn.bind("<Button-1>", lambda _: cancel_cmd())
    btn.bind("<Enter>", lambda _: btn.configure(fg=_TEXT_PRIMARY))
    btn.bind("<Leave>", lambda _: btn.configure(fg=_TEXT_MUTED))


def _center_window(root: tk.Tk, w: int, h: int) -> None:
    """Perfectly centers a window on the primary screen, accounting for decorations and DPI."""
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    
    x = max((sw - w) // 2, 0)
    y = max((sh - h) // 2, 0)
    root.geometry(f"{w}x{h}+{x}+{y}")


def request_student_erp() -> str | None:
    result: dict[str, str | None] = {"erp": None}
    
    root = tk.Tk()
    root.title("Markaz Sentinel")
    root.configure(bg=_BG_BASE)
    root.attributes("-topmost", True)
    root.overrideredirect(True) # Restore frameless original state
    
    w, h = 460, 320 # restored original compact height
    _center_window(root, w, h)
    root.lift()
    root.focus_force()
    
    card = tk.Frame(root, bg=_BG_SURFACE, highlightbackground=_BORDER_SUBTLE, highlightthickness=1)
    card.pack(fill=tk.BOTH, expand=True, padx=0, pady=0) # reduced padding for frameless look

    def cancel() -> None:
        result["erp"] = None
        root.destroy()

    _add_close_button(card, cancel)

    strip_canvas = tk.Canvas(card, bg=_BG_SURFACE, height=0, highlightthickness=0, bd=0) # Hidden strip to keep var references if needed
    strip_canvas.pack()
    
    error_var = tk.StringVar(value="")

    content = tk.Frame(card, bg=_BG_BASE, padx=40, pady=40)
    content.pack(fill=tk.BOTH, expand=True)

    tk.Label(content, text="STEP 1", bg=_BG_BASE, fg=_NEON_CYAN, font=("Segoe UI", 8, "bold")).pack(anchor="center", pady=(10, 0))
    tk.Label(content, text="Verify Your ERP", bg=_BG_BASE, fg=_TEXT_PRIMARY, font=("Segoe UI Light", 24)).pack(anchor="center")
    tk.Label(content, text="Enter your 5-digit ERP to begin the exam session.", bg=_BG_BASE, fg=_TEXT_MUTED, font=("Segoe UI", 9)).pack(anchor="center", pady=(5, 20))

    entry_frame = tk.Frame(content, bg=_BG_BASE)
    entry_frame.pack(fill=tk.X, padx=40)

    entry = tk.Entry(
        entry_frame,
        font=("Consolas", 18, "bold"),
        justify="center",
        bg=_BG_BASE,
        fg=_TEXT_PRIMARY,
        insertbackground=_NEON_CYAN,
        disabledbackground=_BG_BASE,
        disabledforeground=_TEXT_MUTED,
        readonlybackground=_BG_BASE,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
    )
    entry.pack(fill=tk.X, pady=(5, 5))
    
    line = tk.Frame(entry_frame, bg="#333333", height=1)
    line.pack(fill=tk.X)
    
    def on_focus_in(e):
        line.configure(bg=_NEON_CYAN, height=2)
    def on_focus_out(e):
        line.configure(bg="#333333", height=1)

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)
    
    entry.focus_set()

    error_label = tk.Label(content, textvariable=error_var, bg=_BG_BASE, fg=_TEXT_STATUS, font=("Segoe UI", 9))
    error_label.pack(anchor="center", pady=(8, 0))

    def submit(_event=None) -> None:
        erp = entry.get().strip()
        if len(erp) == 5 and erp.isdigit():
            result["erp"] = erp
            root.destroy()
            return
        error_var.set("ERP must be exactly 5 digits.")

    root.bind("<Return>", submit)
    root.bind("<Escape>", lambda _event: cancel())
    root.protocol("WM_DELETE_WINDOW", cancel)
    root.deiconify()
    root.mainloop()
    return result["erp"]


def request_student_erp_with_session_start(
    start_session: Callable[[str], tuple[str, str, str]],
) -> tuple[str | None, tuple[str, str, str] | None]:
    result: dict[str, object | None] = {"erp": None, "session": None}
    state = {"busy": False, "closing": False, "request_id": 0}
    
    root = tk.Tk()
    root.title("Markaz Sentinel")
    root.configure(bg=_BG_BASE)
    root.attributes("-topmost", True)
    root.overrideredirect(True) # Restore frameless original state
    
    w, h = 460, 320 # restored original compact height
    _center_window(root, w, h)
    root.lift()
    root.focus_force()
    
    card = tk.Frame(root, bg=_BG_SURFACE, highlightbackground=_BORDER_SUBTLE, highlightthickness=1)
    card.pack(fill=tk.BOTH, expand=True, padx=0, pady=0) # reduced padding for frameless look

    def cancel() -> None:
        state["closing"] = True
        state["request_id"] += 1
        set_busy(False)
        result["erp"] = None
        result["session"] = None
        if root.winfo_exists():
            root.destroy()

    _add_close_button(card, cancel)

    strip_canvas = tk.Canvas(card, bg=_BG_SURFACE, height=2, highlightthickness=0, bd=0)
    strip_canvas.pack(fill=tk.X) # We keep this here for the loading animation hook, but hide it normally
    segment_id = strip_canvas.create_rectangle(0, 0, 0, 0, fill="#FFFFFF", outline="", state="hidden")
    
    card._strip_pos = 0  # type: ignore[attr-defined]
    card._strip_job = None  # type: ignore[attr-defined]
    
    error_var = tk.StringVar(value="")

    content = tk.Frame(card, bg=_BG_BASE, padx=40, pady=40)
    content.pack(fill=tk.BOTH, expand=True)

    tk.Label(content, text="STEP 1", bg=_BG_BASE, fg=_NEON_CYAN, font=("Segoe UI", 8, "bold")).pack(anchor="center", pady=(10, 0))
    tk.Label(content, text="Verify Your ERP", bg=_BG_BASE, fg=_TEXT_PRIMARY, font=("Segoe UI Light", 24)).pack(anchor="center")
    tk.Label(content, text="Enter your 5-digit ERP to begin the exam session.", bg=_BG_BASE, fg=_TEXT_MUTED, font=("Segoe UI", 9)).pack(anchor="center", pady=(5, 20))

    entry_frame = tk.Frame(content, bg=_BG_BASE)
    entry_frame.pack(fill=tk.X, padx=40)

    entry = tk.Entry(
        entry_frame,
        font=("Consolas", 18, "bold"),
        justify="center",
        bg=_BG_BASE,
        fg=_TEXT_PRIMARY,
        insertbackground=_NEON_CYAN,
        disabledbackground=_BG_BASE,
        disabledforeground=_TEXT_MUTED,
        readonlybackground=_BG_BASE,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
    )
    entry.pack(fill=tk.X, pady=(5, 5))
    
    line = tk.Frame(entry_frame, bg="#333333", height=1)
    line.pack(fill=tk.X)
    
    def on_focus_in(e):
        line.configure(bg=_NEON_CYAN, height=2)
    def on_focus_out(e):
        line.configure(bg="#333333", height=1)

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)
    
    entry.focus_set()

    error_label = tk.Label(content, textvariable=error_var, bg=_BG_BASE, fg=_TEXT_STATUS, font=("Segoe UI", 9))
    error_label.pack(anchor="center", pady=(8, 0))

    def set_busy(busy: bool) -> None:
        if state["closing"] and busy:
            return
        state["busy"] = busy
        entry.configure(state=tk.DISABLED if busy else tk.NORMAL)
        
        job = getattr(card, "_strip_job", None)
        if job:
            strip_canvas.after_cancel(job)
            card._strip_job = None  # type: ignore[attr-defined]
            
        if busy:
            strip_canvas.itemconfigure(segment_id, state="normal")
            card._strip_pos = 0  # type: ignore[attr-defined]
            def animate() -> None:
                if not state["busy"]:
                    return
                w_cv = max(strip_canvas.winfo_width(), 1)
                seg_w = max(w_cv // 5, 56)
                start = getattr(card, "_strip_pos", 0)
                end = min(start + seg_w, w_cv)
                strip_canvas.coords(segment_id, start, 0, end, 2)
                nxt = start + max(w_cv // 18, 18)
                if nxt >= w_cv: nxt = -seg_w
                card._strip_pos = nxt  # type: ignore[attr-defined]
                card._strip_job = strip_canvas.after(30, animate)  # type: ignore[attr-defined]
            animate()
        else:
            strip_canvas.itemconfigure(segment_id, state="hidden")
            entry.focus_set()

    def submit(_event=None) -> str:
        if state["busy"]:
            return "break"

        erp = entry.get().strip()
        if len(erp) != 5 or not erp.isdigit():
            error_var.set("ERP must be exactly 5 digits.")
            entry.focus_set()
            return "break"

        error_var.set("Connecting...")
        set_busy(True)
        state["request_id"] += 1
        current_request_id = int(state["request_id"])

        def handle_timeout() -> None:
            if state["closing"] or current_request_id != state["request_id"] or not state["busy"]:
                return
            complete_error(current_request_id, "Session start timed out. Check your internet or try another ERP.")

        root.after(_REQUEST_TIMEOUT_MS, handle_timeout)

        def worker() -> None:
            try:
                session_info = start_session(erp)
                if state["closing"] or current_request_id != state["request_id"]:
                    return
                try:
                    root.after(0, lambda: complete_success(current_request_id, erp, session_info))
                except RuntimeError:
                    pass
            except Exception as exc:
                if state["closing"] or current_request_id != state["request_id"]:
                    return
                try:
                    root.after(0, lambda: complete_error(current_request_id, str(exc)))
                except RuntimeError:
                    pass

        def complete_success(request_id: int, erp: str, session_info: tuple[str, str, str]) -> None:
            if not root.winfo_exists() or request_id != state["request_id"]: return
            result["erp"] = erp
            result["session"] = session_info
            root.destroy()

        def complete_error(request_id: int, message: str) -> None:
            if not root.winfo_exists() or request_id != state["request_id"]: return
            set_busy(False)
            error_var.set(message or "Unable to start session.")

        threading.Thread(target=worker, daemon=True).start()
        return "break"

    root.bind("<Return>", submit)
    root.bind("<Escape>", lambda _event: cancel())
    root.protocol("WM_DELETE_WINDOW", cancel)
    root.deiconify()
    root.mainloop()
    return result["erp"], result["session"]  # type: ignore[return-value]


def request_consent_confirmation() -> bool:
    result = {"accepted": False, "submitted": False}
    
    root = tk.Tk()
    root.title("Markaz Sentinel")
    root.configure(bg=_BG_BASE)
    root.attributes("-topmost", True)
    root.overrideredirect(True) # Restore frameless original state
    
    # Very compact size for the pledge
    w, h = 480, 420 # restored original compact height
    _center_window(root, w, h)
    root.lift()
    root.focus_force()
    
    card = tk.Frame(root, bg=_BG_SURFACE, highlightbackground=_BORDER_SUBTLE, highlightthickness=1)
    card.pack(fill=tk.BOTH, expand=True, padx=0, pady=0) # reduced padding for frameless look

    def exit_app() -> None:
        result["submitted"] = True
        result["accepted"] = False
        root.destroy()

    _add_close_button(card, exit_app)

    content = tk.Frame(card, bg=_BG_BASE, padx=40, pady=40)
    content.pack(fill=tk.BOTH, expand=True)

    tk.Label(content, text="STEP 2", bg=_BG_BASE, fg=_NEON_CYAN, font=("Segoe UI", 8, "bold")).pack(anchor="center", pady=(10, 0))
    tk.Label(content, text="Academic Integrity", bg=_BG_BASE, fg=_TEXT_PRIMARY, font=("Segoe UI Light", 24)).pack(anchor="center")
    
    msg_frame = tk.Frame(content, bg=_BG_BASE)
    msg_frame.pack(pady=30)
    tk.Label(msg_frame, text="I pledge on my honour that I will not give or receive any unauthorized assistance during this examination.", bg=_BG_BASE, fg=_TEXT_PRIMARY, font=("Segoe UI", 10, "italic"), wraplength=400, justify=tk.CENTER).pack()
    tk.Label(msg_frame, text="Violation of IBA's Academic Integrity Policy results in disciplinary action.", bg=_BG_BASE, fg=_TEXT_MUTED, font=("Segoe UI", 9), wraplength=400, justify=tk.CENTER).pack(pady=(15, 0))

    entry_frame = tk.Frame(content, bg=_BG_BASE)
    entry_frame.pack(fill=tk.X, padx=80)

    entry = tk.Entry(
        entry_frame,
        font=("Consolas", 14, "bold"),
        justify="center",
        bg=_BG_BASE,
        fg=_TEXT_PRIMARY,
        insertbackground=_NEON_CYAN,
        disabledbackground=_BG_BASE,
        disabledforeground=_TEXT_MUTED,
        readonlybackground=_BG_BASE,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
    )
    entry.pack(fill=tk.X, pady=(5, 5))
    
    line = tk.Frame(entry_frame, bg="#333333", height=1)
    line.pack(fill=tk.X)
    
    def on_focus_in(e):
        line.configure(bg=_NEON_CYAN, height=2)
    def on_focus_out(e):
        line.configure(bg="#333333", height=1)

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)
    entry.focus_set()

    tk.Label(content, text="Type YES to continue. Type NO to exit.", bg=_BG_BASE, fg="#555555", font=("Segoe UI", 8)).pack(pady=(10, 0))

    error_var = tk.StringVar(value="")
    error_label = tk.Label(content, textvariable=error_var, bg=_BG_BASE, fg=_TEXT_STATUS, font=("Segoe UI", 8))
    error_label.pack(anchor="center", pady=(4, 0))

    def submit(_event=None) -> None:
        choice = entry.get().strip().upper()
        if choice == "YES":
            result["submitted"] = True
            result["accepted"] = True
            root.destroy()
            return
        if choice == "NO":
            exit_app()
            return
        error_var.set("Type YES or NO.")

    root.bind("<Return>", submit)
    root.bind("<Escape>", lambda _event: exit_app())
    root.protocol("WM_DELETE_WINDOW", exit_app)
    root.deiconify()
    root.mainloop()
    return bool(result["submitted"] and result["accepted"])
