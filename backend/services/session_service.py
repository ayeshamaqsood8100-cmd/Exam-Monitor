from uuid import UUID
from datetime import datetime, timezone
import random
import time
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
    existing = _run_with_retry(
        lambda: db.client.table("exam_sessions").select("id, status, session_start, exam_id, exams(end_time, exam_name)").eq("id", session_id_str).execute()
    )

    if not existing.data:
        return False

    if existing.data[0].get("status") == "completed":
        return True

    now_utc = datetime.now(timezone.utc).isoformat()
    response = _run_with_retry(
        lambda: db.client.table("exam_sessions").update({
            "status": "completed",
            "session_end": now_utc
        }).eq("id", session_id_str).execute()
    )

    if source == "student":
        session_row = existing.data[0]
        exam_join = session_row.get("exams")
        if isinstance(exam_join, list):
            exam_join = exam_join[0] if exam_join else None
        exam_end_time = exam_join.get("end_time") if isinstance(exam_join, dict) else None
        if exam_end_time:
            try:
                exam_end_dt = datetime.fromisoformat(str(exam_end_time).replace("Z", "+00:00"))
                if exam_end_dt > datetime.now(timezone.utc):
                    exam_name = exam_join.get("exam_name", "Exam") if isinstance(exam_join, dict) else "Exam"
                    create_system_alert(
                        session_id_str,
                        "system_session_ended_before_exam_end",
                        "Student ended the session before the exam end time.",
                        evidence=f"{exam_name} was scheduled to end at {exam_end_dt.isoformat()} UTC.",
                        severity="MED",
                    )
            except Exception:
                pass

    return bool(response.data and len(response.data) > 0)


def pause_session(session_id: UUID) -> bool:
    session_id_str = str(session_id)
    existing = _run_with_retry(
        lambda: db.client.table("exam_sessions").select("id, status").eq("id", session_id_str).execute()
    )

    if not existing.data:
        return False

    current_status = existing.data[0].get("status")
    if current_status == "completed":
        return False

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

    now_utc = datetime.now(timezone.utc).isoformat()
    response = _run_with_retry(
        lambda: db.client.table("exam_sessions").update({
            "status": "active",
            "session_end": None,
            "last_heartbeat_at": now_utc
        }).eq("id", session_id_str).execute()
    )

    return bool(response.data and len(response.data) > 0)
