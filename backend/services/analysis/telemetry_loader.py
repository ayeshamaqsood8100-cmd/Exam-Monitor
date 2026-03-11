from __future__ import annotations

from backend.services.analysis.models import NormalizedTelemetry, TelemetryAnalysisRequest, TriggerType
from backend.services.analysis.preprocess import (
    build_input_stats,
    build_keystroke_groups,
    normalize_clipboard_rows,
    normalize_offline_period_rows,
    normalize_window_rows,
)
from backend.services.database import db


DEFAULT_PAGE_SIZE = 2000


def list_completed_session_ids(exam_id: str) -> list[str]:
    response = (
        db.client.table("exam_sessions")
        .select("id")
        .eq("exam_id", exam_id)
        .eq("status", "completed")
        .order("session_start", desc=False)
        .execute()
    )
    return [str(row["id"]) for row in (response.data or [])]


def load_session_request(
    session_id: str,
    *,
    trigger_type: TriggerType,
    prompt_version: str,
) -> TelemetryAnalysisRequest:
    session_res = (
        db.client.table("exam_sessions")
        .select("id, exam_id, student_id, session_start, session_end")
        .eq("id", session_id)
        .single()
        .execute()
    )
    if not session_res.data:
        raise ValueError(f"Session {session_id} not found.")

    session = session_res.data
    student_res = (
        db.client.table("students")
        .select("name, erp")
        .eq("id", session["student_id"])
        .execute()
    )
    student = student_res.data[0] if student_res.data else {"name": "Unknown", "erp": "Unknown"}

    window_rows = _load_rows_keyset(
        table="window_logs",
        session_id=session_id,
        select_fields="id, switched_at, application_name, window_title",
        order_column="switched_at",
    )
    clipboard_rows = _load_rows_keyset(
        table="clipboard_logs",
        session_id=session_id,
        select_fields="id, captured_at, event_type, source_application, destination_application, content",
        order_column="captured_at",
    )
    keystroke_rows = _load_rows_keyset(
        table="keystroke_logs",
        session_id=session_id,
        select_fields="id, captured_at, application, key_data",
        order_column="captured_at",
    )
    telemetry_sync_rows = _load_telemetry_sync_rows(session_id)

    keystroke_groups = build_keystroke_groups(keystroke_rows)
    input_stats = build_input_stats(
        window_rows=window_rows,
        clipboard_rows=clipboard_rows,
        keystroke_rows=keystroke_rows,
        telemetry_sync_rows=telemetry_sync_rows,
        keystroke_groups=keystroke_groups,
    )

    return TelemetryAnalysisRequest(
        session_id=str(session["id"]),
        exam_id=str(session["exam_id"]),
        student_id=str(session["student_id"]),
        student_name=str(student.get("name", "Unknown")),
        student_erp=str(student.get("erp", "Unknown")),
        session_start=str(session["session_start"]),
        session_end=str(session.get("session_end")) if session.get("session_end") else None,
        trigger_type=trigger_type,
        prompt_version=prompt_version,
        telemetry=NormalizedTelemetry(
            windows=normalize_window_rows(window_rows),
            clipboard=normalize_clipboard_rows(clipboard_rows),
            keystrokes=keystroke_groups,
            offline_periods=normalize_offline_period_rows(telemetry_sync_rows),
        ),
        input_stats=input_stats,
    )


def _load_telemetry_sync_rows(session_id: str) -> list[dict]:
    try:
        return _load_rows_keyset(
            table="telemetry_syncs",
            session_id=session_id,
            select_fields="id, synced_at, offline_periods",
            order_column="synced_at",
        )
    except Exception:
        response = (
            db.client.table("telemetry_syncs")
            .select("id, offline_periods")
            .eq("session_id", session_id)
            .order("id", desc=False)
            .execute()
        )
        return response.data or []


def _load_rows_keyset(
    *,
    table: str,
    session_id: str,
    select_fields: str,
    order_column: str,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> list[dict]:
    rows: list[dict] = []
    cursor_value: str | None = None
    cursor_id: str | None = None

    while True:
        if cursor_value is None or cursor_id is None:
            batch = _run_base_query(
                table=table,
                session_id=session_id,
                select_fields=select_fields,
                order_column=order_column,
                limit=page_size,
            )
        else:
            same_timestamp_batch = _run_same_timestamp_query(
                table=table,
                session_id=session_id,
                select_fields=select_fields,
                order_column=order_column,
                cursor_value=cursor_value,
                cursor_id=cursor_id,
                limit=page_size,
            )
            remaining = page_size - len(same_timestamp_batch)
            later_batch: list[dict] = []
            if remaining > 0:
                later_batch = _run_later_timestamp_query(
                    table=table,
                    session_id=session_id,
                    select_fields=select_fields,
                    order_column=order_column,
                    cursor_value=cursor_value,
                    limit=remaining,
                )
            batch = same_timestamp_batch + later_batch

        if not batch:
            break

        rows.extend(batch)
        cursor_value = str(batch[-1].get(order_column))
        cursor_id = str(batch[-1].get("id"))

        if len(batch) < page_size:
            break

    return rows


def _run_base_query(
    *,
    table: str,
    session_id: str,
    select_fields: str,
    order_column: str,
    limit: int,
) -> list[dict]:
    response = (
        db.client.table(table)
        .select(select_fields)
        .eq("session_id", session_id)
        .order(order_column, desc=False)
        .order("id", desc=False)
        .limit(limit)
        .execute()
    )
    return response.data or []


def _run_same_timestamp_query(
    *,
    table: str,
    session_id: str,
    select_fields: str,
    order_column: str,
    cursor_value: str,
    cursor_id: str,
    limit: int,
) -> list[dict]:
    response = (
        db.client.table(table)
        .select(select_fields)
        .eq("session_id", session_id)
        .eq(order_column, cursor_value)
        .gt("id", cursor_id)
        .order(order_column, desc=False)
        .order("id", desc=False)
        .limit(limit)
        .execute()
    )
    return response.data or []


def _run_later_timestamp_query(
    *,
    table: str,
    session_id: str,
    select_fields: str,
    order_column: str,
    cursor_value: str,
    limit: int,
) -> list[dict]:
    response = (
        db.client.table(table)
        .select(select_fields)
        .eq("session_id", session_id)
        .gt(order_column, cursor_value)
        .order(order_column, desc=False)
        .order("id", desc=False)
        .limit(limit)
        .execute()
    )
    return response.data or []
