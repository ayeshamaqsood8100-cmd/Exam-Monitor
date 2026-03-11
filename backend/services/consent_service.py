from uuid import UUID
from datetime import datetime, timezone
from backend.services.database import db


def record_consent(session_id: UUID, agent_version: str) -> tuple[str | None, bool]:
    session_id_str = str(session_id)
    existing = (
        db.client.table("consent_logs")
        .select("id")
        .eq("session_id", session_id_str)
        .order("consented_at", desc=False)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0].get("id"), True

    response = db.client.table("consent_logs").insert({
        "session_id": session_id_str,
        "agent_version": agent_version,
        "consented_at": datetime.now(timezone.utc).isoformat()
    }).execute()

    if response.data and len(response.data) > 0:
        return response.data[0].get("id"), False
    return None, False


def get_session_access_code(session_id: UUID) -> str | None:
    response = (
        db.client.table("exam_sessions")
        .select("exams(access_code)")
        .eq("id", str(session_id))
        .limit(1)
        .execute()
    )
    if not response.data:
        return None

    exams_value = response.data[0].get("exams")
    if isinstance(exams_value, list):
        exams_value = exams_value[0] if exams_value else None
    if isinstance(exams_value, dict):
        return exams_value.get("access_code")
    return None
