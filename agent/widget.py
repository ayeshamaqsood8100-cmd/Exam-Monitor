"""
On-screen monitoring widget that displays student info and allows ending the
session safely.

Windows can host tkinter in a background UI thread. macOS cannot; Cocoa
requires NSWindow creation on the process main thread. To keep the agent
robust across both platforms, macOS runs the widget in a dedicated child
process and forwards events back to the main agent process.
"""
from __future__ import annotations

import multiprocessing as mp
import platform
import queue
import threading
import tkinter as tk
from typing import Callable


_IS_MAC = platform.system() == "Darwin"


def _create_round_rect(cvs: tk.Canvas, x1: int, y1: int, x2: int, y2: int, r: int, **kwargs):
    pts = [
        x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y1 + r,
        x2, y2 - r, x2, y2 - r, x2, y2, x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1,
    ]
    return cvs.create_polygon(pts, smooth=True, **kwargs)


def _run_widget_process(
    student_name: str,
    erp: str,
    access_code: str,
    command_queue: mp.Queue,
    event_queue: mp.Queue,
) -> None:
    end_requested = False
    root = tk.Tk()
    root.title("Markaz Sentinel")
    root.overrideredirect(True)
    root.wm_attributes("-topmost", True)

    bg_main = "#2a2a2c"
    bg_box = "#3D3D3F"

    frame = tk.Frame(root, padx=6, pady=6, bg=bg_main, highlightbackground="#404040", highlightthickness=1)
    frame.pack(fill=tk.BOTH, expand=True)

    info_frame = tk.Frame(frame, bg=bg_main)
    info_frame.pack(fill=tk.X, pady=(0, 4))

    name_label = tk.Label(
        info_frame,
        text=student_name,
        font=("Segoe UI", 10, "bold"),
        bg=bg_main,
        fg="#ffffff",
        wraplength=140,
        justify=tk.CENTER,
    )
    name_label.pack(anchor=tk.CENTER, pady=(0, 1))

    tk.Label(info_frame, text=f"ERP: {erp}", font=("Segoe UI", 8), bg=bg_main, fg="#b3b3b3").pack(anchor=tk.CENTER)

    code_frame = tk.Frame(frame, bg=bg_box, padx=4, pady=6)
    code_frame.pack(fill=tk.X, pady=(0, 6))
    tk.Label(code_frame, text="CODE", font=("Segoe UI", 8, "bold"), bg=bg_box, fg="#d1d1d1").pack(anchor=tk.CENTER, pady=(0, 2))
    tk.Label(code_frame, text=access_code, font=("Consolas", 16, "bold"), bg=bg_box, fg="#ffffff").pack(anchor=tk.CENTER)

    btn_canvas = tk.Canvas(frame, bg=bg_main, highlightthickness=0, height=36, cursor="hand2")
    btn_canvas.pack(fill=tk.X, pady=(4, 0))

    start_x = 0
    start_y = 0
    start_win_x = 0
    start_win_y = 0

    def draw_main_btn(w: int, h: int, hover: bool = False) -> None:
        if w < 10 or h < 10:
            return
        btn_canvas.delete("all")
        r = 6
        _create_round_rect(btn_canvas, 1, 3, w - 1, h, r, fill="#040710", tags="btn")
        fill_color = "#D02046" if hover else "#B81537"
        _create_round_rect(btn_canvas, 0, 0, w, h - 2, r, fill=fill_color, tags="btn")
        highlight_color = "#E62F56" if hover else "#D12146"
        _create_round_rect(btn_canvas, 1, 1, w - 1, h - 4, r - 1, fill=highlight_color, tags="btn")
        btn_canvas.create_text(w / 2, (h - 2) / 2, text="End Session", font=("Segoe UI", 10, "bold"), fill="#ffffff", tags="btn")

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

        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        ww = root.winfo_width()
        wh = root.winfo_height()

        new_x = max(0, min(new_x, sw - ww))
        new_y = max(0, min(new_y, sh - wh))
        root.geometry(f"+{new_x}+{new_y}")

    def on_drag_release(_event) -> None:
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        ww = root.winfo_width()
        wh = root.winfo_height()
        x = root.winfo_x()
        y = root.winfo_y()
        new_x = max(0, min(x, sw - ww))
        new_y = max(0, min(y, sh - wh))
        if x != new_x or y != new_y:
            root.geometry(f"+{new_x}+{new_y}")

    def bind_drag_recursive(widget: tk.Widget) -> None:
        widget.bind("<ButtonPress-1>", on_drag_start)
        widget.bind("<B1-Motion>", on_drag_motion)
        widget.bind("<ButtonRelease-1>", on_drag_release)
        for child in widget.winfo_children():
            bind_drag_recursive(child)

    def prompt_end_session() -> None:
        nonlocal end_requested
        if end_requested:
            return

        overlay = tk.Toplevel(root)
        overlay.overrideredirect(True)
        overlay.wm_attributes("-topmost", True)
        overlay.wm_attributes("-alpha", 0.6)
        overlay.configure(bg="black")
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        overlay.geometry(f"{sw}x{sh}+0+0")

        dialog = tk.Toplevel(root)
        dialog.overrideredirect(True)
        dialog.wm_attributes("-topmost", True)

        bg_modal = "#212121"
        bg_input = "#333333"

        modal_frame = tk.Frame(dialog, padx=24, pady=24, bg=bg_modal, highlightbackground="#404040", highlightthickness=1)
        modal_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(modal_frame, text="End Session?", font=("Segoe UI", 16, "bold"), bg=bg_modal, fg="#ffffff").pack(anchor=tk.W, pady=(0, 6))
        msg = "This will end monitoring and remove the agent from this device. This action cannot be undone."
        tk.Label(
            modal_frame,
            text=msg,
            font=("Segoe UI", 9),
            bg=bg_modal,
            fg="#d1d1d1",
            justify=tk.LEFT,
            wraplength=260,
        ).pack(anchor=tk.W, pady=(0, 16))

        tk.Label(modal_frame, text="CONFIRM WITH CODE", font=("Segoe UI", 8, "bold"), bg=bg_modal, fg="#b3b3b3").pack(anchor=tk.W, pady=(0, 4))

        input_cvs = tk.Canvas(modal_frame, bg=bg_modal, highlightthickness=0, height=44)
        input_cvs.pack(fill=tk.X, pady=(0, 6))
        entry = tk.Entry(
            input_cvs,
            justify="center",
            font=("Consolas", 18, "bold"),
            show="*",
            bg=bg_input,
            fg="#ffffff",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
        )

        def draw_input(cvs: tk.Canvas, w: int, h: int) -> None:
            if w < 10 or h < 10:
                return
            cvs.delete("all")
            _create_round_rect(cvs, 0, 0, w, h, 28, fill=bg_input, tags="bg")
            cvs.create_window(w / 2, h / 2, window=entry, width=w - 30, height=h - 20)

        input_cvs.bind("<Configure>", lambda e: draw_input(input_cvs, e.width, e.height))
        entry.focus_set()

        error_label = tk.Label(modal_frame, text="", bg=bg_modal, fg="#ff4d60", font=("Segoe UI", 11, "bold"))
        error_label.pack(pady=(0, 15))

        def submit(_event=None) -> None:
            nonlocal end_requested
            if not access_code.strip():
                error_label.config(text="Session code unavailable")
                entry.delete(0, tk.END)
                return
            if entry.get().strip() == access_code:
                end_requested = True
                dialog.destroy()
                overlay.destroy()
                event_queue.put({"type": "end_session"})
            else:
                error_label.config(text="Incorrect passcode. Access denied.")
                entry.delete(0, tk.END)

        def cancel(_event=None) -> None:
            dialog.destroy()
            overlay.destroy()

        btn_frame = tk.Frame(modal_frame, bg=bg_modal)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        cancel_cvs = tk.Canvas(btn_frame, bg=bg_modal, highlightthickness=0, height=44, cursor="hand2")
        cancel_cvs.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        confirm_cvs = tk.Canvas(btn_frame, bg=bg_modal, highlightthickness=0, height=44, cursor="hand2")
        confirm_cvs.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0))

        def draw_dialog_btn(cvs: tk.Canvas, w: int, h: int, text: str, color_bg: str, color_hover: str, hover: bool = False) -> None:
            if w < 10 or h < 10:
                return
            cvs.delete("all")
            r = 20
            current_bg = color_hover if hover else color_bg
            _create_round_rect(
                cvs,
                1,
                1,
                w - 2,
                h - 2,
                r,
                fill=current_bg,
                outline="#555555" if color_bg == "#333333" else "",
                width=1,
                tags="btn",
            )
            cvs.create_text(w / 2, h / 2, text=text, font=("Segoe UI", 14, "bold"), fill="#ffffff", tags="btn")

        cancel_cvs.bind("<Configure>", lambda e: draw_dialog_btn(cancel_cvs, e.width, e.height, "Cancel", "#333333", "#4d4d4d"))
        cancel_cvs.bind("<Enter>", lambda _e: draw_dialog_btn(cancel_cvs, cancel_cvs.winfo_width(), cancel_cvs.winfo_height(), "Cancel", "#333333", "#4d4d4d", True))
        cancel_cvs.bind("<Leave>", lambda _e: draw_dialog_btn(cancel_cvs, cancel_cvs.winfo_width(), cancel_cvs.winfo_height(), "Cancel", "#333333", "#4d4d4d", False))
        cancel_cvs.tag_bind("btn", "<ButtonRelease-1>", cancel)

        confirm_cvs.bind("<Configure>", lambda e: draw_dialog_btn(confirm_cvs, e.width, e.height, "Confirm End", "#b0243b", "#c22a42"))
        confirm_cvs.bind("<Enter>", lambda _e: draw_dialog_btn(confirm_cvs, confirm_cvs.winfo_width(), confirm_cvs.winfo_height(), "Confirm End", "#b0243b", "#c22a42", True))
        confirm_cvs.bind("<Leave>", lambda _e: draw_dialog_btn(confirm_cvs, confirm_cvs.winfo_width(), confirm_cvs.winfo_height(), "Confirm End", "#b0243b", "#c22a42", False))
        confirm_cvs.tag_bind("btn", "<ButtonRelease-1>", submit)

        dialog.bind("<Return>", submit)
        dialog.bind("<Escape>", cancel)
        dialog.update_idletasks()

        target_dw = 320
        dh = dialog.winfo_reqheight()
        new_x = (sw - target_dw) // 2
        new_y = (sh - dh) // 2
        dialog.geometry(f"{target_dw}x{dh}+{new_x}+{new_y}")
        dialog.grab_set()

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

    btn_canvas.bind("<Configure>", lambda e: draw_main_btn(e.width, e.height))
    btn_canvas.bind("<Enter>", lambda _e: draw_main_btn(btn_canvas.winfo_width(), btn_canvas.winfo_height(), hover=True))
    btn_canvas.bind("<Leave>", lambda _e: draw_main_btn(btn_canvas.winfo_width(), btn_canvas.winfo_height(), hover=False))
    btn_canvas.tag_bind("btn", "<ButtonRelease-1>", lambda _e: prompt_end_session())

    bind_drag_recursive(frame)
    root.update_idletasks()
    target_width = 160
    target_height = root.winfo_reqheight()
    sw = root.winfo_screenwidth()
    root.geometry(f"{target_width}x{target_height}+{sw - target_width - 20}+20")
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

        self._start_x = 0
        self._start_y = 0
        self._start_win_x = 0
        self._start_win_y = 0

    def start(self) -> None:
        if _IS_MAC:
            self._start_macos_widget()
            return

        if self._thread and self._thread.is_alive():
            self.show()
            return

        self._ready_event.clear()
        self._thread = threading.Thread(target=self._run_app, daemon=True)
        self._thread.start()
        self._ready_event.wait(timeout=5.0)

    def show(self) -> None:
        if _IS_MAC:
            self._send_process_command("show")
            return

        if self.root:
            try:
                self.root.after(0, self.root.deiconify)
            except Exception:
                pass

    def hide(self) -> None:
        if _IS_MAC:
            self._send_process_command("hide")
            return

        if self.root:
            try:
                self.root.after(0, self.root.withdraw)
            except Exception:
                pass

    def stop(self) -> None:
        if _IS_MAC:
            self._stop_macos_widget()
            return

        if self.root:
            try:
                self.root.after(0, self.root.destroy)
            except Exception:
                pass
        if self._thread and self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=2.5)

    def _start_macos_widget(self) -> None:
        if self._process and self._process.is_alive():
            self.show()
            return

        ctx = mp.get_context("spawn")
        self._command_queue = ctx.Queue()
        self._event_queue = ctx.Queue()
        self._ready_event.clear()
        self._listener_stop.clear()
        self._process = ctx.Process(
            target=_run_widget_process,
            args=(self.student_name, self.erp, self.access_code or "", self._command_queue, self._event_queue),
            daemon=True,
        )
        self._process.start()

        self._listener_thread = threading.Thread(target=self._listen_process_events, daemon=True)
        self._listener_thread.start()
        self._ready_event.wait(timeout=8.0)

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

    def _stop_macos_widget(self) -> None:
        self._listener_stop.set()
        self._send_process_command("stop")

        if self._process:
            self._process.join(timeout=3.0)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=2.0)
            self._process = None

        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=1.5)

        self._command_queue = None
        self._event_queue = None
        self._listener_thread = None

    def _run_app(self) -> None:
        self.root = tk.Tk()
        self.root.title("Markaz Sentinel")
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)

        bg_main = "#2a2a2c"
        bg_box = "#3D3D3F"

        frame = tk.Frame(self.root, padx=6, pady=6, bg=bg_main, highlightbackground="#404040", highlightthickness=1)
        frame.pack(fill=tk.BOTH, expand=True)

        info_frame = tk.Frame(frame, bg=bg_main)
        info_frame.pack(fill=tk.X, pady=(0, 4))

        name_label = tk.Label(info_frame, text=self.student_name, font=("Segoe UI", 10, "bold"), bg=bg_main, fg="#ffffff", wraplength=140, justify=tk.CENTER)
        name_label.pack(anchor=tk.CENTER, pady=(0, 1))

        tk.Label(info_frame, text=f"ERP: {self.erp}", font=("Segoe UI", 8), bg=bg_main, fg="#b3b3b3").pack(anchor=tk.CENTER)

        code_frame = tk.Frame(frame, bg=bg_box, padx=4, pady=6)
        code_frame.pack(fill=tk.X, pady=(0, 6))
        tk.Label(code_frame, text="CODE", font=("Segoe UI", 8, "bold"), bg=bg_box, fg="#d1d1d1").pack(anchor=tk.CENTER, pady=(0, 2))
        tk.Label(code_frame, text=self.access_code, font=("Consolas", 16, "bold"), bg=bg_box, fg="#ffffff").pack(anchor=tk.CENTER)

        btn_canvas = tk.Canvas(frame, bg=bg_main, highlightthickness=0, height=36, cursor="hand2")
        btn_canvas.pack(fill=tk.X, pady=(4, 0))

        def draw_main_btn(w, h, hover=False):
            if w < 10 or h < 10:
                return
            btn_canvas.delete("all")
            r = 6
            _create_round_rect(btn_canvas, 1, 3, w - 1, h, r, fill="#040710", tags="btn")
            fill_color = "#D02046" if hover else "#B81537"
            _create_round_rect(btn_canvas, 0, 0, w, h - 2, r, fill=fill_color, tags="btn")
            highlight_color = "#E62F56" if hover else "#D12146"
            _create_round_rect(btn_canvas, 1, 1, w - 1, h - 4, r - 1, fill=highlight_color, tags="btn")
            btn_canvas.create_text(w / 2, (h - 2) / 2, text="End Session", font=("Segoe UI", 10, "bold"), fill="#ffffff", tags="btn")

        btn_canvas.bind("<Configure>", lambda e: draw_main_btn(e.width, e.height))
        btn_canvas.bind("<Enter>", lambda _e: draw_main_btn(btn_canvas.winfo_width(), btn_canvas.winfo_height(), hover=True))
        btn_canvas.bind("<Leave>", lambda _e: draw_main_btn(btn_canvas.winfo_width(), btn_canvas.winfo_height(), hover=False))
        btn_canvas.tag_bind("btn", "<ButtonRelease-1>", lambda _e: self._prompt_end_session())

        def bind_drag_recursive(widget):
            widget.bind("<ButtonPress-1>", self._on_drag_start)
            widget.bind("<B1-Motion>", self._on_drag_motion)
            widget.bind("<ButtonRelease-1>", self._on_drag_release)
            for child in widget.winfo_children():
                bind_drag_recursive(child)

        bind_drag_recursive(frame)

        self.root.update_idletasks()
        target_width = 160
        target_height = self.root.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        self.root.geometry(f"{target_width}x{target_height}+{sw - target_width - 20}+20")
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

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        ww = self.root.winfo_width()
        wh = self.root.winfo_height()

        new_x = max(0, min(new_x, sw - ww))
        new_y = max(0, min(new_y, sh - wh))
        self.root.geometry(f"+{new_x}+{new_y}")

    def _on_drag_release(self, _event) -> None:
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
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.wm_attributes("-topmost", True)
        overlay.wm_attributes("-alpha", 0.6)
        overlay.configure(bg="black")
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        overlay.geometry(f"{sw}x{sh}+0+0")

        dialog = tk.Toplevel(self.root)
        dialog.overrideredirect(True)
        dialog.wm_attributes("-topmost", True)

        bg_modal = "#212121"
        bg_input = "#333333"

        frame = tk.Frame(dialog, padx=24, pady=24, bg=bg_modal, highlightbackground="#404040", highlightthickness=1)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="End Session?", font=("Segoe UI", 16, "bold"), bg=bg_modal, fg="#ffffff").pack(anchor=tk.W, pady=(0, 6))
        msg = "This will end monitoring and remove the agent from this device. This action cannot be undone."
        tk.Label(frame, text=msg, font=("Segoe UI", 9), bg=bg_modal, fg="#d1d1d1", justify=tk.LEFT, wraplength=260).pack(anchor=tk.W, pady=(0, 16))
        tk.Label(frame, text="CONFIRM WITH CODE", font=("Segoe UI", 8, "bold"), bg=bg_modal, fg="#b3b3b3").pack(anchor=tk.W, pady=(0, 4))

        input_cvs = tk.Canvas(frame, bg=bg_modal, highlightthickness=0, height=44)
        input_cvs.pack(fill=tk.X, pady=(0, 6))
        entry = tk.Entry(input_cvs, justify="center", font=("Consolas", 18, "bold"), show="*", bg=bg_input, fg="#ffffff", insertbackground="#ffffff", relief=tk.FLAT, bd=0, highlightthickness=0)

        def draw_input(cvs, w, h):
            if w < 10 or h < 10:
                return
            cvs.delete("all")
            _create_round_rect(cvs, 0, 0, w, h, 28, fill=bg_input, tags="bg")
            cvs.create_window(w / 2, h / 2, window=entry, width=w - 30, height=h - 20)

        input_cvs.bind("<Configure>", lambda e: draw_input(input_cvs, e.width, e.height))
        entry.focus_set()

        error_label = tk.Label(frame, text="", bg=bg_modal, fg="#ff4d60", font=("Segoe UI", 11, "bold"))
        error_label.pack(pady=(0, 15))

        def on_submit(_e=None) -> None:
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

        def on_cancel(_e=None) -> None:
            dialog.destroy()
            overlay.destroy()

        btn_frame = tk.Frame(frame, bg=bg_modal)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        cancel_cvs = tk.Canvas(btn_frame, bg=bg_modal, highlightthickness=0, height=44, cursor="hand2")
        cancel_cvs.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        confirm_cvs = tk.Canvas(btn_frame, bg=bg_modal, highlightthickness=0, height=44, cursor="hand2")
        confirm_cvs.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0))

        def draw_dialog_btn(cvs, w, h, text, color_bg, color_hover, hover=False):
            if w < 10 or h < 10:
                return
            cvs.delete("all")
            r = 20
            current_bg = color_hover if hover else color_bg
            _create_round_rect(cvs, 1, 1, w - 2, h - 2, r, fill=current_bg, outline="#555555" if color_bg == "#333333" else "", width=1, tags="btn")
            cvs.create_text(w / 2, h / 2, text=text, font=("Segoe UI", 14, "bold"), fill="#ffffff", tags="btn")

        cancel_cvs.bind("<Configure>", lambda e: draw_dialog_btn(cancel_cvs, e.width, e.height, "Cancel", "#333333", "#4d4d4d"))
        cancel_cvs.bind("<Enter>", lambda _e: draw_dialog_btn(cancel_cvs, cancel_cvs.winfo_width(), cancel_cvs.winfo_height(), "Cancel", "#333333", "#4d4d4d", True))
        cancel_cvs.bind("<Leave>", lambda _e: draw_dialog_btn(cancel_cvs, cancel_cvs.winfo_width(), cancel_cvs.winfo_height(), "Cancel", "#333333", "#4d4d4d", False))
        cancel_cvs.tag_bind("btn", "<ButtonRelease-1>", on_cancel)

        confirm_cvs.bind("<Configure>", lambda e: draw_dialog_btn(confirm_cvs, e.width, e.height, "Confirm End", "#b0243b", "#c22a42"))
        confirm_cvs.bind("<Enter>", lambda _e: draw_dialog_btn(confirm_cvs, confirm_cvs.winfo_width(), confirm_cvs.winfo_height(), "Confirm End", "#b0243b", "#c22a42", True))
        confirm_cvs.bind("<Leave>", lambda _e: draw_dialog_btn(confirm_cvs, confirm_cvs.winfo_width(), confirm_cvs.winfo_height(), "Confirm End", "#b0243b", "#c22a42", False))
        confirm_cvs.tag_bind("btn", "<ButtonRelease-1>", on_submit)

        dialog.bind("<Return>", on_submit)
        dialog.bind("<Escape>", on_cancel)
        dialog.update_idletasks()

        target_dw = 320
        dh = dialog.winfo_reqheight()
        new_x = (sw - target_dw) // 2
        new_y = (sh - dh) // 2
        dialog.geometry(f"{target_dw}x{dh}+{new_x}+{new_y}")
        dialog.grab_set()
