// SERVER ONLY
import { unstable_noStore as noStore } from "next/cache";
import { supabase } from "@/lib/supabase";
import { HEARTBEAT_LOST_THRESHOLD_MS } from "@/lib/monitoring";

const SYSTEM_FLAG_PREFIX = "system_";

export type HeartbeatStatus = "active" | "paused" | "heartbeat_lost" | "completed" | "terminated";
export type SessionDisplayStatus =
    | "ACTIVE"
    | "PAUSED"
    | "COMPLETED"
    | "COMPLETED - ENDED EARLY"
    | "COMPLETED - ENDED LATE"
    | "TERMINATED"
    | "AGENT LOST"
    | "AGENT KILLED"
    | "RESTARTED AFTER REBOOT";

export interface SessionWithStudent {
    id: string;
    student_id: string;
    exam_id: string;
    session_start: string;
    session_end: string | null;
    status: string;
    last_heartbeat_at: string | null;
    created_at: string;
    student: {
        name: string;
        erp: string;
    };
    flag_count: number;
    agent_event_count: number;
    heartbeat_status: HeartbeatStatus;
    display_status: SessionDisplayStatus;
    needs_attention: boolean;
    attention_reason: string | null;
    attention_updated_at: string | null;
    can_restart: boolean;
}

export interface ExamSummary {
    id: string;
    exam_name: string;
    class_number: string;
    start_time: string;
    end_time: string;
    force_stop: boolean;
}

interface RawFlaggedEventSummary {
    id: string;
    flag_type: string;
    flagged_at: string;
    reviewed: boolean;
}

interface RawSessionRow {
    id: string;
    student_id: string;
    exam_id: string;
    session_start: string;
    session_end: string | null;
    status: string;
    last_heartbeat_at: string | null;
    created_at: string;
    student: { name: string; erp: string } | { name: string; erp: string }[];
    flagged_events: RawFlaggedEventSummary[] | null;
}

interface SessionListSummaryRow {
    id: string;
    student_id: string;
    exam_id: string;
    session_start: string;
    session_end: string | null;
    status: string;
    last_heartbeat_at: string | null;
    created_at: string;
    student_name: string;
    student_erp: string;
    non_system_flag_count: number;
    system_event_count: number;
    early_end_at: string | null;
    late_end_at: string | null;
    unexpected_exit_at: string | null;
    reboot_restart_at: string | null;
}

interface AttentionState {
    displayStatus: SessionDisplayStatus;
    needsAttention: boolean;
    attentionReason: string | null;
    attentionUpdatedAt: string | null;
    canRestart: boolean;
}

interface HeartbeatRow {
    status: string;
    last_heartbeat_at: string | null;
}

function parseEventTime(value: string | null): number {
    if (!value) return 0;
    const timestamp = new Date(value).getTime();
    return Number.isNaN(timestamp) ? 0 : timestamp;
}

function isResolvedByLaterRestart(unexpectedExitAt: string | null, rebootRestartAt: string | null): boolean {
    return parseEventTime(rebootRestartAt) > parseEventTime(unexpectedExitAt);
}

function getHeartbeatStatus(row: HeartbeatRow, heartbeatCutoff: Date): HeartbeatStatus {
    if (row.status === "terminated") return "terminated";
    if (row.status === "completed") return "completed";
    if (row.status === "paused") return "paused";
    if (!row.last_heartbeat_at) return "heartbeat_lost";
    return new Date(row.last_heartbeat_at) < heartbeatCutoff ? "heartbeat_lost" : "active";
}

function newestUnreviewedEventAt(events: RawFlaggedEventSummary[], flagType: string): string | null {
    const matches = events
        .filter((event) => event.flag_type === flagType && !event.reviewed)
        .map((event) => event.flagged_at)
        .sort((a, b) => new Date(b).getTime() - new Date(a).getTime());
    return matches[0] || null;
}

