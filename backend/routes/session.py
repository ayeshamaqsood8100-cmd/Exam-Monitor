from fastapi import APIRouter, Depends, HTTPException, status
from backend.models.session import SessionStartModel, SessionEndModel
from backend.services.security import verify_api_key
from backend.services.session_service import start_session, end_session

router = APIRouter()

@router.post("/session/start", dependencies=[Depends(verify_api_key)])
async def process_session_start(payload: SessionStartModel):
    try:
        result = start_session(payload.student_erp, payload.exam_id)
        return result
        
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "Student not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        elif error_msg == "Session already active":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request.")
            
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while starting the session."
        )

@router.post("/session/end", dependencies=[Depends(verify_api_key)])
async def process_session_end(payload: SessionEndModel):
    try:
        updated = end_session(payload.session_id)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session not found."
            )
        return {"status": "ok"}
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while ending the session."
        )
