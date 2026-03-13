"""
On-screen monitoring widget that displays student info and allows ending the
session safely.

Windows can host tkinter in a background UI thread. macOS cannot; Cocoa
requires NSWindow creation on the process main thread. To keep the agent
robust across both platforms, macOS runs the widget in a dedicated child
process and forwards events back to the main agent process.
"""
from __future__ import annotations

import ctypes
import multiprocessing as mp
import platform
import queue
import threading
import time
import tkinter as tk
from typing import Callable, Any


_IS_MAC = platform.system() == "Darwin"
_BG_BASE = "#000000"
_BG_SURFACE = "#000000"
_BG_INPUT = "#000000"
_BORDER_SUBTLE = "#111111"

_NEON_CYAN = "#00B8D9"
_NEON_ROSE = "#FF3366"
_NEON_AMBER = "#FFD166"

_TEXT_PRIMARY = "#FFFFFF"
_TEXT_MUTED = "#888888"
_TEXT_SUBTITLE = "#AAAAAA"
_TEXT_ERROR = "#FF3366"
_INPUT_FONT_FAMILY = "Consolas"
_END_SESSION_INPUT_FONT = (_INPUT_FONT_FAMILY, 16, "bold")


def _try_enable_windows_blur(window: tk.Toplevel) -> bool:
    if platform.system() != "Windows":
        return False

    try:
        class ACCENT_POLICY(ctypes.Structure):
            _fields_ = [
                ("AccentState", ctypes.c_int),
                ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint),
                ("AnimationId", ctypes.c_int),
            ]

        class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
            _fields_ = [
                ("Attribute", ctypes.c_int),
                ("Data", ctypes.c_void_p),
                ("SizeOfData", ctypes.c_size_t),
            ]

        accent = ACCENT_POLICY()
        accent.AccentState = 3
        accent.AccentFlags = 2
        accent.GradientColor = 0x8A05070B
        accent.AnimationId = 0

        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19
        data.Data = ctypes.addressof(accent)
        data.SizeOfData = ctypes.sizeof(accent)

        hwnd = window.winfo_id()
        api = ctypes.windll.user32.SetWindowCompositionAttribute
        return bool(api(hwnd, ctypes.byref(data)))
    except Exception:
        return False


def _configure_floating_window(root: tk.Tk | tk.Toplevel, title: str) -> None:
    root.title(title)
    root.overrideredirect(True)
    root.wm_attributes("-topmost", True)
    root.configure(bg="#000000")


def _make_button(
    parent: tk.Widget,
    *,
    text: str,
    command: Callable[[], None],
    fill: str,
    outline: str,
    text_color: str,
    active_fill: str,
    width: int,
) -> tk.Button:
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=("Segoe UI", 10, "bold"),
        bg=fill,
        fg=text_color,
        activebackground=active_fill,
        activeforeground=text_color,
        highlightbackground=outline,
        highlightthickness=1,
        bd=0,
        relief=tk.FLAT,
        padx=14,
        pady=9,
        width=width,
        cursor="hand2",
    )


def _bind_drag(widget: tk.Widget, *, on_drag_start, on_drag_motion, on_drag_release) -> None:
    widget.bind("<ButtonPress-1>", on_drag_start)
    widget.bind("<B1-Motion>", on_drag_motion)
    widget.bind("<ButtonRelease-1>", on_drag_release)


