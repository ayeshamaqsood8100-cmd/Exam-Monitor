"""
Native macOS Accessibility helpers for Markaz Sentinel.

This module avoids AppleScript browser automation during the exam. Instead, it
reads the frontmost application and focused window through the Accessibility
API, then scans the focused window for web/document metadata when available.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import platform
from typing import Any


_IS_MAC = platform.system() == "Darwin"
_HAS_RUNTIME = False

if _IS_MAC:
    try:
        from AppKit import NSWorkspace
        from ApplicationServices import (
            AXIsProcessTrusted,
            AXIsProcessTrustedWithOptions,
            AXUIElementCopyAttributeValue,
            AXUIElementCreateApplication,
        )
        _HAS_RUNTIME = True
    except Exception:
        _HAS_RUNTIME = False


@dataclass
class MacWindowSnapshot:
    app_name: str
    window_title: str
    page_title: str | None = None
    page_url: str | None = None

    @property
    def title(self) -> str:
        best = self.page_title or self.window_title or self.app_name or "Unknown"
        if self.app_name and best and best.lower() != self.app_name.lower():
            return f"{best} - {self.app_name}"
        return best or self.app_name or "Unknown"


def is_runtime_available() -> bool:
    return _HAS_RUNTIME


def is_accessibility_trusted() -> bool:
    if not _HAS_RUNTIME:
        return False
    try:
        return bool(AXIsProcessTrusted())
    except Exception:
        return False


def request_accessibility_permission() -> bool:
    if not _HAS_RUNTIME:
        return False
    try:
        return bool(AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": True}))
    except Exception:
        return is_accessibility_trusted()


def get_front_window_snapshot() -> MacWindowSnapshot | None:
    if not _HAS_RUNTIME:
        return None

    try:
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return None

        app_name = str(app.localizedName() or "Unknown")
        pid = int(app.processIdentifier())
        app_element = AXUIElementCreateApplication(pid)

        focused_window = _copy_attribute(app_element, "AXFocusedWindow")
        window_title = _coerce_text(_copy_attribute(focused_window, "AXTitle")) if focused_window is not None else None
        metadata = _extract_window_metadata(focused_window, app_name)

        return MacWindowSnapshot(
            app_name=app_name or "Unknown",
            window_title=(window_title or app_name or "Unknown").strip(),
            page_title=metadata.get("page_title"),
            page_url=metadata.get("page_url"),
        )
    except Exception:
        return None


def _extract_window_metadata(window_element: Any, app_name: str) -> dict[str, str | None]:
    if window_element is None:
        return {"page_title": None, "page_url": None}

    queue = deque([(window_element, 0)])
    visited: set[int] = set()
    best_page_title: str | None = None
    best_page_url: str | None = None
    fallback_title: str | None = None
    nodes_seen = 0

    while queue and nodes_seen < 120:
        element, depth = queue.popleft()
        if element is None:
            continue

        object_id = id(element)
        if object_id in visited:
            continue
        visited.add(object_id)
        nodes_seen += 1

        role = _coerce_text(_copy_attribute(element, "AXRole")) or ""
        title = _clean_candidate(_copy_attribute(element, "AXTitle"), app_name)
        description = _clean_candidate(_copy_attribute(element, "AXDescription"), app_name)
        value = _clean_candidate(_copy_attribute(element, "AXValue"), app_name)
        document = _coerce_text(_copy_attribute(element, "AXDocument"))
        url = _coerce_text(_copy_attribute(element, "AXURL"))

        if role == "AXWebArea":
            if title and not best_page_title:
                best_page_title = title
            if document and not best_page_url:
                best_page_url = document
            elif url and not best_page_url:
                best_page_url = url

        if not fallback_title:
            fallback_title = title or description or value

        if depth >= 4:
            continue

        for attr_name in ("AXChildren", "AXTabs", "AXContents", "AXVisibleChildren", "AXSelectedChildren"):
            children = _copy_attribute(element, attr_name)
            if isinstance(children, (list, tuple)):
                for child in children:
                    queue.append((child, depth + 1))

    return {
        "page_title": best_page_title or fallback_title,
        "page_url": best_page_url,
    }


def _copy_attribute(element: Any, attribute: str) -> Any:
    if element is None or not _HAS_RUNTIME:
        return None

    try:
        result = AXUIElementCopyAttributeValue(element, attribute, None)
    except Exception:
        return None

    if not isinstance(result, tuple) or len(result) != 2:
        return None

    error_code, value = result
    if error_code != 0:
        return None

    return value


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None

    try:
        text = str(value).strip()
    except Exception:
        return None

    return text or None


def _clean_candidate(value: Any, app_name: str) -> str | None:
    text = _coerce_text(value)
    if not text:
        return None

    lowered = text.lower()
    if lowered == app_name.lower():
        return None
    if lowered.startswith("ax") and " " not in text:
        return None

    return text
