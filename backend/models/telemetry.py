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

class OfflinePeriodEntry(BaseModel):
    disconnected_at: AwareDatetime
    reconnected_at: AwareDatetime

# Staggered sync models — one per endpoint
class KeystrokeSyncModel(BaseModel):
    session_id: UUID
    sync_number: int
    synced_at: AwareDatetime
    telemetry_sync_id: Optional[str] = None
    keystrokes: List[KeystrokeEntry] = []

class WindowSyncModel(BaseModel):
    session_id: UUID
    sync_number: int
    synced_at: AwareDatetime
    telemetry_sync_id: Optional[str] = None
    windows: List[WindowEntry] = []

class ClipboardSyncModel(BaseModel):
    session_id: UUID
    sync_number: int
    synced_at: AwareDatetime
    telemetry_sync_id: Optional[str] = None
    clipboard: List[ClipboardEntry] = []

class OfflineSyncModel(BaseModel):
    session_id: UUID
    sync_number: int
    synced_at: AwareDatetime
    telemetry_sync_id: Optional[str] = None
    offline_periods: List[OfflinePeriodEntry] = []


class SyncInitModel(BaseModel):
    session_id: UUID
    sync_number: int
    synced_at: AwareDatetime
