from fastapi import APIRouter, Depends, HTTPException, status
from backend.models.heartbeat import HeartbeatModel, HeartbeatResponseModel
from backend.services.security import authorize_session_access, verify_student_agent_auth
from backend.services.heartbeat_service import update_heartbeat

router = APIRouter()

@router.post("/heartbeat", response_model=HeartbeatResponseModel)
def process_heartbeat(payload: HeartbeatModel, auth: dict = Depends(verify_student_agent_auth)):
    try:
        authorize_session_access(str(payload.session_id), auth)
        result = update_heartbeat(payload.session_id)

        if not result["updated"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session not found."
            )

        return {"status": "ok", "force_stop": result["force_stop"]}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the heartbeat."
        )
