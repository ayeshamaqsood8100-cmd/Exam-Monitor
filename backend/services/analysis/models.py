from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TriggerType(str, Enum):
    SINGLE_SESSION = "single_session"
    EXAM_BATCH = "exam_batch"


class RunStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    NO_DATA = "no_data"


class Severity(str, Enum):
    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"


class KeystrokeGroup(BaseModel):
    application: str
    start_at: str
    end_at: str
    text: str


class WindowEntry(BaseModel):
    id: str
    switched_at: str
    application_name: str | None = None
    window_title: str | None = None


class ClipboardEntry(BaseModel):
    id: str
    captured_at: str
    event_type: str | None = None
    source_application: str | None = None
    destination_application: str | None = None
    content: str | None = None


class OfflinePeriod(BaseModel):
    start: str | None = None
    end: str | None = None
    duration_seconds: int | float | None = None
    synced_at: str | None = None


class TelemetryInputStats(BaseModel):
    window_rows: int = 0
    clipboard_rows: int = 0
    keystroke_rows: int = 0
    telemetry_sync_rows: int = 0
    keystroke_groups: int = 0
    chunk_count: int = 0
    empty_telemetry: bool = False


class NormalizedTelemetry(BaseModel):
    windows: list[WindowEntry] = Field(default_factory=list)
    clipboard: list[ClipboardEntry] = Field(default_factory=list)
    keystrokes: list[KeystrokeGroup] = Field(default_factory=list)
    offline_periods: list[OfflinePeriod] = Field(default_factory=list)


class TelemetryAnalysisRequest(BaseModel):
    session_id: str
    exam_id: str
    student_id: str
    student_name: str
    student_erp: str
    session_start: str
    session_end: str | None = None
    trigger_type: TriggerType
    prompt_version: str
    telemetry: NormalizedTelemetry
    input_stats: TelemetryInputStats


class PromptChunk(BaseModel):
    index: int
    total: int
    window_start: str | None = None
    window_end: str | None = None
    window_lines: list[str] = Field(default_factory=list)
    clipboard_lines: list[str] = Field(default_factory=list)
    keystroke_lines: list[str] = Field(default_factory=list)
    offline_lines: list[str] = Field(default_factory=list)


class AnalysisFlag(BaseModel):
    flag_type: str
    description: str
    evidence: str
    severity: Severity
    flagged_at: datetime


class ProviderAttemptRecord(BaseModel):
    provider: str
    model: str
    attempted_at: str
    outcome: str
    latency_ms: int
    chunk_count: int
    http_status: int | None = None
    request_id: str | None = None
    error_reason: str | None = None


class ProviderExecutionResult(BaseModel):
    provider_used: str
    model_used: str
    fallback_used: bool
    attempts: list[ProviderAttemptRecord]
    flags: list[AnalysisFlag]
