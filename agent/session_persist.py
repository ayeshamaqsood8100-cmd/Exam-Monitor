"""
Session persistence for Markaz Sentinel.

Saves the active session_id to a local JSON file so the agent can
resume the same session after a crash, kill, or laptop reboot.
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any

import httpx

from .config import settings

_SESSION_FILE = Path.home() / ".markaz_session.json"


def save_session(
    session_id: str,
    erp: str,
    student_name: str,
    *,
    consent_recorded: bool = False,
    access_code: str | None = None,
) -> None:
    data = {
        "session_id": session_id,
        "erp": erp,
        "student_name": student_name,
        "exam_id": settings.EXAM_ID,
        "consent_recorded": consent_recorded,
        "access_code": access_code,
    }
    try:
        _SESSION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[PERSIST] Warning: could not save session file - {e}")


def load_session() -> Optional[Dict[str, Any]]:
    if not _SESSION_FILE.exists():
        return None
    try:
        data = json.loads(_SESSION_FILE.read_text(encoding="utf-8"))
        if data.get("session_id") and data.get("erp") and data.get("exam_id"):
            data.setdefault("student_name", "Student")
            data.setdefault("consent_recorded", False)
            data.setdefault("access_code", None)
            return data
        return None
    except Exception:
        return None


def update_session_metadata(*, consent_recorded: bool | None = None, access_code: str | None = None) -> None:
    data = load_session()
    if not data:
        return

    if consent_recorded is not None:
        data["consent_recorded"] = consent_recorded
    if access_code is not None or "access_code" not in data:
        data["access_code"] = access_code

    try:
        _SESSION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[PERSIST] Warning: could not update session file - {e}")


def clear_session() -> None:
    try:
        if _SESSION_FILE.exists():
            _SESSION_FILE.unlink()
    except Exception as e:
        print(f"[PERSIST] Warning: could not delete session file - {e}")


def check_session_active(session_id: str) -> bool:
    try:
        url = f"{settings.BACKEND_URL.rstrip('/')}/session/status"
        headers = {
            "X-API-Key": settings.BACKEND_API_KEY,
            "Content-Type": "application/json"
        }
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json={"session_id": session_id})

        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "")
            return status in {"active", "paused"}
        return False
    except Exception:
        return True
