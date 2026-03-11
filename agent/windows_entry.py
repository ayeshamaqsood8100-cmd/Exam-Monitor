"""
Windows packaging entrypoint for the Markaz Sentinel student executable.

Normal launch path:
    EXE -> watchdog supervisor

Internal child launch path:
    EXE --markaz-agent-child -> agent main process
"""
from __future__ import annotations

import os
import platform
import sys


CHILD_PROCESS_ARG = "--markaz-agent-child"
_null_streams: list[object] = []


def _ensure_background_stdio() -> None:
    if platform.system() != "Windows" or not getattr(sys, "frozen", False):
        return

    if sys.stdin is None:
        stdin_stream = open(os.devnull, "r", encoding="utf-8")
        _null_streams.append(stdin_stream)
        sys.stdin = stdin_stream

    if sys.stdout is None:
        stdout_stream = open(os.devnull, "w", encoding="utf-8")
        _null_streams.append(stdout_stream)
        sys.stdout = stdout_stream

    if sys.stderr is None:
        stderr_stream = open(os.devnull, "w", encoding="utf-8")
        _null_streams.append(stderr_stream)
        sys.stderr = stderr_stream


def _apply_baked_config() -> None:
    try:
        from agent import build_config
    except ImportError:
        return

    for key in ("BACKEND_URL", "EXAM_ID"):
        value = getattr(build_config, key, None)
        if value and not os.environ.get(key):
            os.environ[key] = str(value)


def main() -> None:
    _ensure_background_stdio()
    _apply_baked_config()

    if CHILD_PROCESS_ARG in sys.argv[1:]:
        from agent.main import AgentOrchestrator

        orchestrator = AgentOrchestrator()
        orchestrator.run()
        return

    from agent.watchdog import run_watchdog

    run_watchdog()


if __name__ == "__main__":
    main()
