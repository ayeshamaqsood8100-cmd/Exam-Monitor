from uuid import UUID
from datetime import datetime, timezone
from backend.services.database import db

def update_heartbeat(session_id: UUID) -> bool:
    response = db.client.table("exam_sessions").update({
        "last_heartbeat_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", str(session_id)).execute()

    if len(response.data) > 0:
        return True
    return False
