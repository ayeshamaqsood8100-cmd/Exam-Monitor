import httpx
import json
from backend.config.settings import settings
from backend.services.database import db

def run_analysis(exam_id: str) -> dict:
    # Fetch all completed sessions for this exam
    sessions_res = db.client.table("exam_sessions").select(
        "id, session_start, session_end, student_id"
    ).eq("exam_id", exam_id).eq("status", "completed").execute()
    
    if not sessions_res.data:
        return {"sessions_analyzed": 0, "flags_inserted": 0}

    sessions_analyzed = 0
    flags_inserted = 0

    with httpx.Client(timeout=60) as client:
        for session in sessions_res.data:
            session_id = session["id"]
            
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
                "application, key_data"
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
            
            prompt = f"""You are an academic integrity analysis system for IBA Karachi, a top university in Pakistan.

EXAM CONTEXT:
- University exam conducted on Moodle LMS on student laptops in a physical exam hall
- Exam duration: approximately 2 hours
- Internet browsing is allowed — students may look up references, datasets, documentation
- Phones are physically banned from the hall
- Human invigilators are present in the room watching students
- Exam formats include: written answers, MCQs, coding problems, Excel/spreadsheet tasks
- Subjects vary: CS, programming, business, finance, math, statistics
- Students are expected to TYPE their own answers — they may reference material but must write answers themselves
- It is completely normal for students to copy short references, dataset values, formula names, question text, or numbers from any source

STRICT RULES BEING ENFORCED:
1. No use of AI tools of any kind (ChatGPT, Google Gemini, Copilot, Claude, Bard, character.ai, any AI assistant or writing tool)
2. No communication with other students or anyone outside during the exam
3. No receiving or sharing complete answers, solutions, or files with others
4. Students must not submit answers written by someone else — including answers uploaded to the LMS by an outsider that the student is copying from
5. Students must not enter another student's ERP or name
6. Pasting a complete answer, essay, code solution, or pre-written response into Moodle is forbidden even if the source looks legitimate

STUDENT SESSION DATA:
Student: {student_data.get('name')} (ERP: {student_data.get('erp')})
Session start: {session.get('session_start')}
Session end: {session.get('session_end')}
Total keystrokes typed: {len(keystrokes_res.data) if keystrokes_res.data else 0}

WINDOW ACTIVITY ({len(windows_res.data) if windows_res.data else 0} switches):
{window_text}

CLIPBOARD ACTIVITY ({len(clipboard_res.data) if clipboard_res.data else 0} events):
{clipboard_text}

OFFLINE PERIODS ({len(offline_lines)} gaps detected):
{offline_text}

FLAGGING RULES — READ CAREFULLY:

HIGH severity:
- Any AI tool detected in window titles or application names (ChatGPT, Gemini, Copilot, Claude, Bard, character.ai, any AI assistant)
- Communication apps active during exam (WhatsApp, WhatsApp Web, Telegram, Discord, Teams, Zoom, Gmail, Outlook, any messaging or email app)
- Virtual machine software detected (vmware, virtualbox, parallels)
- A paste INTO Moodle or the exam browser whose CONTENT looks like a complete pre-written answer, a full paragraph response, a complete code solution, or AI-generated text — the key signal is whether the content reads like a finished answer rather than a reference or data value
- Student typed very few keystrokes (under 50 total) for a 2-hour exam — strongly suggests answers were pasted rather than typed

MED severity:
- A paste INTO Moodle whose content looks like a structured answer, code block, or written response even if not perfectly complete
- Switching to file management apps or cloud storage during the exam (Google Drive, OneDrive, Dropbox, File Explorer accessing external drives)
- Repeated switching to note-taking or document apps (Notepad, Word, Google Docs) more than 3 times — suggests pre-written notes being referenced beyond normal lookup
- Any window title or clipboard content containing what appears to be a different student's name or ERP number
- Offline period longer than 90 seconds

LOW severity:
- Switching to non-Moodle browser tabs more than 5 times
- Brief offline periods between 30 and 90 seconds
- Clipboard paste whose content is ambiguous — could be legitimate reference or could be a prepared answer — log it for human review
- Switching to YouTube, social media, or entertainment sites even briefly

CLIPBOARD JUDGMENT INSTRUCTIONS — THIS IS CRITICAL:
- Do NOT flag short pastes of data values, numbers, formula names, question text, or references — these are normal exam behavior
- DO flag pastes whose content reads like a complete answer, essay paragraph, code solution, or pre-written response
- The source application does not matter — a suspicious paste from Word is just as concerning as one from Notepad
- Focus entirely on what the content IS, not where it came from
- When in doubt about clipboard content, flag it as LOW for human review rather than ignoring it
- For evidence, include the actual pasted content truncated to 150 characters

GENERAL INSTRUCTIONS:
- Use exact timestamps from the data for flagged_at
- Evidence must be specific — include actual content, window titles, or app names
- Do not flag normal Moodle navigation, single brief alt-tabs, or obvious reference lookups
- Every flag will be reviewed by a human invigilator — it is better to flag something borderline than to miss real cheating
- An empty array [] is valid if behavior is completely clean

Return ONLY a JSON array. No markdown. No backticks. No explanation. Just the array.
Each object must have exactly these fields:
- flag_type: string
- description: string
- evidence: string
- severity: "HIGH" or "MED" or "LOW"
- flagged_at: ISO 8601 timestamp string
"""

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048}
            }

            try:
                response = client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                text_response = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                
                # Strip markdown blocks if the model generated them
                if text_response.startswith("```json"):
                    text_response = text_response[7:]
                if text_response.startswith("```"):
                    text_response = text_response[3:]
                if text_response.endswith("```"):
                    text_response = text_response[:-3]
                
                text_response = text_response.strip()
                
                flags = json.loads(text_response)
                
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
                
                sessions_analyzed += 1

            except Exception as e:
                # If JSON parsing or Gemini API fails, skip this session and continue
                print(f"Error analyzing session {session_id}: {e}")
                continue

    return {"sessions_analyzed": sessions_analyzed, "flags_inserted": flags_inserted}
