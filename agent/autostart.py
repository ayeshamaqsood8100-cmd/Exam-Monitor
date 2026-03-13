"""
Auto-start registration for Markaz Sentinel.

Registers the watchdog to start automatically when the student logs into
their computer, so the agent survives laptop reboots during exams.
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

if platform.system() == "Windows":
    import winreg


_WINDOWS_TASK_NAME = "MarkazSentinel"
_WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_WINDOWS_HELPER_DIR = Path(os.environ.get("APPDATA", "")) / "MarkazSentinel"
_WINDOWS_HELPER_BAT = _WINDOWS_HELPER_DIR / "launch_watchdog.bat"
_WINDOWS_HELPER_VBS = _WINDOWS_HELPER_DIR / "launch_watchdog.vbs"
_WINDOWS_STARTUP_BAT = (
    Path(os.environ.get("APPDATA", ""))
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs"
    / "Startup"
    / "MarkazSentinel.bat"
)


def _get_working_directory() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_windows_launch_command() -> str:
    return f'wscript.exe "{_WINDOWS_HELPER_VBS}"'


def _write_windows_helper() -> None:
    _WINDOWS_HELPER_DIR.mkdir(parents=True, exist_ok=True)
    cwd = _get_working_directory()
    python_path = sys.executable

    if getattr(sys, "frozen", False):
        bat_content = f'@echo off\ncd /d "{cwd}"\n"{python_path}"\n'
        vbs_run_target = f'Chr(34) & "{python_path}" & Chr(34)'
    else:
        bat_content = f'@echo off\ncd /d "{cwd}"\n"{python_path}" -m agent.watchdog\n'
        vbs_run_target = f'Chr(34) & "{python_path}" & Chr(34) & " -m agent.watchdog"'

    _WINDOWS_HELPER_BAT.write_text(bat_content, encoding="utf-8")
    vbs_content = (
        'Set shell = CreateObject("WScript.Shell")\n'
        f'shell.CurrentDirectory = "{cwd}"\n'
        f"shell.Run {vbs_run_target}, 0, False\n"
    )
    _WINDOWS_HELPER_VBS.write_text(vbs_content, encoding="utf-8")


def _verify_windows_task() -> bool:
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", _WINDOWS_TASK_NAME],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _install_windows_task() -> bool:
    result = subprocess.run(
        [
            "schtasks",
            "/Create",
            "/F",
            "/SC",
            "ONLOGON",
            "/TN",
            _WINDOWS_TASK_NAME,
            "/TR",
            _get_windows_launch_command(),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[AUTOSTART] Scheduled task creation failed: {result.stderr.strip() or result.stdout.strip()}")
        return False
    return _verify_windows_task()


def _verify_windows_run_entry() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WINDOWS_RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, _WINDOWS_TASK_NAME)
        return str(value).strip() == _get_windows_launch_command()
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"[AUTOSTART] Failed to verify HKCU Run entry: {e}")
        return False


def _install_windows_run_entry() -> bool:
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _WINDOWS_RUN_KEY) as key:
            winreg.SetValueEx(key, _WINDOWS_TASK_NAME, 0, winreg.REG_SZ, _get_windows_launch_command())
        return _verify_windows_run_entry()
    except Exception as e:
        print(f"[AUTOSTART] Failed to register HKCU Run fallback: {e}")
        return False


def _install_windows_startup_fallback() -> bool:
    try:
        _WINDOWS_STARTUP_BAT.parent.mkdir(parents=True, exist_ok=True)
        _WINDOWS_STARTUP_BAT.write_text(
            f'@echo off\nstart "" /min {_get_windows_launch_command()}\n',
            encoding="utf-8",
        )
        return _WINDOWS_STARTUP_BAT.exists()
    except Exception as e:
        print(f"[AUTOSTART] Failed to write Startup fallback: {e}")
        return False


def _remove_windows_startup_fallback() -> None:
    if _WINDOWS_STARTUP_BAT.exists():
        _WINDOWS_STARTUP_BAT.unlink()


def _install_windows() -> bool:
    try:
        _write_windows_helper()
        _remove_windows_startup_fallback()

        if _install_windows_task():
            print(f"[AUTOSTART] Registered scheduled task: {_WINDOWS_TASK_NAME}")
            return True

        if _install_windows_run_entry():
            print("[AUTOSTART] Scheduled task unavailable; registered HKCU Run fallback")
            return True

        if _install_windows_startup_fallback():
            print("[AUTOSTART] Scheduled task and Run entry unavailable; registered Startup-folder fallback")
            return True

        print("[AUTOSTART] Failed to register any verified Windows autostart mechanism.")
        return False
    except Exception as e:
        print(f"[AUTOSTART] Failed to register on Windows: {e}")
        return False


def _uninstall_windows() -> bool:
    success = True

    try:
        subprocess.run(
            ["schtasks", "/Delete", "/TN", _WINDOWS_TASK_NAME, "/F"],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as e:
        print(f"[AUTOSTART] Failed to remove scheduled task: {e}")
        success = False

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _WINDOWS_RUN_KEY) as key:
            try:
                winreg.DeleteValue(key, _WINDOWS_TASK_NAME)
            except FileNotFoundError:
                pass
    except Exception as e:
        print(f"[AUTOSTART] Failed to remove HKCU Run entry: {e}")
        success = False

    try:
        _remove_windows_startup_fallback()
        if _WINDOWS_HELPER_BAT.exists():
            _WINDOWS_HELPER_BAT.unlink()
        if _WINDOWS_HELPER_VBS.exists():
            _WINDOWS_HELPER_VBS.unlink()
        if _WINDOWS_HELPER_DIR.exists() and not any(_WINDOWS_HELPER_DIR.iterdir()):
            _WINDOWS_HELPER_DIR.rmdir()
    except Exception as e:
        print(f"[AUTOSTART] Failed to clean Windows helper files: {e}")
        success = False

    if success:
        print(f"[AUTOSTART] Removed Windows autostart: {_WINDOWS_TASK_NAME}")
    return success


_MACOS_PLIST_NAME = "com.markaz.sentinel.plist"


def _install_mac() -> bool:
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)
    plist_file = launch_agents_dir / _MACOS_PLIST_NAME

    cwd = _get_working_directory()
    python_path = sys.executable

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.markaz.sentinel</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>agent.watchdog</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{cwd}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/markaz_sentinel.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/markaz_sentinel_err.log</string>
</dict>
</plist>
"""

    try:
        plist_file.write_text(plist_content, encoding="utf-8")
        os.system(f'launchctl load -w "{plist_file}"')
        print(f"[AUTOSTART] Registered: {plist_file}")
        return True
    except Exception as e:
        print(f"[AUTOSTART] Failed to register on macOS: {e}")
        return False


def _uninstall_mac() -> bool:
    plist_file = Path.home() / "Library" / "LaunchAgents" / _MACOS_PLIST_NAME

    try:
        if plist_file.exists():
            os.system(f'launchctl unload -w "{plist_file}"')
            plist_file.unlink()
            print(f"[AUTOSTART] Removed: {plist_file}")
        return True
    except Exception as e:
        print(f"[AUTOSTART] Failed to remove on macOS: {e}")
        return False


def install() -> bool:
    system = platform.system()
    if system == "Windows":
        return _install_windows()
    if system == "Darwin":
        return _install_mac()
    print(f"[AUTOSTART] Unsupported OS: {system}")
    return False


def uninstall() -> bool:
    system = platform.system()
    if system == "Windows":
        return _uninstall_windows()
    if system == "Darwin":
        return _uninstall_mac()
    print(f"[AUTOSTART] Unsupported OS: {system}")
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("install", "uninstall"):
        print("Usage: python -m agent.autostart [install|uninstall]")
        sys.exit(1)

    action = sys.argv[1]
    success = install() if action == "install" else uninstall()
    sys.exit(0 if success else 1)
