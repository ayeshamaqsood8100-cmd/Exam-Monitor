from uuid import UUID
from datetime import datetime, timezone
from backend.services.database import db

def record_consent(session_id: UUID, agent_version: str) -> str | None:
    response = db.client.table("consent_logs").insert({
        "session_id": str(session_id),
        "agent_version": agent_version,
        "consented_at": datetime.now(timezone.utc).isoformat()
    }).execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0].get("id")
    return None
