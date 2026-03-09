import { unstable_noStore as noStore } from "next/cache";
import { supabase } from "@/lib/supabase";
export interface FlaggedEventWithContext {
    id: string;
    session_id: string;
    flag_type: string;
    description: string;
    evidence: string;
    severity: "HIGH" | "MED" | "LOW";
    flagged_at: string;
    reviewed: boolean;
    student: { name: string; erp: string; };
    exam: { exam_name: string; class_number: string; };
}
type JoinedFlagResponse = {
    id: string; session_id: string; flag_type: string; description: string;
    evidence: string; severity: string; flagged_at: string; reviewed: boolean;
    exam_sessions: {
        students: { name: string; erp: string } | { name: string; erp: string }[] | null;
        exams: { exam_name: string; class_number: string } | { exam_name: string; class_number: string }[] | null;
    } | { students: { name: string; erp: string } | { name: string; erp: string }[] | null; exams: { exam_name: string; class_number: string } | { exam_name: string; class_number: string }[] | null; }[] | null;
}
export async function getAllFlaggedEvents(): Promise<FlaggedEventWithContext[]> {
    noStore();
    const { data, error } = await supabase
        .from("flagged_events")
        .select(`id, session_id, flag_type, description, evidence, severity, flagged_at, reviewed, exam_sessions!flagged_events_session_id_fkey ( student_id, exam_id, students (name, erp), exams (exam_name, class_number) )`)
        .order("flagged_at", { ascending: false });
    if (error) throw new Error(`Failed to fetch flagged events: ${error.message}`);
    const rawData = (data as unknown) as JoinedFlagResponse[];
    return rawData.map(row => {
        const sessionJoin = Array.isArray(row.exam_sessions) ? row.exam_sessions[0] : row.exam_sessions;
        const studentJoin = sessionJoin ? (Array.isArray(sessionJoin.students) ? sessionJoin.students[0] : sessionJoin.students) : null;
        const examJoin = sessionJoin ? (Array.isArray(sessionJoin.exams) ? sessionJoin.exams[0] : sessionJoin.exams) : null;
        return {
            id: row.id, session_id: row.session_id, flag_type: row.flag_type,
            description: row.description || "No description provided",
            evidence: row.evidence || "",
            severity: row.severity as "HIGH" | "MED" | "LOW",
            flagged_at: row.flagged_at, reviewed: row.reviewed,
            student: { name: studentJoin?.name || "Unknown Student", erp: studentJoin?.erp || "Unknown ERP" },
            exam: { exam_name: examJoin?.exam_name || "Unknown Exam", class_number: examJoin?.class_number || "Unknown Class" }
        };
    });
}
export async function markEventReviewed(id: string): Promise<void> {
    const { error } = await supabase.from("flagged_events").update({ reviewed: true }).eq("id", id);
    if (error) throw new Error(`Failed to mark event as reviewed: ${error.message}`);
}
