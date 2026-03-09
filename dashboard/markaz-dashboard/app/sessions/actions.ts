"use server";
import { revalidatePath } from "next/cache";
import { postToBackend } from "@/lib/backendApi";

interface AnalyzeSessionsResponse {
    sessions_total?: number;
    sessions_analyzed: number;
    sessions_failed?: number;
    failed_session_ids?: string[];
    flags_inserted: number;
}

export async function forceStopSessionAction(sessionId: string): Promise<{ error?: string }> {
    try {
        await postToBackend<{ status: string }>("/session/pause", { session_id: sessionId });
        revalidatePath("/sessions");
        return {};
    } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : "Unknown error occurred";
        return { error: msg };
    }
}

export async function restartSessionAction(sessionId: string): Promise<{ error?: string }> {
    try {
        await postToBackend<{ status: string }>("/session/restart", { session_id: sessionId });
        revalidatePath("/sessions");
        return {};
    } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : "Unknown error occurred";
        return { error: msg };
    }
}

export async function analyzeSessionsAction(examId: string): Promise<AnalyzeSessionsResponse> {
    return await postToBackend<AnalyzeSessionsResponse>(`/analyze/${examId}`);
}
