from __future__ import annotations

import ctypes
import platform
import sys
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Callable


_WINDOW_BG = "#000000"
_BACKDROP_BG = "#05070B"
_CARD_BG = "#07090D"
_CARD_BORDER = "#143846"
_PANEL_BG = "#0A0D12"
_PANEL_BORDER = "#1A2430"
_INPUT_BG = "#0B1118"
_INPUT_BORDER = "#1D4B5A"
_INPUT_ACTIVE = "#2AB7D3"
_TEXT_PRIMARY = "#F6FAFF"
_TEXT_MUTED = "#9AA6B2"
_TEXT_SUBTLE = "#6E7985"
_TEXT_CYAN = "#67E8F9"
_TEXT_ROSE = "#FDA4AF"
_ERROR = "#FB7185"
_INPUT_FONT_FAMILY = "Consolas"
_ERP_INPUT_FONT = (_INPUT_FONT_FAMILY, 16)
_CONSENT_INPUT_FONT = (_INPUT_FONT_FAMILY, 18, "bold")

_ERP_SIZE = (520, 330)
_CONSENT_SIZE = (500, 456)

_modal_host: tk.Tk | None = None


def is_windows_packaged_runtime() -> bool:
    return platform.system() == "Windows" and bool(getattr(sys, "frozen", False))


def show_error_dialog(title: str, message: str) -> None:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    messagebox.showerror(title, message, parent=root)
    root.destroy()


def request_student_erp() -> str | None:
    result: dict[str, str | None] = {"erp": None}
    root = _build_modal_shell("Markaz", *_ERP_SIZE)

    def cancel() -> None:
        result["erp"] = None
        _close_modal(root)

    def submit(erp: str) -> None:
        result["erp"] = erp
        _close_modal(root)

    _build_erp_popup(root, on_submit=submit, on_cancel=cancel)
    _show_modal(root)
    root.protocol("WM_DELETE_WINDOW", cancel)
    root.wait_window()
    return result["erp"]


def request_student_erp_with_session_start(
    start_session: Callable[[str], tuple[str, str, str]],
) -> tuple[str | None, tuple[str, str, str] | None]:
    result: dict[str, object | None] = {"erp": None, "session": None}
    state = {"busy": False}
    root = _build_modal_shell("Markaz", *_ERP_SIZE)
    view_holder: dict[str, _ErpPopupView] = {}

    def cancel() -> None:
        if state["busy"]:
            return
        result["erp"] = None
        result["session"] = None
        _close_modal(root)

    def complete_success(erp: str, session_info: tuple[str, str, str]) -> None:
        if not root.winfo_exists():
            return
        result["erp"] = erp
        result["session"] = session_info
        _close_modal(root)

    def complete_error(message: str) -> None:
        if not root.winfo_exists():
            return
        state["busy"] = False
        view = view_holder["view"]
        view.set_busy(False)
        view.set_error(message)

    def submit(erp: str) -> None:
        if state["busy"]:
            return

        state["busy"] = True
        view = view_holder["view"]
        view.set_busy(True)
        view.set_status("Connecting...")

        def worker() -> None:
            try:
                session_info = start_session(erp)
            except Exception as exc:
                root.after(0, lambda: complete_error(str(exc)))
                return
            root.after(0, lambda: complete_success(erp, session_info))

        threading.Thread(target=worker, daemon=True).start()

    view_holder["view"] = _build_erp_popup(root, on_submit=submit, on_cancel=cancel)
    _show_modal(root)
    root.protocol("WM_DELETE_WINDOW", cancel)
    root.wait_window()
    return result["erp"], result["session"]  # type: ignore[return-value]


def request_consent_confirmation() -> bool:
    result = {"accepted": False}
    root = _build_modal_shell("Markaz", *_CONSENT_SIZE)

    def cancel() -> None:
        result["accepted"] = False
        _close_modal(root)

    def submit() -> None:
        result["accepted"] = True
        _close_modal(root)

    _build_consent_popup(root, on_submit=submit, on_cancel=cancel)
    _show_modal(root)
    root.protocol("WM_DELETE_WINDOW", cancel)
    root.wait_window()
    return bool(result["accepted"])


def _get_modal_host() -> tk.Tk:
    global _modal_host

    if _modal_host is None or not _modal_host.winfo_exists():
        _modal_host = tk.Tk()
        _modal_host.withdraw()
        _modal_host.configure(bg=_WINDOW_BG)

    return _modal_host


