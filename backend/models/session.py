from typing import Literal
from pydantic import BaseModel
from uuid import UUID

class SessionStartModel(BaseModel):
    student_erp: str
    exam_id: UUID

class SessionEndModel(BaseModel):
    session_id: UUID
    source: Literal["student", "system", "admin"] = "system"


class SessionPauseModel(BaseModel):
    session_id: UUID


class SessionRestartModel(BaseModel):
    session_id: UUID


class SessionEventModel(BaseModel):
    session_id: UUID
    event_type: str
    description: str
    evidence: str = ""
    severity: Literal["HIGH", "MED", "LOW"] = "LOW"
