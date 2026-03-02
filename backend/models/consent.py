from pydantic import BaseModel, AwareDatetime
from uuid import UUID

class ConsentModel(BaseModel):
    session_id: UUID
    agent_version: str
    timestamp: AwareDatetime
