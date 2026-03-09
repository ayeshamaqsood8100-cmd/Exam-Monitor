"""
Consent management module for the Markaz Exam Monitor agent.
Handles presenting the academic integrity pledge, recording consent, and retrieving the exam access code.
"""
import os
import sys
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from .config import settings

PLEDGE_TEXT = """
============================================================
  IBA KARACHI — ACADEMIC INTEGRITY PLEDGE
============================================================

I pledge on my honour that I will not give or receive any
unauthorized assistance during this examination.

I understand that any violation of IBA's Academic Integrity
Policy may result in serious disciplinary action.

============================================================
Type YES to accept this pledge and access your exam.
Type NO to exit.
============================================================
"""

class ConsentManager:
    """
    Manages the presentation of the academic integrity pledge and the retrieval of the exam access code.
    """
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        
    def request(self) -> Optional[str]:
        """
        Presents the pledge, waits for valid YES/NO input, records consent with backend, and returns access_code.
        """
        os.system('cls' if os.name == 'nt' else 'clear')
        print(PLEDGE_TEXT, end="")
        
        while True:
            choice = input().strip().upper()
            if choice == "NO":
                print("Exam access declined. Exiting.")
                sys.exit(0)
            elif choice == "YES":
                break
            else:
                print("Please type YES or NO.")
                
        # Send consent to backend
        url = f"{settings.BACKEND_URL.rstrip('/')}/consent"
        headers = {
            "X-API-Key": settings.BACKEND_API_KEY,
            "Content-Type": "application/json"
        }
        
        # Ensure timestamp is explicit timezone-aware UTC inside Python, formatted as ISO 8601 string
        timestamp = datetime.now(timezone.utc).isoformat()
        
        payload = {
            "session_id": self.session_id,
            "agent_version": "1.0.0",
            "timestamp": timestamp
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data: Dict[str, Any] = response.json()
            access_code = data.get("access_code")
            
            os.system('cls' if os.name == 'nt' else 'clear')
            
            if access_code is not None:
                print("============================================================")
                print("  PLEDGE ACCEPTED — EXAM ACCESS GRANTED")
                print("============================================================\n")
                print("  Your exam access code is:\n")
                print(f"        [ {access_code} ]\n")
                print("  Enter this code on Moodle to access your exam.")
                print("  Keep this window open for the duration of your exam.")
                print("============================================================")
            else:
                print("============================================================")
                print("  PLEDGE ACCEPTED — EXAM ACCESS GRANTED")
                print("============================================================\n")
                print("  Access code unavailable. Please contact your instructor.\n")
                print("  Keep this window open for the duration of your exam.")
                print("============================================================")
                
            return access_code
            
        except httpx.ConnectError as e:
            print(f"\n[!] Network error connecting to backend: {str(e)}")
            sys.exit(1)
        except httpx.TimeoutException as e:
            print(f"\n[!] Network timeout while recording consent: {str(e)}")
            sys.exit(1)
        except httpx.HTTPStatusError as e:
            print(f"\n[!] Backend rejected consent. HTTP {e.response.status_code}")
            sys.exit(1)
        except Exception as e:
            print(f"\n[!] Unexpected error while recording consent: {str(e)}")
            sys.exit(1)
