from pydantic import BaseModel, AwareDatetime
from uuid import UUID

class SessionStartModel(BaseModel):
    student_erp: str
    exam_id: UUID

class SessionEndModel(BaseModel):
    session_id: UUID
    timestamp: AwareDatetime
