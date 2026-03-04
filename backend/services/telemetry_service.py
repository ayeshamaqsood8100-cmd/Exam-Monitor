from typing import List
from uuid import UUID
from backend.services.database import db
from backend.models.telemetry import (
    KeystrokeEntry, WindowEntry, ClipboardEntry, OfflinePeriodEntry
)

def create_or_get_sync(session_id: UUID, sync_number: int, synced_at: str) -> str:
    session_id_str = str(session_id)
    
    # Check if row already exists
    response = db.client.table("telemetry_syncs").select("id").eq("session_id", session_id_str).eq("sync_number", sync_number).execute()
    if response.data:
        return response.data[0]["id"]
        
    # Try to insert — if duplicate crash, fetch the winner's row
    try:
        insert_res = db.client.table("telemetry_syncs").insert({
            "session_id": session_id_str,
            "sync_number": sync_number,
            "synced_at": synced_at,
            "offline_periods": []
        }).execute()
        if insert_res.data:
            return insert_res.data[0]["id"]
    except Exception:
        pass
        
    # If insert failed due to race, fetch the row the winning thread created
    retry = db.client.table("telemetry_syncs").select("id").eq("session_id", session_id_str).eq("sync_number", sync_number).execute()
    if retry.data:
        return retry.data[0]["id"]
        
    raise Exception("Failed to create or retrieve telemetry sync record")


def insert_keystrokes(session_id: UUID, sync_id: str, keystrokes: List[KeystrokeEntry]) -> None:
    if not keystrokes:
        return
        
    session_id_str = str(session_id)
    keystroke_rows = [
        {
            "session_id": session_id_str,
            "telemetry_sync_id": sync_id,
            "application": k.application,
            "key_data": k.key_data,
            "captured_at": k.captured_at.isoformat()
        } for k in keystrokes
    ]
    db.client.table("keystroke_logs").insert(keystroke_rows).execute()


def insert_windows(session_id: UUID, sync_id: str, windows: List[WindowEntry]) -> None:
    if not windows:
        return
        
    session_id_str = str(session_id)
    window_rows = [
        {
            "session_id": session_id_str,
            "telemetry_sync_id": sync_id,
            "window_title": w.window_title,
            "application_name": w.application_name,
            "switched_at": w.switched_at.isoformat()
        } for w in windows
    ]
    db.client.table("window_logs").insert(window_rows).execute()


def insert_clipboard(session_id: UUID, sync_id: str, clipboard: List[ClipboardEntry]) -> None:
    if not clipboard:
        return
        
    session_id_str = str(session_id)
    clipboard_rows = [
        {
            "session_id": session_id_str,
            "telemetry_sync_id": sync_id,
            "event_type": c.event_type,
            "content": c.content,
            "source_application": c.source_application,
            "destination_application": c.destination_application,
            "captured_at": c.captured_at.isoformat()
        } for c in clipboard
    ]
    db.client.table("clipboard_logs").insert(clipboard_rows).execute()


def insert_offline_periods(session_id: UUID, sync_number: int, offline_periods: List[OfflinePeriodEntry]) -> None:
    if not offline_periods:
        return
        
    offline_periods_json = [period.model_dump(mode="json") for period in offline_periods]
    db.client.table("telemetry_syncs").update({
        "offline_periods": offline_periods_json
    }).eq("session_id", str(session_id)).eq("sync_number", sync_number).execute()
