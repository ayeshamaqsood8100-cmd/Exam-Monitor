"""
Main entry point for the Markaz Exam Monitor desktop agent.
Handles the basic interactive terminal interface for starting a session.
"""
import sys
import uuid
import threading
import httpx
from typing import Optional
from .config import settings
from .session import SessionManager
from .heartbeat import HeartbeatManager
from .consent import ConsentManager
from .collectors.window_collector import WindowCollector
from .collectors.clipboard_collector import ClipboardCollector
from .collectors.keystroke_collector import KeystrokeCollector
from .sync import SyncEngine
from .widget import MonitoringWidget

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
        self.student_name: Optional[str] = None
        self.session_manager: Optional[SessionManager] = None
        
        self._shutdown_lock = threading.Lock()
        self._is_shutting_down = False
        self._exit_event = threading.Event()
        
        self.heartbeat_manager: Optional[HeartbeatManager] = None
        self.consent_manager: Optional[ConsentManager] = None
        self.access_code: Optional[str] = None
        
        self.window_collector: Optional[WindowCollector] = None
        self.clipboard_collector: Optional[ClipboardCollector] = None
        self.keystroke_collector: Optional[KeystrokeCollector] = None
        
        self.sync_engine: Optional[SyncEngine] = None
        self.widget: Optional[MonitoringWidget] = None

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
            
            self.session_manager = SessionManager()
            self.session_id, self.student_name = self.session_manager.start(erp)
            
            print("\nSession started successfully.")
            print(f"Session ID: {self.session_id}\n")
            
            self.heartbeat_manager = HeartbeatManager(self.session_id, on_force_stop=self.shutdown)
            self.heartbeat_manager.start()
            print("[HEARTBEAT] Started — pinging every 30 seconds\n")
            
            self.consent_manager = ConsentManager(self.session_id)
            self.access_code = self.consent_manager.request()
            print("\n[CONSENT] Recorded successfully")
            
            self.window_collector = WindowCollector()
            self.clipboard_collector = ClipboardCollector()
            self.keystroke_collector = KeystrokeCollector()
            
            self.window_collector.start()
            self.clipboard_collector.start()
            self.keystroke_collector.start()
            print("[COLLECTORS] All monitoring collectors started")
            
            self.sync_engine = SyncEngine(
                self.session_id,
                self.window_collector,
                self.clipboard_collector,
                self.keystroke_collector
            )
            self.sync_engine.start()
            print("[SYNC] Sync engine started — uploading every ~60 seconds\n")
            
            self.widget = MonitoringWidget(
                student_name=self.student_name,
                erp=erp,
                access_code=self.access_code,
                on_end_session=self.shutdown
            )
            self.widget.start()
            print("[WIDGET] Monitoring widget active")
            
            print("[EXAM] Monitoring active. Do not close this window.")
            # Block main thread until shutdown completes
            self._exit_event.wait()
            
        except Exception as e:
            # Catch any human-readable exceptions raised by the session module and display cleanly
            print(f"\n[!] CRITICAL ERROR: Failed to start session.")
            print(f"Detail: {str(e)}\n")
            print("Cannot proceed with monitoring. Please contact your instructor or IT support.")
            sys.exit(1)

    def shutdown(self) -> None:
        """
        Gracefully terminates all agent systems: stops sync loop, pushes final cache,
        closes session via API, halts collectors & UI, and releases main thread.
        """
        with self._shutdown_lock:
            if self._is_shutting_down:
                return
            self._is_shutting_down = True
            
        print("\n[SHUTDOWN] Graceful shutdown initiated...")
        
        # Step 1: Stop sync engine
        if self.sync_engine:
            try:
                self.sync_engine.stop()
            except Exception as e:
                print(f"[SHUTDOWN] Warning: failed to stop sync engine — {e}")
                
        # Step 2: Run final sync immediately
        if self.sync_engine:
            try:
                self.sync_engine._sync()
            except Exception as e:
                print(f"[SHUTDOWN] Warning: final telemetry sync failed — {e}")
                
        # Step 3: Call POST /session/end
        if self.session_id:
            try:
                url = f"{settings.BACKEND_URL.rstrip('/')}/session/end"
                headers = {"X-API-Key": settings.API_KEY, "Content-Type": "application/json"}
                with httpx.Client(timeout=10.0) as client:
                    client.post(url, headers=headers, json={"session_id": self.session_id})
            except Exception as e:
                print(f"[SHUTDOWN] Warning: failed to mark session as complete on backend — {e}")
                
        # Step 4: Stop heartbeat
        if self.heartbeat_manager:
            try:
                self.heartbeat_manager.stop()
            except Exception as e:
                print(f"[SHUTDOWN] Warning: failed to stop heartbeat — {e}")
                
        # Step 5: Stop collectors
        for collector, name in [
            (self.window_collector, "window"),
            (self.clipboard_collector, "clipboard"),
            (self.keystroke_collector, "keystroke")
        ]:
            if collector:
                try:
                    collector.stop()
                except Exception as e:
                    print(f"[SHUTDOWN] Warning: failed to stop {name} collector — {e}")
                    
        # Step 6: Stop widget
        if self.widget:
            try:
                self.widget.stop()
            except Exception as e:
                print(f"[SHUTDOWN] Warning: failed to stop monitoring widget — {e}")
                
        # Step 7: Release main thread
        print("[SHUTDOWN] Session ended cleanly.")
        self._exit_event.set()

if __name__ == "__main__":
    orchestrator = AgentOrchestrator()
    orchestrator.run()
