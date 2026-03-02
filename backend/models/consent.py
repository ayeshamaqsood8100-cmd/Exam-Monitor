from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class ConsentModel(BaseModel):
    session_id: UUID
    timestamp: datetime