def _build_side_widget(
    root: tk.Tk,
    *,
    student_name: str,
    erp: str,
    access_code: str,
    status_text: str,
    status_color: str,
    status_ref: dict[str, tk.Label] | None,
    on_end_session: Callable[[], None],
    on_drag_start: Callable[[tk.Event], None],
    on_drag_motion: Callable[[tk.Event], None],
    on_drag_release: Callable[[tk.Event], None],
) -> tuple[int, int]:
    card = tk.Frame(root, bg=_BG_BASE, highlightbackground=_BORDER_SUBTLE, highlightthickness=1)
    card.pack(fill=tk.BOTH, expand=True)

    # Top neon line recreated per reference image
    tk.Frame(card, bg=_NEON_CYAN, height=2).pack(fill=tk.X)

    handle = tk.Frame(card, bg=_BG_BASE, cursor="fleur")
    handle.pack(fill=tk.X, expand=True, pady=(10, 6))

    tk.Label(
        handle, 
        text=student_name, 
        bg=_BG_BASE, 
        fg=_TEXT_PRIMARY, 
        font=("Segoe UI", 11, "bold"),
        wraplength=180,
        justify=tk.CENTER
    ).pack(padx=15)
    
    tk.Label(
        handle, 
        text=f"ERP - {erp}", 
        bg=_BG_BASE, 
        fg=_TEXT_MUTED, 
        font=("Segoe UI", 8)
    ).pack(pady=(2, 0))

    # Access code panel box
    panel = tk.Frame(card, bg=_BG_BASE, highlightbackground="#1A1A1A", highlightthickness=1)
    panel.pack(fill=tk.X, padx=15, pady=(0, 10))

    tk.Label(panel, text="ACCESS CODE", bg=_BG_BASE, fg=_TEXT_MUTED, font=("Segoe UI", 7, "bold")).pack(pady=(6, 2))
    tk.Label(panel, text=access_code or "---", bg=_BG_BASE, fg=_NEON_CYAN, font=("Consolas", 11, "bold")).pack(pady=(0, 6))

    if status_ref is not None:
        status_ref["label"] = tk.Label(card)

    # Dark background button
    _DARK_ROSE_BG = "#2A0810"
    end_btn = tk.Label(card, text="End Session", bg=_DARK_ROSE_BG, fg=_NEON_ROSE, font=("Segoe UI", 9, "bold"), cursor="hand2")
    end_btn.pack(fill=tk.X, padx=15, pady=(0, 10), ipady=5)

    def on_enter(e):
        end_btn.configure(fg="#ffffff", bg=_NEON_ROSE)
    def on_leave(e):
        end_btn.configure(fg=_NEON_ROSE, bg=_DARK_ROSE_BG)

    end_btn.bind("<Enter>", on_enter)
    end_btn.bind("<Leave>", on_leave)
    end_btn.bind("<Button-1>", lambda _: on_end_session())

    _bind_drag(card, on_drag_start=on_drag_start, on_drag_motion=on_drag_motion, on_drag_release=on_drag_release)
    _bind_drag(handle, on_drag_start=on_drag_start, on_drag_motion=on_drag_motion, on_drag_release=on_drag_release)
    
    root.update_idletasks()
    return card.winfo_reqwidth(), card.winfo_reqheight()


