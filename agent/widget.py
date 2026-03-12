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
import tkinter as tk
from typing import Callable


_IS_MAC = platform.system() == "Darwin"
_WIDGET_BG = "#06080D"
_WIDGET_BORDER = "#173B47"
_PANEL_BG = "#0A0E14"
_PANEL_BORDER = "#1C2832"
_TEXT_PRIMARY = "#F4F8FF"
_TEXT_MUTED = "#8D98A4"
_TEXT_SUBTLE = "#6D7884"
_TEXT_CYAN = "#67E8F9"
_TEXT_ROSE = "#FDA4AF"
_ERROR = "#FB7185"
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
    root: tk.Tk | tk.Toplevel,
    *,
    student_name: str,
    erp: str,
    access_code: str,
    on_end_session: Callable[[], None],
    on_drag_start,
    on_drag_motion,
    on_drag_release,
) -> tuple[int, int]:
    width = 196
    height = 1

    outer = tk.Frame(root, bg="#000000", padx=8, pady=8)
    outer.pack(fill=tk.BOTH, expand=True)

    card = tk.Frame(
        outer,
        bg=_WIDGET_BG,
        highlightbackground=_WIDGET_BORDER,
        highlightthickness=1,
        bd=0,
        padx=14,
        pady=14,
    )
    card.pack(fill=tk.BOTH, expand=True)

    tk.Frame(card, bg=_TEXT_CYAN, height=2).pack(fill=tk.X, side=tk.TOP, pady=(0, 10))

    header = tk.Frame(card, bg=_WIDGET_BG)
    header.pack(fill=tk.X)
    tk.Label(
        header,
        text=student_name,
        bg=_WIDGET_BG,
        fg=_TEXT_PRIMARY,
        font=("Segoe UI Semibold", 14),
        wraplength=150,
        justify=tk.CENTER,
    ).pack(anchor="center")
    tk.Label(
        header,
        text=f"ERP - {erp}",
        bg=_WIDGET_BG,
        fg=_TEXT_MUTED,
        font=("Segoe UI", 9),
    ).pack(anchor="center", pady=(5, 0))

    code_panel = tk.Frame(
        card,
        bg=_PANEL_BG,
        highlightbackground=_PANEL_BORDER,
        highlightthickness=1,
        bd=0,
        padx=12,
        pady=12,
    )
    code_panel.pack(fill=tk.X, pady=(14, 0))

    tk.Label(
        code_panel,
        text="ACCESS CODE",
        bg=_PANEL_BG,
        fg=_TEXT_SUBTLE,
        font=("Segoe UI", 8, "bold"),
    ).pack(anchor="center")
    tk.Label(
        code_panel,
        text=access_code,
        bg=_PANEL_BG,
        fg=_TEXT_CYAN,
        font=("Consolas", 15, "bold"),
        pady=7,
    ).pack(anchor="center")

    button = _make_button(
        card,
        text="End Session",
        command=on_end_session,
        fill="#3A0B17",
        outline="#6F1930",
        text_color=_TEXT_ROSE,
        active_fill="#4B0D1D",
        width=11,
    )
    button.pack(fill=tk.X, pady=(14, 0))

    _bind_drag(card, on_drag_start=on_drag_start, on_drag_motion=on_drag_motion, on_drag_release=on_drag_release)
    _bind_drag(header, on_drag_start=on_drag_start, on_drag_motion=on_drag_motion, on_drag_release=on_drag_release)
    _bind_drag(code_panel, on_drag_start=on_drag_start, on_drag_motion=on_drag_motion, on_drag_release=on_drag_release)

    root.update_idletasks()
    return max(width, outer.winfo_reqwidth()), max(height, outer.winfo_reqheight())


