from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.models.session import SessionStartModel, SessionEndModel, SessionPauseModel, SessionRestartModel, SessionEventModel, ExamTerminateModel
from backend.services.security import authorize_session_access, create_student_agent_token, verify_api_key, verify_student_agent_auth
from backend.services.session_service import start_session, end_session, pause_session, restart_session, terminate_exam_sessions, TransientSessionError
from backend.services.alert_service import create_system_alert
from backend.services.database import db

router = APIRouter()

@router.post("/session/start")
def process_session_start(payload: SessionStartModel):
    try:
        result = start_session(payload.student_erp, payload.exam_id)
        result["session_token"] = create_student_agent_token(
            session_id=str(result["session_id"]),
            exam_id=str(payload.exam_id),
        )
        return result
        
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "Student not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request.")

    except TransientSessionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
            
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while starting the session."
        )

@router.post("/session/end")
def process_session_end(payload: SessionEndModel, auth: dict = Depends(verify_student_agent_auth)):
    try:
        authorize_session_access(str(payload.session_id), auth)
        updated = end_session(payload.session_id, source=payload.source)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session not found."
            )
        return {"status": "ok"}
        
    except TransientSessionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while ending the session."
        )


@router.post("/session/event")
def process_session_event(payload: SessionEventModel, auth: dict = Depends(verify_student_agent_auth)):
    try:
        authorize_session_access(str(payload.session_id), auth)
        event_type = payload.event_type.strip().lower()
        create_system_alert(
            str(payload.session_id),
            event_type if event_type.startswith("system_") else f"system_{event_type}",
            payload.description,
            evidence=payload.evidence,
            severity=payload.severity,
        )
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while recording the session event."
        )


@router.post("/session/pause")
def process_session_pause(payload: SessionPauseModel, auth: dict = Depends(verify_student_agent_auth)):
    try:
        authorize_session_access(str(payload.session_id), auth)
        updated = pause_session(payload.session_id)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session not found or can no longer be paused."
            )
        return {"status": "ok"}

    except TransientSessionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while pausing the session."
        )


@router.post("/session/restart")
def process_session_restart(payload: SessionRestartModel, auth: dict = Depends(verify_student_agent_auth)):
    try:
        authorize_session_access(str(payload.session_id), auth)
        updated = restart_session(payload.session_id)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session not found or can no longer be resumed."
            )
        return {"status": "ok"}

    except TransientSessionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while restarting the session."
        )


@router.post("/exam/terminate", dependencies=[Depends(verify_api_key)])
def process_exam_terminate(payload: ExamTerminateModel):
    try:
        terminated = terminate_exam_sessions(payload.exam_id)
        return {"status": "ok", "sessions_terminated": terminated}

    except TransientSessionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while terminating the exam."
        )


class SessionStatusModel(BaseModel):
    session_id: str

@router.post("/session/status")
def check_session_status(payload: SessionStatusModel, auth: dict = Depends(verify_student_agent_auth)):
    """Check if a session is still active (used by agent for crash recovery)."""
    try:
        authorize_session_access(str(payload.session_id), auth)
        result = db.client.table("exam_sessions").select("status").eq("id", payload.session_id).execute()
        if result.data and len(result.data) > 0:
            return {"status": result.data[0].get("status", "unknown")}
        return {"status": "not_found"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check session status."
        )

