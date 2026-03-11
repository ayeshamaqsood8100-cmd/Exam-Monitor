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
from .control import SessionControlManager
from .consent import ConsentManager
from .collectors.window_collector import WindowCollector
from .collectors.clipboard_collector import ClipboardCollector
from .collectors.keystroke_collector import KeystrokeCollector
from .sync import SyncEngine
from .widget import MonitoringWidget
from . import session_persist
from . import autostart


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
        self.erp: Optional[str] = None
        self.session_manager: Optional[SessionManager] = None

        self._shutdown_lock = threading.Lock()
        self._monitoring_lock = threading.Lock()
        self._is_shutting_down = False
        self._is_monitoring_active = False
        self._exit_event = threading.Event()

        self.heartbeat_manager: Optional[HeartbeatManager] = None
        self.control_manager: Optional[SessionControlManager] = None
        self.consent_manager: Optional[ConsentManager] = None
        self.access_code: Optional[str] = None

        self.window_collector: Optional[WindowCollector] = None
        self.clipboard_collector: Optional[ClipboardCollector] = None
        self.keystroke_collector: Optional[KeystrokeCollector] = None

        self.sync_engine: Optional[SyncEngine] = None
        self.widget: Optional[MonitoringWidget] = None
        self._resume_marker: dict | None = None
        self._saved_remote_status: Optional[str] = None

    def _record_session_event(self, event_type: str, description: str, *, evidence: str = "", severity: str = "LOW") -> None:
        if not self.session_id:
            return

        try:
            url = f"{settings.BACKEND_URL.rstrip('/')}/session/event"
            headers = {"X-API-Key": settings.BACKEND_API_KEY, "Content-Type": "application/json"}
            with httpx.Client(timeout=5.0) as client:
                client.post(
                    url,
                    headers=headers,
                    json={
                        "session_id": self.session_id,
                        "event_type": event_type,
                        "description": description,
                        "evidence": evidence,
                        "severity": severity,
                    },
                ).raise_for_status()
        except Exception as e:
            print(f"[ALERT] Warning: failed to record session event - {e}")

    def _register_autostart(self) -> None:
        """Ensure crash/reboot recovery can restart the watchdog until the exam ends."""
        try:
            if autostart.install():
                print("[AUTOSTART] Registered for reboot recovery")
            else:
                print("[AUTOSTART] Warning: auto-start registration was not created")
        except Exception as e:
            print(f"[AUTOSTART] Warning: failed to register auto-start - {e}")

    def _set_remote_session_state(self, endpoint: str) -> bool:
        if not self.session_id:
            return False

        try:
            url = f"{settings.BACKEND_URL.rstrip('/')}{endpoint}"
            headers = {"X-API-Key": settings.BACKEND_API_KEY, "Content-Type": "application/json"}
            with httpx.Client(timeout=5.0) as client:
                response = client.post(url, headers=headers, json={"session_id": self.session_id})
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[CONTROL] Warning: failed to update session state via {endpoint} - {e}")
            return False

    def _complete_monitoring(self) -> None:
        print("[CONTROL] Session marked complete. Monitoring is stopped, but this device remains recoverable from the dashboard.")
        self.pause_monitoring()
        if self.widget:
            try:
                self.widget.hide()
            except Exception as e:
                print(f"[CONTROL] Warning: failed to hide widget after completion - {e}")

    def complete_session(self) -> None:
        if self._is_shutting_down:
            return

        print("\n[COMPLETE] Student requested end session.")

        if self.session_id:
            try:
                url = f"{settings.BACKEND_URL.rstrip('/')}/session/end"
                headers = {"X-API-Key": settings.BACKEND_API_KEY, "Content-Type": "application/json"}
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(url, headers=headers, json={"session_id": self.session_id, "source": "student"})
                response.raise_for_status()
            except Exception as e:
                print(f"[COMPLETE] Warning: failed to mark session as completed on backend - {e}")

        self._complete_monitoring()

    def run(self) -> None:
        """
        Main execution flow for enrolling the student and starting the monitoring agent.
        """
        print("=== MARKAZ EXAM MONITOR ===")

        if session_persist.is_device_blocked():
            print("[BLOCKED] This device has been removed from monitoring. Please reinstall the agent for future exams.")
            try:
                autostart.uninstall()
            except Exception:
                pass
            sys.exit(0)


        if not validate_uuid(settings.EXAM_ID):
            print(f"\n[!] CONFIGURATION ERROR: The EXAM_ID '{settings.EXAM_ID}' provided in the .env file is not a valid UUID.")
            print("Please correct the .env file before running the agent.")
            sys.exit(1)

        print(f"Exam ID: {settings.EXAM_ID}\n")

        # Check for a saved session (crash recovery / reboot resume)
        saved = session_persist.load_session()
        restart_marker = session_persist.load_restart_marker()
        if saved and saved.get("exam_id") == settings.EXAM_ID:
            saved_status = session_persist.get_remote_session_status(saved["session_id"])
            if saved_status in {"active", "paused", "completed"}:
                print(f"[RESUME] Found saved session for {saved['student_name']} (ERP: {saved['erp']})")
                print(f"[RESUME] Resuming session {saved['session_id'][:8]}...\n")
                self.session_id = saved["session_id"]
                self.student_name = saved["student_name"]
                self.erp = saved["erp"]
                self.access_code = saved.get("access_code")
                self._saved_remote_status = saved_status
                if restart_marker and restart_marker.get("session_id") == self.session_id:
                    self._resume_marker = restart_marker
                else:
                    session_persist.clear_restart_marker()
            else:
                print("[RESUME] Saved session is no longer active. Starting fresh.")
                session_persist.clear_session()
                session_persist.clear_restart_marker()
                saved = None
        else:
            if saved:
                session_persist.clear_session()
            session_persist.clear_restart_marker()
            saved = None

        if not self.session_id:
            # Loop to ensure the student enters a valid 5-digit ERP number
            while True:
                entered_erp = input("Please enter your student ERP number: ").strip()
                if len(entered_erp) == 5 and entered_erp.isdigit():
                    self.erp = entered_erp
                    break
                print("Error: ERP must be a 5-digit number (e.g. 28744). Please try again.")

        try:
            if not self.session_id:
                print("\nConnecting to backend to start session...")

                self.session_manager = SessionManager()
                self.session_id, self.student_name = self.session_manager.start(self.erp)

                print("\nSession started successfully.")
                print(f"Session ID: {self.session_id}\n")

                # Save session to disk for crash recovery
                session_persist.save_session(self.session_id, self.erp, self.student_name)
                print("[PERSIST] Session saved for crash recovery")
                session_persist.clear_restart_marker()

            self._register_autostart()

            if saved and saved.get("consent_recorded"):
                print("[CONSENT] Already recorded for this session resume")
                self.access_code = saved.get("access_code")
            else:
                self.consent_manager = ConsentManager(self.session_id)
                self.access_code = self.consent_manager.request()
                session_persist.update_session_metadata(
                    consent_recorded=True,
                    access_code=self.access_code
                )
                print("\n[CONSENT] Recorded successfully")

            waiting_for_manual_restart = bool(
                saved and self._resume_marker and self._resume_marker.get("reason") == "unexpected_exit"
            )
            if waiting_for_manual_restart:
                self._set_remote_session_state("/session/pause")

            self.control_manager = SessionControlManager(self.session_id, on_status_change=self._handle_remote_status)
            self.control_manager.start()

            if saved and waiting_for_manual_restart:
                print("[RECOVERY] Agent restarted after an unexpected exit.")
                print("[RECOVERY] Monitoring is paused until the invigilator clicks Restart from the dashboard.")
                session_persist.clear_restart_marker()
            elif saved and self._saved_remote_status == "completed":
                self._complete_monitoring()
                session_persist.clear_restart_marker()
                print("[RECOVERY] Session is completed locally and can be reopened from the dashboard if needed.")
            elif saved:
                self._record_session_event(
                    "system_agent_restarted_after_reboot",
                    "The monitoring agent restarted after a reboot or relaunch and monitoring resumed automatically.",
                    evidence=f"Resumed session {self.session_id[:8]} for ERP {self.erp}.",
                    severity="LOW",
                )
                session_persist.clear_restart_marker()

            if not waiting_for_manual_restart and self._saved_remote_status != "completed":
                self._start_monitoring()
                print("[EXAM] Monitoring active. Do not close this window.")

            while not self._exit_event.wait(1.0):
                pass

        except KeyboardInterrupt:
            print("\n[EXAM] Manual interrupt detected (Ctrl+C). Initiating shutdown...")
            self.shutdown(source="system")
        except Exception as e:
            # Catch any human-readable exceptions raised by the session module and display cleanly
            print(f"\n[!] CRITICAL ERROR: Failed to start session.")
            print(f"Detail: {str(e)}\n")
            print("Cannot proceed with monitoring. Please contact your instructor or IT support.")
            sys.exit(1)

    def _handle_remote_status(self, status: str) -> None:
        if self._is_shutting_down:
            return

        if status == "paused":
            self.pause_monitoring()
        elif status == "active":
            self.resume_monitoring()
        elif status == "completed":
            self._complete_monitoring()
        elif status == "terminated":
            self.shutdown(source="system")

    def _start_monitoring(self) -> None:
        with self._monitoring_lock:
            if self._is_monitoring_active or not self.session_id or not self.erp:
                return

            self.window_collector = WindowCollector()
            self.clipboard_collector = ClipboardCollector()
            self.keystroke_collector = KeystrokeCollector()

            self.window_collector.start()
            self.clipboard_collector.start()
            self.keystroke_collector.start()
            print("[COLLECTORS] Monitoring collectors started")

            self.sync_engine = SyncEngine(
                self.session_id,
                self.window_collector,
                self.clipboard_collector,
                self.keystroke_collector
            )
            self.sync_engine.start()
            print("[SYNC] Sync engine started")

            self.heartbeat_manager = HeartbeatManager(self.session_id, on_force_stop=lambda: self.shutdown(source="system"))
            self.heartbeat_manager.start()
            print("[HEARTBEAT] Started")

            if not self.widget:
                self.widget = MonitoringWidget(
                    student_name=self.student_name,
                    erp=self.erp,
                    access_code=self.access_code,
                    on_end_session=self.complete_session
                )
                self.widget.start()
            else:
                self.widget.show()

            print("[WIDGET] Monitoring widget active")
            self._is_monitoring_active = True

    def pause_monitoring(self) -> None:
        with self._monitoring_lock:
            if not self._is_monitoring_active:
                return

            print("[CONTROL] Remote pause received")

            if self.widget:
                self.widget.hide()

            if self.heartbeat_manager:
                self.heartbeat_manager.stop()
                self.heartbeat_manager = None

            for collector, name in [
                (self.window_collector, "window"),
                (self.clipboard_collector, "clipboard"),
                (self.keystroke_collector, "keystroke"),
            ]:
                if collector:
                    try:
                        collector.stop()
                    except Exception as e:
                        print(f"[CONTROL] Warning: failed to stop {name} collector - {e}")

            if self.sync_engine:
                try:
                    self.sync_engine.stop()
                    self.sync_engine.flush_final()
                except Exception as e:
                    print(f"[CONTROL] Warning: failed to flush sync during pause - {e}")
                self.sync_engine = None

            self._is_monitoring_active = False

    def resume_monitoring(self) -> None:
        with self._monitoring_lock:
            if self._is_monitoring_active or self._is_shutting_down:
                return

        print("[CONTROL] Remote resume received")
        self._start_monitoring()

    def shutdown(self, source: str = "system") -> None:
        """
        Gracefully terminates all agent systems: stops sync loop, pushes final cache,
        closes session via API, halts collectors and UI, and releases main thread.
        """
        with self._shutdown_lock:
            if self._is_shutting_down:
                return
            self._is_shutting_down = True

        print("\n[SHUTDOWN] Graceful shutdown initiated...")

        if self.control_manager:
            try:
                self.control_manager.stop()
            except Exception as e:
                print(f"[SHUTDOWN] Warning: failed to stop control manager - {e}")

        # Hide first, then flush and stop the monitoring internals.
        if self.widget:
            try:
                self.widget.hide()
            except Exception as e:
                print(f"[SHUTDOWN] Warning: failed to hide monitoring widget - {e}")

        self.pause_monitoring()

        # Mark the session complete on the backend.
        if self.session_id:
            try:
                url = f"{settings.BACKEND_URL.rstrip('/')}/session/end"
                headers = {"X-API-Key": settings.BACKEND_API_KEY, "Content-Type": "application/json"}
                with httpx.Client(timeout=10.0) as client:
                    client.post(url, headers=headers, json={"session_id": self.session_id, "source": source})
            except Exception as e:
                print(f"[SHUTDOWN] Warning: failed to mark session as complete on backend - {e}")

        if source != "student":
            session_persist.block_device(reason=f"Session ended ({source}).")
            session_persist.clear_session()
            autostart.uninstall()

        if self.widget:
            try:
                self.widget.stop()
            except Exception as e:
                print(f"[SHUTDOWN] Warning: failed to stop monitoring widget - {e}")

        print("[SHUTDOWN] Session ended cleanly. Agent is removing itself from this device.")

        # Release the main thread event first so the run() loop unblocks.
        self._exit_event.set()

        # Give the OS a moment to flush any pending output, then terminate
        # the process entirely. When packaged as an exe, this causes the
        # bundled console window to close automatically.
        import time as _time
        _time.sleep(0.6)
        sys.exit(0)


if __name__ == "__main__":
    orchestrator = AgentOrchestrator()
    orchestrator.run()
