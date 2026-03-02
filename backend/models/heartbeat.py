from pydantic import BaseModel, AwareDatetime
from uuid import UUID

class HeartbeatModel(BaseModel):
    session_id: UUID
    timestamp: AwareDatetime
