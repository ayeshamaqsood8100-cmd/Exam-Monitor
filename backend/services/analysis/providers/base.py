from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

from backend.config.settings import ProviderConfig


@dataclass(frozen=True)
class ProviderRawResult:
    provider: str
    model: str
    raw_text: str
    latency_ms: int
    http_status: int
    request_id: str | None
    usage: dict[str, Any] | None
    outcome: str = "success"


class ProviderFailure(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        provider: str,
        model: str,
        outcome: str,
        http_status: int | None = None,
        request_id: str | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.outcome = outcome
        self.http_status = http_status
        self.request_id = request_id
        self.retryable = retryable


class BaseProvider(ABC):
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self.name = config.name
        self.model = config.model
        self.max_input_tokens = config.max_input_tokens

    @abstractmethod
    def send_prompt(
        self,
        *,
        prompt: str,
        client: httpx.Client,
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> ProviderRawResult:
        raise NotImplementedError


class OpenAICompatibleProvider(BaseProvider):
    base_url: str = ""
    title_header: tuple[str, str] | None = None

    def send_prompt(
        self,
        *,
        prompt: str,
        client: httpx.Client,
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> ProviderRawResult:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        if self.title_header:
            headers[self.title_header[0]] = self.title_header[1]

        payload = {
            "model": self.model,
            "temperature": 0.1,
            "max_tokens": max(max_output_tokens, 1),
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "You are a JSON-only academic integrity analysis system. Return only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
        }

        try:
            response = client.post(self.base_url, json=payload, headers=headers, timeout=timeout_seconds)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise ProviderFailure(
                f"{self.name} transport error: {exc}",
                provider=self.name,
                model=self.model,
                outcome="retryable_error",
                retryable=True,
            ) from exc

        request_id = _extract_request_id(response)
        if response.status_code == 429:
            message = _extract_error_message(response)
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                raise ProviderFailure(
                    f"{self.name} rate limited: {message}",
                    provider=self.name,
                    model=self.model,
                    outcome="retryable_error",
                    http_status=response.status_code,
                    request_id=request_id,
                    retryable=True,
                )
            raise ProviderFailure(
                f"{self.name} quota exhausted: {message}",
                provider=self.name,
                model=self.model,
                outcome="quota_exhausted",
                http_status=response.status_code,
                request_id=request_id,
            )

        if response.status_code >= 500:
            raise ProviderFailure(
                f"{self.name} server error: {_extract_error_message(response)}",
                provider=self.name,
                model=self.model,
                outcome="retryable_error",
                http_status=response.status_code,
                request_id=request_id,
                retryable=True,
            )

        if response.status_code >= 400:
            error_message = _extract_error_message(response)
            if _looks_like_context_too_large(error_message):
                raise ProviderFailure(
                    f"{self.name} context too large: {error_message}",
                    provider=self.name,
                    model=self.model,
                    outcome="context_too_large",
                    http_status=response.status_code,
                    request_id=request_id,
                )
            raise ProviderFailure(
                f"{self.name} request failed: {error_message}",
                provider=self.name,
                model=self.model,
                outcome="fallback_error",
                http_status=response.status_code,
                request_id=request_id,
            )

        data = response.json()
        raw_text = _extract_content_text(data)
        if not raw_text:
            raise ProviderFailure(
                f"{self.name} returned no text content.",
                provider=self.name,
                model=self.model,
                outcome="parse_error",
                http_status=response.status_code,
                request_id=request_id,
            )

        return ProviderRawResult(
            provider=self.name,
            model=self.model,
            raw_text=raw_text,
            latency_ms=int(response.elapsed.total_seconds() * 1000),
            http_status=response.status_code,
            request_id=request_id,
            usage=data.get("usage") if isinstance(data, dict) else None,
        )


def _extract_request_id(response: httpx.Response) -> str | None:
    for key in ("x-request-id", "request-id", "openrouter-request-id"):
        value = response.headers.get(key)
        if value:
            return value
    return None


def _extract_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip()

    if isinstance(payload, dict):
        if isinstance(payload.get("error"), dict):
            return str(payload["error"].get("message") or payload["error"])
        if "error" in payload:
            return str(payload["error"])
        if "message" in payload:
            return str(payload["message"])
    return str(payload)


def _extract_content_text(data: dict[str, Any]) -> str:
    choices = data.get("choices") if isinstance(data, dict) else None
    if not choices:
        return ""

    message = choices[0].get("message", {})
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(str(part.get("text", "")))
            elif isinstance(part, str):
                text_parts.append(part)
        return "\n".join(part.strip() for part in text_parts if part.strip()).strip()
    return ""


def _looks_like_context_too_large(message: str) -> bool:
    lower = message.lower()
    markers = (
        "context length",
        "maximum context",
        "too many tokens",
        "context window",
        "input is too long",
        "request too large",
    )
    return any(marker in lower for marker in markers)