def _show_end_session_modal(
    parent: tk.Tk | tk.Toplevel,
    *,
    access_code: str,
    on_confirm: Callable[[], None],
) -> None:
    overlay = tk.Toplevel(parent)
    overlay.withdraw()
    overlay.overrideredirect(True)
    overlay.wm_attributes("-topmost", True)
    overlay.wm_attributes("-alpha", 0.58)
    overlay.configure(bg="#05070B")

    screen_width = parent.winfo_screenwidth()
    screen_height = parent.winfo_screenheight()
    overlay.geometry(f"{screen_width}x{screen_height}+0+0")
    _try_enable_windows_blur(overlay)
    overlay.deiconify()

    dialog = tk.Toplevel(parent)
    dialog.withdraw()
    _configure_floating_window(dialog, "End Session")
    dialog.geometry("430x340+0+0")

    outer = tk.Frame(dialog, bg="#000000", padx=18, pady=18)
    outer.pack(fill=tk.BOTH, expand=True)

    card = tk.Frame(
        outer,
        bg=_WIDGET_BG,
        highlightbackground=_WIDGET_BORDER,
        highlightthickness=1,
        bd=0,
        padx=24,
        pady=22,
    )
    card.pack(fill=tk.BOTH, expand=True)
    tk.Frame(card, bg=_TEXT_ROSE, height=2).pack(fill=tk.X, side=tk.TOP, pady=(0, 16))

    tk.Label(card, text="SECURITY CHECK", bg=_WIDGET_BG, fg=_TEXT_ROSE, font=("Segoe UI", 9, "bold")).pack(anchor="w")
    tk.Label(card, text="End Session?", bg=_WIDGET_BG, fg=_TEXT_PRIMARY, font=("Segoe UI Semibold", 22)).pack(anchor="w", pady=(10, 0))
    tk.Label(
        card,
        text="This will end monitoring and remove the agent from this device. This action cannot be undone.",
        bg=_WIDGET_BG,
        fg=_TEXT_MUTED,
        font=("Segoe UI", 10),
        wraplength=340,
        justify=tk.LEFT,
    ).pack(anchor="w", pady=(10, 0))

    panel = tk.Frame(
        card,
        bg=_PANEL_BG,
        highlightbackground=_PANEL_BORDER,
        highlightthickness=1,
        bd=0,
        padx=16,
        pady=16,
    )
    panel.pack(fill=tk.X, pady=(18, 0))

    tk.Label(panel, text="CONFIRM WITH CODE", bg=_PANEL_BG, fg=_TEXT_SUBTLE, font=("Segoe UI", 9, "bold")).pack(anchor="w")

    entry_shell = tk.Frame(
        panel,
        bg="#0B1118",
        highlightbackground="#1D4B5A",
        highlightthickness=1,
        bd=0,
        padx=1,
        pady=1,
    )
    entry_shell.configure(height=68)
    entry_shell.pack_propagate(False)
    entry_shell.pack(fill=tk.X, pady=(10, 0))
    entry = tk.Entry(
        entry_shell,
        justify="center",
        font=_END_SESSION_INPUT_FONT,
        bg="#0B1118",
        fg=_TEXT_PRIMARY,
        insertbackground=_TEXT_CYAN,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
        insertwidth=2,
    )
    entry.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.9, height=34)
    entry_shell.bind("<Button-1>", lambda _event: entry.focus_set())
    panel.bind("<Button-1>", lambda _event: entry.focus_set())

    error_label = tk.Label(panel, text="", bg=_PANEL_BG, fg=_ERROR, font=("Segoe UI", 9))
    error_label.pack(anchor="w", pady=(10, 0))

    action_row = tk.Frame(card, bg=_WIDGET_BG)
    action_row.pack(fill=tk.X, pady=(18, 0))

    def close_modal() -> None:
        try:
            dialog.grab_release()
        except tk.TclError:
            pass
        if dialog.winfo_exists():
            dialog.destroy()
        if overlay.winfo_exists():
            overlay.destroy()

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

    _make_button(
        action_row,
        text="Cancel",
        command=lambda: cancel(),
        fill="#0E1014",
        outline="#1E2530",
        text_color=_TEXT_PRIMARY,
        active_fill="#151A21",
        width=11,
    ).pack(side=tk.LEFT)
    _make_button(
        action_row,
        text="Confirm End",
        command=lambda: submit(),
        fill="#3A0B17",
        outline="#6F1930",
        text_color=_TEXT_ROSE,
        active_fill="#4B0D1D",
        width=14,
    ).pack(side=tk.RIGHT)

    dialog.bind("<Return>", submit)
    dialog.bind("<KP_Enter>", submit)
    dialog.bind("<Escape>", cancel)
    dialog.update_idletasks()
    dialog_width = dialog.winfo_width()
    dialog_height = dialog.winfo_height()
    dialog.geometry(
        f"{dialog_width}x{dialog_height}+{(screen_width - dialog_width) // 2}+{(screen_height - dialog_height) // 2}"
    )
    dialog.deiconify()
    dialog.lift()
    dialog.grab_set()
    entry.focus_set()


