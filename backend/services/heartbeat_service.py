from uuid import UUID
from datetime import datetime, timezone

from backend.services.database import db


def update_heartbeat(session_id: UUID) -> dict:
    rpc_result = _update_heartbeat_via_rpc(session_id)
    if rpc_result is not None:
        return rpc_result

    return _update_heartbeat_legacy(session_id)


def _update_heartbeat_via_rpc(session_id: UUID) -> dict | None:
    try:
        response = db.client.rpc("process_exam_session_heartbeat", {
            "target_session_id": str(session_id),
        }).execute()
        if not response.data:
            return None

        row = response.data[0] if isinstance(response.data, list) else response.data
        if row is None:
            return None

        return {
            "updated": bool(row.get("updated", False)),
            "force_stop": bool(row.get("force_stop", False)),
        }
    except Exception:
        return None


def _update_heartbeat_legacy(session_id: UUID) -> dict:
    status_res = db.client.table("exam_sessions").select("status").eq("id", str(session_id)).execute()
    if status_res.data and len(status_res.data) > 0:
        session_status = status_res.data[0].get("status", "")
        if session_status in {"completed", "terminated"}:
            return {"updated": True, "force_stop": True}
        if session_status == "paused":
            return {"updated": True, "force_stop": False}

    update_res = db.client.table("exam_sessions").update({
        "last_heartbeat_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", str(session_id)).execute()

    if not update_res.data or len(update_res.data) == 0:
        return {"updated": False, "force_stop": False}

    select_res = db.client.table("exam_sessions").select("exams(force_stop)").eq("id", str(session_id)).execute()

    if not select_res.data or len(select_res.data) == 0:
        return {"updated": True, "force_stop": False}

    session_data = select_res.data[0]
    force_stop = False

    exams_data = session_data.get("exams")
    if exams_data:
        if isinstance(exams_data, dict):
            force_stop = bool(exams_data.get("force_stop", False))
        elif isinstance(exams_data, list) and len(exams_data) > 0:
            force_stop = bool(exams_data[0].get("force_stop", False))

    return {"updated": True, "force_stop": force_stop}
