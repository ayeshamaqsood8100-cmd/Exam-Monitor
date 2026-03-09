// SERVER ONLY
import { unstable_noStore as noStore } from "next/cache";
import { supabase } from "@/lib/supabase";

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
    heartbeat_status: "active" | "paused" | "heartbeat_lost" | "completed";
}

export interface ExamSummary {
    id: string;
    exam_name: string;
    class_number: string;
    start_time: string;
    end_time: string;
    force_stop: boolean;
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
    flagged_events: { id: string }[] | null;
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
    const { data, error } = await supabase
        .from("exam_sessions")
        .select(`
      *,
      student:students(name, erp),
      flagged_events(id)
    `)
        .eq("exam_id", examId)
        .order("session_start", { ascending: true });

    if (error) throw new Error(`Failed to fetch sessions: ${error.message}`);

    const now = new Date();
    const heartbeatCutoff = new Date(now.getTime() - 12000);

    const mappedData: SessionWithStudent[] = (data || []).map((row: RawSessionRow) => {
        // Typecast from joined arrays to single object/count
        const student = Array.isArray(row.student) ? row.student[0] : row.student;
        const flag_count = row.flagged_events ? row.flagged_events.length : 0;

        let heartbeat_status: "active" | "paused" | "heartbeat_lost" | "completed" = "active";

        if (row.status === "completed") {
            heartbeat_status = "completed";
        } else if (row.status === "paused") {
            heartbeat_status = "paused";
        } else {
            if (!row.last_heartbeat_at) {
                heartbeat_status = "heartbeat_lost";
            } else {
                const lastHb = new Date(row.last_heartbeat_at);
                if (lastHb < heartbeatCutoff) {
                    heartbeat_status = "heartbeat_lost";
                }
            }
        }

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
            flag_count,
            heartbeat_status
        };
    });

    return mappedData;
}
