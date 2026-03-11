"""
macOS permission setup guide for Markaz Sentinel.

Run this script before exam day on a Mac to guide the student through
granting the necessary permissions.

Usage:
    python -m agent.setup_mac
"""
from __future__ import annotations

import platform
import subprocess
import sys

from . import mac_accessibility
from . import platform_compat  # noqa: F401


def main() -> None:
    if platform.system() != "Darwin":
        print("This setup script is only needed on macOS.")
        print("On Windows, no additional setup is required.")
        sys.exit(0)

    print("=" * 50)
    print("MARKAZ EXAM SOFTWARE - SETUP")
    print("=" * 50)
    print()
    print("This will configure your system so the exam")
    print("software can function properly during your exam.")
    print()

    if not mac_accessibility.is_runtime_available():
        print("PyObjC macOS dependencies are missing.")
        print("Install the mac requirements first:")
        print("pip install -r agent/requirements_mac.txt")
        print()
        sys.exit(1)

    print("STEP 1: Accessibility Settings")
    print("-" * 40)
    print("Opening System Settings...")
    print("Please click the lock icon, enter your password,")
    print("and toggle ON 'Terminal' (or 'Python').")
    print()

    mac_accessibility.request_accessibility_permission()
    input("Press ENTER to open settings...")
    subprocess.run(
        ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"],
        check=False,
    )

    print()
    input("After toggling it ON, press ENTER to continue...")

    print()
    print("STEP 2: Input Monitoring Settings")
    print("-" * 40)
    print("Opening Input Monitoring settings...")
    print("Please toggle ON 'Terminal' (or 'Python') here as well.")
    print()

    input("Press ENTER to open settings...")
    subprocess.run(
        ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"],
        check=False,
    )

    print()
    input("After toggling it ON, press ENTER to verify...")

    print()
    print("VERIFYING SETUP...")
    print("-" * 40)

    keyboard_ok = _verify_keyboard_access()
    window_ok = _verify_window_detection()
    warmup_ok = _verify_runtime_warmup()
    clipboard_ok = _verify_clipboard_access()

    print()
    if keyboard_ok and window_ok and warmup_ok and clipboard_ok:
        print("=" * 50)
        print("SETUP COMPLETE")
        print("=" * 50)
        print("Your system is ready for the exam.")
        print("You can close this window.")
    else:
        print("=" * 50)
        print("SETUP INCOMPLETE")
        print("=" * 50)
        print("Some permissions or runtime checks failed.")
        print("Please rerun this setup and ensure the required")
        print("privacy toggles are enabled in System Settings.")

    print()
    input("Press ENTER to exit...")


def _verify_keyboard_access() -> bool:
    try:
        from pynput import keyboard

        received = []

        def _on_press(_key):
            received.append(True)
            return False

        listener = keyboard.Listener(on_press=_on_press)
        listener.start()

        print("Please press ANY KEY on your keyboard to test...")
        listener.join(timeout=15)

        if received:
            print("  OK Keyboard access: WORKING")
            return True

        print("  FAIL Keyboard access: NOT WORKING")
        print("     Please ensure Input Monitoring is enabled.")
        return False
    except Exception as exc:
        print(f"  FAIL Keyboard access: {exc}")
        return False


def _verify_window_detection() -> bool:
    try:
        snapshot = mac_accessibility.get_front_window_snapshot()
        if snapshot is not None and snapshot.title:
            print(f"  OK Window detection: WORKING ({snapshot.title})")
            return True

        print("  FAIL Window detection: NOT WORKING")
        print("     Please ensure Accessibility is enabled.")
        return False
    except Exception as exc:
        print(f"  FAIL Window detection: {exc}")
        return False


def _verify_runtime_warmup() -> bool:
    try:
        import pygetwindow

        active_window = pygetwindow.getActiveWindow()
        if active_window and getattr(active_window, "title", None):
            print(f"  OK Runtime warm-up: READY ({active_window.title})")
            return True

        print("  FAIL Runtime warm-up: no active window metadata returned")
        return False
    except Exception as exc:
        print(f"  FAIL Runtime warm-up: {exc}")
        return False


def _verify_clipboard_access() -> bool:
    try:
        import pyperclip

        pyperclip.paste()
        print("  OK Clipboard access: WORKING")
        return True
    except Exception as exc:
        print(f"  WARN Clipboard access: could not verify ({exc})")
        return True


if __name__ == "__main__":
    main()
