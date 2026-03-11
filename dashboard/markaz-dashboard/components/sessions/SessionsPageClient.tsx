"use client";

import React, { useState, useEffect } from "react";
import { type ExamSummary, type SessionWithStudent } from "@/lib/sessions";
import { THEME } from "@/constants/theme";
import { useSessionPolling } from "@/hooks/useSessionPolling";
import SessionsTable from "@/components/sessions/SessionsTable";
import Card from "@/components/ui/Card";

interface SessionsPageClientProps {
    examId: string;
    initialSessions: SessionWithStudent[];
    exam: ExamSummary;
    onForceStopSession: (sessionId: string) => Promise<{ error?: string }>;
}

function buildRestoreSessionSql(examId: string): string {
    return `with target_student as (
  select id
  from students
  where erp = trim('ENTER_ERP_HERE')
  order by created_at desc nulls last, id desc
  limit 1
),
target_session as (
  select s.id
  from exam_sessions s
  join target_student st on st.id = s.student_id
  where s.exam_id = '${examId}'
  order by coalesce(s.session_start, s.created_at) desc, s.created_at desc, s.id desc
  limit 1
)
update exam_sessions s
set
  status = 'active',
  session_end = null,
  last_heartbeat_at = now()
from target_session ts
where s.id = ts.id
returning s.id, s.student_id, s.exam_id, s.status, s.session_end, s.last_heartbeat_at;`;
}

function buildStudentUpsertSql(): string {
    return `with existing_student as (
  select id
  from students
  where erp = trim('ENTER_ERP_HERE')
  order by created_at desc nulls last, id desc
  limit 1
),
updated as (
  update students
  set name = trim('ENTER_STUDENT_NAME_HERE')
  where id in (select id from existing_student)
  returning id, name, erp, created_at
),
inserted as (
  insert into students (name, erp)
  select trim('ENTER_STUDENT_NAME_HERE'), trim('ENTER_ERP_HERE')
  where not exists (select 1 from existing_student)
  returning id, name, erp, created_at
)
select *
from updated
union all
select *
from inserted;`;
}

interface SqlSnippetCardProps {
    title: string;
    description: string;
    sql: string;
    copyKey: string;
    copiedKey: string | null;
    onCopy: (key: string, sql: string) => Promise<void>;
}

