from uuid import UUID
from datetime import datetime, timezone
import random
import time
import threading
from backend.services.database import db
from backend.services.alert_service import create_system_alert


TRANSIENT_ERROR_MARKERS = (
    "timeout",
    "timed out",
    "connection",
    "temporarily unavailable",
    "too many requests",
    "rate limit",
    "gateway",
    "connection pool",
)


class TransientSessionError(RuntimeError):
    pass


def _is_transient_error(exc: Exception) -> bool:
    return any(marker in str(exc).lower() for marker in TRANSIENT_ERROR_MARKERS)


def _run_with_retry(operation, attempts: int = 3):
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return operation()
        except Exception as exc:
            last_exc = exc
            if not _is_transient_error(exc) or attempt == attempts - 1:
                break
            time.sleep((0.25 * (2 ** attempt)) + random.uniform(0.0, 0.2))

    if last_exc and _is_transient_error(last_exc):
        raise TransientSessionError("Supabase is temporarily unavailable. Please retry the session request.") from last_exc
    if last_exc:
        raise last_exc
    raise RuntimeError("Session operation failed unexpectedly.")


def start_session(student_erp: str, exam_id: UUID) -> dict:
    # 1. Look up student by ERP
    student_response = _run_with_retry(
        lambda: db.client.table("students").select("id, name").eq("erp", student_erp).execute()
    )
    if not student_response.data:
        raise ValueError("Student not found")
    
    student_id = student_response.data[0]["id"]
    student_name = student_response.data[0].get("name", "Unknown Student")
    now_utc = datetime.now(timezone.utc).isoformat()
    
    # 2. Check for existing session
    session_response = _run_with_retry(
        lambda: db.client.table("exam_sessions").select("id, status").eq("student_id", student_id).eq("exam_id", str(exam_id)).execute()
    )
    
    if session_response.data:
        existing_session = session_response.data[0]
        if existing_session["status"] == "active":
            # Treat duplicate starts as idempotent so brief retry storms do not fail the student.
            return {"session_id": existing_session["id"], "student_id": student_id, "student_name": student_name}

        if existing_session["status"] == "terminated":
            raise ValueError("Session terminated; reinstall required.")

        # 3. Reactivate existing completed/abandoned session
        _run_with_retry(
            lambda: db.client.table("exam_sessions").update({
                "status": "active",
                "session_start": now_utc,
                "session_end": None,
                "last_heartbeat_at": now_utc
            }).eq("id", existing_session["id"]).execute()
        )
        return {"session_id": existing_session["id"], "student_id": student_id, "student_name": student_name}
            
    # 4. Insert entirely new session
    try:
        insert_res = _run_with_retry(
            lambda: db.client.table("exam_sessions").insert({
                "student_id": student_id,
                "exam_id": str(exam_id),
                "status": "active",
                "session_start": now_utc,
                "last_heartbeat_at": now_utc
            }).execute()
        )
    except Exception:
        # If another concurrent request won the insert race, return that session instead of failing.
        recovery = _run_with_retry(
            lambda: db.client.table("exam_sessions").select("id, status").eq("student_id", student_id).eq("exam_id", str(exam_id)).execute()
        )
        if recovery.data:
            existing_session = recovery.data[0]
            if existing_session["status"] == "terminated":
                raise ValueError("Session terminated; reinstall required.")
            if existing_session["status"] != "active":
                _run_with_retry(
                    lambda: db.client.table("exam_sessions").update({
                        "status": "active",
                        "session_start": now_utc,
                        "session_end": None,
                        "last_heartbeat_at": now_utc
                    }).eq("id", existing_session["id"]).execute()
                )
            return {"session_id": existing_session["id"], "student_id": student_id, "student_name": student_name}
        raise
    
    new_session_id = insert_res.data[0]["id"]
    return {"session_id": new_session_id, "student_id": student_id, "student_name": student_name}

