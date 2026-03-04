"""
Main entry point for the Markaz Exam Monitor desktop agent.
Handles the basic interactive terminal interface for starting a session.
"""
import sys
import uuid
from typing import Optional
from .config import settings
from .session import SessionManager
from .heartbeat import HeartbeatManager
from .consent import ConsentManager

def validate_uuid(val: str) -> bool:
    try:
        uuid.UUID(val)
        return True
    except ValueError:
        return False

class AgentOrchestrator:
    """
    Central orchestrator for the Markaz Exam Monitor desktop agent.
    Manages the overall flow, state, and coordination of different modules.
    """
    
    def __init__(self) -> None:
        self.session_id: Optional[str] = None
        self.heartbeat_manager: Optional[HeartbeatManager] = None
        self.consent_manager: Optional[ConsentManager] = None
        self.access_code: Optional[str] = None

    def run(self) -> None:
        """
        Main execution flow for enrolling the student and starting the monitoring agent.
        """
        print("=== MARKAZ EXAM MONITOR ===")
        
        if not validate_uuid(settings.EXAM_ID):
            print(f"\n[!] CONFIGURATION ERROR: The EXAM_ID '{settings.EXAM_ID}' provided in the .env file is not a valid UUID.")
            print("Please correct the .env file before running the agent.")
            sys.exit(1)
            
        print(f"Exam ID: {settings.EXAM_ID}\n")
        
        erp = ""
        # Loop to ensure the student enters a valid 5-digit ERP number
        while True:
            erp = input("Please enter your student ERP number: ").strip()
            if len(erp) == 5 and erp.isdigit():
                break
            print("Error: ERP must be a 5-digit number (e.g. 28744). Please try again.")
                
        try:
            print("\nConnecting to backend to start session...")
            
            session_manager = SessionManager()
            self.session_id = session_manager.start(erp)
            
            print("\nSession started successfully.")
            print(f"Session ID: {self.session_id}\n")
            
            self.heartbeat_manager = HeartbeatManager(self.session_id)
            self.heartbeat_manager.start()
            print("[HEARTBEAT] Started — pinging every 30 seconds\n")
            
            self.consent_manager = ConsentManager(self.session_id)
            self.access_code = self.consent_manager.request()
            print("\n[CONSENT] Recorded successfully")
            
        except Exception as e:
            # Catch any human-readable exceptions raised by the session module and display cleanly
            print(f"\n[!] CRITICAL ERROR: Failed to start session.")
            print(f"Detail: {str(e)}\n")
            print("Cannot proceed with monitoring. Please contact your instructor or IT support.")
            sys.exit(1)

if __name__ == "__main__":
    orchestrator = AgentOrchestrator()
    orchestrator.run()