function SqlSnippetCard({
    title,
    description,
    sql,
    copyKey,
    copiedKey,
    onCopy,
}: SqlSnippetCardProps): React.JSX.Element {
    return (
        <Card style={{ padding: "20px 22px", flex: "1 1 420px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "flex-start", marginBottom: "10px", flexWrap: "wrap" }}>
                <div>
                    <div style={{ color: THEME.textPrimary, fontSize: "14px", fontWeight: 700 }}>{title}</div>
                    <div style={{ color: THEME.textSecondary, fontSize: "12px", marginTop: "6px", lineHeight: 1.5 }}>{description}</div>
                </div>
                <button
                    onClick={() => void onCopy(copyKey, sql)}
                    style={{
                        background: "transparent",
                        border: `1px solid ${THEME.cyan}`,
                        color: THEME.cyan,
                        padding: "6px 12px",
                        borderRadius: "8px",
                        fontSize: "12px",
                        fontWeight: 700,
                        cursor: "pointer",
                        whiteSpace: "nowrap",
                    }}
                >
                    {copiedKey === copyKey ? "Copied" : "Copy SQL"}
                </button>
            </div>
            <textarea
                readOnly
                value={sql}
                spellCheck={false}
                style={{
                    width: "100%",
                    minHeight: "260px",
                    resize: "vertical",
                    background: "rgba(0,0,0,0.32)",
                    color: THEME.textPrimary,
                    border: `1px solid ${THEME.cardBorder}`,
                    borderRadius: "12px",
                    padding: "14px",
                    fontFamily: THEME.fontMono,
                    fontSize: "12px",
                    lineHeight: 1.55,
                }}
            />
        </Card>
    );
}

export default function SessionsPageClient({ examId, initialSessions, exam, onForceStopSession }: SessionsPageClientProps): React.JSX.Element {
    const { sessions, setSessions, lastRefreshed } = useSessionPolling(examId, initialSessions, 5000);
    const [stoppingIds, setStoppingIds] = useState<Set<string>>(new Set());
    const [isMounted, setIsMounted] = useState(false);
    const [copiedKey, setCopiedKey] = useState<string | null>(null);

    useEffect(() => {
        setIsMounted(true);
    }, []);

    const activeCount = sessions.filter(s => s.display_status === "ACTIVE").length;
    const pausedCount = sessions.filter(s => s.display_status === "PAUSED").length;
    const attentionCount = sessions.filter(s => s.needs_attention).length;
    const restoreSessionSql = buildRestoreSessionSql(examId);
    const studentUpsertSql = buildStudentUpsertSql();

    const handleForceStop = async (sessionId: string) => {
        setStoppingIds(prev => {
            const next = new Set(prev);
            next.add(sessionId);
            return next;
        });

        // Optimistic UI update
        setSessions(prev => prev.map(s =>
            s.id === sessionId ?
                {
                    ...s,
                    status: "terminated",
                    heartbeat_status: "terminated",
                    display_status: "TERMINATED",
                    needs_attention: false,
                    attention_reason: null,
                    can_restart: false,
                    session_end: new Date().toISOString(),
                } : s
        ));

        await onForceStopSession(sessionId);

        setStoppingIds(prev => {
            const next = new Set(prev);
            next.delete(sessionId);
            return next;
        });
    };

    const formatTime = (d: Date) => {
        return d.toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false // Force 24 hr for technical readout
        });
    };

    const handleCopySql = async (key: string, sql: string) => {
        try {
            await navigator.clipboard.writeText(sql);
            setCopiedKey(key);
            window.setTimeout(() => {
                setCopiedKey((current) => (current === key ? null : current));
            }, 1600);
        } catch {
            window.alert("Copy failed. Please select the SQL manually.");
        }
    };

    return (
        <div>
            {/* Optional Top Warning Banner */}
            {exam.force_stop && (
                <div
                    style={{
                        background: `${THEME.pink}1A`, // ~10% opacity
                        border: `1px solid ${THEME.pink}4D`, // ~30% opacity
                        color: THEME.pink,
                        padding: "16px",
                        borderRadius: "8px",
                        marginBottom: "24px",
                        fontWeight: "bold",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        letterSpacing: "0.5px"
                    }}
                >
                    EXAM FORCE STOPPED — All sessions have been terminated.
                </div>
            )}

            {/* Header Area */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>

                <div>
                    <div style={{ color: THEME.textMuted, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" }}>
                        {exam.class_number}
                    </div>
                    <h1 style={{ color: THEME.textPrimary, fontSize: "26px", fontWeight: "bold", margin: 0 }}>
                        {exam.exam_name}
                    </h1>
                    <div style={{ color: THEME.textMuted, fontFamily: THEME.fontMono, fontSize: "12px", marginTop: "12px" }}>
                        Last refreshed: {isMounted ? formatTime(lastRefreshed) : null}
                    </div>
                </div>

                {/* Header Badges */}
                <div style={{ display: "flex", gap: "12px" }}>
                    <div
                        style={{
                            background: `${THEME.cyan}1A`,
                            border: `1px solid ${THEME.cyan}33`,
                            color: THEME.cyan,
                            padding: "6px 16px",
                            borderRadius: "20px",
                            fontSize: "14px",
                            fontWeight: 600,
                            display: "flex",
                            alignItems: "center",
                            gap: "8px"
                        }}
                    >
                        <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: THEME.cyan, animation: "breathe 2s infinite" }} />
                        {activeCount} Active
                    </div>

                    {attentionCount > 0 && (
                        <div
                            style={{
                                background: `${THEME.pink}1A`,
                                border: `1px solid ${THEME.pink}33`,
                                color: THEME.pink,
                                padding: "6px 16px",
                                borderRadius: "20px",
                                fontSize: "14px",
                                fontWeight: 600,
                                display: "flex",
                                alignItems: "center",
                                gap: "8px"
                            }}
                        >
                            <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: THEME.pink }} />
                            {attentionCount} Needs Attention
                        </div>
                    )}

                    {pausedCount > 0 && (
                        <div
                            style={{
                                background: `${THEME.yellow}1A`,
                                border: `1px solid ${THEME.yellow}33`,
                                color: THEME.yellow,
                                padding: "6px 16px",
                                borderRadius: "20px",
                                fontSize: "14px",
                                fontWeight: 600,
                                display: "flex",
                                alignItems: "center",
                                gap: "8px"
                            }}
                        >
                            <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: THEME.yellow }} />
                            {pausedCount} Paused
                        </div>
                    )}
                </div>

            </div>

            {/* Neon divider line */}
            <div
                style={{
                    height: "1px",
                    background: `linear-gradient(90deg, transparent, ${THEME.cyan}26, transparent)`,
                    marginBottom: "32px",
                }}
            />

            <div style={{ marginBottom: "32px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: "16px", flexWrap: "wrap", marginBottom: "14px" }}>
                    <div>
                        <div style={{ color: THEME.textPrimary, fontSize: "13px", fontWeight: 700 }}>Operational SQL</div>
                        <div style={{ color: THEME.textMuted, fontSize: "12px", marginTop: "6px", maxWidth: "760px" }}>
                            Replace the placeholders before running in Supabase. The restore query is scoped to this exam only, which makes it safer than reviving the student&apos;s latest session across every exam.
                        </div>
                    </div>
                    <div style={{ color: THEME.textMuted, fontFamily: THEME.fontMono, fontSize: "11px" }}>
                        Exam ID: {examId}
                    </div>
                </div>
                <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
                    <SqlSnippetCard
                        title="Restore Session By ERP"
                        description="Reactivates the latest session for this ERP inside the current exam only. If the exam was globally force-stopped, clear that first or the agent will shut down again on the next heartbeat."
                        sql={restoreSessionSql}
                        copyKey="restore-session"
                        copiedKey={copiedKey}
                        onCopy={handleCopySql}
                    />
                    <SqlSnippetCard
                        title="Add Or Update Student"
                        description="Creates the student if the ERP does not exist yet. If it already exists, this updates the student name instead of inserting a duplicate."
                        sql={studentUpsertSql}
                        copyKey="upsert-student"
                        copiedKey={copiedKey}
                        onCopy={handleCopySql}
                    />
                </div>
            </div>

            <SessionsTable
                sessions={sessions}
                onForceStop={handleForceStop}
                stoppingIds={stoppingIds}
            />
        </div>
    );
}
