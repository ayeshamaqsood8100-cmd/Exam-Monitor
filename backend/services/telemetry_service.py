from backend.services.database import db
from backend.models.telemetry import TelemetrySyncModel

def process_sync(payload: TelemetrySyncModel) -> str:
    # 1. Serialize offline_periods list of Pydantic models to a list of dicts for JSONB storage
    offline_periods_json = [period.model_dump(mode="json") for period in payload.offline_periods]
    
    # 2. Insert main telemetry_sync record
    sync_insert = db.client.table("telemetry_syncs").insert({
        "session_id": str(payload.session_id),
        "sync_number": payload.sync_number,
        "synced_at": payload.synced_at.isoformat(),
        "offline_periods": offline_periods_json
    }).execute()
    
    if not sync_insert.data:
        raise Exception("Failed to insert telemetry sync record")
        
    sync_id = sync_insert.data[0]["id"]
    session_id_str = str(payload.session_id)
    
    # 3. Bulk insert Keystrokes
    if payload.keystrokes:
        keystroke_rows = [
            {
                "session_id": session_id_str,
                "telemetry_sync_id": sync_id,
                "application": k.application,
                "key_data": k.key_data,
                "captured_at": k.captured_at.isoformat()
            } for k in payload.keystrokes
        ]
        db.client.table("keystroke_logs").insert(keystroke_rows).execute()
        
    # 4. Bulk insert Windows
    if payload.windows:
        window_rows = [
            {
                "session_id": session_id_str,
                "telemetry_sync_id": sync_id,
                "window_title": w.window_title,
                "application_name": w.application_name,
                "switched_at": w.switched_at.isoformat()
            } for w in payload.windows
        ]
        db.client.table("window_logs").insert(window_rows).execute()
        
    # 5. Bulk insert Clipboard
    if payload.clipboard:
        clipboard_rows = [
            {
                "session_id": session_id_str,
                "telemetry_sync_id": sync_id,
                "event_type": c.event_type,
                "content": c.content,
                "source_application": c.source_application,
                "destination_application": c.destination_application,
                "captured_at": c.captured_at.isoformat()
            } for c in payload.clipboard
        ]
        db.client.table("clipboard_logs").insert(clipboard_rows).execute()
        
    # 6. Bulk insert Processes
    if payload.processes:
        process_rows = [
            {
                "session_id": session_id_str,
                "telemetry_sync_id": sync_id,
                "process_name": p.process_name,
                "captured_at": p.captured_at.isoformat()
            } for p in payload.processes
        ]
        db.client.table("process_logs").insert(process_rows).execute()

    return sync_id