def _build_modal_shell(title: str, width: int, height: int) -> tk.Toplevel:
    root = tk.Toplevel(_get_modal_host())
    root.withdraw()
    root.title(title)
    root.overrideredirect(True)
    root.resizable(False, False)
    root.configure(bg=_WINDOW_BG)
    root.attributes("-topmost", True)
    root.geometry(f"{width}x{height}+0+0")
    return root


def _show_modal(root: tk.Toplevel) -> None:
    backdrop = _create_backdrop()
    setattr(root, "_modal_backdrop", backdrop)
    _center_modal(root)
    if backdrop is not None and backdrop.winfo_exists():
        backdrop.deiconify()
        backdrop.lift()
    root.deiconify()
    root.lift()
    root.focus_force()
    try:
        root.grab_set()
    except tk.TclError:
        pass


def _close_modal(root: tk.Toplevel) -> None:
    def destroy_later() -> None:
        backdrop = getattr(root, "_modal_backdrop", None)
        if root.winfo_exists():
            try:
                root.grab_release()
            except tk.TclError:
                pass
            root.destroy()
        if backdrop is not None and backdrop.winfo_exists():
            backdrop.destroy()

    if root.winfo_exists():
        root.after_idle(destroy_later)


def _center_modal(root: tk.Misc) -> None:
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.geometry(f"{width}x{height}+{(screen_width - width) // 2}+{(screen_height - height) // 2}")


def _create_backdrop() -> tk.Toplevel | None:
    overlay = tk.Toplevel(_get_modal_host())
    overlay.withdraw()
    overlay.overrideredirect(True)
    overlay.wm_attributes("-topmost", True)
    overlay.wm_attributes("-alpha", 0.58)
    overlay.configure(bg=_BACKDROP_BG)

    width = overlay.winfo_screenwidth()
    height = overlay.winfo_screenheight()
    overlay.geometry(f"{width}x{height}+0+0")
    _try_enable_windows_blur(overlay)
    return overlay


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
        accent.GradientColor = 0x9405070B
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


def _build_card(root: tk.Toplevel) -> tuple[tk.Frame, tk.Frame]:
    outer = tk.Frame(root, bg=_WINDOW_BG, padx=18, pady=18)
    outer.pack(fill=tk.BOTH, expand=True)

    card = tk.Frame(
        outer,
        bg=_CARD_BG,
        highlightbackground=_CARD_BORDER,
        highlightthickness=1,
        bd=0,
    )
    card.pack(fill=tk.BOTH, expand=True)

    top_strip = tk.Frame(card, bg=_TEXT_CYAN, height=2)
    top_strip.pack(fill=tk.X, side=tk.TOP)

    content = tk.Frame(card, bg=_CARD_BG, padx=28, pady=24)
    content.pack(fill=tk.BOTH, expand=True)
    return card, content


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
        pady=10,
        width=width,
        cursor="hand2",
    )


class _ErpPopupView:
    def __init__(
        self,
        *,
        entry: tk.Entry,
        entry_shell: tk.Frame,
        error_label: tk.Label,
        continue_button: tk.Button,
        exit_button: tk.Button,
    ) -> None:
        self.entry = entry
        self.entry_shell = entry_shell
        self.error_label = error_label
        self.continue_button = continue_button
        self.exit_button = exit_button

    def focus(self) -> None:
        self.entry.focus_force()
        self.entry.icursor(tk.END)

    def set_error(self, message: str) -> None:
        self.error_label.configure(text=message, fg=_ERROR)
        _style_entry_error(self.entry_shell, has_error=True)
        self.focus()

    def set_status(self, message: str) -> None:
        self.error_label.configure(text=message, fg=_TEXT_MUTED)
        _style_entry_error(self.entry_shell, has_error=False)

    def set_busy(self, busy: bool) -> None:
        button_state = tk.DISABLED if busy else tk.NORMAL
        entry_state = tk.DISABLED if busy else tk.NORMAL
        self.entry.configure(state=entry_state)
        self.continue_button.configure(
            state=button_state,
            text="Connecting..." if busy else "Continue",
            cursor="watch" if busy else "hand2",
        )
        self.exit_button.configure(
            state=button_state,
            cursor="watch" if busy else "hand2",
        )
        if not busy:
            self.focus()


