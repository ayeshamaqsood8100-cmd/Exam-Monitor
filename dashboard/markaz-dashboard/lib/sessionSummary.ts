// SERVER ONLY
import { supabase } from "@/lib/supabase";

export interface SessionSummaryData {
    student: {
        name: string;
        erp: string;
    };
    exam: {
        name: string;
        class_number: string;
    };
    session: {
        start: string;
        end: string | null;
        status: string;
        last_heartbeat: string | null;
    };
    stats: {
        keystrokes: number;
        windows: number;
        clipboard: number;
        flags: number;
        syncs: number;
        offline_periods: number;
    };
    health: {
        agent_version: string;
        consented_at: string | null;
    };
    flags: {
        id: string;
        severity: "HIGH" | "MED" | "LOW";
        flag_type: string;
        flagged_at: string;
        description: string | null;
        evidence: string | null;
    }[];
    windows: {
        switched_at: string;
        app_name: string;
        window_title: string;
    }[];
    clipboard: {
        id: string;
        captured_at: string;
        event_type: "COPY" | "PASTE";
        source_app: string;
        destination_app: string | null;
        content: string;
    }[];
}

function formatDateToKarachi(dateString: string | null): string {
    if (!dateString) return "";
    return new Date(dateString).toLocaleString("en-US", { timeZone: "Asia/Karachi" });
}

export async function getSessionSummary(sessionId: string): Promise<SessionSummaryData | null> {
    const [
        sessionRes,
        consentRes,
        telemetryRes,
        keystrokesRes,
        windowsRes,
        clipboardRes,
        flagsRes
    ] = await Promise.all([
        supabase.from("exam_sessions").select(`
      session_start, session_end, status, last_heartbeat_at,
      students (name, erp),
      exams (exam_name, class_number)
    `).eq("id", sessionId).single(),

        supabase.from("consent_logs").select("consented_at, agent_version").eq("session_id", sessionId).maybeSingle(),
        supabase.from("telemetry_syncs").select("offline_periods").eq("session_id", sessionId),
        supabase.from("keystroke_logs").select("id", { count: "exact", head: true }).eq("session_id", sessionId),
        supabase.from("window_logs").select("switched_at, application_name, window_title").eq("session_id", sessionId).order("switched_at", { ascending: true }),
        supabase.from("clipboard_logs").select("id, captured_at, event_type, source_application, destination_application, content").eq("session_id", sessionId).order("captured_at", { ascending: true }),
        supabase.from("flagged_events").select("id, severity, flag_type, flagged_at, description, evidence").eq("session_id", sessionId).order("flagged_at", { ascending: true })
    ]);

    if (sessionRes.error || !sessionRes.data) return null;

    type JoinedSessionData = {
        session_start: string | null;
        session_end: string | null;
        status: string;
        last_heartbeat_at: string | null;
        students: { name: string; erp: string } | { name: string; erp: string }[] | null;
        exams: { exam_name: string; class_number: string } | { exam_name: string; class_number: string }[] | null;
    };

    const data = sessionRes.data as unknown as JoinedSessionData;
    const student = Array.isArray(data.students) ? data.students[0] : data.students;
    const exam = Array.isArray(data.exams) ? data.exams[0] : data.exams;

    // Process Telemetry Offline Periods
    let offlinePeriodsCount = 0;
    if (telemetryRes.data) {
        for (const row of telemetryRes.data) {
            if (row.offline_periods && Array.isArray(row.offline_periods)) {
                offlinePeriodsCount += row.offline_periods.length;
            }
        }
    }

    return {
        student: {
            name: student?.name || "Unknown",
            erp: student?.erp || "Unknown"
        },
        exam: {
            name: exam?.exam_name || "Unknown",
            class_number: exam?.class_number || "Unknown"
        },
        session: {
            start: formatDateToKarachi(data.session_start),
            end: formatDateToKarachi(data.session_end),
            status: data.status,
            last_heartbeat: formatDateToKarachi(data.last_heartbeat_at)
        },
        stats: {
            keystrokes: keystrokesRes.count || 0,
            windows: windowsRes.data?.length || 0,
            clipboard: clipboardRes.data?.length || 0,
            flags: flagsRes.data?.length || 0,
            syncs: telemetryRes.data?.length || 0,
            offline_periods: offlinePeriodsCount
        },
        health: {
            agent_version: consentRes.data?.agent_version || "Unknown",
            consented_at: formatDateToKarachi(consentRes.data?.consented_at || null)
        },
        flags: (flagsRes.data || []).map(row => ({
            id: row.id,
            severity: row.severity as "HIGH" | "MED" | "LOW",
            flag_type: row.flag_type,
            flagged_at: formatDateToKarachi(row.flagged_at),
            description: row.description,
            evidence: row.evidence
        })),
        windows: (windowsRes.data || []).map(row => ({
            switched_at: formatDateToKarachi(row.switched_at),
            app_name: row.application_name,
            window_title: row.window_title
        })),
        clipboard: (clipboardRes.data || []).map(row => ({
            id: row.id,
            captured_at: formatDateToKarachi(row.captured_at),
            event_type: row.event_type as "COPY" | "PASTE",
            source_app: row.source_application || "Unknown",
            destination_app: row.destination_application,
            content: row.content || ""
        }))
    };
}
