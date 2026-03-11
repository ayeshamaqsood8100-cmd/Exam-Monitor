from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from backend.services.analysis.models import AnalysisFlag, RunStatus, TelemetryAnalysisRequest
from backend.services.database import db


def create_analysis_run(
    request: TelemetryAnalysisRequest,
    *,
    provider_chain: list[dict],
) -> str:
    run_id = str(uuid4())
    payload = {
        "id": run_id,
        "session_id": request.session_id,
        "exam_id": request.exam_id,
        "trigger_type": request.trigger_type.value,
        "prompt_version": request.prompt_version,
        "provider_chain": provider_chain,
        "attempts": [],
        "input_stats": request.input_stats.model_dump(mode="json"),
        "flags_inserted": 0,
        "fallback_used": False,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "error_summary": None,
    }
    db.client.table("analysis_runs").insert(payload).execute()
    return run_id


def complete_analysis_run(
    run_id: str,
    *,
    status: RunStatus,
    provider_used: str | None,
    model_used: str | None,
    fallback_used: bool,
    attempts: list[dict],
    input_stats: dict,
    flags_inserted: int,
    error_summary: str | None,
) -> None:
    payload = {
        "status": status.value,
        "provider_used": provider_used,
        "model_used": model_used,
        "fallback_used": fallback_used,
        "attempts": attempts,
        "input_stats": input_stats,
        "flags_inserted": flags_inserted,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "error_summary": error_summary,
    }
    db.client.table("analysis_runs").update(payload).eq("id", run_id).execute()


def delete_existing_ai_flags(session_id: str) -> None:
    (
        db.client.table("flagged_events")
        .delete()
        .eq("session_id", session_id)
        .not_.like("flag_type", "system_%")
        .execute()
    )


def insert_ai_flags(
    *,
    session_id: str,
    analysis_run_id: str,
    flags: list[AnalysisFlag],
) -> int:
    if not flags:
        return 0

    payload = [
        {
            "session_id": session_id,
            "analysis_run_id": analysis_run_id,
            "flag_type": flag.flag_type,
            "description": flag.description,
            "evidence": flag.evidence,
            "severity": flag.severity.value,
            "flagged_at": flag.flagged_at.astimezone(timezone.utc).isoformat(),
            "reviewed": False,
        }
        for flag in flags
    ]
    db.client.table("flagged_events").insert(payload).execute()
    return len(payload)
