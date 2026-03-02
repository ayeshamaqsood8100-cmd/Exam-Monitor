from fastapi import APIRouter, Depends, HTTPException, status
from backend.models.telemetry import TelemetrySyncModel
from backend.services.security import verify_api_key
from backend.services.telemetry_service import process_sync

router = APIRouter()

@router.post("/sync", dependencies=[Depends(verify_api_key)])
async def upload_sync(payload: TelemetrySyncModel):
    try:
        sync_id = process_sync(payload)
        return {"success": True, "telemetry_sync_id": sync_id}
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the telemetry sync."
        )
