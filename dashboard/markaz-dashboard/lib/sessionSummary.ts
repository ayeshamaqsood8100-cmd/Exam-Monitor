// SERVER ONLY
import { unstable_noStore as noStore } from "next/cache";
import { supabase } from "@/lib/supabase";
import {
    HEARTBEAT_LOST_THRESHOLD_MS,
    MAX_CLIPBOARD_DETAIL_ROWS,
    MAX_KEYSTROKE_DETAIL_ROWS,
    MAX_WINDOW_DETAIL_ROWS,
} from "@/lib/monitoring";

export interface KeystrokeGroup {
    startTime: string;
    endTime: string;
    application: string;
    text: string;
}

export interface SessionSummaryData {
    sessionId: string;
    exam_id: string;
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
        display_status: string;
        last_heartbeat: string | null;
    };
    stats: {
        keystrokes: number;
        windows: number;
        clipboard: number;
        flags: number;
        agent_events: number;
        syncs: number;
        offline_periods: number;
    };
    health: {
        agent_version: string;
        consented_at: string | null;
    };
    limits: {
        maxKeystrokeRows: number;
        maxWindowRows: number;
        maxClipboardRows: number;
        keystrokesTruncated: boolean;
        windowsTruncated: boolean;
        clipboardTruncated: boolean;
    };
    flags: {
        id: string;
        severity: "HIGH" | "MED" | "LOW";
        flag_type: string;
        flagged_at: string;
        description: string | null;
        evidence: string | null;
    }[];
    agentEvents: {
        id: string;
        severity: "HIGH" | "MED" | "LOW";
        flag_type: string;
        flagged_at: string;
        description: string | null;
        evidence: string | null;
        reviewed: boolean;
    }[];
    windows: {
        switched_at: string;
        app_name: string;
        window_title: string;
    }[];
    keystrokes: {
        id: string;
        captured_at: string;
        application: string;
    }[];
    keystrokeGroups: KeystrokeGroup[];
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

function deriveSessionDisplayStatus(status: string, lastHeartbeatAt: string | null, agentEvents: { flag_type: string; reviewed: boolean }[]): string {
    const hasUnreviewedEarlyEnd = agentEvents.some((event) => event.flag_type === "system_session_ended_before_exam_end" && !event.reviewed);
    const hasUnreviewedKill = agentEvents.some((event) => event.flag_type === "system_agent_process_exited_unexpectedly" && !event.reviewed);
    const hasUnreviewedReboot = agentEvents.some((event) => event.flag_type === "system_agent_restarted_after_reboot" && !event.reviewed);
    const heartbeatLost = status === "active" && (!lastHeartbeatAt || new Date(lastHeartbeatAt).getTime() < Date.now() - HEARTBEAT_LOST_THRESHOLD_MS);

    if (status === "completed" && hasUnreviewedEarlyEnd) return "COMPLETED - ENDED EARLY";
    if (status === "terminated") return "TERMINATED";
    if (status === "completed") return "COMPLETED";
    if (status === "paused" && hasUnreviewedKill) return "AGENT KILLED";
    if (heartbeatLost) return "AGENT LOST";
    if (status === "active" && hasUnreviewedReboot) return "RESTARTED AFTER REBOOT";
    if (status === "paused") return "PAUSED";
    return "ACTIVE";
}

