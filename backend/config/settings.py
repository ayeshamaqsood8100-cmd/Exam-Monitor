from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


ProviderName = Literal["deepseek", "groq", "openrouter"]


class AnalysisConfigError(RuntimeError):
    """Raised when the provider-agnostic analysis configuration is invalid."""


@dataclass(frozen=True)
class ProviderConfig:
    name: ProviderName
    model: str
    api_key: str
    max_input_tokens: int


@dataclass(frozen=True)
class AnalysisRuntimeConfig:
    provider_order: list[ProviderConfig]
    timeout_seconds: float
    max_retries_per_provider: int
    retry_backoff_seconds: float
    output_token_reserve: int
    chunk_window_minutes: int
    chunk_overlap_seconds: int
    max_estimated_chars_per_token: float
    dedup_time_tolerance_seconds: int


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    BACKEND_API_KEY: str
    FRONTEND_URL: str

    AI_PROVIDER_ORDER: str = "deepseek,groq,openrouter"
    AI_TIMEOUT_SECONDS: float = 45.0
    AI_MAX_RETRIES_PER_PROVIDER: int = 2
    AI_RETRY_BACKOFF_SECONDS: float = 2.0
    AI_OUTPUT_TOKEN_RESERVE: int = 800
    AI_CHUNK_WINDOW_MINUTES: int = 20
    AI_CHUNK_OVERLAP_SECONDS: int = 30
    AI_MAX_ESTIMATED_CHARS_PER_TOKEN: float = 3.5
    DEDUP_TIME_TOLERANCE_SECONDS: int = 60

    DEEPSEEK_API_KEY: str | None = None
    DEEPSEEK_MODEL: str | None = None
    DEEPSEEK_MAX_INPUT_TOKENS: int = 64000

    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str | None = None
    GROQ_MAX_INPUT_TOKENS: int = 24000

    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_MODEL: str | None = None
    OPENROUTER_MAX_INPUT_TOKENS: int = 32000

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        return [
            "http://localhost:3000",
            self.FRONTEND_URL,
        ]

    def build_analysis_config(self) -> AnalysisRuntimeConfig:
        if self.DEDUP_TIME_TOLERANCE_SECONDS < self.AI_CHUNK_OVERLAP_SECONDS:
            raise AnalysisConfigError(
                "DEDUP_TIME_TOLERANCE_SECONDS must be greater than or equal to AI_CHUNK_OVERLAP_SECONDS."
            )

        provider_order_names = [name.strip().lower() for name in self.AI_PROVIDER_ORDER.split(",") if name.strip()]
        if not provider_order_names:
            raise AnalysisConfigError("AI_PROVIDER_ORDER must contain at least one provider.")

        providers: list[ProviderConfig] = []
        seen: set[str] = set()
        for name in provider_order_names:
            if name in seen:
                continue
            seen.add(name)

            if name == "deepseek":
                providers.append(self._build_provider_config(
                    name="deepseek",
                    api_key=self.DEEPSEEK_API_KEY,
                    model=self.DEEPSEEK_MODEL,
                    max_input_tokens=self.DEEPSEEK_MAX_INPUT_TOKENS,
                ))
                continue

            if name == "groq":
                providers.append(self._build_provider_config(
                    name="groq",
                    api_key=self.GROQ_API_KEY,
                    model=self.GROQ_MODEL,
                    max_input_tokens=self.GROQ_MAX_INPUT_TOKENS,
                ))
                continue

            if name == "openrouter":
                providers.append(self._build_provider_config(
                    name="openrouter",
                    api_key=self.OPENROUTER_API_KEY,
                    model=self.OPENROUTER_MODEL,
                    max_input_tokens=self.OPENROUTER_MAX_INPUT_TOKENS,
                ))
                continue

            raise AnalysisConfigError(f"Unsupported AI provider '{name}' in AI_PROVIDER_ORDER.")

        if not providers:
            raise AnalysisConfigError("No enabled AI providers found in AI_PROVIDER_ORDER.")

        return AnalysisRuntimeConfig(
            provider_order=providers,
            timeout_seconds=self.AI_TIMEOUT_SECONDS,
            max_retries_per_provider=self.AI_MAX_RETRIES_PER_PROVIDER,
            retry_backoff_seconds=self.AI_RETRY_BACKOFF_SECONDS,
            output_token_reserve=self.AI_OUTPUT_TOKEN_RESERVE,
            chunk_window_minutes=self.AI_CHUNK_WINDOW_MINUTES,
            chunk_overlap_seconds=self.AI_CHUNK_OVERLAP_SECONDS,
            max_estimated_chars_per_token=self.AI_MAX_ESTIMATED_CHARS_PER_TOKEN,
            dedup_time_tolerance_seconds=self.DEDUP_TIME_TOLERANCE_SECONDS,
        )

    def _build_provider_config(
        self,
        *,
        name: ProviderName,
        api_key: str | None,
        model: str | None,
        max_input_tokens: int,
    ) -> ProviderConfig:
        if not api_key:
            raise AnalysisConfigError(
                f"{name.upper()}_API_KEY is required because '{name}' is listed in AI_PROVIDER_ORDER."
            )
        if not model:
            raise AnalysisConfigError(
                f"{name.upper()}_MODEL is required because '{name}' is listed in AI_PROVIDER_ORDER."
            )
        if name == "openrouter" and "/" not in model:
            raise AnalysisConfigError(
                "OPENROUTER_MODEL must use a namespaced provider/model format such as 'deepseek/deepseek-chat'."
            )
        if max_input_tokens <= 0:
            raise AnalysisConfigError(f"{name.upper()}_MAX_INPUT_TOKENS must be greater than zero.")

        return ProviderConfig(
            name=name,
            api_key=api_key,
            model=model,
            max_input_tokens=max_input_tokens,
        )


settings = Settings()
