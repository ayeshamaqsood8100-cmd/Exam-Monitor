from __future__ import annotations

import httpx
from fastapi import HTTPException

from backend.config.settings import AnalysisConfigError, AnalysisRuntimeConfig, settings
from backend.services.analysis.models import RunStatus, TriggerType
from backend.services.analysis.prompt_builder import PROMPT_VERSION
from backend.services.analysis.provider_router import AllProvidersFailedError, analyze_request
from backend.services.analysis.repository import (
    complete_analysis_run,
    create_analysis_run,
    delete_existing_ai_flags,
    insert_ai_flags,
)
from backend.services.analysis.telemetry_loader import list_completed_session_ids, load_session_request


def run_session_analysis(session_id: str) -> dict:
    runtime_config = _build_runtime_config()

    try:
        request = load_session_request(
            session_id,
            trigger_type=TriggerType.SINGLE_SESSION,
            prompt_version=PROMPT_VERSION,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    provider_chain = _build_provider_chain(runtime_config)
    run_id = create_analysis_run(request, provider_chain=provider_chain)

    if request.input_stats.empty_telemetry:
        return _complete_no_data_run(request=request, run_id=run_id)

    try:
        with httpx.Client() as client:
            execution_result = analyze_request(
                request,
                runtime_config=runtime_config,
                client=client,
            )
    except AllProvidersFailedError as exc:
        _complete_failed_run(
            run_id=run_id,
            input_stats=request.input_stats.model_dump(mode="json"),
            attempts=[attempt.model_dump(mode="json") for attempt in exc.attempts],
            error_summary=exc.last_error,
        )
        raise HTTPException(status_code=503, detail=f"Analysis failed: {exc.last_error}") from exc
    except Exception as exc:
        _complete_failed_run(
            run_id=run_id,
            input_stats=request.input_stats.model_dump(mode="json"),
            attempts=[],
            error_summary=str(exc),
        )
        raise

    chunk_count = execution_result.attempts[-1].chunk_count if execution_result.attempts else 0
    input_stats = request.input_stats.model_copy(update={"chunk_count": chunk_count})

    delete_existing_ai_flags(request.session_id)
    flags_inserted = insert_ai_flags(
        session_id=request.session_id,
        analysis_run_id=run_id,
        flags=execution_result.flags,
    )
    complete_analysis_run(
        run_id,
        status=RunStatus.SUCCESS,
        provider_used=execution_result.provider_used,
        model_used=execution_result.model_used,
        fallback_used=execution_result.fallback_used,
        attempts=[attempt.model_dump(mode="json") for attempt in execution_result.attempts],
        input_stats=input_stats.model_dump(mode="json"),
        flags_inserted=flags_inserted,
        error_summary=None,
    )
    return {
        "session_id": request.session_id,
        "flags_inserted": flags_inserted,
        "analysis_run_id": run_id,
        "provider_used": execution_result.provider_used,
        "fallback_used": execution_result.fallback_used,
    }


def run_exam_analysis(exam_id: str) -> dict:
    runtime_config = _build_runtime_config()
    session_ids = list_completed_session_ids(exam_id)

    if not session_ids:
        return {
            "sessions_total": 0,
            "sessions_analyzed": 0,
            "sessions_failed": 0,
            "failed_session_ids": [],
            "flags_inserted": 0,
        }

    sessions_analyzed = 0
    failed_session_ids: list[str] = []
    flags_inserted_total = 0

    with httpx.Client() as client:
        for session_id in session_ids:
            try:
                request = load_session_request(
                    session_id,
                    trigger_type=TriggerType.EXAM_BATCH,
                    prompt_version=PROMPT_VERSION,
                )
            except ValueError:
                failed_session_ids.append(session_id)
                continue

            provider_chain = _build_provider_chain(runtime_config)
            run_id = create_analysis_run(request, provider_chain=provider_chain)

            if request.input_stats.empty_telemetry:
                _complete_no_data_run(request=request, run_id=run_id)
                sessions_analyzed += 1
                continue

            try:
                execution_result = analyze_request(
                    request,
                    runtime_config=runtime_config,
                    client=client,
                )
            except AllProvidersFailedError as exc:
                _complete_failed_run(
                    run_id=run_id,
                    input_stats=request.input_stats.model_dump(mode="json"),
                    attempts=[attempt.model_dump(mode="json") for attempt in exc.attempts],
                    error_summary=exc.last_error,
                )
                failed_session_ids.append(session_id)
                continue
            except Exception as exc:
                _complete_failed_run(
                    run_id=run_id,
                    input_stats=request.input_stats.model_dump(mode="json"),
                    attempts=[],
                    error_summary=str(exc),
                )
                failed_session_ids.append(session_id)
                continue

            chunk_count = execution_result.attempts[-1].chunk_count if execution_result.attempts else 0
            input_stats = request.input_stats.model_copy(update={"chunk_count": chunk_count})

            delete_existing_ai_flags(request.session_id)
            inserted = insert_ai_flags(
                session_id=request.session_id,
                analysis_run_id=run_id,
                flags=execution_result.flags,
            )
            complete_analysis_run(
                run_id,
                status=RunStatus.SUCCESS,
                provider_used=execution_result.provider_used,
                model_used=execution_result.model_used,
                fallback_used=execution_result.fallback_used,
                attempts=[attempt.model_dump(mode="json") for attempt in execution_result.attempts],
                input_stats=input_stats.model_dump(mode="json"),
                flags_inserted=inserted,
                error_summary=None,
            )
            sessions_analyzed += 1
            flags_inserted_total += inserted

    return {
        "sessions_total": len(session_ids),
        "sessions_analyzed": sessions_analyzed,
        "sessions_failed": len(failed_session_ids),
        "failed_session_ids": failed_session_ids,
        "flags_inserted": flags_inserted_total,
    }


def _build_runtime_config() -> AnalysisRuntimeConfig:
    try:
        return settings.build_analysis_config()
    except AnalysisConfigError as exc:
        raise HTTPException(status_code=503, detail=f"Analysis configuration error: {exc}") from exc


def _build_provider_chain(runtime_config: AnalysisRuntimeConfig) -> list[dict]:
    return [
        {
            "provider": provider.name,
            "model": provider.model,
            "position": index + 1,
            "enabled": True,
        }
        for index, provider in enumerate(runtime_config.provider_order)
    ]


def _complete_no_data_run(*, request, run_id: str) -> dict:
    delete_existing_ai_flags(request.session_id)
    input_stats = request.input_stats.model_copy(update={"chunk_count": 0})
    complete_analysis_run(
        run_id,
        status=RunStatus.NO_DATA,
        provider_used=None,
        model_used=None,
        fallback_used=False,
        attempts=[],
        input_stats=input_stats.model_dump(mode="json"),
        flags_inserted=0,
        error_summary=None,
    )
    return {
        "session_id": request.session_id,
        "flags_inserted": 0,
        "analysis_run_id": run_id,
        "provider_used": None,
        "fallback_used": False,
    }


def _complete_failed_run(
    *,
    run_id: str,
    input_stats: dict,
    attempts: list[dict],
    error_summary: str,
) -> None:
    complete_analysis_run(
        run_id,
        status=RunStatus.FAILED,
        provider_used=None,
        model_used=None,
        fallback_used=False,
        attempts=attempts,
        input_stats=input_stats,
        flags_inserted=0,
        error_summary=error_summary,
    )