def _make_numeric_entry_shell(parent: tk.Widget) -> tuple[tk.Frame, tk.Entry]:
    shell = tk.Frame(
        parent,
        bg=_INPUT_BG,
        highlightbackground=_INPUT_BORDER,
        highlightcolor=_INPUT_ACTIVE,
        highlightthickness=1,
        bd=0,
        padx=1,
        pady=1,
    )
    
    var = tk.StringVar()
    
    def on_validate(P: str) -> bool:
        if len(P) > 5:
            return False
        return P.isdigit() or P == ""

    vcmd = (parent.register(on_validate), '%P')
    
    entry = tk.Entry(
        shell,
        textvariable=var,
        bg=_INPUT_BG,
        fg=_TEXT_PRIMARY,
        insertbackground=_TEXT_CYAN,
        relief=tk.FLAT,
        bd=0,
        font=_ERP_INPUT_FONT,
        highlightthickness=0,
        insertwidth=2,
        validate="key",
        validatecommand=vcmd
    )
    entry.pack(fill=tk.X, padx=14, pady=10)
    return shell, entry


def _make_confirmation_entry_shell(parent: tk.Widget) -> tuple[tk.Frame, tk.Entry]:
    shell = tk.Frame(
        parent,
        bg=_INPUT_BG,
        highlightbackground=_INPUT_BORDER,
        highlightcolor=_INPUT_ACTIVE,
        highlightthickness=1,
        bd=0,
        padx=1,
        pady=1,
    )
    
    var = tk.StringVar()
    
    def on_validate(P: str) -> bool:
        if len(P) > 3:
            return False
        return P.isalpha() or P == ""

    vcmd = (parent.register(on_validate), '%P')
    
    entry = tk.Entry(
        shell,
        textvariable=var,
        bg=_INPUT_BG,
        fg=_TEXT_PRIMARY,
        insertbackground=_TEXT_CYAN,
        relief=tk.FLAT,
        bd=0,
        font=_CONSENT_INPUT_FONT,
        validate="key",
        validatecommand=vcmd
    )
    entry.pack(fill=tk.BOTH, expand=True, padx=16, pady=10)
    return shell, entry


def _style_entry_error(shell: tk.Frame, *, has_error: bool) -> None:
    shell.configure(highlightbackground=_ERROR if has_error else _INPUT_BORDER)