export async function getSessionSummary(sessionId: string): Promise<SessionSummaryData | null> {
    noStore();
    const [
        sessionRes,
        consentRes,
        telemetryRes,
        keystrokesRes,
        windowsCountRes,
        clipboardCountRes,
        keystrokesDataRes,
        windowsRes,
        clipboardRes
    ] = await Promise.all([
        supabase.from("exam_sessions").select(`
      session_start, session_end, status, last_heartbeat_at, exam_id,
      students (name, erp),
      exams (exam_name, class_number)
    `).eq("id", sessionId).single(),

        supabase.from("consent_logs").select("consented_at, agent_version").eq("session_id", sessionId).maybeSingle(),
        supabase.from("telemetry_syncs").select("offline_periods").eq("session_id", sessionId),
        supabase.from("keystroke_logs").select("id", { count: "exact", head: true }).eq("session_id", sessionId),
        supabase.from("window_logs").select("id", { count: "exact", head: true }).eq("session_id", sessionId),
        supabase.from("clipboard_logs").select("id", { count: "exact", head: true }).eq("session_id", sessionId),
        supabase
            .from("keystroke_logs")
            .select("id, captured_at, application, key_data")
            .eq("session_id", sessionId)
            .order("captured_at", { ascending: true })
            .limit(MAX_KEYSTROKE_DETAIL_ROWS),
        supabase
            .from("window_logs")
            .select("switched_at, application_name, window_title")
            .eq("session_id", sessionId)
            .order("switched_at", { ascending: true })
            .limit(MAX_WINDOW_DETAIL_ROWS),
        supabase
            .from("clipboard_logs")
            .select("id, captured_at, event_type, source_application, destination_application, content")
            .eq("session_id", sessionId)
            .order("captured_at", { ascending: true })
            .limit(MAX_CLIPBOARD_DETAIL_ROWS)
    ]);

    // Queried separately to avoid Next.js fetch cache returning stale empty results
    const flagsRes = await supabase.from("flagged_events").select("id, severity, flag_type, flagged_at, description, evidence, reviewed").eq("session_id", sessionId).order("flagged_at", { ascending: true });

    if (sessionRes.error || !sessionRes.data) return null;

    type JoinedSessionData = {
        exam_id: string;
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

    const allFlags = flagsRes.data || [];
    const cheatingFlags = allFlags.filter((row) => !row.flag_type.startsWith("system_"));
    const agentEvents = allFlags.filter((row) => row.flag_type.startsWith("system_"));
    const displayStatus = deriveSessionDisplayStatus(data.status, data.last_heartbeat_at, agentEvents);
    const keystrokeCount = keystrokesRes.count || 0;
    const windowCount = windowsCountRes.count || 0;
    const clipboardCount = clipboardCountRes.count || 0;
    const keystrokeRows = keystrokesDataRes.data || [];
    const windowRows = windowsRes.data || [];
    const clipboardRows = clipboardRes.data || [];

    return {
        sessionId: sessionId,
        exam_id: data.exam_id,
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
            display_status: displayStatus,
            last_heartbeat: formatDateToKarachi(data.last_heartbeat_at)
        },
        stats: {
            keystrokes: keystrokeCount,
            windows: windowCount,
            clipboard: clipboardCount,
            flags: cheatingFlags.length,
            agent_events: agentEvents.length,
            syncs: telemetryRes.data?.length || 0,
            offline_periods: offlinePeriodsCount
        },
        health: {
            agent_version: consentRes.data?.agent_version || "Unknown",
            consented_at: formatDateToKarachi(consentRes.data?.consented_at || null)
        },
        limits: {
            maxKeystrokeRows: MAX_KEYSTROKE_DETAIL_ROWS,
            maxWindowRows: MAX_WINDOW_DETAIL_ROWS,
            maxClipboardRows: MAX_CLIPBOARD_DETAIL_ROWS,
            keystrokesTruncated: keystrokeCount > keystrokeRows.length,
            windowsTruncated: windowCount > windowRows.length,
            clipboardTruncated: clipboardCount > clipboardRows.length,
        },
        flags: cheatingFlags.map(row => ({
            id: row.id,
            severity: row.severity as "HIGH" | "MED" | "LOW",
            flag_type: row.flag_type,
            flagged_at: formatDateToKarachi(row.flagged_at),
            description: row.description,
            evidence: row.evidence
        })),
        agentEvents: agentEvents.map(row => ({
            id: row.id,
            severity: row.severity as "HIGH" | "MED" | "LOW",
            flag_type: row.flag_type,
            flagged_at: formatDateToKarachi(row.flagged_at),
            description: row.description,
            evidence: row.evidence,
            reviewed: row.reviewed
        })),
        windows: windowRows.map(row => ({
            switched_at: formatDateToKarachi(row.switched_at),
            app_name: row.application_name,
            window_title: row.window_title
        })),
        keystrokes: keystrokeRows.map(row => ({
            id: row.id,
            captured_at: formatDateToKarachi(row.captured_at),
            application: row.application || "Unknown"
        })),
        keystrokeGroups: buildKeystrokeGroups(keystrokeRows),
        clipboard: clipboardRows.map(row => ({
            id: row.id,
            captured_at: formatDateToKarachi(row.captured_at),
            event_type: row.event_type as "COPY" | "PASTE",
            source_app: row.source_application || "Unknown",
            destination_app: row.destination_application,
            content: row.content || ""
        }))
    };
}
type KeystrokeDbRow = {
    id: string;
    captured_at: string | null;
    application: string | null;
    key_data: string | null;
};

function extractTimeOnly(dateString: string | null): string {
    const formatted = formatDateToKarachi(dateString);
    if (!formatted) return "—";
    const parts = formatted.split(", ");
    return parts[1] || formatted;
}

