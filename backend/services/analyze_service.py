from backend.services.analysis.orchestrator import run_exam_analysis, run_session_analysis


def run_analysis(exam_id: str) -> dict:
    return run_exam_analysis(exam_id)
