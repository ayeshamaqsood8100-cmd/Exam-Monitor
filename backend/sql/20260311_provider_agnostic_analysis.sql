create table if not exists analysis_runs (
  id uuid primary key,
  session_id uuid not null references exam_sessions(id) on delete cascade,
  exam_id uuid not null references exams(id) on delete cascade,
  trigger_type text not null check (trigger_type in ('single_session', 'exam_batch')),
  prompt_version text not null,
  status text null check (status in ('success', 'failed', 'no_data')),
  provider_used text null,
  model_used text null,
  fallback_used boolean not null default false,
  provider_chain jsonb not null,
  attempts jsonb not null,
  input_stats jsonb not null,
  flags_inserted integer not null default 0,
  started_at timestamptz not null,
  finished_at timestamptz null,
  error_summary text null
);

alter table flagged_events
  add column if not exists analysis_run_id uuid null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'flagged_events_analysis_run_id_fkey'
  ) then
    alter table flagged_events
      add constraint flagged_events_analysis_run_id_fkey
      foreign key (analysis_run_id)
      references analysis_runs(id)
      on delete set null;
  end if;
end $$;

create index if not exists idx_analysis_runs_session_id
  on analysis_runs(session_id);

create index if not exists idx_analysis_runs_exam_id
  on analysis_runs(exam_id);

create index if not exists idx_analysis_runs_started_at_desc
  on analysis_runs(started_at desc);

create index if not exists idx_flagged_events_analysis_run_id
  on flagged_events(analysis_run_id);
