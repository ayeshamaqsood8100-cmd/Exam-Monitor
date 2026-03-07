from fastapi import APIRouter, Depends, HTTPException
from backend.services.security import verify_api_key
from backend.services import analyze_service

router = APIRouter(
    prefix="/analyze",
    tags=["analysis"],
    dependencies=[Depends(verify_api_key)]
)

@router.post("/{exam_id}")
def analyze_exam_sessions(exam_id: str):
    try:
        # We do not pass the supabase client anymore, the service handles it internally via 'db' singleton.
        result = analyze_service.run_analysis(exam_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
