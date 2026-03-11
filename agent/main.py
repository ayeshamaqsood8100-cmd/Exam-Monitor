"""
Main entry point for the Markaz Exam Monitor desktop agent.
Handles the basic interactive terminal interface for starting a session.
"""
import sys
import time
import uuid
import threading
from typing import Optional
from .auth import build_auth_headers, clear_session_token, set_session_token
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
from .http_client import close_http_client, get_http_client
from .windows_student_ui import is_windows_packaged_runtime, request_student_erp, show_error_dialog

KEYSTROKE_HEALTH_CHECK_INTERVAL_SECONDS = 15.0
KEYSTROKE_HEALTH_STALE_AFTER_SECONDS = 90.0
KEYSTROKE_HEALTH_INITIAL_GRACE_SECONDS = 30.0
KEYSTROKE_HEALTH_ALERT_COOLDOWN_SECONDS = 300.0


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
        self.session_token: Optional[str] = None
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
        self._keystroke_health_thread: threading.Thread | None = None
        self._keystroke_health_stop_event = threading.Event()
        self._keystroke_alert_active = False
        self._keystroke_last_alert_reason: Optional[str] = None
        self._keystroke_last_alert_monotonic: float | None = None

    def _record_session_event(self, event_type: str, description: str, *, evidence: str = "", severity: str = "LOW") -> None:
        if not self.session_id:
            return

        try:
            url = f"{settings.BACKEND_URL.rstrip('/')}/session/event"
            headers = build_auth_headers()
            get_http_client().post(
                url,
                headers=headers,
                json={
                    "session_id": self.session_id,
                    "event_type": event_type,
                    "description": description,
                    "evidence": evidence,
                    "severity": severity,
                },
                timeout=5.0,
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
            headers = build_auth_headers()
            response = get_http_client().post(
                url,
                headers=headers,
                json={"session_id": self.session_id},
                timeout=5.0,
            )
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
                headers = build_auth_headers()
                response = get_http_client().post(
                    url,
                    headers=headers,
                    json={"session_id": self.session_id, "source": "student"},
                    timeout=10.0,
                )
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
            message = "This device has been removed from monitoring. Please reinstall the agent for future exams."
            if is_windows_packaged_runtime():
                show_error_dialog("Markaz", message)
            else:
                print(f"[BLOCKED] {message}")
            try:
                autostart.uninstall()
            except Exception:
                pass
            sys.exit(0)


        if not validate_uuid(settings.EXAM_ID):
            message = (
                f"The EXAM_ID '{settings.EXAM_ID}' provided for the agent is not a valid UUID.\n\n"
                "Please correct the configuration before running the agent."
            )
            if is_windows_packaged_runtime():
                show_error_dialog("Markaz", message)
            else:
                print(f"\n[!] CONFIGURATION ERROR: The EXAM_ID '{settings.EXAM_ID}' provided in the .env file is not a valid UUID.")
                print("Please correct the .env file before running the agent.")
            sys.exit(1)

        print(f"Exam ID: {settings.EXAM_ID}\n")

        # Check for a saved session (crash recovery / reboot resume)
        saved = session_persist.load_session()
        restart_marker = session_persist.load_restart_marker()
        if saved and not saved.get("session_token") and not settings.BACKEND_API_KEY:
            session_persist.clear_session()
            session_persist.clear_restart_marker()
            saved = None
        if saved and saved.get("exam_id") == settings.EXAM_ID:
            saved_status = session_persist.get_remote_session_status(
                saved["session_id"],
                session_token=saved.get("session_token"),
            )
            if saved_status in {"active", "paused", "completed"}:
                print(f"[RESUME] Found saved session for {saved['student_name']} (ERP: {saved['erp']})")
                print(f"[RESUME] Resuming session {saved['session_id'][:8]}...\n")
                self.session_id = saved["session_id"]
                self.student_name = saved["student_name"]
                self.erp = saved["erp"]
                self.access_code = saved.get("access_code")
                self.session_token = saved.get("session_token")
                set_session_token(self.session_token)
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
            if is_windows_packaged_runtime():
                entered_erp = request_student_erp()
                if not entered_erp:
                    sys.exit(0)
                self.erp = entered_erp
            else:
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
                self.session_id, self.student_name, self.session_token = self.session_manager.start(self.erp)
                set_session_token(self.session_token)

                print("\nSession started successfully.")
                print(f"Session ID: {self.session_id}\n")

                # Save session to disk for crash recovery
                session_persist.save_session(
                    self.session_id,
                    self.erp,
                    self.student_name,
                    session_token=self.session_token,
                )
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
                    access_code=self.access_code,
                    session_token=self.session_token,
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
                if not is_windows_packaged_runtime():
                    print("[EXAM] Monitoring active. Do not close this window.")

            while not self._exit_event.wait(1.0):
                pass

        except KeyboardInterrupt:
            print("\n[EXAM] Manual interrupt detected (Ctrl+C). Initiating shutdown...")
            self.shutdown(source="system")
        except Exception as e:
            # Catch any human-readable exceptions raised by the session module and display cleanly
            if is_windows_packaged_runtime():
                show_error_dialog(
                    "Markaz",
                    f"Failed to start the exam session.\n\nDetail: {str(e)}\n\nPlease contact your instructor or IT support.",
                )
            else:
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

    def _start_keystroke_health_monitor(self) -> None:
        if self._keystroke_health_thread and self._keystroke_health_thread.is_alive():
            return

        self._keystroke_health_stop_event.clear()
        self._keystroke_health_thread = threading.Thread(target=self._keystroke_health_loop, daemon=True)
        self._keystroke_health_thread.start()

    def _stop_keystroke_health_monitor(self) -> None:
        self._keystroke_health_stop_event.set()
        if self._keystroke_health_thread and self._keystroke_health_thread.is_alive() and threading.current_thread() is not self._keystroke_health_thread:
            self._keystroke_health_thread.join(timeout=2.5)
        self._keystroke_health_thread = None

    def _keystroke_health_loop(self) -> None:
        while not self._keystroke_health_stop_event.wait(KEYSTROKE_HEALTH_CHECK_INTERVAL_SECONDS):
            if self._is_shutting_down or not self._is_monitoring_active:
                continue
            self._check_keystroke_health()

    def _check_keystroke_health(self) -> None:
        collector = self.keystroke_collector
        if collector is None:
            return

        snapshot = collector.get_health_snapshot()
        reason = self._get_keystroke_unhealthy_reason(snapshot)

        if reason is None:
            if self._keystroke_alert_active:
                self._record_session_event(
                    "system_keystroke_collector_recovered",
                    "The keystroke collector recovered after becoming unresponsive.",
                    evidence=self._keystroke_last_alert_reason or "Recovered after a local listener restart.",
                    severity="LOW",
                )
                self._keystroke_alert_active = False
                self._keystroke_last_alert_reason = None
                self._keystroke_last_alert_monotonic = None
            return

        now = time.monotonic()
        should_emit_alert = (
            not self._keystroke_alert_active
            or self._keystroke_last_alert_monotonic is None
            or (now - self._keystroke_last_alert_monotonic) >= KEYSTROKE_HEALTH_ALERT_COOLDOWN_SECONDS
        )

        if should_emit_alert:
            self._record_session_event(
                "system_keystroke_collector_unhealthy",
                "The keystroke collector became unresponsive while other agent activity continued.",
                evidence=reason,
                severity="MED",
            )
            self._keystroke_alert_active = True
            self._keystroke_last_alert_reason = reason
            self._keystroke_last_alert_monotonic = now

        self._restart_keystroke_collector(reason)

    def _get_keystroke_unhealthy_reason(self, snapshot: dict[str, float | bool | None]) -> Optional[str]:
        listener_alive = bool(snapshot.get("listener_alive"))
        if not listener_alive:
            return "pynput keyboard listener is no longer alive."

        listener_started = snapshot.get("listener_started_monotonic")
        listener_uptime = snapshot.get("listener_uptime_seconds")
        if listener_uptime is None or listener_uptime < KEYSTROKE_HEALTH_INITIAL_GRACE_SECONDS:
            return None

        last_keypress = snapshot.get("last_keypress_monotonic")
        last_window_activity = self.window_collector.get_last_activity_monotonic() if self.window_collector else None
        last_clipboard_activity = self.clipboard_collector.get_last_activity_monotonic() if self.clipboard_collector else None
        other_activity = max(
            [value for value in (last_window_activity, last_clipboard_activity) if value is not None],
            default=None,
        )

        if other_activity is None:
            return None

        if last_keypress is None:
            if listener_started is not None and other_activity > listener_started:
                return "No keystrokes were captured even though other local activity was recorded after the listener started."
            return None

        if other_activity > last_keypress and (other_activity - last_keypress) >= KEYSTROKE_HEALTH_STALE_AFTER_SECONDS:
            seconds_since_last_keypress = snapshot.get("seconds_since_last_keypress")
            if seconds_since_last_keypress is not None and seconds_since_last_keypress >= KEYSTROKE_HEALTH_STALE_AFTER_SECONDS:
                return (
                    f"Last keystroke was {int(seconds_since_last_keypress)}s ago while window or clipboard activity continued."
                )

        return None

    def _restart_keystroke_collector(self, reason: str) -> None:
        with self._monitoring_lock:
            if not self._is_monitoring_active or self._is_shutting_down or self.keystroke_collector is None:
                return

            try:
                self.keystroke_collector.restart()
                print(f"[HEALTH] Keystroke collector restarted: {reason}")
            except Exception as e:
                print(f"[HEALTH] Warning: failed to restart keystroke collector - {e}")

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
            self._keystroke_alert_active = False
            self._keystroke_last_alert_reason = None
            self._keystroke_last_alert_monotonic = None
            self._start_keystroke_health_monitor()

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
            self._stop_keystroke_health_monitor()

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
                headers = build_auth_headers()
                get_http_client().post(
                    url,
                    headers=headers,
                    json={"session_id": self.session_id, "source": source},
                    timeout=10.0,
                )
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
        clear_session_token()
        close_http_client()
        sys.exit(0)


if __name__ == "__main__":
    orchestrator = AgentOrchestrator()
    orchestrator.run()
