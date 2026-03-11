"""
Configuration module for the Markaz Exam Monitor agent.

Development runs continue to load from the repo-root `.env`.
Windows packaged builds can fall back to baked values generated into
`agent/build_config.py` during the packaging step.
"""
from __future__ import annotations

import os
from pydantic_settings import BaseSettings


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE_PATH = os.path.join(ROOT_DIR, ".env")

try:
    from . import build_config as _build_config
except ImportError:
    _build_config = None


def _build_default(name: str) -> str | None:
    if _build_config is None:
        return None
    value = getattr(_build_config, name, None)
    return str(value) if value else None


class Settings(BaseSettings):
    """
    Agent settings loaded from environment first, then optional baked build values.
    """

    BACKEND_URL: str | None = _build_default("BACKEND_URL")
    BACKEND_API_KEY: str | None = _build_default("BACKEND_API_KEY")
    EXAM_ID: str | None = _build_default("EXAM_ID")

    class Config:
        env_file = ENV_FILE_PATH
        extra = "ignore"


settings = Settings()

missing_settings = [
    name
    for name in ("BACKEND_URL", "EXAM_ID")
    if not getattr(settings, name, None)
]

if missing_settings:
    missing_str = ", ".join(missing_settings)
    raise RuntimeError(
        f"Missing required agent settings: {missing_str}. "
        "Provide them via environment, repo .env, or generated build_config.py."
    )
