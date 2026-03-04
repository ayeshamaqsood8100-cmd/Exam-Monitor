# Project Markaz: Exam Monitoring System Context

## 1. Project Overview
A consent-based, visible desktop monitoring agent and backend system designed to detect cheating during online Moodle examinations. Phones are banned from the physical exam hall and human invigilators supervise students locally; this automated system specifically detects on-device tampering (e.g., hidden virtual machines, copy-pasting from forbidden documents, excessive alt-tabbing).

## 2. Tech Stack

- **Desktop Agent:** Python 3.12 (pynput, pygetwindow, psutil, tkinter)
- **Backend API:** FastAPI (Python), Supabase SDK
- **Database:** Supabase (PostgreSQL)
- **Frontend Dashboard:** React (Vercel)

## 3. Current Status
- **Phase 1 (Environment Setup):** 100% Complete.
- **Phase 2 (Database Design):** 100% Complete. 
- **Phase 3 (Backend API):** 100% Complete. Deployed successfully to Vercel.
- **Phase 4 (Desktop Agent):** 100% Complete.
- **Phase 5 (Dashboard):** Pending.

## 4. Key Architectural Decisions (From DECISIONS.md)
1. **Heartbeat Design (Option 3):** No standalone `heartbeats` table. Agent pings every 30s to update `last_heartbeat_at` in `exam_sessions`. Agent maintains a local "offline log" and uploads it every 60s within the telemetry batch.
2. **Sync Jitter:** Telemetry upload interval randomized between 55–65s to prevent massive simultaneous connection spikes on the Supabase free tier database.
3. **Session Linking:** Telemetry logs reference `session_id` directly, structurally replacing standalone `student_id` & `exam_id` logic. 
4. **Peek-then-Pop Sync Architecture:** Collectors never `flush()` blindly. `SyncEngine` explicitly executes `peek(limit=500)` to extract a safe bounded slice, attempts the HTTP upload, and solely executes `.pop(count)` upon receiving a confirmed HTTP 200 success. This natively solves unbounded cache bloat and concurrent data loss.
5. **Connection Pooling:** `SyncEngine` utilizes a single `httpx.Client()` context manager per sync cycle to upload all four endpoints securely and rapidly, mitigating overhead.
6. **Graceful Shutdown (`force_stop`):** Heartbeat dynamically returns a `force_stop` boolean flag derived from the `exams` table. The SyncEngine can process this flag to safely invoke the agent's shutdown routine. Global and per-student session end triggers from the dashboard utilize this. Heartbeat update and `force_stop` fetch are now two separate queries due to Supabase 2.9.1 chained update/select incompatibility.
7. **Session End Pipeline:** The agent interface features a passcode-protected 'End Session' button alongside an access code display. Selecting it triggers the `/session/end` backend endpoint, stamping the `exam_sessions` row with a UTC `session_end` timestamp and locking the status to `"completed"`.
8. **Widget Shutdown Threading:** The `MonitoringWidget` dispatches the `on_end_session` callback onto a background `daemon` thread upon passcode success rather than executing it directly. This decisively guards the synchronous `tkinter` `mainloop` from being blocked or killed by the OS during the 15-60+ second HTTP telemetry tear-down operations triggered by `AgentOrchestrator.shutdown()`.
9. **Verification & Communication Constraints:** All new system modifications must be strictly visually confirmed by the human user. The AI must remain direct and concise.
10. **Dependency Splitting:** Backend and agent dependencies are now separated into `requirements.txt` (backend/Vercel) and `agent/requirements.txt` (local agent).
11. **Keystroke Collector:** Keystroke collector window lookup is now isolated in its own try/except to prevent silent event drops.

## 5. Database Schema (Supabase)
*All tables have Row Level Security (RLS) ENABLED, locking out public anon access. The backend uses the `service_role` key to naturally bypass RLS.*

