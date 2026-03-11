create or replace function process_exam_session_heartbeat(target_session_id uuid)
returns table(updated boolean, force_stop boolean)
language sql
as $$
  with session_row as (
    select es.id, es.status, e.force_stop
    from exam_sessions es
    left join exams e on e.id = es.exam_id
    where es.id = target_session_id
  ),
  completed_or_terminated as (
    select true as updated, true as force_stop
    from session_row
    where status in ('completed', 'terminated')
  ),
  paused_session as (
    select true as updated, false as force_stop
    from session_row
    where status = 'paused'
  ),
  heartbeat_update as (
    update exam_sessions es
    set last_heartbeat_at = now()
    where es.id = target_session_id
      and exists (
        select 1
        from session_row sr
        where sr.id = es.id
          and sr.status not in ('completed', 'terminated', 'paused')
      )
    returning true as updated
  )
  select updated, force_stop from completed_or_terminated
  union all
  select updated, force_stop from paused_session
  union all
  select hu.updated, coalesce(sr.force_stop, false) as force_stop
  from heartbeat_update hu
  join session_row sr on true
  union all
  select false as updated, false as force_stop
  where not exists (select 1 from session_row);
$$;

create or replace function get_exam_session_dashboard_rows(target_exam_id uuid)
returns table(
  id uuid,
  student_id uuid,
  exam_id uuid,
  session_start timestamptz,
  session_end timestamptz,
  status text,
  last_heartbeat_at timestamptz,
  created_at timestamptz,
  student_name text,
  student_erp text,
  non_system_flag_count integer,
  system_event_count integer,
  early_end_at timestamptz,
  late_end_at timestamptz,
  unexpected_exit_at timestamptz,
  reboot_restart_at timestamptz
)
language sql
as $$
  select
    es.id,
    es.student_id,
    es.exam_id,
    es.session_start,
    es.session_end,
    es.status,
    es.last_heartbeat_at,
    es.created_at,
    st.name as student_name,
    st.erp as student_erp,
    count(*) filter (where fe.flag_type not like 'system_%')::integer as non_system_flag_count,
    count(*) filter (where fe.flag_type like 'system_%')::integer as system_event_count,
    max(fe.flagged_at) filter (where fe.flag_type = 'system_session_ended_before_exam_end' and fe.reviewed = false) as early_end_at,
    max(fe.flagged_at) filter (where fe.flag_type = 'system_session_ended_after_exam_end' and fe.reviewed = false) as late_end_at,
    max(fe.flagged_at) filter (where fe.flag_type = 'system_agent_process_exited_unexpectedly' and fe.reviewed = false) as unexpected_exit_at,
    max(fe.flagged_at) filter (where fe.flag_type = 'system_agent_restarted_after_reboot' and fe.reviewed = false) as reboot_restart_at
  from exam_sessions es
  join students st on st.id = es.student_id
  left join flagged_events fe on fe.session_id = es.id
  where es.exam_id = target_exam_id
  group by
    es.id,
    es.student_id,
    es.exam_id,
    es.session_start,
    es.session_end,
    es.status,
    es.last_heartbeat_at,
    es.created_at,
    st.name,
    st.erp
  order by es.session_start asc;
$$;
