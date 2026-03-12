from __future__ import annotations

from datetime import datetime, timezone

from backend.services.analysis.models import (
    ClipboardEntry,
    KeystrokeGroup,
    OfflinePeriod,
    TelemetryInputStats,
    WindowEntry,
)


IGNORED_KEYS = {
    "Key.shift", "Key.shift_r", "Key.shift_l",
    "Key.ctrl", "Key.ctrl_l", "Key.ctrl_r",
    "Key.alt", "Key.alt_l", "Key.alt_r", "Key.alt_gr",
    "Key.caps_lock",
    "Key.cmd", "Key.cmd_r", "Key.cmd_l",
    "Key.up", "Key.down", "Key.left", "Key.right",
    "Key.f1", "Key.f2", "Key.f3", "Key.f4", "Key.f5", "Key.f6",
    "Key.f7", "Key.f8", "Key.f9", "Key.f10", "Key.f11", "Key.f12",
}


def normalize_app_name(app: str | None) -> str:
    if not app:
        return "Unknown"

    lower = app.lower()
    if "google chrome" in lower or "chrome" in lower:
        return "Chrome"
    if "microsoft edge" in lower or "edge" in lower:
        return "Edge"
    if "firefox" in lower:
        return "Firefox"
    if "excel" in lower:
        return "Excel"
    if "word" in lower:
        return "Word"
    if "whatsapp" in lower:
        return "WhatsApp"
    if "notepad" in lower:
        return "Notepad"
    if "visual studio code" in lower or lower == "code":
        return "VS Code"
    return app


def parse_key_data(raw: str | None) -> str:
    if not raw:
        return ""

    if raw == "Key.space":
        return " "
    if raw == "Key.enter":
        return "[ENTER]"
    if raw == "Key.backspace":
        return "[BS]"
    if raw == "Key.tab":
        return "[TAB]"
    if raw == "Key.delete":
        return "[DEL]"
    if raw == "Key.esc":
        return "[ESC]"

    if raw in IGNORED_KEYS or raw.startswith("Key."):
        return ""

    processed = raw
    if len(processed) == 3 and processed.startswith("'") and processed.endswith("'"):
        processed = processed[1]

    if len(processed) == 1 and (ord(processed) < 32 or ord(processed) > 126):
        return ""

    return processed


def apply_backspaces(texts: list[str]) -> list[str]:
    result: list[str] = []
    for char in texts:
        if char == "[BS]":
            if result:
                result.pop()
        else:
            result.append(char)
    return result


def build_keystroke_groups(rows: list[dict]) -> list[KeystrokeGroup]:
    if not rows:
        return []

    groups: list[KeystrokeGroup] = []
    current_app = normalize_app_name(rows[0].get("application"))
    start_timestamp = rows[0].get("captured_at")
    end_timestamp = rows[0].get("captured_at")
    current_texts: list[str] = []

    initial_parsed = parse_key_data(rows[0].get("key_data"))
    if initial_parsed:
        current_texts.append(initial_parsed)

    for row in rows[1:]:
        normalized_app = normalize_app_name(row.get("application"))
        parsed = parse_key_data(row.get("key_data"))

        if normalized_app == current_app:
            end_timestamp = row.get("captured_at")
            if parsed:
                current_texts.append(parsed)
            continue

        joined_text = "".join(apply_backspaces(current_texts))
        if joined_text.strip():
            groups.append(
                KeystrokeGroup(
                    application=current_app,
                    start_at=str(start_timestamp),
                    end_at=str(end_timestamp),
                    text=joined_text,
                )
            )

        current_app = normalized_app
        start_timestamp = row.get("captured_at")
        end_timestamp = row.get("captured_at")
        current_texts = [parsed] if parsed else []

    final_joined_text = "".join(apply_backspaces(current_texts))
    if final_joined_text.strip():
        groups.append(
            KeystrokeGroup(
                application=current_app,
                start_at=str(start_timestamp),
                end_at=str(end_timestamp),
                text=final_joined_text,
            )
        )

    return groups


def normalize_window_rows(rows: list[dict]) -> list[WindowEntry]:
    return [
        WindowEntry(
            id=str(row.get("id")),
            switched_at=str(row.get("switched_at")),
            application_name=normalize_app_name(row.get("application_name")),
            window_title=row.get("window_title"),
        )
        for row in rows
    ]


def normalize_clipboard_rows(rows: list[dict]) -> list[ClipboardEntry]:
    return [
        ClipboardEntry(
            id=str(row.get("id")),
            captured_at=str(row.get("captured_at")),
            event_type=row.get("event_type"),
            source_application=normalize_app_name(row.get("source_application")),
            destination_application=normalize_app_name(row.get("destination_application")),
            content=row.get("content"),
        )
        for row in rows
    ]


def normalize_offline_period_rows(rows: list[dict]) -> list[OfflinePeriod]:
    periods: list[OfflinePeriod] = []
    for row in rows:
        synced_at = str(row.get("synced_at")) if row.get("synced_at") else None
        for period in row.get("offline_periods") or []:
            start = period.get("start") or period.get("disconnected_at")
            end = period.get("end") or period.get("reconnected_at")
            duration_seconds = period.get("duration_seconds")
            if duration_seconds is None:
                duration_seconds = _compute_offline_duration_seconds(start, end)
            periods.append(
                OfflinePeriod(
                    start=start,
                    end=end,
                    duration_seconds=duration_seconds,
                    synced_at=synced_at,
                )
            )
    return periods


def build_input_stats(
    *,
    window_rows: list[dict],
    clipboard_rows: list[dict],
    keystroke_rows: list[dict],
    telemetry_sync_rows: list[dict],
    keystroke_groups: list[KeystrokeGroup],
) -> TelemetryInputStats:
    total_events = len(window_rows) + len(clipboard_rows) + len(keystroke_rows) + len(telemetry_sync_rows)
    return TelemetryInputStats(
        window_rows=len(window_rows),
        clipboard_rows=len(clipboard_rows),
        keystroke_rows=len(keystroke_rows),
        telemetry_sync_rows=len(telemetry_sync_rows),
        keystroke_groups=len(keystroke_groups),
        empty_telemetry=total_events == 0,
    )


def _compute_offline_duration_seconds(start: str | None, end: str | None) -> int | None:
    if not start or not end:
        return None

    try:
        start_dt = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
    except ValueError:
        return None

    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)

    duration = int((end_dt - start_dt).total_seconds())
    return max(duration, 0)
