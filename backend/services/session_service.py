from uuid import UUID
from datetime import datetime, timezone
from backend.services.database import db

def start_session(student_erp: str, exam_id: UUID) -> dict:
    # 1. Look up student by ERP
    student_response = db.client.table("students").select("id, name").eq("erp", student_erp).execute()
    if not student_response.data:
        raise ValueError("Student not found")
    
    student_id = student_response.data[0]["id"]
    student_name = student_response.data[0].get("name", "Unknown Student")
    now_utc = datetime.now(timezone.utc).isoformat()
    
    # 2. Check for existing session
    session_response = db.client.table("exam_sessions").select("id, status").eq("student_id", student_id).eq("exam_id", str(exam_id)).execute()
    
    if session_response.data:
        existing_session = session_response.data[0]
        if existing_session["status"] == "active":
            raise ValueError("Session already active")
        else:
            # 3. Reactivate existing completed/abandoned session
            update_res = db.client.table("exam_sessions").update({
                "status": "active",
                "session_start": now_utc,
                "session_end": None,
                "last_heartbeat_at": now_utc
            }).eq("id", existing_session["id"]).execute()
            return {"session_id": existing_session["id"], "student_id": student_id, "student_name": student_name}
            
    # 4. Insert entirely new session
    insert_res = db.client.table("exam_sessions").insert({
        "student_id": student_id,
        "exam_id": str(exam_id),
        "status": "active",
        "session_start": now_utc,
        "last_heartbeat_at": now_utc
    }).execute()
    
    new_session_id = insert_res.data[0]["id"]
    return {"session_id": new_session_id, "student_id": student_id, "student_name": student_name}

def end_session(session_id: UUID) -> bool:
    now_utc = datetime.now(timezone.utc).isoformat()
    response = db.client.table("exam_sessions").update({
        "status": "completed",
        "session_end": now_utc
    }).eq("id", str(session_id)).execute()
    
    if response.data and len(response.data) > 0:
        return True
    return False
