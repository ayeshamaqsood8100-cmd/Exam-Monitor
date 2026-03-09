import httpx
import json
import re
import time
from fastapi import HTTPException
from backend.config.settings import settings
from backend.services.database import db
from backend.services.alert_service import get_existing_system_alerts, restore_system_alerts


IGNORED_KEYS = {
    "Key.shift", "Key.shift_r", "Key.shift_l",
    "Key.ctrl", "Key.ctrl_l", "Key.ctrl_r",
    "Key.alt", "Key.alt_l", "Key.alt_r", "Key.alt_gr",
    "Key.caps_lock",
    "Key.cmd", "Key.cmd_r", "Key.cmd_l",
    "Key.up", "Key.down", "Key.left", "Key.right",
    "Key.f1", "Key.f2", "Key.f3", "Key.f4", "Key.f5", "Key.f6",
    "Key.f7", "Key.f8", "Key.f9", "Key.f10", "Key.f11", "Key.f12",
}


def normalize_app_name(app: str | None) -> str:
    if not app:
        return "Unknown"

    lower = app.lower()
    if "google chrome" in lower or "chrome" in lower:
        return "Chrome"
    if "microsoft edge" in lower or "edge" in lower:
        return "Edge"
    if "firefox" in lower:
        return "Firefox"
    if "excel" in lower:
        return "Excel"
    if "word" in lower:
        return "Word"
    if "whatsapp" in lower:
        return "WhatsApp"
    if "notepad" in lower:
        return "Notepad"
    if "visual studio code" in lower or lower == "code":
        return "VS Code"
    return app


def parse_key_data(raw: str | None) -> str:
    if not raw:
        return ""

    if raw == "Key.space":
        return " "
    if raw == "Key.enter":
        return "[ENTER]"
    if raw == "Key.backspace":
        return "[BS]"
    if raw == "Key.tab":
        return "[TAB]"
    if raw == "Key.delete":
        return "[DEL]"
    if raw == "Key.esc":
        return "[ESC]"

    if raw in IGNORED_KEYS:
        return ""

    if raw.startswith("Key."):
        return ""

    processed = raw
    if len(processed) == 3 and processed.startswith("'") and processed.endswith("'"):
        processed = processed[1]

    if len(processed) == 1 and (ord(processed) < 32 or ord(processed) > 126):
        return ""

    return processed


def apply_backspaces(texts: list[str]) -> list[str]:
    result: list[str] = []
    for char in texts:
        if char == "[BS]":
            if result:
                result.pop()
        else:
            result.append(char)
    return result


def build_keystroke_groups(rows: list[dict]) -> list[dict]:
    if not rows:
        return []

    groups: list[dict] = []
    current_app = normalize_app_name(rows[0].get("application"))
    start_timestamp = rows[0].get("captured_at")
    end_timestamp = rows[0].get("captured_at")
    current_texts: list[str] = []

    initial_parsed = parse_key_data(rows[0].get("key_data"))
    if initial_parsed:
        current_texts.append(initial_parsed)

    for row in rows[1:]:
        normalized_app = normalize_app_name(row.get("application"))
        parsed = parse_key_data(row.get("key_data"))

        if normalized_app == current_app:
            end_timestamp = row.get("captured_at")
            if parsed:
                current_texts.append(parsed)
            continue

        joined_text = "".join(apply_backspaces(current_texts))
        if joined_text.strip():
            groups.append({
                "application": current_app,
                "start_at": start_timestamp,
                "end_at": end_timestamp,
                "text": joined_text,
            })

        current_app = normalized_app
        start_timestamp = row.get("captured_at")
        end_timestamp = row.get("captured_at")
        current_texts = [parsed] if parsed else []

    final_joined_text = "".join(apply_backspaces(current_texts))
    if final_joined_text.strip():
        groups.append({
            "application": current_app,
            "start_at": start_timestamp,
            "end_at": end_timestamp,
            "text": final_joined_text,
        })

    return groups


