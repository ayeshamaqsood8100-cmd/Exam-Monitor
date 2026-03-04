from fastapi import APIRouter, Depends, HTTPException, status
from backend.models.consent import ConsentModel
from backend.services.security import verify_api_key
from backend.services.consent_service import record_consent
from backend.services.database import db

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
            
        access_code = None
        session_res = db.client.table("exam_sessions").select("exam_id").eq("id", str(payload.session_id)).execute()
        
        if session_res.data:
            exam_id = session_res.data[0].get("exam_id")
            if exam_id:
                exam_res = db.client.table("exams").select("access_code").eq("id", str(exam_id)).execute()
                if exam_res.data:
                    access_code = exam_res.data[0].get("access_code")
            
        return {"status": "ok", "access_code": access_code}
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing consent."
        )
