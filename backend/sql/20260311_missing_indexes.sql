create index if not exists idx_exam_sessions_exam_id
  on exam_sessions(exam_id);

create index if not exists idx_exam_sessions_student_id
  on exam_sessions(student_id);

create index if not exists idx_exam_sessions_status
  on exam_sessions(status);

create index if not exists idx_flagged_events_session_id
  on flagged_events(session_id);

create index if not exists idx_consent_logs_session_id
  on consent_logs(session_id);
