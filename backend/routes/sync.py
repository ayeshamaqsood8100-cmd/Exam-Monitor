from fastapi import APIRouter, Depends, HTTPException, status
from backend.models.telemetry import (
    ClipboardSyncModel,
    KeystrokeSyncModel,
    OfflineSyncModel,
    SyncInitModel,
    WindowSyncModel,
)
from backend.services.security import authorize_session_access, verify_student_agent_auth
from backend.services.telemetry_service import (
    create_or_get_sync,
    insert_clipboard,
    insert_keystrokes,
    insert_offline_periods,
    insert_windows,
    update_sync_timestamp,
)

router = APIRouter()


@router.post("/sync/init")
def initialize_sync(payload: SyncInitModel, auth: dict = Depends(verify_student_agent_auth)):
    try:
        authorize_session_access(str(payload.session_id), auth)
        sync_id = create_or_get_sync(payload.session_id, payload.sync_number, payload.synced_at.isoformat())
        update_sync_timestamp(sync_id, payload.synced_at.isoformat())
        return {"success": True, "telemetry_sync_id": sync_id}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize telemetry sync."
        )

@router.post("/sync/keystrokes")
def upload_keystrokes(payload: KeystrokeSyncModel, auth: dict = Depends(verify_student_agent_auth)):
    try:
        authorize_session_access(str(payload.session_id), auth)
        sync_id = payload.telemetry_sync_id or create_or_get_sync(payload.session_id, payload.sync_number, payload.synced_at.isoformat())
        insert_keystrokes(payload.session_id, sync_id, payload.keystrokes)
        return {"success": True, "telemetry_sync_id": sync_id}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process keystrokes sync."
        )

@router.post("/sync/windows")
def upload_windows(payload: WindowSyncModel, auth: dict = Depends(verify_student_agent_auth)):
    try:
        authorize_session_access(str(payload.session_id), auth)
        sync_id = payload.telemetry_sync_id or create_or_get_sync(payload.session_id, payload.sync_number, payload.synced_at.isoformat())
        insert_windows(payload.session_id, sync_id, payload.windows)
        return {"success": True}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process windows sync."
        )

@router.post("/sync/clipboard")
def upload_clipboard(payload: ClipboardSyncModel, auth: dict = Depends(verify_student_agent_auth)):
    try:
        authorize_session_access(str(payload.session_id), auth)
        sync_id = payload.telemetry_sync_id or create_or_get_sync(payload.session_id, payload.sync_number, payload.synced_at.isoformat())
        insert_clipboard(payload.session_id, sync_id, payload.clipboard)
        return {"success": True}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process clipboard sync."
        )

@router.post("/sync/offline")
def upload_offline_periods(payload: OfflineSyncModel, auth: dict = Depends(verify_student_agent_auth)):
    try:
        authorize_session_access(str(payload.session_id), auth)
        # Ensure the parent row exists first, because update() will silently succeed if no row exists in Supabase.
        sync_id = payload.telemetry_sync_id or create_or_get_sync(payload.session_id, payload.sync_number, payload.synced_at.isoformat())
        update_sync_timestamp(sync_id, payload.synced_at.isoformat())
        insert_offline_periods(payload.session_id, payload.sync_number, payload.offline_periods)
        return {"success": True}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process offline periods sync."
        )
