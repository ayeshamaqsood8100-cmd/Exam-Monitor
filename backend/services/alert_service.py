import json
from datetime import datetime, timezone
from typing import Iterable

from backend.services.database import db


SYSTEM_ALERT_PREFIX = "system_"
MAX_OCCURRENCE_HISTORY = 10


def _load_alert_meta(evidence: str) -> tuple[dict, str]:
    if not evidence:
        return {}, ""

    try:
        parsed = json.loads(evidence)
    except json.JSONDecodeError:
        return {}, evidence

    if not isinstance(parsed, dict):
        return {}, evidence

    raw_evidence = parsed.get("raw_evidence", "")
    if not isinstance(raw_evidence, str):
        raw_evidence = evidence

    return parsed, raw_evidence


def _build_evidence_payload(
    *,
    existing_evidence: str,
    description: str,
    new_evidence: str,
    flagged_at: str,
) -> str:
    meta, raw_evidence = _load_alert_meta(existing_evidence)
    previous_count = meta.get("occurrence_count", 0)
    if not isinstance(previous_count, int) or previous_count < 0:
        previous_count = 0

    first_seen_at = meta.get("first_seen_at", flagged_at)
    if not isinstance(first_seen_at, str) or not first_seen_at:
        first_seen_at = flagged_at

    existing_occurrences = meta.get("occurrences", [])
    if not isinstance(existing_occurrences, list):
        existing_occurrences = []

    occurrence = {
        "at": flagged_at,
        "description": description,
        "evidence": new_evidence,
    }
    trimmed_occurrences = (existing_occurrences + [occurrence])[-MAX_OCCURRENCE_HISTORY:]

    payload = {
        "raw_evidence": new_evidence or raw_evidence,
        "occurrence_count": previous_count + 1,
        "first_seen_at": first_seen_at,
        "last_seen_at": flagged_at,
        "occurrences": trimmed_occurrences,
    }
    return json.dumps(payload)


def create_system_alert(
    session_id: str,
    flag_type: str,
    description: str,
    *,
    evidence: str = "",
    severity: str = "LOW",
) -> None:
    if not flag_type.startswith(SYSTEM_ALERT_PREFIX):
        raise ValueError("System alert flag_type must start with 'system_'.")

    flagged_at = datetime.now(timezone.utc).isoformat()
    existing = (
        db.client.table("flagged_events")
        .select("id, evidence")
        .eq("session_id", session_id)
        .eq("flag_type", flag_type)
        .order("flagged_at", desc=True)
        .execute()
    )

    rows = existing.data or []
    existing_evidence = rows[0].get("evidence", "") if rows else ""
    payload = {
        "session_id": session_id,
        "flag_type": flag_type,
        "description": description,
        "evidence": _build_evidence_payload(
            existing_evidence=existing_evidence,
            description=description,
            new_evidence=evidence,
            flagged_at=flagged_at,
        ),
        "severity": severity,
        "flagged_at": flagged_at,
        "reviewed": False,
    }

    if rows:
        keep_id = rows[0]["id"]
        db.client.table("flagged_events").update(payload).eq("id", keep_id).execute()
        extra_ids = [extra["id"] for extra in rows[1:] if extra.get("id")]
        if extra_ids:
            db.client.table("flagged_events").delete().in_("id", extra_ids).execute()
        return

    db.client.table("flagged_events").insert(payload).execute()


def get_existing_system_alerts(session_id: str) -> list[dict]:
    response = (
        db.client.table("flagged_events")
        .select("session_id, flag_type, description, evidence, severity, flagged_at, reviewed")
        .eq("session_id", session_id)
        .like("flag_type", f"{SYSTEM_ALERT_PREFIX}%")
        .execute()
    )
    return response.data or []


def restore_system_alerts(alerts: Iterable[dict]) -> None:
    rows = list(alerts)
    if not rows:
        return
    db.client.table("flagged_events").insert(rows).execute()
