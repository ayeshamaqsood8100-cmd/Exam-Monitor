"""
Cross-platform window detection for Markaz Sentinel.

On Windows: delegates to the real pygetwindow library.
On macOS: uses native Accessibility APIs to get the active window.

This module also patches sys.modules so existing collectors that
`import pygetwindow` will transparently use the macOS implementation
without any code changes.
"""
from dataclasses import dataclass
import platform
import sys

from . import mac_accessibility

_IS_MAC = platform.system() == "Darwin"
_IS_WINDOWS = platform.system() == "Windows"


@dataclass
class _ActiveWindow:
    """Minimal object mimicking pygetwindow's window object."""
    title: str
    app_name: str = "Unknown"
    window_title: str = "Unknown"
    tab_title: str | None = None
    tab_url: str | None = None


def get_active_window():
    """
    Returns the currently focused window as an object with a .title attribute,
    or None if detection fails. Works on both Windows and macOS.
    """
    if _IS_WINDOWS:
        return _get_active_window_windows()
    if _IS_MAC:
        return _get_active_window_mac()
    return None


def _get_active_window_windows():
    """Windows implementation using pygetwindow."""
    try:
        import pygetwindow as gw
        return gw.getActiveWindow()
    except Exception:
        return None


def _get_active_window_mac():
    """macOS implementation using native Accessibility APIs."""
    try:
        snapshot = mac_accessibility.get_front_window_snapshot()
        if snapshot is None:
            return None

        return _ActiveWindow(
            title=snapshot.title,
            app_name=snapshot.app_name,
            window_title=snapshot.window_title,
            tab_title=snapshot.page_title,
            tab_url=snapshot.page_url,
        )
    except Exception:
        return None


if _IS_MAC:
    import types

    _fake_module = types.ModuleType("pygetwindow")
    _fake_module.getActiveWindow = get_active_window  # type: ignore
    sys.modules["pygetwindow"] = _fake_module
