import { unstable_noStore as noStore } from "next/cache";
import { supabase } from "@/lib/supabase";
import { HEARTBEAT_LOST_THRESHOLD_MS } from "@/lib/monitoring";

export interface StoredAgentAlert {
    id: string;
    session_id: string;
    flag_type: string;
    description: string;
    evidence: string;
    occurrenceCount: number;
    firstSeenAt: string;
    lastSeenAt: string;
    severity: "HIGH" | "MED" | "LOW";
    flagged_at: string;
    reviewed: boolean;
    student: { name: string; erp: string };
    exam: { exam_name: string; class_number: string };
}

export interface LiveAgentAlert {
    session_id: string;
    student_name: string;
    student_erp: string;
    exam_name: string;
    class_number: string;
    status: string;
    last_heartbeat_at: string | null;
    alert_type: "heartbeat_lost";
    severity: "HIGH";
    description: string;
}

type JoinedFlagResponse = {
    id: string;
    session_id: string;
    flag_type: string;
    description: string;
    evidence: string;
    severity: string;
    flagged_at: string;
    reviewed: boolean;
    exam_sessions:
        | {
              students: { name: string; erp: string } | { name: string; erp: string }[] | null;
              exams: { exam_name: string; class_number: string } | { exam_name: string; class_number: string }[] | null;
          }
        | {
              students: { name: string; erp: string } | { name: string; erp: string }[] | null;
              exams: { exam_name: string; class_number: string } | { exam_name: string; class_number: string }[] | null;
          }[]
        | null;
};

type RawSessionAlert = {
    id: string;
    status: string;
    last_heartbeat_at: string | null;
    students: { name: string; erp: string } | { name: string; erp: string }[] | null;
    exams: { exam_name: string; class_number: string } | { exam_name: string; class_number: string }[] | null;
};

type ParsedEvidenceMeta = {
    rawEvidence: string;
    occurrenceCount: number;
    firstSeenAt: string;
    lastSeenAt: string;
};

function parseEvidenceMeta(evidence: string, flaggedAt: string): ParsedEvidenceMeta {
    if (!evidence) {
        return {
            rawEvidence: "",
            occurrenceCount: 1,
            firstSeenAt: flaggedAt,
            lastSeenAt: flaggedAt,
        };
    }

    try {
        const parsed: unknown = JSON.parse(evidence);
        if (!parsed || typeof parsed !== "object") {
            throw new Error("Invalid evidence payload");
        }
        const meta = parsed as Record<string, unknown>;
        return {
            rawEvidence: typeof meta.raw_evidence === "string" ? meta.raw_evidence : evidence,
            occurrenceCount: typeof meta.occurrence_count === "number" && meta.occurrence_count > 0 ? meta.occurrence_count : 1,
            firstSeenAt: typeof meta.first_seen_at === "string" && meta.first_seen_at ? meta.first_seen_at : flaggedAt,
            lastSeenAt: typeof meta.last_seen_at === "string" && meta.last_seen_at ? meta.last_seen_at : flaggedAt,
        };
    } catch {
        return {
            rawEvidence: evidence,
            occurrenceCount: 1,
            firstSeenAt: flaggedAt,
            lastSeenAt: flaggedAt,
        };
    }
}

export async function getStoredAgentAlerts(): Promise<StoredAgentAlert[]> {
    noStore();
    const { data, error } = await supabase
        .from("flagged_events")
        .select(`
            id, session_id, flag_type, description, evidence, severity, flagged_at, reviewed,
            exam_sessions!flagged_events_session_id_fkey (
                students(name, erp),
                exams(exam_name, class_number)
            )
        `)
        .like("flag_type", "system_%")
        .order("flagged_at", { ascending: false });

    if (error) throw new Error(`Failed to fetch stored agent alerts: ${error.message}`);

    const rows = (data as unknown as JoinedFlagResponse[]) || [];
    return rows.map((row) => {
        const sessionJoin = Array.isArray(row.exam_sessions) ? row.exam_sessions[0] : row.exam_sessions;
        const studentJoin = sessionJoin ? (Array.isArray(sessionJoin.students) ? sessionJoin.students[0] : sessionJoin.students) : null;
        const examJoin = sessionJoin ? (Array.isArray(sessionJoin.exams) ? sessionJoin.exams[0] : sessionJoin.exams) : null;
        const evidenceMeta = parseEvidenceMeta(row.evidence || "", row.flagged_at);
        return {
            id: row.id,
            session_id: row.session_id,
            flag_type: row.flag_type,
            description: row.description || "No description provided",
            evidence: evidenceMeta.rawEvidence,
            occurrenceCount: evidenceMeta.occurrenceCount,
            firstSeenAt: evidenceMeta.firstSeenAt,
            lastSeenAt: evidenceMeta.lastSeenAt,
            severity: row.severity as "HIGH" | "MED" | "LOW",
            flagged_at: row.flagged_at,
            reviewed: row.reviewed,
            student: { name: studentJoin?.name || "Unknown Student", erp: studentJoin?.erp || "Unknown ERP" },
            exam: { exam_name: examJoin?.exam_name || "Unknown Exam", class_number: examJoin?.class_number || "Unknown Class" },
        };
    });
}

export async function getLiveAgentAlerts(): Promise<LiveAgentAlert[]> {
    noStore();
    const { data, error } = await supabase
        .from("exam_sessions")
        .select(`
            id, status, last_heartbeat_at,
            students(name, erp),
            exams(exam_name, class_number)
        `)
        .eq("status", "active");

    if (error) throw new Error(`Failed to fetch live agent alerts: ${error.message}`);

    const cutoff = Date.now() - HEARTBEAT_LOST_THRESHOLD_MS;
    return ((data as RawSessionAlert[]) || [])
        .filter((row) => {
            if (!row.last_heartbeat_at) return true;
            return new Date(row.last_heartbeat_at).getTime() < cutoff;
        })
        .map((row) => {
            const student = Array.isArray(row.students) ? row.students[0] : row.students;
            const exam = Array.isArray(row.exams) ? row.exams[0] : row.exams;
            return {
                session_id: row.id,
                student_name: student?.name || "Unknown Student",
                student_erp: student?.erp || "Unknown ERP",
                exam_name: exam?.exam_name || "Unknown Exam",
                class_number: exam?.class_number || "Unknown Class",
                status: row.status,
                last_heartbeat_at: row.last_heartbeat_at,
                alert_type: "heartbeat_lost",
                severity: "HIGH",
                description: "Agent heartbeat has been lost. The laptop may have crashed, rebooted, or the agent may have been killed.",
            };
        });
}

export async function getAgentAlertsSnapshot(): Promise<{
    liveAlerts: LiveAgentAlert[];
    storedAlerts: StoredAgentAlert[];
}> {
    const [liveAlerts, storedAlerts] = await Promise.all([
        getLiveAgentAlerts(),
        getStoredAgentAlerts(),
    ]);
    return { liveAlerts, storedAlerts };
}

export async function markAgentAlertReviewed(id: string): Promise<void> {
    const { error } = await supabase.from("flagged_events").update({ reviewed: true }).eq("id", id);
    if (error) throw new Error(`Failed to mark agent alert as reviewed: ${error.message}`);
}

export async function markSessionAgentAlertsReviewed(sessionId: string, flagTypes: string[]): Promise<void> {
    if (flagTypes.length === 0) {
        return;
    }

    const { error } = await supabase
        .from("flagged_events")
        .update({ reviewed: true })
        .eq("session_id", sessionId)
        .in("flag_type", flagTypes);

    if (error) throw new Error(`Failed to clear agent alerts for session: ${error.message}`);
}
