from fastapi import APIRouter, Depends, HTTPException, status
from backend.models.telemetry import (
    ClipboardSyncModel,
    KeystrokeSyncModel,
    OfflineSyncModel,
    SyncInitModel,
    WindowSyncModel,
)
from backend.services.security import verify_api_key
from backend.services.telemetry_service import (
    create_or_get_sync,
    insert_clipboard,
    insert_keystrokes,
    insert_offline_periods,
    insert_windows,
    update_sync_timestamp,
)

router = APIRouter()


@router.post("/sync/init", dependencies=[Depends(verify_api_key)])
def initialize_sync(payload: SyncInitModel):
    try:
        sync_id = create_or_get_sync(payload.session_id, payload.sync_number, payload.synced_at.isoformat())
        update_sync_timestamp(sync_id, payload.synced_at.isoformat())
        return {"success": True, "telemetry_sync_id": sync_id}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize telemetry sync."
        )

@router.post("/sync/keystrokes", dependencies=[Depends(verify_api_key)])
def upload_keystrokes(payload: KeystrokeSyncModel):
    try:
        sync_id = payload.telemetry_sync_id or create_or_get_sync(payload.session_id, payload.sync_number, payload.synced_at.isoformat())
        insert_keystrokes(payload.session_id, sync_id, payload.keystrokes)
        return {"success": True, "telemetry_sync_id": sync_id}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process keystrokes sync."
        )

@router.post("/sync/windows", dependencies=[Depends(verify_api_key)])
def upload_windows(payload: WindowSyncModel):
    try:
        sync_id = payload.telemetry_sync_id or create_or_get_sync(payload.session_id, payload.sync_number, payload.synced_at.isoformat())
        insert_windows(payload.session_id, sync_id, payload.windows)
        return {"success": True}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process windows sync."
        )

@router.post("/sync/clipboard", dependencies=[Depends(verify_api_key)])
def upload_clipboard(payload: ClipboardSyncModel):
    try:
        sync_id = payload.telemetry_sync_id or create_or_get_sync(payload.session_id, payload.sync_number, payload.synced_at.isoformat())
        insert_clipboard(payload.session_id, sync_id, payload.clipboard)
        return {"success": True}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process clipboard sync."
        )

@router.post("/sync/offline", dependencies=[Depends(verify_api_key)])
def upload_offline_periods(payload: OfflineSyncModel):
    try:
        # Ensure the parent row exists first, because update() will silently succeed if no row exists in Supabase.
        sync_id = payload.telemetry_sync_id or create_or_get_sync(payload.session_id, payload.sync_number, payload.synced_at.isoformat())
        update_sync_timestamp(sync_id, payload.synced_at.isoformat())
        insert_offline_periods(payload.session_id, payload.sync_number, payload.offline_periods)
        return {"success": True}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process offline periods sync."
        )
