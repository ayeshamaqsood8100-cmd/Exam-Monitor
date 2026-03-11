from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from dateutil import parser as date_parser

from backend.config.settings import AnalysisRuntimeConfig, ProviderConfig
from backend.services.analysis.models import PromptChunk, TelemetryAnalysisRequest


PROMPT_VERSION = "telemetry-flagging-v2"


def estimate_tokens(text: str, chars_per_token: float) -> int:
    if chars_per_token <= 0:
        return len(text)
    return int(len(text) / chars_per_token) + 1


def build_prompt_chunks(
    request: TelemetryAnalysisRequest,
    *,
    provider: ProviderConfig,
    runtime_config: AnalysisRuntimeConfig,
) -> list[PromptChunk]:
    full_chunk = _build_full_chunk(request)
    full_prompt = build_prompt(request, full_chunk)
    input_budget = max(provider.max_input_tokens - runtime_config.output_token_reserve, 1)
    if estimate_tokens(full_prompt, runtime_config.max_estimated_chars_per_token) <= input_budget:
        return [full_chunk.model_copy(update={"index": 1, "total": 1})]

    timeline = _build_timeline(request)
    if not timeline:
        return [full_chunk.model_copy(update={"index": 1, "total": 1})]

    window_minutes = max(runtime_config.chunk_window_minutes, 1)
    chunks = _build_window_chunks(timeline, window_minutes, runtime_config.chunk_overlap_seconds)
    while True:
        prompts_fit = True
        for chunk in chunks:
            prompt = build_prompt(request, chunk)
            if estimate_tokens(prompt, runtime_config.max_estimated_chars_per_token) > input_budget:
                prompts_fit = False
                break

        if prompts_fit or window_minutes <= 1:
            break

        window_minutes = max(window_minutes // 2, 1)
        chunks = _build_window_chunks(timeline, window_minutes, runtime_config.chunk_overlap_seconds)

    total = len(chunks)
    return [
        chunk.model_copy(update={"index": index + 1, "total": total})
        for index, chunk in enumerate(chunks)
    ]


def build_prompt(request: TelemetryAnalysisRequest, chunk: PromptChunk) -> str:
    chunk_range = "entire session"
    if chunk.window_start and chunk.window_end:
        chunk_range = f"{chunk.window_start} to {chunk.window_end}"

    return f"""You are an academic integrity analysis system for IBA Karachi, a top university in Pakistan.

You are analyzing telemetry for exam investigation support. Your job is to produce suspicious activity flags for human review.

Return ONLY valid JSON matching this shape:
{{
  "flags": [
    {{
      "flag_type": "short_machine_readable_name",
      "description": "concise explanation for invigilators",
      "evidence": "specific supporting evidence",
      "severity": "HIGH|MED|LOW",
      "flagged_at": "ISO-8601 timestamp"
    }}
  ]
}}

Important:
- False positives are acceptable because humans will review later.
- Flags are for investigation support, not final judgment.
- Use exact timestamps from the telemetry when available.
- If behavior is clean, return {{"flags":[]}}.
- This chunk may overlap nearby chunks in time; duplicate flags will be deduplicated later.

EXAM CONTEXT:
- Moodle exam on student laptops in a physical exam hall
- Internet reference lookups may be legitimate
- Phones are banned
- Human invigilators are present
- Students must type their own answers
- Short factual pastes may be legitimate
- Markaz Sentinel is the monitoring agent itself and is not suspicious

STRICT RULES:
1. No AI tools of any kind (ChatGPT, Gemini, Claude, Copilot, Bard, character.ai, etc.)
2. No communication with other students or outsiders
3. No receiving or sharing complete answers, files, or solutions
4. No copying answers written by someone else
5. No entering another student's ERP or name
6. No pasting complete pre-written answers or code into Moodle
7. No asking for help from an AI tool or another person

STUDENT:
- Name: {request.student_name}
- ERP: {request.student_erp}
- Session start: {request.session_start}
- Session end: {request.session_end or "Active"}
- Chunk range: {chunk_range}
- Chunk number: {chunk.index}/{chunk.total}

HIGH severity examples:
- typed names of AI tools in browsers
- AI tool window titles/apps
- messages asking for answers/help
- WhatsApp/Telegram/Discord/Teams usage for communication
- virtual machine software
- clear full-answer paste into Moodle
- extremely low typing suggesting pasted work

MED severity examples:
- asking for files/notes/materials
- structured answer or code paste into Moodle
- cloud drive/file manager access
- repeated note/document app switching
- another student's ERP/name appearing
- offline period longer than 90 seconds

LOW severity examples:
- many non-Moodle tab switches
- brief offline periods
- ambiguous clipboard activity
- social media or entertainment sites
- suspicious but unclear behavior worth review

KEYSTROKES:
{_render_section(chunk.keystroke_lines)}

WINDOWS:
{_render_section(chunk.window_lines)}

CLIPBOARD:
{_render_section(chunk.clipboard_lines)}

OFFLINE PERIODS:
{_render_section(chunk.offline_lines)}
"""


def _render_section(lines: list[str]) -> str:
    return "\n".join(lines) if lines else "None"


def _build_full_chunk(request: TelemetryAnalysisRequest) -> PromptChunk:
    return PromptChunk(
        index=1,
        total=1,
        window_start=request.session_start,
        window_end=request.session_end,
        window_lines=[
            f"[{entry.switched_at}] App: {entry.application_name} | Title: {entry.window_title}"
            for entry in request.telemetry.windows
        ],
        clipboard_lines=[
            f"[{entry.captured_at}] {entry.event_type} from {entry.source_application} to {entry.destination_application}: {entry.content}"
            for entry in request.telemetry.clipboard
        ],
        keystroke_lines=[
            f"[{group.application}] {group.start_at} to {group.end_at}: \"{group.text}\""
            for group in request.telemetry.keystrokes
        ],
        offline_lines=[
            f"Offline from {period.start} to {period.end} ({period.duration_seconds}s)"
            for period in request.telemetry.offline_periods
        ],
    )


def _build_timeline(request: TelemetryAnalysisRequest) -> list[tuple[datetime, str, str]]:
    timeline: list[tuple[datetime, str, str]] = []
    for entry in request.telemetry.windows:
        timeline.append((
            _parse_timestamp(entry.switched_at),
            "window",
            f"[{entry.switched_at}] App: {entry.application_name} | Title: {entry.window_title}",
        ))
    for entry in request.telemetry.clipboard:
        timeline.append((
            _parse_timestamp(entry.captured_at),
            "clipboard",
            f"[{entry.captured_at}] {entry.event_type} from {entry.source_application} to {entry.destination_application}: {entry.content}",
        ))
    for group in request.telemetry.keystrokes:
        timeline.append((
            _parse_timestamp(group.start_at),
            "keystroke",
            f"[{group.application}] {group.start_at} to {group.end_at}: \"{group.text}\"",
        ))
    for period in request.telemetry.offline_periods:
        timestamp = period.start or period.synced_at or request.session_start
        timeline.append((
            _parse_timestamp(timestamp),
            "offline",
            f"Offline from {period.start} to {period.end} ({period.duration_seconds}s)",
        ))

    timeline.sort(key=lambda item: (item[0], item[1], item[2]))
    return timeline


def _build_window_chunks(
    timeline: list[tuple[datetime, str, str]],
    window_minutes: int,
    overlap_seconds: int,
) -> list[PromptChunk]:
    if not timeline:
        return [PromptChunk(index=1, total=1)]

    chunks: list[PromptChunk] = []
    start = timeline[0][0]
    max_time = timeline[-1][0]
    window_delta = timedelta(minutes=max(window_minutes, 1))
    overlap_delta = timedelta(seconds=max(overlap_seconds, 0))
    step = window_delta - overlap_delta
    if step <= timedelta(0):
        step = window_delta

    while start <= max_time:
        end = start + window_delta
        bucket: dict[str, list[str]] = defaultdict(list)
        for timestamp, kind, line in timeline:
            if start <= timestamp <= end:
                bucket[kind].append(line)
        if any(bucket.values()):
            chunks.append(
                PromptChunk(
                    index=1,
                    total=1,
                    window_start=start.astimezone(timezone.utc).isoformat(),
                    window_end=end.astimezone(timezone.utc).isoformat(),
                    window_lines=bucket["window"],
                    clipboard_lines=bucket["clipboard"],
                    keystroke_lines=bucket["keystroke"],
                    offline_lines=bucket["offline"],
                )
            )
        start = start + step

    return chunks or [PromptChunk(index=1, total=1)]


def _parse_timestamp(value: str) -> datetime:
    parsed = date_parser.isoparse(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