def _run_widget_process(
    student_name: str,
    erp: str,
    access_code: str,
    command_queue: mp.Queue,
    event_queue: mp.Queue,
) -> None:
    end_requested = False
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

        _show_end_session_modal(root, access_code=access_code or "", on_confirm=confirm)

    def poll_commands() -> None:
        try:
            while True:
                command = command_queue.get_nowait()
                action = command.get("action")
                if action == "show":
                    root.deiconify()
                elif action == "hide":
                    root.withdraw()
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
        on_end_session=prompt_end_session,
        on_drag_start=on_drag_start,
        on_drag_motion=on_drag_motion,
        on_drag_release=on_drag_release,
    )
    screen_width = root.winfo_screenwidth()
    root.geometry(f"{target_width}x{target_height}+{screen_width - target_width - 20}+20")
    event_queue.put({"type": "ready"})
    root.after(150, poll_commands)

    try:
        root.mainloop()
    finally:
        event_queue.put({"type": "stopped"})


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

        self._start_x = 0
        self._start_y = 0
        self._start_win_x = 0
        self._start_win_y = 0

    def start(self) -> None:
        if _IS_MAC:
            self._start_process_widget(_run_widget_process, ready_timeout=8.0)
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

        if self.root:
            try:
                self.root.after(0, self.root.deiconify)
            except Exception:
                pass

    def hide(self) -> None:
        if self._uses_process_backend:
            self._send_process_command("hide")
            return

        if self.root:
            try:
                self.root.after(0, self.root.withdraw)
            except Exception:
                pass

    def stop(self) -> None:
        if self._uses_process_backend:
            self._stop_process_widget()
            return

        if self.root:
            try:
                self.root.after(0, self.root.destroy)
            except Exception:
                pass
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
        self._process = ctx.Process(
            target=target,
            args=(self.student_name, self.erp, self.access_code or "", self._command_queue, self._event_queue),
            daemon=True,
        )
        self._process.start()

        self._listener_thread = threading.Thread(target=self._listen_process_events, daemon=True)
        self._listener_thread.start()
        if self._ready_event.wait(timeout=ready_timeout):
            self._uses_process_backend = True
            return True

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

    def _run_app(self) -> None:
        self.root = tk.Tk()
        _configure_floating_window(self.root, "Markaz Sentinel")

        target_width, target_height = _build_side_widget(
            self.root,
            student_name=self.student_name,
            erp=self.erp,
            access_code=self.access_code,
            on_end_session=self._prompt_end_session,
            on_drag_start=self._on_drag_start,
            on_drag_motion=self._on_drag_motion,
            on_drag_release=self._on_drag_release,
        )
        screen_width = self.root.winfo_screenwidth()
        self.root.geometry(f"{target_width}x{target_height}+{screen_width - target_width - 20}+20")
        self._ready_event.set()
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

        _show_end_session_modal(self.root, access_code=self.access_code or "", on_confirm=confirm)
