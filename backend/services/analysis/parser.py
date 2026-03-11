from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

from dateutil import parser as date_parser
from pydantic import ValidationError

from backend.services.analysis.models import AnalysisFlag


class AnalysisParseError(RuntimeError):
    pass


class AnalysisValidationError(RuntimeError):
    pass


def parse_flags_response(
    raw_text: str,
    *,
    session_start: str,
    session_end: str | None,
) -> list[AnalysisFlag]:
    candidates = _extract_json_candidates(raw_text)
    if not candidates:
        raise AnalysisParseError("Provider returned no parseable JSON content.")

    last_error = "Unknown parse failure"
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = str(exc)
            continue

        if isinstance(parsed, list):
            payload = {"flags": parsed}
        elif isinstance(parsed, dict):
            payload = parsed
        else:
            last_error = "Provider returned JSON that was not an object or array."
            continue

        raw_flags = payload.get("flags")
        if raw_flags is None and isinstance(parsed, list):
            raw_flags = parsed
        if not isinstance(raw_flags, list):
            last_error = "Provider JSON did not include a 'flags' array."
            continue

        validated_flags: list[AnalysisFlag] = []
        invalid_count = 0
        for item in raw_flags:
            try:
                flag = AnalysisFlag.model_validate(item)
            except ValidationError:
                invalid_count += 1
                continue

            if not _is_flag_in_bounds(flag.flagged_at, session_start=session_start, session_end=session_end):
                invalid_count += 1
                continue

            validated_flags.append(flag)

        if raw_flags and not validated_flags:
            last_error = "Provider returned flags, but none survived validation."
            continue

        return validated_flags

    if "none survived validation" in last_error.lower():
        raise AnalysisValidationError(last_error)
    raise AnalysisParseError(last_error)


def dedupe_flags(flags: list[AnalysisFlag], *, tolerance_seconds: int) -> list[AnalysisFlag]:
    if not flags:
        return []

    tolerance_seconds = max(tolerance_seconds, 0)
    ordered = sorted(flags, key=lambda flag: flag.flagged_at)
    deduped: list[AnalysisFlag] = []

    for flag in ordered:
        evidence_hash = _evidence_hash(flag.evidence)
        matched_index = None
        for idx, existing in enumerate(deduped):
            same_key = (
                existing.flag_type == flag.flag_type
                and existing.severity == flag.severity
                and _evidence_hash(existing.evidence) == evidence_hash
            )
            if not same_key:
                continue
            delta = abs((existing.flagged_at - flag.flagged_at).total_seconds())
            if delta <= tolerance_seconds:
                matched_index = idx
                break

        if matched_index is None:
            deduped.append(flag)
            continue

        existing = deduped[matched_index]
        preferred_description = existing.description
        if len(flag.description.strip()) > len(existing.description.strip()):
            preferred_description = flag.description

        deduped[matched_index] = existing.model_copy(
            update={
                "flagged_at": min(existing.flagged_at, flag.flagged_at),
                "description": preferred_description,
            }
        )

    return deduped


def _extract_json_candidates(raw_text: str) -> list[str]:
    stripped = raw_text.strip()
    candidates: list[str] = []
    if stripped:
        candidates.append(stripped)

    fenced_blocks = re.findall(r"```(?:json)?\s*(.*?)```", raw_text, flags=re.DOTALL | re.IGNORECASE)
    candidates.extend(block.strip() for block in fenced_blocks if block.strip())

    first_brace = stripped.find("{")
    last_brace = stripped.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidates.append(stripped[first_brace:last_brace + 1])

    first_bracket = stripped.find("[")
    last_bracket = stripped.rfind("]")
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        candidates.append(stripped[first_bracket:last_bracket + 1])

    seen: set[str] = set()
    unique: list[str] = []
    for candidate in candidates:
        normalized = candidate.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique


def _is_flag_in_bounds(flagged_at: datetime, *, session_start: str, session_end: str | None) -> bool:
    lower = _to_utc(session_start)
    upper = _to_utc(session_end) if session_end else datetime.now(timezone.utc)
    flagged_utc = flagged_at.astimezone(timezone.utc)
    return lower <= flagged_utc <= upper


def _to_utc(value: str) -> datetime:
    parsed = date_parser.isoparse(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _evidence_hash(evidence: str) -> str:
    normalized = " ".join((evidence or "").strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
