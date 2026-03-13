"use client";

import React, { useState, useEffect } from "react";
import { type ExamSummary, type SessionWithStudent } from "@/lib/sessions";
import { useSessionPolling } from "@/hooks/useSessionPolling";
import SessionsTable from "@/components/sessions/SessionsTable";

interface SessionsPageClientProps {
    examId: string;
    initialSessions: SessionWithStudent[];
    exam: ExamSummary;
    onForceStopSession: (sessionId: string) => Promise<{ error?: string }>;
    onTerminateExam: (examId: string) => Promise<{ error?: string; count?: number }>;
    onAcknowledgeSession: (sessionId: string) => Promise<{ error?: string }>;
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
        <div className="aesthetic-card p-6 flex-1 min-w-[420px]">
            <div className="flex justify-between items-start gap-3 mb-3 flex-wrap">
                <div>
                    <div className="text-[var(--text-primary)] text-sm font-bold">{title}</div>
                    <div className="text-[var(--text-secondary)] text-xs mt-1.5 leading-relaxed max-w-[400px]">{description}</div>
                </div>
                <button
                    onClick={() => void onCopy(copyKey, sql)}
                    className="bg-transparent border border-[var(--accent-cyan)] text-[var(--accent-cyan)] px-3 py-1.5 rounded-lg text-xs font-bold cursor-pointer whitespace-nowrap transition-colors hover:bg-[var(--accent-cyan)] hover:text-white"
                >
                    {copiedKey === copyKey ? "Copied" : "Copy SQL"}
                </button>
            </div>
            <textarea
                readOnly
                value={sql}
                spellCheck={false}
                className="w-full min-h-[260px] resize-y bg-black/30 text-[var(--text-primary)] border border-[var(--border)] rounded-xl p-3.5 font-mono text-xs leading-relaxed outline-none focus:border-[var(--accent-cyan)] transition-colors"
            />
        </div>
    );
}