function deriveAttentionState(row: RawSessionRow, heartbeatStatus: HeartbeatStatus, systemEvents: RawFlaggedEventSummary[]): AttentionState {
    const earlyEndAt = newestUnreviewedEventAt(systemEvents, "system_session_ended_before_exam_end");
    const lateEndAt = newestUnreviewedEventAt(systemEvents, "system_session_ended_after_exam_end");
    const unexpectedExitAt = newestUnreviewedEventAt(systemEvents, "system_agent_process_exited_unexpectedly");
    const rebootRestartAt = newestUnreviewedEventAt(systemEvents, "system_agent_restarted_after_reboot");
    const restartResolved = isResolvedByLaterRestart(unexpectedExitAt, rebootRestartAt);

    if (row.status === "completed") {
        if (earlyEndAt) {
            return {
                displayStatus: "COMPLETED - ENDED EARLY",
                needsAttention: true,
                attentionReason: "Student ended the session before exam time was over.",
                attentionUpdatedAt: earlyEndAt,
                canRestart: true,
            };
        }
        if (lateEndAt) {
            return {
                displayStatus: "COMPLETED - ENDED LATE",
                needsAttention: false,
                attentionReason: "Student ended the session after exam time was over.",
                attentionUpdatedAt: lateEndAt,
                canRestart: true,
            };
        }
        return {
            displayStatus: "COMPLETED",
            needsAttention: false,
            attentionReason: null,
            attentionUpdatedAt: null,
            canRestart: true,
        };
    }

    if (row.status === "terminated") {
        return {
            displayStatus: "TERMINATED",
            needsAttention: false,
            attentionReason: null,
            attentionUpdatedAt: row.session_end,
            canRestart: false,
        };
    }

    if (unexpectedExitAt && !restartResolved && heartbeatStatus === "paused") {
        return {
            displayStatus: "AGENT KILLED",
            needsAttention: true,
            attentionReason: "The agent was interrupted and is waiting for an invigilator restart.",
            attentionUpdatedAt: unexpectedExitAt,
            canRestart: true,
        };
    }

    if (heartbeatStatus === "heartbeat_lost") {
        return {
            displayStatus: "AGENT LOST",
            needsAttention: true,
            attentionReason: "Heartbeat is missing. The agent may have crashed, rebooted, or been killed.",
            attentionUpdatedAt: row.last_heartbeat_at,
            canRestart: true,
        };
    }

    if (rebootRestartAt && heartbeatStatus === "active") {
        return {
            displayStatus: "RESTARTED AFTER REBOOT",
            needsAttention: true,
            attentionReason: "The agent resumed automatically after a reboot or relaunch.",
            attentionUpdatedAt: rebootRestartAt,
            canRestart: false,
        };
    }

    if (heartbeatStatus === "paused") {
        return {
            displayStatus: "PAUSED",
            needsAttention: false,
            attentionReason: null,
            attentionUpdatedAt: row.last_heartbeat_at,
            canRestart: true,
        };
    }

    return {
        displayStatus: "ACTIVE",
        needsAttention: false,
        attentionReason: null,
        attentionUpdatedAt: row.last_heartbeat_at,
        canRestart: false,
    };
}

function deriveAttentionStateFromSummary(
    row: SessionListSummaryRow,
    heartbeatStatus: HeartbeatStatus,
): AttentionState {
    const earlyEndAt = row.early_end_at;
    const lateEndAt = row.late_end_at;
    const unexpectedExitAt = row.unexpected_exit_at;
    const rebootRestartAt = row.reboot_restart_at;
    const restartResolved = isResolvedByLaterRestart(unexpectedExitAt, rebootRestartAt);

    if (row.status === "completed") {
        if (earlyEndAt) {
            return {
                displayStatus: "COMPLETED - ENDED EARLY",
                needsAttention: true,
                attentionReason: "Student ended the session before exam time was over.",
                attentionUpdatedAt: earlyEndAt,
                canRestart: true,
            };
        }
        if (lateEndAt) {
            return {
                displayStatus: "COMPLETED - ENDED LATE",
                needsAttention: false,
                attentionReason: "Student ended the session after exam time was over.",
                attentionUpdatedAt: lateEndAt,
                canRestart: true,
            };
        }
        return {
            displayStatus: "COMPLETED",
            needsAttention: false,
            attentionReason: null,
            attentionUpdatedAt: null,
            canRestart: true,
        };
    }

    if (row.status === "terminated") {
        return {
            displayStatus: "TERMINATED",
            needsAttention: false,
            attentionReason: null,
            attentionUpdatedAt: row.session_end,
            canRestart: false,
        };
    }

    if (unexpectedExitAt && !restartResolved && heartbeatStatus === "paused") {
        return {
            displayStatus: "AGENT KILLED",
            needsAttention: true,
            attentionReason: "The agent was interrupted and is waiting for an invigilator restart.",
            attentionUpdatedAt: unexpectedExitAt,
            canRestart: true,
        };
    }

    if (heartbeatStatus === "heartbeat_lost") {
        return {
            displayStatus: "AGENT LOST",
            needsAttention: true,
            attentionReason: "Heartbeat is missing. The agent may have crashed, rebooted, or been killed.",
            attentionUpdatedAt: row.last_heartbeat_at,
            canRestart: true,
        };
    }

    if (rebootRestartAt && heartbeatStatus === "active") {
        return {
            displayStatus: "RESTARTED AFTER REBOOT",
            needsAttention: true,
            attentionReason: "The agent resumed automatically after a reboot or relaunch.",
            attentionUpdatedAt: rebootRestartAt,
            canRestart: false,
        };
    }

    if (heartbeatStatus === "paused") {
        return {
            displayStatus: "PAUSED",
            needsAttention: false,
            attentionReason: null,
            attentionUpdatedAt: row.last_heartbeat_at,
            canRestart: true,
        };
    }

    return {
        displayStatus: "ACTIVE",
        needsAttention: false,
        attentionReason: null,
        attentionUpdatedAt: row.last_heartbeat_at,
        canRestart: false,
    };
}

