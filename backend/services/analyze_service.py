from backend.services.analysis.orchestrator import (
    run_exam_analysis,
    run_session_analysis as run_single_session_analysis,
)


def run_analysis(exam_id: str) -> dict:
    return run_exam_analysis(exam_id)


def run_session_analysis(session_id: str) -> dict:
    return run_single_session_analysis(session_id)
