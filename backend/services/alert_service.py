from datetime import datetime, timezone
from typing import Iterable

from backend.services.database import db


SYSTEM_ALERT_PREFIX = "system_"


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

    db.client.table("flagged_events").insert({
        "session_id": session_id,
        "flag_type": flag_type,
        "description": description,
        "evidence": evidence,
        "severity": severity,
        "flagged_at": datetime.now(timezone.utc).isoformat(),
        "reviewed": False,
    }).execute()


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