def _show_end_session_modal(
    parent: tk.Tk | tk.Toplevel,
    *,
    access_code: str,
    on_confirm: Callable[[], None],
) -> None:
    # Prevent multiple modals from opening
    if getattr(parent, "_modal_open", False):
        return
    parent._modal_open = True

    dialog = tk.Toplevel(parent)
    dialog.title("End Session")
    dialog.configure(bg=_BG_BASE)
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)
    dialog.transient(parent)

    dialog.update_idletasks()
    dialog_width = 460
    dialog_height = 400
    screen_width = parent.winfo_screenwidth()
    screen_height = parent.winfo_screenheight()
    x = max((screen_width - dialog_width) // 2, 0)
    y = max((screen_height - dialog_height) // 2, 0)
    dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    card = tk.Frame(dialog, bg=_BG_BASE, highlightbackground=_BORDER_SUBTLE, highlightthickness=1)
    card.pack(fill=tk.BOTH, expand=True)
    
    # Added themed '×' close button for End Session Modal
    close_btn = tk.Label(
        card,
        text="×",
        bg=_BG_BASE,
        fg=_TEXT_MUTED,
        font=("Segoe UI", 16),
        cursor="hand2",
    )
    close_btn.place(relx=0.0, rely=0.0, anchor="nw", x=15, y=10)

    def on_close_click(_event=None):
        cancel()

    close_btn.bind("<Button-1>", on_close_click)
    close_btn.bind("<Enter>", lambda _: close_btn.configure(fg=_TEXT_PRIMARY))
    close_btn.bind("<Leave>", lambda _: close_btn.configure(fg=_TEXT_MUTED))

    content = tk.Frame(card, bg=_BG_BASE, padx=40, pady=40)
    content.pack(fill=tk.BOTH, expand=True)

    tk.Label(content, text="SECURITY CHECK", bg=_BG_BASE, fg=_NEON_ROSE, font=("Segoe UI", 8, "bold")).pack(anchor="center", pady=(10, 0))
    tk.Label(content, text="End Session?", bg=_BG_BASE, fg=_TEXT_PRIMARY, font=("Segoe UI Light", 24)).pack(anchor="center")
    tk.Label(content, text="This will end monitoring and remove the agent from this device. This action cannot be undone.", bg=_BG_BASE, fg=_TEXT_MUTED, font=("Segoe UI", 9), wraplength=340, justify=tk.CENTER).pack(anchor="center", pady=(5, 20))

    entry_frame = tk.Frame(content, bg=_BG_BASE)
    entry_frame.pack(fill=tk.X, padx=50)

    # Permanent label in between the title and the input line
    tk.Label(entry_frame, text="ENTER ACCESS CODE", bg=_BG_BASE, fg="#555555", font=("Segoe UI", 8, "bold")).pack(anchor="center", pady=(0, 5))

    entry = tk.Entry(
        entry_frame,
        justify="center",
        font=("Consolas", 18, "bold"),
        bg=_BG_BASE,
        fg=_TEXT_PRIMARY,
        insertbackground=_NEON_ROSE,
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
        line.configure(bg=_NEON_ROSE, height=2)
    def on_focus_out(e):
        line.configure(bg="#333333", height=1)

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)

    error_label = tk.Label(content, text="", bg=_BG_BASE, fg=_TEXT_ERROR, font=("Segoe UI", 9))
    error_label.pack(anchor="center", pady=(8, 0))

    # Action row not needed for minimalistic design

    def close_modal() -> None:
        try:
            dialog.grab_release()
        except tk.TclError:
            pass
        if dialog.winfo_exists():
            dialog.destroy()
        parent._modal_open = False

    def cancel(_event=None) -> str:
        close_modal()
        return "break"

    def submit(_event=None) -> str:
        if not access_code.strip():
            error_label.configure(text="Session code unavailable.")
            entry.delete(0, tk.END)
            entry.focus_set()
            return "break"
        if entry.get().strip() == access_code:
            close_modal()
            on_confirm()
            return "break"
        error_label.configure(text="Incorrect passcode. Access denied.")
        entry.delete(0, tk.END)
        entry.focus_set()
        return "break"

    # Action buttons removed per user request

    dialog.bind("<Return>", submit)
    dialog.bind("<KP_Enter>", submit)
    dialog.bind("<Escape>", cancel)
    dialog.protocol("WM_DELETE_WINDOW", cancel)

    dialog.update_idletasks()
    dialog.lift()
    dialog.grab_set()
    entry.focus_set()
    dialog.after(80, lambda: (entry.focus_force(), entry.icursor(tk.END)))


def _run_widget_process(
    student_name: str,
    erp: str,
    access_code: str,
    command_queue: mp.Queue,
    event_queue: mp.Queue,
) -> None:
    end_requested = False
    root = None
    status_label_ref: dict[str, tk.Label] = {}

    try:
        root = tk.Tk()
        _configure_floating_window(root, "Markaz Sentinel")

        start_x = 0
        start_y = 0
        start_win_x = 0
        start_win_y = 0

        def on_drag_start(event) -> None:
            nonlocal start_x, start_y, start_win_x, start_win_y
            start_x = event.x_root
            start_y = event.y_root
            start_win_x = root.winfo_x()
            start_win_y = root.winfo_y()

        def on_drag_motion(event) -> None:
            dx = event.x_root - start_x
            dy = event.y_root - start_y
            new_x = start_win_x + dx
            new_y = start_win_y + dy

            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            width = root.winfo_width()
            height = root.winfo_height()

            new_x = max(0, min(new_x, screen_width - width))
            new_y = max(0, min(new_y, screen_height - height))
            root.geometry(f"+{new_x}+{new_y}")

        def on_drag_release(_event) -> None:
            root.update_idletasks()
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            width = root.winfo_width()
            height = root.winfo_height()
            x = root.winfo_x()
            y = root.winfo_y()
            new_x = max(0, min(x, screen_width - width))
            new_y = max(0, min(y, screen_height - height))
            if x != new_x or y != new_y:
                root.geometry(f"+{new_x}+{new_y}")

        def prompt_end_session() -> None:
            nonlocal end_requested
            if end_requested:
                return

            def confirm() -> None:
                nonlocal end_requested
                end_requested = True
                event_queue.put({"type": "end_session"})

            root.after(0, lambda: _show_end_session_modal(root, access_code=access_code or "", on_confirm=confirm))

        def update_status(text: str, color: str) -> None:
            label = status_label_ref.get("label")
            if label:
                label.configure(text=text, fg=color)

        def poll_commands() -> None:
            try:
                while True:
                    command = command_queue.get_nowait()
                    action = command.get("action")
                    if action == "show":
                        root.deiconify()
                    elif action == "hide":
                        root.withdraw()
                    elif action == "set_status":
                        update_status(str(command.get("text") or "Monitoring Active"), str(command.get("color") or _NEON_CYAN))
                    elif action == "stop":
                        root.destroy()
                        return
            except queue.Empty:
                pass

            root.after(150, poll_commands)

        target_width, target_height = _build_side_widget(
            root,
            student_name=student_name,
            erp=erp,
            access_code=access_code,
            status_text="Monitoring Active",
            status_color=_NEON_CYAN,
            status_ref=status_label_ref,
            on_end_session=prompt_end_session,
            on_drag_start=on_drag_start,
            on_drag_motion=on_drag_motion,
            on_drag_release=on_drag_release,
        )
        screen_width = root.winfo_screenwidth()
        root.geometry(f"{target_width}x{target_height}+{screen_width - target_width - 20}+20")
        event_queue.put({"type": "ready"})
        root.after(150, poll_commands)
        root.mainloop()
    except Exception as exc:
        try:
            event_queue.put(
                {
                    "type": "error",
                    "message": (
                        "The macOS monitoring widget could not start. "
                        f"{exc.__class__.__name__}: {exc}"
                    ),
                }
            )
        except Exception:
            pass
        raise
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass
        try:
            event_queue.put({"type": "stopped"})
        except Exception:
            pass


class MonitoringWidget:
    def __init__(self, student_name: str, erp: str, access_code: str, on_end_session: Callable[[], None]) -> None:
        self.student_name = student_name
        self.erp = erp
        self.access_code = access_code
        self.on_end_session = on_end_session
        self.root = None
        self._thread: threading.Thread | None = None
        self._ready_event = threading.Event()
        self._listener_stop = threading.Event()
        self._process = None
        self._command_queue = None
        self._event_queue = None
        self._listener_thread: threading.Thread | None = None
        self._uses_process_backend = False
        self._startup_error_message: str | None = None
        self._status_label: tk.Label | None = None
        self._status_text = "Monitoring Active"
        self._status_color = _NEON_CYAN
        self._thread_command_queue: queue.Queue[dict[str, str]] = queue.Queue()

        self._start_x = 0
        self._start_y = 0
        self._start_win_x = 0
        self._start_win_y = 0

    def start(self) -> None:
        if _IS_MAC:
            if not self._start_process_widget(_run_widget_process, ready_timeout=8.0):
                error_message = self._startup_error_message or (
                    "The macOS monitoring widget did not become ready. "
                    "Close any existing Markaz processes and rerun the agent from Terminal."
                )
                raise RuntimeError(error_message)
            return

        if self._thread and self._thread.is_alive():
            self.show()
            return

        self._ready_event.clear()
        self._thread = threading.Thread(target=self._run_app, daemon=True)
        self._thread.start()
        self._ready_event.wait(timeout=5.0)

    def show(self) -> None:
        if self._uses_process_backend:
            self._send_process_command("show")
            return

        self._send_thread_command({"action": "show"})

    def hide(self) -> None:
        if self._uses_process_backend:
            self._send_process_command("hide")
            return

        self._send_thread_command({"action": "hide"})

    def stop(self) -> None:
        if self._uses_process_backend:
            self._stop_process_widget()
            return

        self._send_thread_command({"action": "stop"})
        if self._thread and self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=2.5)

    def _start_process_widget(self, target, *, ready_timeout: float) -> bool:
        if self._process and self._process.is_alive():
            self.show()
            self._uses_process_backend = True
            return True

        ctx = mp.get_context("spawn")
        self._command_queue = ctx.Queue()
        self._event_queue = ctx.Queue()
        self._ready_event.clear()
        self._listener_stop.clear()
        self._startup_error_message = None
        self._process = ctx.Process(
            target=target,
            args=(self.student_name, self.erp, self.access_code or "", self._command_queue, self._event_queue),
            daemon=True,
        )
        self._process.start()

        self._listener_thread = threading.Thread(target=self._listen_process_events, daemon=True)
        self._listener_thread.start()

        deadline = time.monotonic() + ready_timeout
        while time.monotonic() < deadline:
            if self._ready_event.wait(timeout=0.1):
                self._uses_process_backend = True
                return True
            if self._startup_error_message:
                break
            if self._process and not self._process.is_alive():
                break

        self._stop_process_widget()
        return False

    def _listen_process_events(self) -> None:
        while not self._listener_stop.is_set():
            if not self._event_queue:
                return
            try:
                event = self._event_queue.get(timeout=0.5)
            except queue.Empty:
                if self._process and not self._process.is_alive():
                    return
                continue
            except Exception:
                return

            event_type = event.get("type")
            if event_type == "ready":
                self._ready_event.set()
            elif event_type == "error":
                self._startup_error_message = str(
                    event.get("message") or "The macOS monitoring widget failed to start."
                )
                return
            elif event_type == "end_session":
                threading.Thread(target=self.on_end_session, daemon=True).start()
            elif event_type == "stopped":
                return

    def _send_process_command(self, action: str) -> None:
        if self._command_queue and self._process and self._process.is_alive():
            try:
                self._command_queue.put({"action": action})
            except Exception:
                pass

    def _stop_process_widget(self) -> None:
        self._listener_stop.set()
        self._send_process_command("stop")

        if self._process:
            self._process.join(timeout=3.0)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=2.0)
            if self._process.is_alive():
                self._process.kill()
                self._process.join(timeout=1.0)
            self._process = None

        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=1.5)

        if self._command_queue:
            try:
                self._command_queue.close()
                self._command_queue.cancel_join_thread()
            except Exception:
                pass
        if self._event_queue:
            try:
                self._event_queue.close()
                self._event_queue.cancel_join_thread()
            except Exception:
                pass

        self._command_queue = None
        self._event_queue = None
        self._listener_thread = None
        self._uses_process_backend = False
        self._startup_error_message = None

    def _run_app(self) -> None:
        self.root = tk.Tk()
        _configure_floating_window(self.root, "Markaz Sentinel")
        status_label_ref: dict[str, tk.Label] = {}

        target_width, target_height = _build_side_widget(
            self.root,
            student_name=self.student_name,
            erp=self.erp,
            access_code=self.access_code,
            status_text=self._status_text,
            status_color=self._status_color,
            status_ref=status_label_ref,
            on_end_session=self._prompt_end_session,
            on_drag_start=self._on_drag_start,
            on_drag_motion=self._on_drag_motion,
            on_drag_release=self._on_drag_release,
        )
        self._status_label = status_label_ref.get("label")
        screen_width = self.root.winfo_screenwidth()
        self.root.geometry(f"{target_width}x{target_height}+{screen_width - target_width - 20}+20")
        self._ready_event.set()
        self.root.after(100, self._poll_thread_commands)
        self.root.mainloop()
        self.root = None
        self._status_label = None

    def _poll_thread_commands(self) -> None:
        if not self.root:
            return

        try:
            while True:
                command = self._thread_command_queue.get_nowait()
                action = command.get("action")
                if action == "show":
                    self.root.deiconify()
                elif action == "hide":
                    self.root.withdraw()
                elif action == "stop":
                    self.root.destroy()
                    return
                elif action == "set_status" and self._status_label:
                    self._status_label.configure(
                        text=str(command.get("text") or self._status_text),
                        fg=str(command.get("color") or self._status_color),
                    )
        except queue.Empty:
            pass

        if self.root:
            self.root.after(100, self._poll_thread_commands)

    def _send_thread_command(self, command: dict[str, str]) -> None:
        try:
            self._thread_command_queue.put(command)
        except Exception:
            pass

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

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = self.root.winfo_width()
        height = self.root.winfo_height()

        new_x = max(0, min(new_x, screen_width - width))
        new_y = max(0, min(new_y, screen_height - height))
        self.root.geometry(f"+{new_x}+{new_y}")

    def _on_drag_release(self, _event) -> None:
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        new_x = max(0, min(x, screen_width - width))
        new_y = max(0, min(y, screen_height - height))

        if x != new_x or y != new_y:
            self.root.geometry(f"+{new_x}+{new_y}")

    def _prompt_end_session(self) -> None:
        def confirm() -> None:
            if self.on_end_session:
                threading.Thread(target=self.on_end_session, daemon=True).start()

        if self.root:
            self.root.after(0, lambda: _show_end_session_modal(self.root, access_code=self.access_code or "", on_confirm=confirm))

    def _apply_status(self, text: str, color: str) -> None:
        self._status_text = text
        self._status_color = color
        if self._uses_process_backend:
            if self._command_queue and self._process and self._process.is_alive():
                try:
                    self._command_queue.put({"action": "set_status", "text": text, "color": color})
                except Exception:
                    pass
            return

        if self.root and self._status_label:
            self._send_thread_command({"action": "set_status", "text": text, "color": color})

    def set_online(self) -> None:
        self._apply_status("Monitoring Active", _NEON_CYAN)

    def set_reconnecting(self, detail: str | None = None) -> None:
        message = "Offline / Reconnecting"
        if detail and "timed out" in detail.lower():
            message = "Offline / Reconnecting"
        self._apply_status(message, _NEON_AMBER)