1. **`students`**: `id` UUID(PK), `name` TEXT, `erp` TEXT, `created_at` TIMESTAMPTZ
2. **`exams`**: `id` UUID(PK), `exam_name` TEXT, `class_number` TEXT, `start_time` TIMESTAMPTZ, `end_time` TIMESTAMPTZ, `created_at` TIMESTAMPTZ, `access_code` TEXT, `force_stop` BOOLEAN
3. **`exam_sessions`**: `id` UUID(PK), `student_id` UUID(FK), `exam_id` UUID(FK), `session_start` TIMESTAMPTZ, `session_end` TIMESTAMPTZ, `status` TEXT, `last_heartbeat_at` TIMESTAMPTZ, `created_at` TIMESTAMPTZ (Unique Contraint on student_id + exam_id).
4. **`consent_logs`**: `id` UUID(PK), `session_id` UUID(FK), `consented_at` TIMESTAMPTZ, `agent_version` TEXT
5. **`telemetry_syncs`**: `id` UUID(PK), `session_id` UUID(FK), `sync_number` INTEGER, `synced_at` TIMESTAMPTZ, `offline_periods` JSONB
6. **`keystroke_logs`**: `id` UUID(PK), `session_id` UUID(FK), `telemetry_sync_id` UUID(FK), `captured_at` TIMESTAMPTZ, `application` TEXT, `key_data` TEXT
7. **`window_logs`**: `id` UUID(PK), `session_id` UUID(FK), `telemetry_sync_id` UUID(FK), `switched_at` TIMESTAMPTZ, `window_title` TEXT, `application_name` TEXT
8. **`clipboard_logs`**: `id` UUID(PK), `session_id` UUID(FK), `telemetry_sync_id` UUID(FK), `event_type` TEXT, `content` TEXT, `source_application` TEXT, `destination_application` TEXT, `captured_at` TIMESTAMPTZ
9. **`flagged_events`**: `id` UUID(PK), `session_id` UUID(FK), `flag_type` TEXT, `description` TEXT, `evidence` TEXT, `severity` TEXT, `flagged_at` TIMESTAMPTZ, `reviewed` BOOLEAN

## 6. Phase 4 — Desktop Agent (In Progress)

- ✅ **Step 1 Complete: Agent skeleton**
  - `agent/__init__.py` — formalizes agent as Python package
  - `agent/config.py` — `Settings` class, reads `BACKEND_URL`, `API_KEY`, `EXAM_ID` from `.env`
  - `agent/session.py` — `SessionManager` class, `start(erp)` method, POSTs to `/session/start`, returns `session_id`
  - `agent/main.py` — `AgentOrchestrator` class, validates config, collects ERP, stores `session_id`, coordinates all modules

- ✅ **Step 2 Complete: Heartbeat**
  - `agent/heartbeat.py` — `HeartbeatManager` class, daemon thread, pings `/heartbeat` every 30 seconds, updates `last_heartbeat_at` in Supabase. Awaits `force_stop` responses.

- ✅ **Step 3 Complete: Consent flow**
  - `agent/consent.py` — `ConsentManager` class, displays IBA honour pledge, records consent via `/consent`, returns exam access code
  - `backend/routes/consent.py` — updated to fetch and return `access_code` from `exams` table after recording consent

- ✅ **Step 4 Complete: Collectors** 
  - `agent/collectors/window_collector.py`, `clipboard_collector.py`, `keystroke_collector.py`. 
  - Single-responsibility daemon background threads buffering hardware events natively with strict threading locks and atomic `.peek()` and `.pop()` capacity logic.

- ✅ **Step 5 Complete: Staggered sync engine**
  - `agent/sync.py` — `SyncEngine` class. Implements 55-65s interval randomized jitter cycles. Extracts slices from all collectors, uploads simultaneously through a single `httpx.Client` cache, populates and securely manages offline tracking arrays securely natively.

- ✅ **Step 6 Complete: Graceful shutdown**
  - `backend/models/heartbeat.py` & `backend/services/heartbeat_service.py` & `backend/routes/heartbeat.py` updated to return the dynamic `force_stop` flag from the database upon every heartbeat tick. 
  - `backend/routes/session.py` expanded with `POST /session/end` architecture to logically lock an active session locally to 'completed'.
  - `agent/widget.py` — Created `MonitoringWidget` running a strictly bound `tkinter` daemon overlay securely clamped to the desktop viewport, managing student consent payload state and passcode shutdown authentication.
  - `agent/heartbeat.py` & `agent/main.py` — Implemented thread-safe `AgentOrchestrator.shutdown()` bounded sequence executing strict HTTP timeouts, forcing a final synchronous telemetry buffer pop before issuing a clean `tk.destroy()` to safely exit the main thread.

## 7. Next Immediate Task
- **Begin Phase 5 — Dashboard:** Initialize the React/Next.js dashboard to visualize telemetry, sessions, and flagged events.
