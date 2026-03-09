from fastapi import APIRouter, Depends, HTTPException
from backend.services.security import verify_api_key
from backend.services import analyze_service

router = APIRouter(
    prefix="/analyze",
    tags=["analysis"],
    dependencies=[Depends(verify_api_key)]
)

# Per-session endpoint MUST be defined before the catch-all /{exam_id}
@router.post("/session/{session_id}")
def analyze_single_session(session_id: str):
    try:
        result = analyze_service.run_session_analysis(session_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{exam_id}")
def analyze_exam_sessions(exam_id: str):
    try:
        result = analyze_service.run_analysis(exam_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