def _build_erp_popup(root: tk.Toplevel, *, on_submit: Callable[[str], None], on_cancel: Callable[[], None]) -> _ErpPopupView:
    _, content = _build_card(root)

    header = tk.Frame(content, bg=_CARD_BG)
    header.pack(fill=tk.X)
    tk.Label(header, text="STEP 1", bg=_CARD_BG, fg=_TEXT_CYAN, font=("Segoe UI", 9, "bold")).pack(anchor="w")
    tk.Label(
        header,
        text="Verify Your ERP",
        bg=_CARD_BG,
        fg=_TEXT_PRIMARY,
        font=("Segoe UI Semibold", 24),
    ).pack(anchor="w", pady=(10, 0))
    tk.Label(
        header,
        text="Enter your 5-digit ERP.",
        bg=_CARD_BG,
        fg=_TEXT_MUTED,
        font=("Segoe UI", 11),
    ).pack(anchor="w", pady=(8, 0))

    panel = tk.Frame(
        content,
        bg=_PANEL_BG,
        highlightbackground=_PANEL_BORDER,
        highlightthickness=1,
        bd=0,
        padx=18,
        pady=18,
    )
    panel.pack(fill=tk.X, pady=(22, 0))

    tk.Label(panel, text="ERP NUMBER", bg=_PANEL_BG, fg=_TEXT_SUBTLE, font=("Segoe UI", 9, "bold")).pack(anchor="w")

    entry_var = tk.StringVar()
    digit_labels: list[tk.Label] = []
    digit_lines: list[tk.Frame] = []

    entry_shell = tk.Frame(
        panel,
        bg=_INPUT_BG,
        highlightbackground=_INPUT_BORDER,
        highlightcolor=_INPUT_ACTIVE,
        highlightthickness=1,
        bd=0,
        padx=18,
        pady=16,
    )
    entry_shell.pack(fill=tk.X, pady=(12, 0))

    digits_row = tk.Frame(entry_shell, bg=_INPUT_BG)
    digits_row.pack(anchor="center")

    for index in range(5):
        slot = tk.Frame(digits_row, bg=_INPUT_BG)
        slot.grid(row=0, column=index, padx=8)
        digit_label = tk.Label(
            slot,
            text="",
            bg=_INPUT_BG,
            fg=_TEXT_PRIMARY,
            font=(_INPUT_FONT_FAMILY, 22, "bold"),
            width=2,
            anchor="center",
        )
        digit_label.pack()
        digit_line = tk.Frame(slot, bg=_INPUT_BORDER, width=30, height=2)
        digit_line.pack(pady=(8, 0))
        digit_labels.append(digit_label)
        digit_lines.append(digit_line)

    def sync_digits(*_args) -> None:
        value = entry_var.get()
        for index, digit_label in enumerate(digit_labels):
            digit = value[index] if index < len(value) else ""
            digit_label.configure(text=digit)
            digit_lines[index].configure(bg=_TEXT_CYAN if digit else _INPUT_BORDER)

    def on_validate(proposed: str) -> bool:
        if len(proposed) > 5:
            return False
        return proposed.isdigit() or proposed == ""

    vcmd = (root.register(on_validate), "%P")
    entry = tk.Entry(
        entry_shell,
        textvariable=entry_var,
        bg=_INPUT_BG,
        fg=_INPUT_BG,
        insertbackground=_INPUT_BG,
        selectbackground=_INPUT_BG,
        selectforeground=_INPUT_BG,
        relief=tk.FLAT,
        bd=0,
        font=_ERP_INPUT_FONT,
        justify="center",
        highlightthickness=0,
        insertwidth=0,
        validate="key",
        validatecommand=vcmd,
    )
    entry.place(relx=0.5, rely=0.5, anchor="center", width=1, height=1)
    entry_var.trace_add("write", sync_digits)
    sync_digits()

    error_label = tk.Label(content, text="", bg=_CARD_BG, fg=_ERROR, font=("Segoe UI", 9))
    error_label.pack(anchor="center", pady=(10, 0))

    button_row = tk.Frame(content, bg=_CARD_BG)
    button_row.pack(fill=tk.X, pady=(20, 0))
    exit_button = _make_button(
        button_row,
        text="Exit",
        command=on_cancel,
        fill="#0E1014",
        outline="#1E2530",
        text_color=_TEXT_PRIMARY,
        active_fill="#151A21",
        width=12,
    )
    exit_button.pack(side=tk.LEFT)
    continue_button = _make_button(
        button_row,
        text="Continue",
        command=lambda: submit(),
        fill="#083946",
        outline="#156274",
        text_color=_TEXT_CYAN,
        active_fill="#0B4554",
        width=14,
    )
    continue_button.pack(side=tk.RIGHT)

    def submit(_event=None) -> str:
        erp = entry.get().strip()
        if len(erp) == 5:
            on_submit(erp)
            return "break"
        error_label.configure(text="ERP must be exactly 5 digits.")
        _style_entry_error(entry_shell, has_error=True)
        entry.focus_set()
        return "break"

    def cancel_event(_event=None) -> str:
        on_cancel()
        return "break"

    def focus_entry(_event=None) -> str:
        entry.focus_force()
        entry.icursor(tk.END)
        return "break"

    def handle_keypress(event: tk.Event) -> str | None:
        if str(entry.cget("state")) == tk.DISABLED:
            return "break"

        current = entry_var.get()
        if event.keysym in {"BackSpace", "Delete"}:
            if current:
                entry_var.set(current[:-1])
            return "break"

        if event.char and event.char.isdigit():
            if len(current) < 5:
                entry_var.set(current + event.char)
            return "break"

        if event.keysym in {"Left", "Right", "Tab"}:
            return "break"
        return None

    entry_shell.bind("<Button-1>", focus_entry)
    digits_row.bind("<Button-1>", focus_entry)
    for digit_label in digit_labels:
        digit_label.bind("<Button-1>", focus_entry)
        digit_label.bind("<KeyPress>", handle_keypress)
    entry.bind("<KeyPress>", handle_keypress)
    entry_shell.bind("<KeyPress>", handle_keypress)
    panel.bind("<Button-1>", focus_entry)
    root.bind("<KeyPress>", handle_keypress, add="+")
    root.bind("<Return>", submit)
    root.bind("<KP_Enter>", submit)
    root.bind("<Escape>", cancel_event)
    root.after(20, lambda: entry.focus_force())
    return _ErpPopupView(
        entry=entry,
        entry_shell=entry_shell,
        error_label=error_label,
        continue_button=continue_button,
        exit_button=exit_button,
    )


