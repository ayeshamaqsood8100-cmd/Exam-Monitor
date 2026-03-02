from pydantic import BaseModel, AwareDatetime
from uuid import UUID
from typing import List, Optional

class KeystrokeEntry(BaseModel):
    application: str
    key_data: str
    captured_at: AwareDatetime

class WindowEntry(BaseModel):
    window_title: str
    application_name: Optional[str] = None
    switched_at: AwareDatetime

class ClipboardEntry(BaseModel):
    event_type: str
    content: str
    source_application: Optional[str] = None
    destination_application: Optional[str] = None
    captured_at: AwareDatetime

class ProcessEntry(BaseModel):
    process_name: str
    captured_at: AwareDatetime

class OfflinePeriodEntry(BaseModel):
    disconnected_at: AwareDatetime
    reconnected_at: AwareDatetime

class TelemetrySyncModel(BaseModel):
    session_id: UUID
    sync_number: int
    synced_at: AwareDatetime
    keystrokes: List[KeystrokeEntry] = []
    windows: List[WindowEntry] = []
    clipboard: List[ClipboardEntry] = []
    processes: List[ProcessEntry] = []
    offline_periods: List[OfflinePeriodEntry] = []

