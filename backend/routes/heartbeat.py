from fastapi import APIRouter, Depends, HTTPException, status
from backend.models.heartbeat import HeartbeatModel
from backend.services.security import verify_api_key
from backend.services.heartbeat_service import update_heartbeat

router = APIRouter()

@router.post("/heartbeat", dependencies=[Depends(verify_api_key)])
async def process_heartbeat(payload: HeartbeatModel):
    try:
        updated = update_heartbeat(payload.session_id)

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session not found."
            )

        return {"success": True}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the heartbeat."
        )
