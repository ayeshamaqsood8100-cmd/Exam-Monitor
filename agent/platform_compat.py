"""
Cross-platform window detection for Markaz Sentinel.

On Windows: delegates to the real pygetwindow library.
On macOS: uses AppleScript via subprocess to get the active window.

This module also patches sys.modules so existing collectors that
`import pygetwindow` will transparently use the macOS implementation
without any code changes.
"""
import platform
import sys

_IS_MAC = platform.system() == "Darwin"
_IS_WINDOWS = platform.system() == "Windows"


class _ActiveWindow:
    """Minimal object mimicking pygetwindow's window object."""
    def __init__(self, title: str):
        self.title = title


def get_active_window():
    """
    Returns the currently focused window as an object with a .title attribute,
    or None if detection fails. Works on both Windows and macOS.
    """
    if _IS_WINDOWS:
        return _get_active_window_windows()
    elif _IS_MAC:
        return _get_active_window_mac()
    else:
        # Linux or unknown — return None gracefully
        return None


def _get_active_window_windows():
    """Windows implementation using pygetwindow."""
    try:
        import pygetwindow as gw
        return gw.getActiveWindow()
    except Exception:
        return None


def _get_active_window_mac():
    """
    macOS implementation using AppleScript via subprocess.
    Gets the frontmost application name and its window title.
    No extra dependencies needed — osascript ships with every Mac.
    """
    import subprocess

    try:
        # Get the frontmost application name
        app_script = 'tell application "System Events" to get name of first application process whose frontmost is true'
        app_result = subprocess.run(
            ["osascript", "-e", app_script],
            capture_output=True, text=True, timeout=2
        )
        app_name = app_result.stdout.strip() if app_result.returncode == 0 else "Unknown"

        # Get the window title of the frontmost application
        title_script = f'''
            tell application "System Events"
                tell process "{app_name}"
                    if (count of windows) > 0 then
                        get name of front window
                    else
                        return "{app_name}"
                    end if
                end tell
            end tell
        '''
        title_result = subprocess.run(
            ["osascript", "-e", title_script],
            capture_output=True, text=True, timeout=2
        )
        window_title = title_result.stdout.strip() if title_result.returncode == 0 else app_name

        # Format like Windows: "Window Title - App Name"
        if app_name and window_title and app_name != window_title:
            full_title = f"{window_title} - {app_name}"
        else:
            full_title = window_title or app_name or "Unknown"

        return _ActiveWindow(full_title)

    except Exception:
        return None


# ---------------------------------------------------------------------------
# pygetwindow compatibility shim
# ---------------------------------------------------------------------------
# On macOS, we install a fake 'pygetwindow' module into sys.modules so that
# existing collectors which `import pygetwindow` will use our macOS
# implementation without needing any code changes.
# On Windows, pygetwindow is the real library and this shim is not needed.
# ---------------------------------------------------------------------------

if _IS_MAC:
    import types

    _fake_module = types.ModuleType("pygetwindow")
    _fake_module.getActiveWindow = get_active_window  # type: ignore
    sys.modules["pygetwindow"] = _fake_module
