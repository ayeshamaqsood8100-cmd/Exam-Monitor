from uuid import UUID
from datetime import datetime, timezone
from backend.services.database import db

def update_heartbeat(session_id: UUID) -> dict:
    update_res = db.client.table("exam_sessions").update({
        "last_heartbeat_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", str(session_id)).execute()

    if not update_res.data or len(update_res.data) == 0:
        return {"updated": False, "force_stop": False}

    # Second query: fetch exactly the joined force_stop flag for this session
    select_res = db.client.table("exam_sessions").select("exams(force_stop)").eq("id", str(session_id)).execute()
    
    if not select_res.data or len(select_res.data) == 0:
        return {"updated": True, "force_stop": False}
        
    session_data = select_res.data[0]
    force_stop = False
    
    # Extract nested joined relation securely handling both Object and Array return formats
    exams_data = session_data.get("exams")
    if exams_data:
        if isinstance(exams_data, dict):
            force_stop = bool(exams_data.get("force_stop", False))
        elif isinstance(exams_data, list) and len(exams_data) > 0:
            force_stop = bool(exams_data[0].get("force_stop", False))

    return {"updated": True, "force_stop": force_stop}
