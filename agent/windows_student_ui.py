from __future__ import annotations

import platform
import sys
import tkinter as tk
from tkinter import messagebox
from tkinter import scrolledtext


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
    root = _build_modal_shell("Markaz")
    error_var = tk.StringVar(value="")

    card = _build_card(root, width=420)
    _headline(card, "Student Verification")
    _subheadline(card, "Enter your 5-digit ERP to begin the exam session.")

    entry = tk.Entry(
        card,
        font=("Segoe UI", 16),
        justify="center",
        bg="#0f172a",
        fg="#f8fafc",
        insertbackground="#22d3ee",
        relief=tk.FLAT,
        bd=0,
    )
    entry.pack(fill=tk.X, pady=(18, 6), ipady=10)
    entry.focus_set()

    tk.Label(card, textvariable=error_var, bg="#060816", fg="#fb7185", font=("Segoe UI", 10)).pack(anchor=tk.W, pady=(0, 12))

    button_row = tk.Frame(card, bg="#060816")
    button_row.pack(fill=tk.X, pady=(6, 0))

    def cancel() -> None:
        result["erp"] = None
        root.destroy()

    def submit(_event=None) -> None:
        erp = entry.get().strip()
        if len(erp) == 5 and erp.isdigit():
            result["erp"] = erp
            root.destroy()
            return
        error_var.set("ERP must be exactly 5 digits.")

    _secondary_button(button_row, "Exit", cancel).pack(side=tk.LEFT, padx=(0, 8))
    _primary_button(button_row, "Continue", submit).pack(side=tk.RIGHT)

    root.bind("<Return>", submit)
    root.protocol("WM_DELETE_WINDOW", cancel)
    root.mainloop()
    return result["erp"]


def request_consent_confirmation() -> bool:
    result = {"accepted": False, "submitted": False}
    root = _build_modal_shell("Markaz")
    error_var = tk.StringVar(value="")

    card = _build_card(root, width=560)
    _headline(card, "Academic Integrity Pledge")
    _subheadline(card, "Type YES to accept the pledge and begin monitoring.")

    text = scrolledtext.ScrolledText(
        card,
        height=11,
        wrap=tk.WORD,
        font=("Segoe UI", 11),
        bg="#0a1020",
        fg="#e2e8f0",
        relief=tk.FLAT,
        bd=0,
        insertbackground="#e2e8f0",
        padx=12,
        pady=12,
    )
    text.insert(
        "1.0",
        (
            "I pledge on my honour that I will not give or receive any unauthorized "
            "assistance during this examination.\n\n"
            "I understand that any violation of IBA's Academic Integrity Policy may "
            "result in serious disciplinary action.\n\n"
            "Type YES to accept this pledge and continue. Type NO to exit."
        ),
    )
    text.configure(state=tk.DISABLED)
    text.pack(fill=tk.BOTH, expand=True, pady=(18, 14))

    entry = tk.Entry(
        card,
        font=("Segoe UI", 15),
        justify="center",
        bg="#0f172a",
        fg="#f8fafc",
        insertbackground="#22d3ee",
        relief=tk.FLAT,
        bd=0,
    )
    entry.pack(fill=tk.X, pady=(0, 6), ipady=10)
    entry.focus_set()

    tk.Label(card, textvariable=error_var, bg="#060816", fg="#fb7185", font=("Segoe UI", 10)).pack(anchor=tk.W, pady=(0, 12))

    button_row = tk.Frame(card, bg="#060816")
    button_row.pack(fill=tk.X, pady=(6, 0))

    def exit_app() -> None:
        result["submitted"] = True
        result["accepted"] = False
        root.destroy()

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
        error_var.set("Type YES to continue or NO to exit.")

    _secondary_button(button_row, "Exit", exit_app).pack(side=tk.LEFT, padx=(0, 8))
    _primary_button(button_row, "Submit", submit).pack(side=tk.RIGHT)

    root.bind("<Return>", submit)
    root.protocol("WM_DELETE_WINDOW", exit_app)
    root.mainloop()
    return bool(result["submitted"] and result["accepted"])


def _build_modal_shell(title: str) -> tk.Tk:
    root = tk.Tk()
    root.title(title)
    root.configure(bg="#020617")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"+{(sw // 2) - 240}+{(sh // 2) - 200}")
    root.lift()
    root.focus_force()
    return root


def _build_card(root: tk.Tk, *, width: int) -> tk.Frame:
    outer = tk.Frame(root, bg="#020617", padx=20, pady=20)
    outer.pack(fill=tk.BOTH, expand=True)

    glow = tk.Frame(outer, bg="#0f172a", padx=2, pady=2)
    glow.pack(fill=tk.BOTH, expand=True)

    card = tk.Frame(glow, bg="#060816", padx=26, pady=24, width=width)
    card.pack(fill=tk.BOTH, expand=True)
    card.pack_propagate(False)
    return card


def _headline(parent: tk.Widget, text: str) -> None:
    tk.Label(parent, text=text, bg="#060816", fg="#f8fafc", font=("Segoe UI Semibold", 18)).pack(anchor=tk.W)


def _subheadline(parent: tk.Widget, text: str) -> None:
    tk.Label(
        parent,
        text=text,
        bg="#060816",
        fg="#cbd5e1",
        font=("Segoe UI", 10),
        wraplength=500,
        justify=tk.LEFT,
    ).pack(anchor=tk.W, pady=(6, 0))


def _primary_button(parent: tk.Widget, text: str, command) -> tk.Button:
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=("Segoe UI Semibold", 10),
        bg="#0ea5e9",
        fg="#f8fafc",
        activebackground="#22d3ee",
        activeforeground="#020617",
        relief=tk.FLAT,
        bd=0,
        padx=18,
        pady=10,
        cursor="hand2",
    )


def _secondary_button(parent: tk.Widget, text: str, command) -> tk.Button:
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=("Segoe UI", 10),
        bg="#111827",
        fg="#e2e8f0",
        activebackground="#1f2937",
        activeforeground="#f8fafc",
        relief=tk.FLAT,
        bd=0,
        padx=18,
        pady=10,
        cursor="hand2",
    )
