from pydantic import BaseModel, AwareDatetime
from uuid import UUID

class HeartbeatModel(BaseModel):
    session_id: UUID
    timestamp: AwareDatetime

class HeartbeatResponseModel(BaseModel):
    status: str
    force_stop: bool
