from fastapi import APIRouter, Depends, HTTPException, status
from backend.models.consent import ConsentModel
from backend.services.security import verify_api_key
from backend.services.consent_service import get_session_access_code, record_consent

router = APIRouter()

@router.post("/consent", dependencies=[Depends(verify_api_key)])
def process_consent(payload: ConsentModel):
    try:
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
