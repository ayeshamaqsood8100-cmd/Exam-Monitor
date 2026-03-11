"""
Consent management module for the Markaz Exam Monitor agent.
Handles presenting the academic integrity pledge, recording consent, and retrieving the exam access code.
"""
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from .auth import build_auth_headers
from .config import settings
from .http_client import get_http_client
from .windows_student_ui import (
    is_windows_packaged_runtime,
    request_consent_confirmation,
    show_error_dialog,
)

PLEDGE_TEXT = """
============================================================
  IBA KARACHI - ACADEMIC INTEGRITY PLEDGE
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
        if is_windows_packaged_runtime():
            if not request_consent_confirmation():
                sys.exit(0)
        else:
            os.system("cls" if os.name == "nt" else "clear")
            print(PLEDGE_TEXT, end="")

            while True:
                choice = input().strip().upper()
                if choice == "NO":
                    print("Exam access declined. Exiting.")
                    sys.exit(0)
                if choice == "YES":
                    break
                print("Please type YES or NO.")

        url = f"{settings.BACKEND_URL.rstrip('/')}/consent"
        headers = build_auth_headers()
        timestamp = datetime.now(timezone.utc).isoformat()
        payload = {
            "session_id": self.session_id,
            "agent_version": "1.0.0",
            "timestamp": timestamp,
        }

        try:
            response = get_http_client().post(url, headers=headers, json=payload, timeout=10.0)
            response.raise_for_status()

            data: Dict[str, Any] = response.json()
            access_code = data.get("access_code")

            if not is_windows_packaged_runtime():
                os.system("cls" if os.name == "nt" else "clear")

                if access_code is not None:
                    print("============================================================")
                    print("  PLEDGE ACCEPTED - EXAM ACCESS GRANTED")
                    print("============================================================\n")
                    print("  Your exam access code is:\n")
                    print(f"        [ {access_code} ]\n")
                    print("  Enter this code on Moodle to access your exam.")
                    print("  Keep this window open for the duration of your exam.")
                    print("============================================================")
                else:
                    print("============================================================")
                    print("  PLEDGE ACCEPTED - EXAM ACCESS GRANTED")
                    print("============================================================\n")
                    print("  Access code unavailable. Please contact your instructor.\n")
                    print("  Keep this window open for the duration of your exam.")
                    print("============================================================")

            return access_code

        except httpx.ConnectError as e:
            self._fail(f"Network error connecting to backend: {str(e)}")
        except httpx.TimeoutException as e:
            self._fail(f"Network timeout while recording consent: {str(e)}")
        except httpx.HTTPStatusError as e:
            self._fail(f"Backend rejected consent. HTTP {e.response.status_code}")
        except Exception as e:
            self._fail(f"Unexpected error while recording consent: {str(e)}")

        return None

    def _fail(self, message: str) -> None:
        if is_windows_packaged_runtime():
            show_error_dialog("Markaz", message)
        else:
            print(f"\n[!] {message}")
        sys.exit(1)
