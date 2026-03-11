"""
Session management module for the Markaz Exam Monitor agent.
Handles initiating the exam session with the remote backend over HTTP.
"""
import httpx
from typing import Dict, Any, Tuple
from .config import settings
from .http_client import get_http_client

class SessionManager:
    """
    Manages the lifecycle of an exam session with the remote backend.
    """
    
    def start(self, erp: str) -> Tuple[str, str, str]:
        """
        Initiates an exam session for the given student ERP by calling the backend API.
        Raises clear, human-readable exceptions on any failure condition.
        
        Args:
            erp: The student's ERP number (e.g., '24501').
            
        Returns:
            The session ID (UUID string) and student name returned by the backend.
        """
        # Defensive URL joining to prevent double slashes
        url = f"{settings.BACKEND_URL.rstrip('/')}/session/start"
        
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "student_erp": erp,
            "exam_id": str(settings.EXAM_ID) # Cast UUID to string for JSON serialization
        }
        
        try:
            response = get_http_client().post(url, headers=headers, json=payload, timeout=10.0)
                
            # Immediately raise an exception if HTTP status is 4xx or 5xx
            response.raise_for_status()
            
            # Parse JSON payload safely
            data: Dict[str, Any] = response.json()
            
            session_id = data.get("session_id")
            
            if not session_id:
                raise ValueError(
                    f"Backend responded with success, but 'session_id' was missing from the response body. Payload received: {data}"
                )
                
            student_name = data.get("student_name", "Student")
            
            session_token = data.get("session_token")
            if not session_token:
                raise ValueError(
                    f"Backend responded with success, but 'session_token' was missing from the response body. Payload received: {data}"
                )

            return str(session_id), str(student_name), str(session_token)
            
        except httpx.ConnectError as e:
            raise ConnectionError(f"Network error: Failed to connect to the backend at {settings.BACKEND_URL}. Please check your internet connection.") from e
            
        except httpx.TimeoutException as e:
            raise TimeoutError("Network error: The request to the backend timed out.") from e
            
        except httpx.HTTPStatusError as e:
            # Attempt to extract a detailed error message from the backend's JSON response if available
            error_detail = "Unknown Server Error"
            try:
                error_detail = e.response.json().get('detail', e.response.text)
            except Exception:
                error_detail = e.response.text
                
            raise ValueError(f"Backend rejected the session request (HTTP {e.response.status_code}): {error_detail}") from e
            
        except httpx.RequestError as e:
            raise RuntimeError(f"An unexpected underlying network error occurred: {str(e)}") from e
            
        except ValueError as e:
             # Re-raise explicit payload format ValueErrors cleanly
             raise e
             
        except Exception as e:
            raise RuntimeError(f"An unexpected critical error occurred while initializing the session: {str(e)}") from e
