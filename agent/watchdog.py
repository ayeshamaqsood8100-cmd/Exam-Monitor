"""
Watchdog for Markaz Sentinel agent.

A lightweight supervisor that monitors the agent process and restarts it
automatically if it crashes, is killed, or exits unexpectedly.

Usage:
    python -m agent.watchdog

Students run the watchdog instead of main.py directly.
The watchdog starts the agent and keeps it alive for the duration of the exam.
"""
import subprocess
import sys
import time
import os
import signal
import platform
import httpx


# How often to check if the agent is Still alive (seconds)
CHECK_INTERVAL = 1

# Maximum number of rapid restarts before giving up (prevents infinite crash loops)
MAX_RAPID_RESTARTS = 10
RAPID_RESTART_WINDOW = 120  # seconds


def get_agent_command():
    """Returns the command to start the agent, using the same Python interpreter."""
    return [sys.executable, "-m", "agent.main"]


def _record_agent_event(saved_session: dict, event_type: str, description: str, *, evidence: str = "", severity: str = "LOW") -> None:
    from agent.config import settings

    url = f"{settings.BACKEND_URL.rstrip('/')}/session/event"
    headers = {
        "X-API-Key": settings.BACKEND_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(
                url,
                headers=headers,
                json={
                    "session_id": saved_session["session_id"],
                    "event_type": event_type,
                    "description": description,
                    "evidence": evidence,
                    "severity": severity,
                },
            ).raise_for_status()
    except Exception as e:
        print(f"[WATCHDOG] Warning: failed to record agent event - {e}")


def _pause_session_for_restart(saved_session: dict) -> None:
    from agent.config import settings

    url = f"{settings.BACKEND_URL.rstrip('/')}/session/pause"
    headers = {
        "X-API-Key": settings.BACKEND_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(
                url,
                headers=headers,
                json={"session_id": saved_session["session_id"]},
            ).raise_for_status()
    except Exception as e:
        print(f"[WATCHDOG] Warning: failed to pause session for restart - {e}")


def _stop_agent_process(agent_process: subprocess.Popen) -> None:
    """Terminate the child process without leaving it running after watchdog exit."""
    if agent_process.poll() is not None:
        return

    try:
        if platform.system() == "Windows":
            agent_process.terminate()
        else:
            agent_process.send_signal(signal.SIGTERM)
        agent_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        agent_process.kill()
        try:
            agent_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def run_watchdog():
    """
    Main watchdog loop.
    Starts the agent and restarts it if it dies, until the session
    is ended cleanly or the restart limit is reached.
    """
    print("=" * 50)
    print("MARKAZ SENTINEL — WATCHDOG")
    print("=" * 50)
    print("The watchdog will keep the exam agent running.")
    print("Do NOT close this window during the exam.\n")

    # Track rapid restarts to detect crash loops
    restart_times = []

    agent_process = None

    try:
        while True:
            # Start the agent
            cmd = get_agent_command()
            cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            print(f"[WATCHDOG] Starting agent...")
            agent_process = subprocess.Popen(
                cmd,
                cwd=cwd,
                # Inherit stdin/stdout so student can interact with ERP prompt
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr
            )

            # Wait for the agent to exit
            exit_code = agent_process.wait()

            print(f"\n[WATCHDOG] Agent exited with code {exit_code}")

            # Check if the session was ended cleanly
            # If the session file is gone, the agent ended normally — don't restart
            from agent.session_persist import load_session
            saved = load_session()
            if saved is None:
                print("[WATCHDOG] Session ended cleanly. Watchdog shutting down.")
                break

            from agent.session_persist import save_restart_marker

            save_restart_marker(
                saved["session_id"],
                "unexpected_exit",
                evidence=f"Agent process exit code: {exit_code}",
            )

            _pause_session_for_restart(saved)

            _record_agent_event(
                saved,
                "system_agent_process_exited_unexpectedly",
                "The monitoring agent exited unexpectedly and the watchdog is restarting it.",
                evidence=f"Agent process exit code: {exit_code}",
                severity="MED",
            )

            # Track this restart for crash loop detection
            now = time.time()
            restart_times.append(now)
            # Keep only restarts within the rapid restart window
            restart_times = [t for t in restart_times if now - t < RAPID_RESTART_WINDOW]

            if len(restart_times) >= MAX_RAPID_RESTARTS:
                print(f"[WATCHDOG] Agent crashed {MAX_RAPID_RESTARTS} times in {RAPID_RESTART_WINDOW}s. Giving up.")
                print("[WATCHDOG] Please contact your instructor or IT support.")
                break

            print(f"[WATCHDOG] Agent died unexpectedly. Restarting in {CHECK_INTERVAL} seconds...")
            print(f"[WATCHDOG] (Restart {len(restart_times)}/{MAX_RAPID_RESTARTS} in this window)")
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n[WATCHDOG] Interrupted by user.")
        if agent_process and agent_process.poll() is None:
            _stop_agent_process(agent_process)
        print("[WATCHDOG] Shutdown complete.")


if __name__ == "__main__":
    run_watchdog()