def _build_consent_popup(root: tk.Toplevel, *, on_submit: Callable[[], None], on_cancel: Callable[[], None]) -> None:
    _, content = _build_card(root)

    header = tk.Frame(content, bg=_CARD_BG)
    header.pack(fill=tk.X)
    tk.Label(header, text="STEP 2", bg=_CARD_BG, fg=_TEXT_CYAN, font=("Segoe UI", 9, "bold")).pack(anchor="w")
    tk.Label(
        header,
        text="Academic Integrity Pledge",
        bg=_CARD_BG,
        fg=_TEXT_PRIMARY,
        font=("Segoe UI Semibold", 20),
    ).pack(anchor="w", pady=(10, 0))
    tk.Label(
        header,
        text="Read the pledge and confirm to continue.",
        bg=_CARD_BG,
        fg=_TEXT_MUTED,
        font=("Segoe UI", 11),
    ).pack(anchor="w", pady=(8, 0))

    pledge = tk.Frame(
        content,
        bg=_PANEL_BG,
        highlightbackground=_PANEL_BORDER,
        highlightthickness=1,
        bd=0,
        padx=18,
        pady=18,
    )
    pledge.pack(fill=tk.X, pady=(20, 0))

    tk.Label(
        pledge,
        text="I pledge on my honour that I will not give or receive any unauthorized assistance during this examination.",
        bg=_PANEL_BG,
        fg=_TEXT_PRIMARY,
        font=("Segoe UI", 11),
        wraplength=390,
        justify=tk.LEFT,
    ).pack(anchor="w")
    tk.Label(
        pledge,
        text="I understand that violating IBA's Academic Integrity Policy may lead to serious disciplinary consequences.",
        bg=_PANEL_BG,
        fg=_TEXT_PRIMARY,
        font=("Segoe UI", 11),
        wraplength=390,
        justify=tk.LEFT,
    ).pack(anchor="w", pady=(12, 0))

    input_wrap = tk.Frame(content, bg=_CARD_BG)
    input_wrap.pack(fill=tk.X, pady=(18, 0))
    tk.Label(
        input_wrap,
        text="TYPE YES TO CONTINUE",
        bg=_CARD_BG,
        fg=_TEXT_SUBTLE,
        font=("Segoe UI", 9, "bold"),
    ).pack(anchor="w")

    entry_shell, entry = _make_confirmation_entry_shell(input_wrap)
    entry.configure(justify="center")
    entry_shell.pack(fill=tk.X, pady=(10, 0))

    error_label = tk.Label(content, text="", bg=_CARD_BG, fg=_ERROR, font=("Segoe UI", 9))
    error_label.pack(anchor="center", pady=(10, 0))

    button_row = tk.Frame(content, bg=_CARD_BG)
    button_row.pack(fill=tk.X, pady=(18, 0))
    _make_button(
        button_row,
        text="Exit",
        command=on_cancel,
        fill="#0E1014",
        outline="#1E2530",
        text_color=_TEXT_PRIMARY,
        active_fill="#151A21",
        width=12,
    ).pack(side=tk.LEFT)
    _make_button(
        button_row,
        text="Accept and Continue",
        command=lambda: submit(),
        fill="#083946",
        outline="#156274",
        text_color=_TEXT_CYAN,
        active_fill="#0B4554",
        width=18,
    ).pack(side=tk.RIGHT)

    def submit(_event=None) -> str:
        choice = entry.get().strip().upper()
        if choice == "YES":
            on_submit()
            return "break"
        if choice == "NO":
            on_cancel()
            return "break"
        error_label.configure(text="Type YES to continue or click Exit.")
        _style_entry_error(entry_shell, has_error=True)
        entry.focus_set()
        return "break"

    def cancel_event(_event=None) -> str:
        on_cancel()
        return "break"

    entry_shell.bind("<Button-1>", lambda _event: entry.focus_set())
    input_wrap.bind("<Button-1>", lambda _event: entry.focus_set())
    root.bind("<Return>", submit)
    root.bind("<KP_Enter>", submit)
    root.bind("<Escape>", cancel_event)
    root.after(20, entry.focus_set)
