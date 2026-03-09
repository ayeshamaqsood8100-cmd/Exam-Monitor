"""
macOS permission setup guide for Markaz Sentinel.

Run this script ONCE before exam day on a Mac to guide the student through
granting the necessary permissions (Accessibility + Input Monitoring).

Usage:
    python -m agent.setup_mac
"""
import platform
import subprocess
import sys
import time


def main():
    # Only run on macOS
    if platform.system() != "Darwin":
        print("This setup script is only needed on macOS.")
        print("On Windows, no additional setup is required.")
        sys.exit(0)

    print("=" * 50)
    print("MARKAZ EXAM SOFTWARE — SETUP")
    print("=" * 50)
    print()
    print("This will configure your system so the exam")
    print("software can function properly during your exam.")
    print()

    # Step 1: Open Accessibility settings
    print("STEP 1: Accessibility Settings")
    print("-" * 40)
    print("Opening System Settings...")
    print("Please click the lock icon, enter your password,")
    print("and toggle ON 'Terminal' (or 'Python').")
    print()

    input("Press ENTER to open settings...")
    subprocess.run([
        "open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
    ])

    print()
    input("After toggling it ON, press ENTER to continue...")

    # Step 2: Open Input Monitoring settings
    print()
    print("STEP 2: Input Monitoring Settings")
    print("-" * 40)
    print("Opening Input Monitoring settings...")
    print("Please toggle ON 'Terminal' (or 'Python') here as well.")
    print()

    input("Press ENTER to open settings...")
    subprocess.run([
        "open", "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"
    ])

    print()
    input("After toggling it ON, press ENTER to verify...")

    # Step 3: Verify permissions work
    print()
    print("VERIFYING SETUP...")
    print("-" * 40)

    # Test 1: Keyboard access (pynput)
    keyboard_ok = False
    try:
        from pynput import keyboard

        _test_received = []

        def _on_press(key):
            _test_received.append(True)
            return False  # Stop listener

        listener = keyboard.Listener(on_press=_on_press)
        listener.start()

        print("Please press ANY KEY on your keyboard to test...")
        listener.join(timeout=15)

        if _test_received:
            keyboard_ok = True
            print("  ✅ Keyboard access: WORKING")
        else:
            print("  ❌ Keyboard access: NOT WORKING")
            print("     Please go back and ensure Input Monitoring is enabled.")
    except Exception as e:
        print(f"  ❌ Keyboard access: FAILED — {e}")

    # Test 2: Window detection (AppleScript)
    window_ok = False
    try:
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get name of first application process whose frontmost is true'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            window_ok = True
            print(f"  ✅ Window detection: WORKING (detected: {result.stdout.strip()})")
        else:
            print("  ❌ Window detection: NOT WORKING")
            print("     Please go back and ensure Accessibility is enabled.")
    except Exception as e:
        print(f"  ❌ Window detection: FAILED — {e}")

    # Test 3: Clipboard (always works, no permission needed)
    clipboard_ok = False
    try:
        import pyperclip
        pyperclip.paste()
        clipboard_ok = True
        print("  ✅ Clipboard access: WORKING")
    except Exception:
        print("  ⚠️  Clipboard access: Could not verify (non-critical)")
        clipboard_ok = True  # pyperclip usually works fine

    print()
    if keyboard_ok and window_ok:
        print("=" * 50)
        print("✅ SETUP COMPLETE!")
        print("=" * 50)
        print("Your system is ready for the exam.")
        print("You can close this window.")
    else:
        print("=" * 50)
        print("⚠️  SETUP INCOMPLETE")
        print("=" * 50)
        print("Some permissions were not granted.")
        print("Please re-run this setup and ensure all")
        print("toggles are enabled in System Settings.")

    print()
    input("Press ENTER to exit...")


if __name__ == "__main__":
    main()
