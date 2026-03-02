from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class HeartbeatModel(BaseModel):
    session_id: UUID
    timestamp: datetime