function normalizeAppName(app: string | null): string {
    if (!app) return "Unknown";
    const lower = app.toLowerCase();
    if (lower.includes("google chrome") || lower.includes("chrome")) return "Chrome";
    if (lower.includes("microsoft edge") || lower.includes("edge")) return "Edge";
    if (lower.includes("firefox")) return "Firefox";
    if (lower.includes("excel")) return "Excel";
    if (lower.includes("word")) return "Word";
    if (lower.includes("whatsapp")) return "WhatsApp";
    if (lower.includes("notepad")) return "Notepad";
    if (lower.includes("visual studio code") || lower.includes("code")) return "VS Code";
    return app;
}

function applyBackspaces(texts: string[]): string[] {
    const result: string[] = [];
    for (const char of texts) {
        if (char === "[BS]") {
            if (result.length > 0) {
                result.pop();
            }
        } else {
            result.push(char);
        }
    }
    return result;
}

function parseKeyData(raw: string | null): string {
    if (!raw) return "";

    // Exact mapping matches
    if (raw === "Key.space") return " ";
    if (raw === "Key.enter") return "[ENTER]";
    if (raw === "Key.backspace") return "[BS]";
    if (raw === "Key.tab") return "[TAB]";
    if (raw === "Key.delete") return "[DEL]";
    if (raw === "Key.esc") return "[ESC]";

    // Ignoring mapped modifier keys & arrows & function keys
    const ignoredKeys = [
        "Key.shift", "Key.shift_r", "Key.shift_l",
        "Key.ctrl", "Key.ctrl_l", "Key.ctrl_r",
        "Key.alt", "Key.alt_l", "Key.alt_r", "Key.alt_gr",
        "Key.caps_lock",
        "Key.cmd", "Key.cmd_r", "Key.cmd_l",
        "Key.up", "Key.down", "Key.left", "Key.right",
        "Key.f1", "Key.f2", "Key.f3", "Key.f4", "Key.f5", "Key.f6",
        "Key.f7", "Key.f8", "Key.f9", "Key.f10", "Key.f11", "Key.f12"
    ];

    if (ignoredKeys.includes(raw)) return "";

    // Safely ignore any remaining unknown "Key.*" formatted strings
    if (raw.startsWith("Key.")) return "";

    // Otherwise it's a regular printable char (e.g. "a", "A", "1", "!", etc)
    // Strip surrounding single quotes if present (pynput sometimes logs 'a')
    let processedRaw = raw;
    if (processedRaw.length === 3 && processedRaw.startsWith("'") && processedRaw.endsWith("'")) {
        processedRaw = processedRaw[1];
    }

    if (processedRaw.length === 1 && (processedRaw.charCodeAt(0) < 32 || processedRaw.charCodeAt(0) > 126)) return "";

    return processedRaw;
}

function buildKeystrokeGroups(rows: KeystrokeDbRow[]): KeystrokeGroup[] {
    const groups: KeystrokeGroup[] = [];
    if (!rows || rows.length === 0) return groups;

    let currentApp = normalizeAppName(rows[0].application);
    let startTimestamp = rows[0].captured_at;
    let endTimestamp = rows[0].captured_at;
    let currentTexts: string[] = [];

    const initialParsed = parseKeyData(rows[0].key_data);
    if (initialParsed.length > 0) currentTexts.push(initialParsed);

    for (let i = 1; i < rows.length; i++) {
        const row = rows[i];
        const normalizedApp = normalizeAppName(row.application);
        if (normalizedApp === currentApp) {
            endTimestamp = row.captured_at;
            const parsed = parseKeyData(row.key_data);
            if (parsed.length > 0) currentTexts.push(parsed);
        } else {
            const joinedText = applyBackspaces(currentTexts).join("");
            if (joinedText.trim() !== "") {
                groups.push({
                    startTime: extractTimeOnly(startTimestamp),
                    endTime: extractTimeOnly(endTimestamp),
                    application: currentApp,
                    text: joinedText
                });
            }
            currentApp = normalizedApp;
            startTimestamp = row.captured_at;
            endTimestamp = row.captured_at;

            const parsed = parseKeyData(row.key_data);
            currentTexts = parsed.length > 0 ? [parsed] : [];
        }
    }

    const finalJoinedText = applyBackspaces(currentTexts).join("");
    if (finalJoinedText.trim() !== "") {
        groups.push({
            startTime: extractTimeOnly(startTimestamp),
            endTime: extractTimeOnly(endTimestamp),
            application: currentApp,
            text: finalJoinedText
        });
    }

    return groups;
}
