from fastapi import APIRouter, Depends, HTTPException, status
from backend.models.consent import ConsentModel
from backend.services.security import verify_api_key
from backend.services.consent_service import record_consent

router = APIRouter()

@router.post("/consent", dependencies=[Depends(verify_api_key)])
async def process_consent(payload: ConsentModel):
    try:
        consent_id = record_consent(payload.session_id, payload.agent_version)
        
        if not consent_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record consent in the database."
            )
            
        return {"success": True, "consent_id": consent_id}
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing consent."
        )