function getPriority(displayStatus: SessionDisplayStatus, needsAttention: boolean): number {
    if (!needsAttention) {
        switch (displayStatus) {
            case "ACTIVE":
                return 50;
            case "PAUSED":
                return 60;
            case "COMPLETED":
                return 70;
            case "COMPLETED - ENDED LATE":
                return 75;
            case "TERMINATED":
                return 80;
            default:
                return 90;
        }
    }

    switch (displayStatus) {
        case "AGENT KILLED":
            return 1;
        case "AGENT LOST":
            return 2;
        case "RESTARTED AFTER REBOOT":
            return 3;
        case "COMPLETED - ENDED EARLY":
            return 4;
        default:
            return 10;
    }
}

export async function getExamById(examId: string): Promise<ExamSummary> {
    noStore();
    const { data, error } = await supabase
        .from("exams")
        .select("id, exam_name, class_number, start_time, end_time, force_stop")
        .eq("id", examId)
        .single();

    if (error) throw new Error(`Failed to fetch exam: ${error.message}`);
    if (!data) throw new Error("Exam not found");

    return data as ExamSummary;
}

export async function getSessionsForExam(examId: string): Promise<SessionWithStudent[]> {
    noStore();
    const rpcResult = await supabase.rpc("get_exam_session_dashboard_rows", {
        target_exam_id: examId,
    });

    let mappedData: SessionWithStudent[];
    const heartbeatCutoff = new Date(Date.now() - HEARTBEAT_LOST_THRESHOLD_MS);

    if (!rpcResult.error && rpcResult.data) {
        mappedData = ((rpcResult.data as SessionListSummaryRow[]) || []).map((row) => {
            const heartbeatStatus = getHeartbeatStatus(row, heartbeatCutoff);
            const attentionState = deriveAttentionStateFromSummary(row, heartbeatStatus);

            return {
                id: row.id,
                student_id: row.student_id,
                exam_id: row.exam_id,
                session_start: row.session_start,
                session_end: row.session_end,
                status: row.status,
                last_heartbeat_at: row.last_heartbeat_at,
                created_at: row.created_at,
                student: { name: row.student_name || "Unknown", erp: row.student_erp || "Unknown" },
                flag_count: row.non_system_flag_count || 0,
                agent_event_count: row.system_event_count || 0,
                heartbeat_status: heartbeatStatus,
                display_status: attentionState.displayStatus,
                needs_attention: attentionState.needsAttention,
                attention_reason: attentionState.attentionReason,
                attention_updated_at: attentionState.attentionUpdatedAt,
                can_restart: attentionState.canRestart,
            };
        });
    } else {
        const { data, error } = await supabase
            .from("exam_sessions")
            .select(`
                *,
                student:students(name, erp),
                flagged_events(id, flag_type, flagged_at, reviewed)
            `)
            .eq("exam_id", examId)
            .order("session_start", { ascending: true });

        if (error) throw new Error(`Failed to fetch sessions: ${error.message}`);

        mappedData = ((data as RawSessionRow[]) || []).map((row) => {
            const student = Array.isArray(row.student) ? row.student[0] : row.student;
            const allFlags = row.flagged_events || [];
            const systemEvents = allFlags.filter((event) => event.flag_type.startsWith(SYSTEM_FLAG_PREFIX));
            const cheatingEvents = allFlags.filter((event) => !event.flag_type.startsWith(SYSTEM_FLAG_PREFIX));
            const heartbeatStatus = getHeartbeatStatus(row, heartbeatCutoff);
            const attentionState = deriveAttentionState(row, heartbeatStatus, systemEvents);

            return {
                id: row.id,
                student_id: row.student_id,
                exam_id: row.exam_id,
                session_start: row.session_start,
                session_end: row.session_end,
                status: row.status,
                last_heartbeat_at: row.last_heartbeat_at,
                created_at: row.created_at,
                student: student || { name: "Unknown", erp: "Unknown" },
                flag_count: cheatingEvents.length,
                agent_event_count: systemEvents.length,
                heartbeat_status: heartbeatStatus,
                display_status: attentionState.displayStatus,
                needs_attention: attentionState.needsAttention,
                attention_reason: attentionState.attentionReason,
                attention_updated_at: attentionState.attentionUpdatedAt,
                can_restart: attentionState.canRestart,
            };
        });
    }

    mappedData.sort((left, right) => {
        const priorityDiff = getPriority(left.display_status, left.needs_attention) - getPriority(right.display_status, right.needs_attention);
        if (priorityDiff !== 0) return priorityDiff;

        const leftTime = new Date(left.attention_updated_at || left.session_start).getTime();
        const rightTime = new Date(right.attention_updated_at || right.session_start).getTime();
        return rightTime - leftTime;
    });

    return mappedData;
}
