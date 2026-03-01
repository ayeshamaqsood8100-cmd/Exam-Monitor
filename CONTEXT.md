# Project Markaz: Exam Monitoring System Context

## 1. Project Overview
A consent-based, visible desktop monitoring agent and backend system designed to detect cheating during online Moodle examinations. Phones are banned from the physical exam hall and human invigilators supervise students locally; this automated system specifically detects on-device tampering (e.g., hidden virtual machines, copy-pasting from forbidden documents, excessive alt-tabbing).

## 2. Tech Stack
- **Desktop Agent:** Python 3.12 (pynput, pygetwindow, psutil)
- **Backend API:** FastAPI (Python), Supabase SDK
- **Database:** Supabase (PostgreSQL)
- **Frontend Dashboard:** React/Next.js (Vercel)

## 3. Current Status
- **Phase 1 (Environment Setup):** 100% Complete. Python 3.12 `venv` built, architecture established (`agent/`, `backend/`, `dashboard/`), libraries installed, Supabase `.env` keys securely configured.
- **Phase 2 (Database Design):** 100% Complete. All 10 SQL tables built, Row Level Security (RLS) enabled, 160 participants imported via CSV, relationships mathematically verified via Supabase Schema Visualizer.
- **Phase 3 (Backend API):** Pending.
- **Phase 4+ (Agent, Capture, Dashboard):** Pending.

## 4. Key Architectural Decisions (From DECISIONS.md)
1. **Heartbeat Design (Option 3):** No standalone `heartbeats` table. Agent pings every 30s to update `last_heartbeat_at` in `exam_sessions`. Agent maintains a local "offline log" and uploads it every 60s within the telemetry batch.
2. **Sync Jitter:** Telemetry upload interval randomized between 55–65s to prevent massive simultaneous connection spikes on the Supabase free tier database.
3. **UUIDs:** All primary keys uniformly use PostgreSQL `uuid_generate_v4()`.
4. **Session Linking:** Telemetry logs reference `session_id` directly, structurally replacing standalone `student_id` & `exam_id` logic. 
5. **Verification Rule:** Every single creation, modification, or structural connection in this project must be explicitly and visually verified by the human user before the AI is permitted to generate instructions for the next task.
6. **Communication Rule:** The AI must only output clean, direct instructions and never expose its internal thought processes or filler text.

## 5. Database Schema (Supabase)
*All tables have Row Level Security (RLS) ENABLED, locking out public anon access. The backend uses the `service_role` key to naturally bypass RLS.*

1. **`students`**: `id` UUID(PK), `name` TEXT, `erp` TEXT, `created_at` TIMESTAMPTZ
2. **`exams`**: `id` UUID(PK), `exam_name` TEXT, `class_number` TEXT, `start_time` TIMESTAMPTZ, `end_time` TIMESTAMPTZ, `created_at` TIMESTAMPTZ
3. **`exam_sessions`**: `id` UUID(PK), `student_id` UUID(FK), `exam_id` UUID(FK), `session_start` TIMESTAMPTZ, `session_end` TIMESTAMPTZ, `status` TEXT, `last_heartbeat_at` TIMESTAMPTZ, `created_at` TIMESTAMPTZ (Unique Contraint on student_id + exam_id).
4. **`consent_logs`**: `id` UUID(PK), `session_id` UUID(FK), `consented_at` TIMESTAMPTZ, `agent_version` TEXT
5. **`telemetry_syncs`**: `id` UUID(PK), `session_id` UUID(FK), `sync_number` INTEGER, `synced_at` TIMESTAMPTZ, `offline_periods` JSONB
6. **`keystroke_logs`**: `id` UUID(PK), `session_id` UUID(FK), `telemetry_sync_id` UUID(FK), `captured_at` TIMESTAMPTZ, `application` TEXT, `key_data` TEXT
7. **`window_logs`**: `id` UUID(PK), `session_id` UUID(FK), `telemetry_sync_id` UUID(FK), `switched_at` TIMESTAMPTZ, `window_title` TEXT, `application_name` TEXT
8. **`clipboard_logs`**: `id` UUID(PK), `session_id` UUID(FK), `telemetry_sync_id` UUID(FK), `event_type` TEXT, `content` TEXT, `source_application` TEXT, `destination_application` TEXT, `captured_at` TIMESTAMPTZ
9. **`process_logs`**: `id` UUID(PK), `session_id` UUID(FK), `telemetry_sync_id` UUID(FK), `captured_at` TIMESTAMPTZ, `process_name` TEXT
10. **`flagged_events`**: `id` UUID(PK), `session_id` UUID(FK), `flag_type` TEXT, `description` TEXT, `evidence` TEXT, `severity` TEXT, `flagged_at` TIMESTAMPTZ, `reviewed` BOOLEAN

## 6. Unresolved Issues / Next Steps
- **Next Immediate Task:** Begin "Phase 3: Backend API" to map FastAPI endpoints directly to the completed Supabase architecture above.
- **Frontend Dashboard RLS Policies:** If the React dashboard utilizes client-side Supabase authentication instead of routing through the FastAPI backend, distinct RLS `SELECT` policies will need to be drafted later for teacher accounts.
