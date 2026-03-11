from fastapi import APIRouter, Depends, HTTPException, status
from backend.models.consent import ConsentModel
from backend.services.security import authorize_session_access, verify_student_agent_auth
from backend.services.consent_service import get_session_access_code, record_consent

router = APIRouter()

@router.post("/consent")
def process_consent(payload: ConsentModel, auth: dict = Depends(verify_student_agent_auth)):
    try:
        authorize_session_access(str(payload.session_id), auth)
        consent_id, _already_recorded = record_consent(payload.session_id, payload.agent_version)
        
        if not consent_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record consent in the database."
            )

        access_code = get_session_access_code(payload.session_id)

        return {"status": "ok", "access_code": access_code}
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing consent."
        )
