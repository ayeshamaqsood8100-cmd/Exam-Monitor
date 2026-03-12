// SERVER ONLY — never import in client components
import { unstable_noStore as noStore } from "next/cache";
import { supabase } from "@/lib/supabase";

export interface Exam {
    id: string;
    exam_name: string;
    class_number: string;
    start_time: string;
    end_time: string;
    access_code: string;
    force_stop: boolean;
    created_at: string;
}

export interface CreateExamPayload {
    exam_name: string;
    class_number: string;
    start_time: string;
    end_time: string;
    access_code: string;
}

export async function getAllExams(): Promise<Exam[]> {
    noStore();
    const { data, error } = await supabase
        .from("exams")
        .select("*")
        .order("created_at", { ascending: false });

    if (error) {
        throw new Error(`Failed to fetch exams: ${error.message}`);
    }

    return (data as Exam[]) || [];
}

export async function createExam(payload: CreateExamPayload): Promise<Exam> {
    noStore();
    const { data, error } = await supabase
        .from("exams")
        .insert([{ ...payload, force_stop: false }])
        .select()
        .single();

    if (error) {
        throw new Error(`Failed to create exam: ${error.message}`);
    }

    return data as Exam;
}

export async function terminateExamDirectly(id: string): Promise<number> {
    noStore();

    const nowUtc = new Date().toISOString();

    const { data: examRows, error: examError } = await supabase
        .from("exams")
        .update({ force_stop: true })
        .eq("id", id)
        .select("id");

    if (examError) {
        throw new Error(`Failed to terminate exam: ${examError.message}`);
    }

    if (!examRows || examRows.length === 0) {
        throw new Error("Exam not found");
    }

    const { data: sessionRows, error: sessionError } = await supabase
        .from("exam_sessions")
        .update({ status: "terminated", session_end: nowUtc })
        .eq("exam_id", id)
        .neq("status", "terminated")
        .select("id");

    if (sessionError) {
        throw new Error(`Failed to terminate exam sessions: ${sessionError.message}`);
    }

    return sessionRows?.length || 0;
}

export async function toggleForceStop(id: string, current: boolean): Promise<void> {
    noStore();
    const { error } = await supabase
        .from("exams")
        .update({ force_stop: !current })
        .eq("id", id);

    if (error) {
        throw new Error(`Failed to toggle force stop: ${error.message}`);
    }
}
