# Architectural Decisions Log

This document tracks significant architectural decisions made during the design and execution phases of the Exam Monitor system.

## Database Design

* **Decision 1 — Heartbeat Design:** Using Option 3. Agent pings every 30 seconds updating `last_heartbeat_at` in `exam_sessions` only. Local uptime log maintained by agent and included in telemetry batch. No heartbeats table.
* **Decision 2 — Sync Jitter:** In Phase 6, the agent sync interval must be randomised between 55 and 65 seconds instead of exactly 60 to prevent simultaneous connection spikes on the Supabase free tier.
* **Decision 3 — UUIDs:** All primary keys use UUIDs via `uuid_generate_v4()`.
* **Decision 4 — Session ID in telemetry:** Tables 6 through 10 reference `session_id` from `exam_sessions` instead of `student_id` and `exam_id` directly.

* **Decision 5 � AI Communication:** The AI must completely hide its internal thought process from all future responses, providing only clean, direct instructions.