def end_session(session_id: UUID, source: str = "system") -> bool:
    session_id_str = str(session_id)
    select_fields = "id, status"
    if source == "student":
        select_fields = "id, status, exams(end_time, exam_name)"

    existing = _run_with_retry(
        lambda: db.client.table("exam_sessions").select(select_fields).eq("id", session_id_str).execute()
    )

    if not existing.data:
        return False

    if existing.data[0].get("status") in {"completed", "terminated"}:
        return True

    now_utc = datetime.now(timezone.utc).isoformat()
    final_status = "completed" if source == "student" else "terminated"
    response = _run_with_retry(
        lambda: db.client.table("exam_sessions").update({
            "status": final_status,
            "session_end": now_utc
        }).eq("id", session_id_str).execute()
    )

    if source == "student":
        threading.Thread(
            target=_record_end_timing_alert,
            args=(session_id_str, existing.data[0]),
            daemon=True,
        ).start()

    return bool(response.data and len(response.data) > 0)


def pause_session(session_id: UUID) -> bool:
    session_id_str = str(session_id)
    existing = _run_with_retry(
        lambda: db.client.table("exam_sessions").select("id, status").eq("id", session_id_str).execute()
    )

    if not existing.data:
        return False

    current_status = existing.data[0].get("status")
    if current_status in {"completed", "terminated"}:
        return False
    if current_status == "paused":
        return True

    now_utc = datetime.now(timezone.utc).isoformat()
    response = _run_with_retry(
        lambda: db.client.table("exam_sessions").update({
            "status": "paused",
            "last_heartbeat_at": now_utc
        }).eq("id", session_id_str).execute()
    )

    return bool(response.data and len(response.data) > 0)


def restart_session(session_id: UUID) -> bool:
    session_id_str = str(session_id)
    existing = _run_with_retry(
        lambda: db.client.table("exam_sessions").select("id, status").eq("id", session_id_str).execute()
    )

    if not existing.data:
        return False

    current_status = existing.data[0].get("status")
    if current_status == "terminated":
        return False
    if current_status == "active":
        return True

    now_utc = datetime.now(timezone.utc).isoformat()
    response = _run_with_retry(
        lambda: db.client.table("exam_sessions").update({
            "status": "active",
            "session_end": None,
            "last_heartbeat_at": now_utc
        }).eq("id", session_id_str).execute()
    )

    return bool(response.data and len(response.data) > 0)


def _record_end_timing_alert(session_id_str: str, session_row: dict) -> None:
    try:
        exam_join = session_row.get("exams")
        if isinstance(exam_join, list):
            exam_join = exam_join[0] if exam_join else None

        exam_end_time = exam_join.get("end_time") if isinstance(exam_join, dict) else None
        if not exam_end_time:
            return

        exam_end_dt = datetime.fromisoformat(str(exam_end_time).replace("Z", "+00:00"))
        if exam_end_dt.tzinfo is None:
            exam_end_dt = exam_end_dt.replace(tzinfo=timezone.utc)

        now_dt = datetime.now(timezone.utc)
        exam_name = exam_join.get("exam_name", "Exam") if isinstance(exam_join, dict) else "Exam"

        if exam_end_dt > now_dt:
            create_system_alert(
                session_id_str,
                "system_session_ended_before_exam_end",
                "Student ended the session before the exam end time.",
                evidence=f"{exam_name} was scheduled to end at {exam_end_dt.isoformat()} UTC.",
                severity="MED",
            )
        elif exam_end_dt < now_dt:
            create_system_alert(
                session_id_str,
                "system_session_ended_after_exam_end",
                "Student ended the session after the exam end time.",
                evidence=f"{exam_name} was scheduled to end at {exam_end_dt.isoformat()} UTC.",
                severity="LOW",
            )
    except Exception:
        pass



def terminate_exam_sessions(exam_id: UUID) -> int:
    exam_id_str = str(exam_id)
    now_utc = datetime.now(timezone.utc).isoformat()

    _run_with_retry(
        lambda: db.client.table("exams").update({"force_stop": True}).eq("id", exam_id_str).execute()
    )

    response = _run_with_retry(
        lambda: db.client.table("exam_sessions").update({"status": "terminated", "session_end": now_utc}).eq("exam_id", exam_id_str).neq("status", "terminated").execute()
    )
    return len(response.data or [])