export default function SessionsPageClient({ examId, initialSessions, exam, onForceStopSession, onTerminateExam, onAcknowledgeSession }: SessionsPageClientProps): React.JSX.Element {
    const { sessions, setSessions, lastRefreshed } = useSessionPolling(examId, initialSessions, 5000);
    const [stoppingIds, setStoppingIds] = useState<Set<string>>(new Set());
    const [isMounted, setIsMounted] = useState(false);
    const [copiedKey, setCopiedKey] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<"LIVE" | "SQL">("LIVE");
    const [isTerminating, setIsTerminating] = useState(false);
    const [terminateResult, setTerminateResult] = useState<string | null>(null);
    const [acknowledgingIds, setAcknowledgingIds] = useState<Set<string>>(new Set());
    const [sessionActionResult, setSessionActionResult] = useState<string | null>(null);

    useEffect(() => {
        setIsMounted(true);
    }, []);

    const activeCount = sessions.filter(s => s.display_status === "ACTIVE").length;
    const pausedCount = sessions.filter(s => s.display_status === "PAUSED").length;
    const attentionCount = sessions.filter(s => s.needs_attention).length;
    
    const restoreSessionSql = buildRestoreSessionSql(examId);
    const studentUpsertSql = buildStudentUpsertSql();

    const handleForceStop = async (sessionId: string) => {
        const previousSession = sessions.find((session) => session.id === sessionId);
        if (!previousSession) {
            return;
        }

        setStoppingIds(prev => {
            const next = new Set(prev);
            next.add(sessionId);
            return next;
        });
        setSessionActionResult(null);

        // Optimistic UI update
        setSessions(prev => prev.map(s =>
            s.id === sessionId ?
                {
                    ...s,
                    status: "terminated",
                    display_status: "TERMINATED",
                    needs_attention: false,
                    attention_reason: null,
                    session_end: new Date().toISOString(),
                } : s
        ));

        const result = await onForceStopSession(sessionId);
        if (result.error) {
            setSessions(prev => prev.map(s => (s.id === sessionId ? previousSession : s)));
            setSessionActionResult(`Error: ${result.error}`);
        } else {
            setSessionActionResult("OK Session ended");
        }

        setStoppingIds(prev => {
            const next = new Set(prev);
            next.delete(sessionId);
            return next;
        });
    };

    const handleAcknowledge = async (sessionId: string) => {
        const previousSession = sessions.find((session) => session.id === sessionId);
        if (!previousSession) {
            return;
        }

        setAcknowledgingIds(prev => {
            const next = new Set(prev);
            next.add(sessionId);
            return next;
        });
        setSessionActionResult(null);

        // Optimistic UI update
        setSessions(prev => prev.map(s =>
            s.id === sessionId ? { ...s, needs_attention: false, attention_reason: null } : s
        ));

        const result = await onAcknowledgeSession(sessionId);
        if (result.error) {
            setSessions(prev => prev.map(s => (s.id === sessionId ? previousSession : s)));
            setSessionActionResult(`Error: ${result.error}`);
        } else {
            setSessionActionResult("OK Attention cleared");
        }

        setAcknowledgingIds(prev => {
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
            hour12: false
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
                <div className="bg-[#ec4899]/10 border border-[#ec4899]/30 text-[#ec4899] p-4 rounded-lg mb-6 font-bold flex items-center justify-center tracking-wide">
                    EXAM FORCE STOPPED — All sessions have been terminated.
                </div>
            )}

            {/* Header Area */}
            <div className="flex justify-between items-start mb-6">
                <div>
                    <div className="text-[var(--text-muted)] text-[11px] uppercase tracking-wider mb-1.5">
                        {exam.class_number}
                    </div>
                    <h1 className="text-[var(--text-primary)] text-[26px] font-bold m-0 leading-tight">
                        {exam.exam_name}
                    </h1>
                    <div className="text-[var(--text-muted)] font-mono text-xs mt-3">
                        Last refreshed: {isMounted ? formatTime(lastRefreshed) : null}
                    </div>
                </div>

                {/* Header Badges + Force Stop */}
                <div className="flex gap-3 items-center flex-wrap">
                    <div className="bg-[#06b6d4]/10 border border-[#06b6d4]/20 text-[#06b6d4] px-4 py-1.5 rounded-full text-sm font-semibold flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-[#06b6d4] badge-pulse" />
                        {activeCount} Active
                    </div>

                    {attentionCount > 0 && (
                        <div className="bg-[#ec4899]/10 border border-[#ec4899]/20 text-[#ec4899] px-4 py-1.5 rounded-full text-sm font-semibold flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-[#ec4899]" />
                            {attentionCount} Needs Attention
                        </div>
                    )}

                    {pausedCount > 0 && (
                        <div className="bg-[#ffd166]/10 border border-[#ffd166]/20 text-[#ffd166] px-4 py-1.5 rounded-full text-sm font-semibold flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-[#ffd166]" />
                            {pausedCount} Paused
                        </div>
                    )}

                    {/* Force Stop All Button */}
                    {!exam.force_stop && (
                        <button
                            onClick={async () => {
                                if (!confirm("⚠️ END ALL SESSIONS?\n\nThis will terminate every active session and kill the agent on every student's device. This cannot be undone.")) return;
                                setIsTerminating(true);
                                setTerminateResult(null);
                                const result = await onTerminateExam(examId);
                                if (result.error) {
                                    setTerminateResult(`Error: ${result.error}`);
                                } else {
                                    setTerminateResult(`✓ ${result.count ?? 0} sessions terminated`);
                                    // Refresh after a short delay
                                    setTimeout(() => window.location.reload(), 1500);
                                }
                                setIsTerminating(false);
                            }}
                            disabled={isTerminating}
                            className={`px-4 py-1.5 rounded-full text-sm font-semibold flex items-center gap-2 border transition-colors ${isTerminating ? 'opacity-50 cursor-wait bg-[#ef4444]/5 border-[#ef4444]/20 text-[#ef4444]' : 'bg-[#ef4444]/10 border-[#ef4444]/30 text-[#ef4444] hover:bg-[#ef4444]/20 cursor-pointer'}`}
                        >
                            {isTerminating ? (
                                <>
                                    <div className="w-3 h-3 border-2 border-[#ef4444]/30 border-t-[#ef4444] rounded-full animate-spin" />
                                    Terminating...
                                  </>
                            ) : (
                                <>🛑 End All Sessions</>
                            )}
                        </button>
                    )}
                </div>
            </div>

            {/* Terminate result message */}
            {terminateResult && (
                <div className={`mb-4 text-sm font-medium px-4 py-2.5 rounded-lg inline-block ${terminateResult.startsWith("✓") ? 'text-[#06b6d4] bg-[#06b6d4]/10 border border-[#06b6d4]/30' : 'text-[#ef4444] bg-[#ef4444]/10 border border-[#ef4444]/30'}`}>
                    {terminateResult}
                </div>
            )}

            {sessionActionResult && (
                <div className={`mb-4 ml-3 text-sm font-medium px-4 py-2.5 rounded-lg inline-block ${sessionActionResult.startsWith("OK") ? 'text-[#06b6d4] bg-[#06b6d4]/10 border border-[#06b6d4]/30' : 'text-[#ef4444] bg-[#ef4444]/10 border border-[#ef4444]/30'}`}>
                    {sessionActionResult}
                </div>
            )}

            {/* Tabs */}
            <div className="flex gap-2 border-b border-[var(--border)] mb-8">
                <button 
                    onClick={() => setActiveTab("LIVE")}
                    className={`px-5 py-3 text-sm font-medium transition-colors relative ${activeTab === "LIVE" ? "text-[var(--text-primary)]" : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"}`}
                >
                    Live Monitoring
                    {activeTab === "LIVE" && (
                        <div className="absolute bottom-0 left-0 w-full h-[2px] bg-[#06b6d4] rounded-t-sm shadow-[0_-2px_8px_rgba(6,182,212,0.4)]" />
                    )}
                </button>
                <button 
                    onClick={() => setActiveTab("SQL")}
                    className={`px-5 py-3 text-sm font-medium transition-colors relative ${activeTab === "SQL" ? "text-[var(--text-primary)]" : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"}`}
                >
                    Manual Overrides & SQL
                    {activeTab === "SQL" && (
                        <div className="absolute bottom-0 left-0 w-full h-[2px] bg-[#06b6d4] rounded-t-sm shadow-[0_-2px_8px_rgba(6,182,212,0.4)]" />
                    )}
                </button>
            </div>

            {/* Tab Contents */}
            {activeTab === "LIVE" ? (
                <SessionsTable
                    sessions={sessions}
                    onForceStop={handleForceStop}
                    onAcknowledge={handleAcknowledge}
                    stoppingIds={stoppingIds}
                    acknowledgingIds={acknowledgingIds}
                />
            ) : (
                <div className="animate-in fade-in duration-300">
                    <div className="flex justify-between items-end gap-4 flex-wrap mb-4">
                        <div>
                            <div className="text-[var(--text-primary)] text-[13px] font-bold">Operational SQL</div>
                            <div className="text-[var(--text-muted)] text-[12px] mt-1.5 max-w-[760px]">
                                Replace the placeholders before running in Supabase. The restore query is scoped to this exam only, which makes it safer than reviving the student&apos;s latest session across every exam.
                            </div>
                        </div>
                        <div className="text-[var(--text-muted)] font-mono text-[11px]">
                            Exam ID: {examId}
                        </div>
                    </div>
                    
                    <div className="flex gap-4 flex-wrap">
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
            )}
        </div>
    );
}
