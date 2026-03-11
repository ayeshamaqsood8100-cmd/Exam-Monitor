import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer
from backend.config.settings import settings

api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def _get_student_agent_secret() -> str:
    return settings.STUDENT_AGENT_TOKEN_SECRET or settings.BACKEND_API_KEY


def _encode_segment(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_segment(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _sign_token_payload(payload_segment: str) -> str:
    signature = hmac.new(
        _get_student_agent_secret().encode("utf-8"),
        payload_segment.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _encode_segment(signature)


def create_student_agent_token(*, session_id: str, exam_id: str) -> str:
    now = int(time.time())
    payload = {
        "v": 1,
        "session_id": session_id,
        "exam_id": exam_id,
        "iat": now,
        "exp": now + int(settings.STUDENT_AGENT_TOKEN_TTL_SECONDS),
    }
    payload_segment = _encode_segment(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature_segment = _sign_token_payload(payload_segment)
    return f"{payload_segment}.{signature_segment}"


def verify_student_agent_token(token: str) -> dict[str, Any]:
    try:
        payload_segment, signature_segment = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student agent token.",
        ) from exc

    expected_signature = _sign_token_payload(payload_segment)
    if not secrets.compare_digest(signature_segment, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student agent token.",
        )

    try:
        payload = json.loads(_decode_segment(payload_segment).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student agent token payload.",
        ) from exc

    expires_at = int(payload.get("exp", 0))
    if expires_at <= int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Student agent token expired.",
        )

    if not payload.get("session_id") or not payload.get("exam_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student agent token payload.",
        )

    return payload


async def verify_api_key(api_key: str | None = Security(api_key_scheme)):
    if not api_key or not secrets.compare_digest(api_key, settings.BACKEND_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key."
        )
    return api_key


async def verify_student_agent_auth(
    api_key: str | None = Security(api_key_scheme),
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> dict[str, Any]:
    if api_key and secrets.compare_digest(api_key, settings.BACKEND_API_KEY):
        return {"kind": "api_key"}

    if bearer and bearer.scheme.lower() == "bearer":
        return {"kind": "session_token", "claims": verify_student_agent_token(bearer.credentials)}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing student agent authorization.",
    )


def authorize_session_access(session_id: str, auth: dict[str, Any]) -> None:
    if auth.get("kind") == "api_key":
        return

    claims = auth.get("claims") or {}
    if str(claims.get("session_id")) != str(session_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student agent token does not match this session.",
        )