def _analyze_single_session(
    session_id: str,
    client: httpx.Client,
    *,
    max_attempts: int = 4,
    rate_limit_base_wait_seconds: int = 15,
) -> list[dict]:
    """Core analysis logic for a single session. Returns list of flag dicts."""
    
    # Fetch session info
    session_res = db.client.table("exam_sessions").select(
        "id, session_start, session_end, student_id"
    ).eq("id", session_id).single().execute()
    
    if not session_res.data:
        raise ValueError(f"Session {session_id} not found")
    
    session = session_res.data
    
    # Fetch student info
    student_res = db.client.table("students").select("name, erp").eq("id", session["student_id"]).execute()
    student_data = student_res.data[0] if student_res.data else {"name": "Unknown", "erp": "Unknown"}
    
    # Fetch window logs
    windows_res = db.client.table("window_logs").select(
        "switched_at, application_name, window_title"
    ).eq("session_id", session_id).order("switched_at", desc=False).execute()
    
    # Fetch clipboard logs
    clipboard_res = db.client.table("clipboard_logs").select(
        "event_type, source_application, destination_application, content, captured_at"
    ).eq("session_id", session_id).order("captured_at", desc=False).execute()
    
    # Fetch keystroke logs
    keystrokes_res = db.client.table("keystroke_logs").select(
        "captured_at, application, key_data"
    ).eq("session_id", session_id).order("captured_at", desc=False).execute()
    
    # Fetch telemetry syncs (offline periods)
    telemetry_res = db.client.table("telemetry_syncs").select(
        "offline_periods"
    ).eq("session_id", session_id).execute()
    
    # Format window lines
    window_lines = []
    if windows_res.data:
        for w in windows_res.data:
            window_lines.append(f"[{w.get('switched_at')}] App: {w.get('application_name')} | Title: {w.get('window_title')}")
    window_text = "\n".join(window_lines) if window_lines else "None"
    
    # Format clipboard lines
    clipboard_lines = []
    if clipboard_res.data:
        for c in clipboard_res.data:
            clipboard_lines.append(f"[{c.get('captured_at')}] {c.get('event_type')} from {c.get('source_application')} to {c.get('destination_application')}: {c.get('content')}")
    clipboard_text = "\n".join(clipboard_lines) if clipboard_lines else "None"
    
    # Format offline periods
    offline_lines = []
    if telemetry_res.data:
        for t in telemetry_res.data:
            periods = t.get("offline_periods") or []
            for p in periods:
                offline_lines.append(f"Offline from {p.get('start')} to {p.get('end')} ({p.get('duration_seconds')}s)")
    offline_text = "\n".join(offline_lines) if offline_lines else "None"
    
    parsed_keystroke_groups = build_keystroke_groups(keystrokes_res.data or [])
    keystroke_lines = [
        f"[{group['application']}] {group['start_at']} to {group['end_at']}: \"{group['text']}\""
        for group in parsed_keystroke_groups
    ]
    keystroke_text = "\n".join(keystroke_lines) if keystroke_lines else "None"
    
    prompt = f"""You are an academic integrity analysis system for IBA Karachi, a top university in Pakistan.

EXAM CONTEXT:
- University exam conducted on Moodle LMS on student laptops in a physical exam hall
- Exam duration: approximately 2 hours
- Internet browsing is allowed - students may look up references, datasets, documentation
- Phones are physically banned from the hall
- Human invigilators are present in the room watching students
- Exam formats include: written answers, MCQs, coding problems, Excel/spreadsheet tasks
- Subjects vary: CS, programming, business, finance, math, statistics
- Students are expected to TYPE their own answers - they may reference material but must write answers themselves
- It is completely normal for students to copy short references, dataset values, formula names, question text, or numbers from any source
- The software "Markaz Sentinel" is the monitoring agent itself - it is NOT suspicious

STRICT RULES BEING ENFORCED:
1. No use of AI tools of any kind (ChatGPT, Google Gemini, Copilot, Claude, Bard, character.ai, any AI assistant or writing tool)
2. No communication with other students or anyone outside during the exam (WhatsApp, Telegram, Discord, email, or any messaging)
3. No receiving or sharing complete answers, solutions, or files with others
4. Students must not submit answers written by someone else - including answers uploaded to the LMS by an outsider that the student is copying from
5. Students must not enter another student's ERP or name
6. Pasting a complete answer, essay, code solution, or pre-written response into Moodle is forbidden even if the source looks legitimate
7. No asking for help from anyone - in person, via messaging, or by typing into an AI tool

STUDENT SESSION DATA:
Student: {student_data.get('name')} (ERP: {student_data.get('erp')})
Session start: {session.get('session_start')}
Session end: {session.get('session_end')}

KEYSTROKE CONTENT ({len(keystrokes_res.data) if keystrokes_res.data else 0} keystrokes in {len(parsed_keystroke_groups)} groups):
The following shows what the student actually typed, grouped by application. [ENTER] means Enter key, [BS] means Backspace, [TAB] means Tab.
{keystroke_text}

WINDOW ACTIVITY ({len(windows_res.data) if windows_res.data else 0} switches):
{window_text}

CLIPBOARD ACTIVITY ({len(clipboard_res.data) if clipboard_res.data else 0} events):
{clipboard_text}

OFFLINE PERIODS ({len(offline_lines)} gaps detected):
{offline_text}

FLAGGING RULES - READ ALL DATA CAREFULLY BEFORE FLAGGING:

HIGH severity:
- Student TYPED the name of any AI tool into a browser (e.g. "chatgpt", "gemini", "claude", "copilot", "bard") - this is direct evidence of navigating to an AI tool. Check the KEYSTROKE CONTENT for these keywords.
- Any AI tool detected in WINDOW titles or application names (ChatGPT, Gemini, Copilot, Claude, Bard, character.ai)
- Student TYPED a message asking for help, answers, or solutions in any application (e.g. "can you help me with", "send me the answer", "what is the solution")
- Communication apps active: student typed in WhatsApp, Telegram, Discord, Teams, or any messaging app. Example: typing "send me your files" in WhatsApp is a HIGH flag.
- Virtual machine software detected (vmware, virtualbox, parallels)
- A paste INTO Moodle or the exam browser whose CONTENT looks like a complete pre-written answer, full paragraph, complete code solution, or AI-generated text
- Student typed very few keystrokes (under 50 total) for a 2-hour exam - strongly suggests answers were pasted rather than typed

MED severity:
- Student typed requests for files, notes, or materials in any communication app (e.g. "send me your files right now")
- A paste INTO Moodle whose content looks like a structured answer, code block, or written response even if not perfectly complete
- Switching to file management apps or cloud storage during the exam (Google Drive, OneDrive, Dropbox, File Explorer accessing external drives)
- Repeated switching to note-taking or document apps (Notepad, Word, Google Docs) more than 3 times
- Any window title, clipboard content, or TYPED TEXT containing what appears to be a different student's name or ERP number
- Offline period longer than 90 seconds
- Large copy-paste operations where whole formulas, entire code blocks, or pre-made answers are pasted instead of typed

LOW severity:
- Switching to non-Moodle browser tabs more than 5 times
- Brief offline periods between 30 and 90 seconds
- Clipboard paste whose content is ambiguous - could be legitimate reference or could be a prepared answer
- Switching to YouTube, social media, or entertainment sites even briefly
- Student typed something that looks suspicious but is not clearly a violation - log it for human review

KEYSTROKE ANALYSIS INSTRUCTIONS - THIS IS CRITICAL:
- READ every keystroke group carefully. Students typing "chatgpt" or "gemini" in Chrome are NAVIGATING TO AI TOOLS - this is a HIGH flag.
- Students typing messages like "please send me your files" or "can you help me" in WhatsApp/Chrome are COMMUNICATING - this is a HIGH flag.
- Students typing questions into AI tools like "can you help me with probability distribution" are USING AI - this is a HIGH flag.
- Typing "i did copy" or "i copied alot of stuff" is an ADMISSION of copying - flag it.
- Normal typing in Moodle, Excel formulas, and legitimate application usage is NOT suspicious.
- The monitoring agent "Markaz Sentinel" and its keystrokes (like typing exam codes) should be IGNORED.

CLIPBOARD JUDGMENT INSTRUCTIONS:
- Do NOT flag short pastes of data values, numbers, formula names, question text, or references - these are normal
- DO flag pastes whose content reads like a complete answer, essay paragraph, code solution, or pre-written response
- When in doubt, flag as LOW for human review rather than ignoring
- For evidence, include the actual pasted content truncated to 150 characters

GENERAL INSTRUCTIONS:
- Use exact timestamps from the data for flagged_at
- Evidence must be specific - include actual typed content, window titles, or clipboard content
- Do not flag normal Moodle navigation, single brief alt-tabs, or obvious reference lookups
- Every flag will be reviewed by a human invigilator - it is better to flag something borderline than to miss real cheating
- Any detection is better than no detection - humans cannot manually review 2 hours of data per student but CAN investigate specific flags
- An empty array [] is valid if behavior is completely clean

"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "flag_type": {"type": "STRING", "description": "The type of academic integrity violation"},
                        "description": {"type": "STRING", "description": "A detailed explanation of why this was flagged"},
                        "evidence": {"type": "STRING", "description": "The actual pasted content, window title, or app name (truncated if necessary)"},
                        "severity": {"type": "STRING", "enum": ["HIGH", "MED", "LOW"]},
                        "flagged_at": {"type": "STRING", "description": "ISO 8601 timestamp string"}
                    },
                    "required": ["flag_type", "description", "evidence", "severity", "flagged_at"]
                }
            }
        }
    }

    print(f"\n{'='*60}")
    print(f"ANALYZING: {student_data.get('name')} (ERP: {student_data.get('erp')}) | Session: {session_id[:8]}...")
    print(f"  Keystrokes: {len(keystrokes_res.data) if keystrokes_res.data else 0} | Windows: {len(windows_res.data) if windows_res.data else 0} | Clipboard: {len(clipboard_res.data) if clipboard_res.data else 0} | Keystroke groups: {len(parsed_keystroke_groups)}")
    print(f"  Prompt length: {len(prompt)} chars")
    
    # Call Gemini with retry logic for rate limits
    response = None
    for attempt in range(max_attempts):
        response = client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GEMINI_API_KEY}",
            json=payload
        )
        if response.status_code == 429:
            wait = (attempt + 1) * rate_limit_base_wait_seconds
            print(f"  Rate limited (429). Waiting {wait}s before retry {attempt + 2}/{max_attempts}...")
            time.sleep(wait)
            continue
        response.raise_for_status()
        break
    
    if response is None or response.status_code == 429:
        raise ValueError(f"Rate limit not cleared after {max_attempts} retries for session {session_id}")
    
    data = response.json()
    
    # Gemini 2.5 Flash may return multiple parts (thinking + output).
    parts = data["candidates"][0]["content"]["parts"]
    print(f"  Gemini returned {len(parts)} parts: {[('thought' if 'thought' in p else 'text') for p in parts]}")
    
    text_response = None
    for part in parts:
        if "text" in part:
            text_response = part["text"].strip()
    
    if not text_response:
        print(f"  ERROR: No text part found! Parts: {parts}")
        return []
    
    print(f"  Raw text response ({len(text_response)} chars): {text_response[:300]}...")
    
    # Strip markdown blocks if the model wrapped the output
    if text_response.startswith("```json"):
        text_response = text_response[7:]
    if text_response.startswith("```"):
        text_response = text_response[3:]
    if text_response.endswith("```"):
        text_response = text_response[:-3]
    text_response = text_response.strip()
    
    # Robust multi-strategy JSON parser
    flags = None
    
    # Strategy 1: Direct parse
    try:
        flags = json.loads(text_response)
        print(f"  Strategy 1 (direct parse): {len(flags)} flags")
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Sanitize literal newlines inside strings, then parse
    if flags is None:
        try:
            sanitized = re.sub(r'(?<=[\"])([^\"]*?)\n([^\"]*?)(?=[\"])', 
                              lambda m: m.group(0).replace('\n', ' '), 
                              text_response)
            flags = json.loads(sanitized)
            print(f"  Strategy 2 (sanitized newlines): {len(flags)} flags")
        except (json.JSONDecodeError, Exception):
            pass
    
    # Strategy 3: Split on flag_type boundaries and parse each object
    if flags is None:
        print(f"  Strategy 3 (segment extraction)...")
        segments = re.split(r'(?=\{\s*"flag_type")', text_response)
        flags = []
        for seg in segments:
            seg = seg.strip().rstrip(',').rstrip(']').strip()
            if not seg.startswith('{'):
                continue
            if not seg.endswith('}'):
                last_brace = seg.rfind('}')
                if last_brace > 0:
                    seg = seg[:last_brace + 1]
                else:
                    continue
            # Try direct parse
            try:
                flags.append(json.loads(seg))
                continue
            except json.JSONDecodeError:
                pass
            # Try fixing newlines
            try:
                fixed = seg.replace('\n', ' ').replace('\r', ' ')
                flags.append(json.loads(fixed))
                continue
            except json.JSONDecodeError:
                pass
            # Last resort: extract known fields with regex
            try:
                ft = re.search(r'"flag_type"\s*:\s*"((?:[^"\\]|\\.)*)"', seg)
                desc = re.search(r'"description"\s*:\s*"((?:[^"\\]|\\.)*)"', seg)
                ev = re.search(r'"evidence"\s*:\s*"((?:[^"\\]|\\.)*)"', seg)
                sev = re.search(r'"severity"\s*:\s*"(HIGH|MED|LOW)"', seg)
                fa = re.search(r'"flagged_at"\s*:\s*"((?:[^"\\]|\\.)*)"', seg)
                if ft and sev:
                    flags.append({
                        "flag_type": ft.group(1),
                        "description": desc.group(1) if desc else "See evidence",
                        "evidence": ev.group(1) if ev else "N/A",
                        "severity": sev.group(1),
                        "flagged_at": fa.group(1) if fa else session.get("session_start", "")
                    })
                    continue
            except Exception:
                pass
            print(f"  Could not parse segment: {seg[:100]}...")
        print(f"  Strategy 3 recovered {len(flags)} flags")
    
    if flags is None:
        flags = []
    
    print(f"  TOTAL FLAGS: {len(flags)}")
    return flags


def run_session_analysis(session_id: str) -> dict:
    """Analyze a single session. Deletes existing flags first (idempotent)."""
    system_alerts = get_existing_system_alerts(session_id)
    # Delete any existing flags for this session (makes re-analysis safe)
    db.client.table("flagged_events").delete().eq("session_id", session_id).execute()
    print(f"Cleared existing flags for session {session_id[:8]}...")
    
    with httpx.Client(timeout=120) as client:
        try:
            flags = _analyze_single_session(session_id, client)
            
            flags_inserted = 0
            for flag in flags:
                db.client.table("flagged_events").insert({
                    "session_id": session_id,
                    "flag_type": flag.get("flag_type"),
                    "description": flag.get("description"),
                    "evidence": flag.get("evidence"),
                    "severity": flag.get("severity"),
                    "flagged_at": flag.get("flagged_at"),
                    "reviewed": False
                }).execute()
                flags_inserted += 1

            restore_system_alerts(system_alerts)
            
            return {"session_id": session_id, "flags_inserted": flags_inserted}
        
        except Exception as e:
            restore_system_alerts(system_alerts)
            print(f"Error analyzing session {session_id}: {e}")
            detail = f"Analysis failed: {str(e)}"
            if "Rate limit not cleared" in str(e):
                raise HTTPException(status_code=503, detail=detail)
            raise HTTPException(status_code=500, detail=detail)


def run_analysis(exam_id: str) -> dict:
    """Analyze all completed sessions for an exam (batch mode)."""
    sessions_res = db.client.table("exam_sessions").select(
        "id"
    ).eq("exam_id", exam_id).eq("status", "completed").execute()
    
    if not sessions_res.data:
        return {
            "sessions_total": 0,
            "sessions_analyzed": 0,
            "sessions_failed": 0,
            "failed_session_ids": [],
            "flags_inserted": 0,
        }

    sessions_total = len(sessions_res.data)
    sessions_analyzed = 0
    failed_session_ids: list[str] = []
    flags_inserted = 0

    with httpx.Client(timeout=120) as client:
        for i, session in enumerate(sessions_res.data):
            if i > 0:
                time.sleep(3)
            session_id = session["id"]
            
            try:
                system_alerts = get_existing_system_alerts(session_id)
                # Clear existing flags so reruns stay idempotent.
                db.client.table("flagged_events").delete().eq("session_id", session_id).execute()
                flags = _analyze_single_session(
                    session_id,
                    client,
                    max_attempts=3,
                    rate_limit_base_wait_seconds=5,
                )
                
                for flag in flags:
                    db.client.table("flagged_events").insert({
                        "session_id": session_id,
                        "flag_type": flag.get("flag_type"),
                        "description": flag.get("description"),
                        "evidence": flag.get("evidence"),
                        "severity": flag.get("severity"),
                        "flagged_at": flag.get("flagged_at"),
                        "reviewed": False
                    }).execute()
                    flags_inserted += 1
                restore_system_alerts(system_alerts)
                sessions_analyzed += 1

            except Exception as e:
                restore_system_alerts(system_alerts)
                print(f"Error analyzing session {session_id}: {e}")
                failed_session_ids.append(session_id)
                continue

    return {
        "sessions_total": sessions_total,
        "sessions_analyzed": sessions_analyzed,
        "sessions_failed": len(failed_session_ids),
        "failed_session_ids": failed_session_ids,
        "flags_inserted": flags_inserted,
    }
