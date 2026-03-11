create index if not exists idx_keystroke_logs_session_id
  on keystroke_logs(session_id);

create index if not exists idx_window_logs_session_id
  on window_logs(session_id);

create index if not exists idx_clipboard_logs_session_id
  on clipboard_logs(session_id);

create index if not exists idx_flagged_events_session_id_flag_type
  on flagged_events(session_id, flag_type);

create index if not exists idx_telemetry_syncs_session_id_sync_number
  on telemetry_syncs(session_id, sync_number);
