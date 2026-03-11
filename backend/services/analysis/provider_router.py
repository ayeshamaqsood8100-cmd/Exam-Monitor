from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx

from backend.config.settings import AnalysisRuntimeConfig, ProviderConfig
from backend.services.analysis.models import ProviderAttemptRecord, ProviderExecutionResult, TelemetryAnalysisRequest
from backend.services.analysis.parser import AnalysisParseError, AnalysisValidationError, dedupe_flags, parse_flags_response
from backend.services.analysis.prompt_builder import build_prompt, build_prompt_chunks
from backend.services.analysis.providers.base import BaseProvider, ProviderFailure
from backend.services.analysis.providers.deepseek import DeepSeekProvider
from backend.services.analysis.providers.groq import GroqProvider
from backend.services.analysis.providers.openrouter import OpenRouterProvider


class AllProvidersFailedError(RuntimeError):
    def __init__(self, attempts: list[ProviderAttemptRecord], last_error: str) -> None:
        super().__init__(last_error)
        self.attempts = attempts
        self.last_error = last_error


def analyze_request(
    request: TelemetryAnalysisRequest,
    *,
    runtime_config: AnalysisRuntimeConfig,
    client: httpx.Client,
) -> ProviderExecutionResult:
    providers = [_build_provider(provider_cfg) for provider_cfg in runtime_config.provider_order]
    attempts: list[ProviderAttemptRecord] = []
    last_error = "All configured providers failed."

    for provider_index, provider in enumerate(providers):
        attempted_at = datetime.now(timezone.utc).isoformat()
        chunks = build_prompt_chunks(
            request,
            provider=provider.config,
            runtime_config=runtime_config,
        )
        total_latency_ms = 0
        last_http_status: int | None = None
        last_request_id: str | None = None

        try:
            provider_flags = []
            for chunk in chunks:
                prompt = build_prompt(request, chunk)
                raw_result = _send_with_retries(
                    provider,
                    prompt=prompt,
                    client=client,
                    runtime_config=runtime_config,
                )
                total_latency_ms += raw_result.latency_ms
                last_http_status = raw_result.http_status
                last_request_id = raw_result.request_id
                provider_flags.extend(
                    parse_flags_response(
                        raw_result.raw_text,
                        session_start=request.session_start,
                        session_end=request.session_end,
                    )
                )

            deduped_flags = dedupe_flags(
                provider_flags,
                tolerance_seconds=runtime_config.dedup_time_tolerance_seconds,
            )
            attempts.append(
                ProviderAttemptRecord(
                    provider=provider.name,
                    model=provider.model,
                    attempted_at=attempted_at,
                    outcome="success",
                    latency_ms=total_latency_ms,
                    chunk_count=len(chunks),
                    http_status=last_http_status,
                    request_id=last_request_id,
                    error_reason=None,
                )
            )
            return ProviderExecutionResult(
                provider_used=provider.name,
                model_used=provider.model,
                fallback_used=provider_index > 0,
                attempts=attempts,
                flags=deduped_flags,
            )

        except ProviderFailure as exc:
            last_error = str(exc)
            attempts.append(
                ProviderAttemptRecord(
                    provider=provider.name,
                    model=provider.model,
                    attempted_at=attempted_at,
                    outcome=exc.outcome,
                    latency_ms=total_latency_ms,
                    chunk_count=len(chunks),
                    http_status=exc.http_status,
                    request_id=exc.request_id,
                    error_reason=str(exc),
                )
            )
            continue

        except AnalysisValidationError as exc:
            last_error = str(exc)
            attempts.append(
                ProviderAttemptRecord(
                    provider=provider.name,
                    model=provider.model,
                    attempted_at=attempted_at,
                    outcome="validation_error",
                    latency_ms=total_latency_ms,
                    chunk_count=len(chunks),
                    http_status=last_http_status,
                    request_id=last_request_id,
                    error_reason=str(exc),
                )
            )
            continue

        except AnalysisParseError as exc:
            last_error = str(exc)
            attempts.append(
                ProviderAttemptRecord(
                    provider=provider.name,
                    model=provider.model,
                    attempted_at=attempted_at,
                    outcome="parse_error",
                    latency_ms=total_latency_ms,
                    chunk_count=len(chunks),
                    http_status=last_http_status,
                    request_id=last_request_id,
                    error_reason=str(exc),
                )
            )
            continue

    raise AllProvidersFailedError(attempts=attempts, last_error=last_error)


def _send_with_retries(
    provider: BaseProvider,
    *,
    prompt: str,
    client: httpx.Client,
    runtime_config: AnalysisRuntimeConfig,
):
    total_attempts = max(runtime_config.max_retries_per_provider, 0) + 1
    last_failure: ProviderFailure | None = None
    for attempt in range(total_attempts):
        try:
            return provider.send_prompt(
                prompt=prompt,
                client=client,
                timeout_seconds=runtime_config.timeout_seconds,
                max_output_tokens=runtime_config.output_token_reserve,
            )
        except ProviderFailure as exc:
            last_failure = exc
            if not exc.retryable or attempt == total_attempts - 1:
                raise
            backoff_seconds = runtime_config.retry_backoff_seconds * (attempt + 1)
            time.sleep(backoff_seconds)

    if last_failure is not None:
        raise last_failure
    raise RuntimeError("Provider retry loop exited unexpectedly.")


def _build_provider(provider_config: ProviderConfig) -> BaseProvider:
    if provider_config.name == "deepseek":
        return DeepSeekProvider(provider_config)
    if provider_config.name == "groq":
        return GroqProvider(provider_config)
    if provider_config.name == "openrouter":
        return OpenRouterProvider(provider_config)
    raise ValueError(f"Unsupported provider '{provider_config.name}'.")
