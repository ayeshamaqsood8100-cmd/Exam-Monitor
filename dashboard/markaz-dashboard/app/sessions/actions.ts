"use server";
import { revalidatePath } from "next/cache";
import { postToBackend } from "@/lib/backendApi";
import { markSessionAgentAlertsReviewed } from "@/lib/alerts";

interface AnalyzeSessionsResponse {
    sessions_total?: number;
    sessions_analyzed: number;
    sessions_failed?: number;
    failed_session_ids?: string[];
    flags_inserted: number;
}

export async function forceStopSessionAction(sessionId: string): Promise<{ error?: string }> {
    try {
        await postToBackend<{ status: string }>("/session/end", { session_id: sessionId, source: "admin" });
        revalidatePath("/sessions");
        revalidatePath("/agent");
        revalidatePath("/alerts");
        return {};
    } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : "Unknown error occurred";
        return { error: msg };
    }
}

export async function restartSessionAction(sessionId: string): Promise<{ error?: string }> {
    try {
        await postToBackend<{ status: string }>("/session/restart", { session_id: sessionId });
        await markSessionAgentAlertsReviewed(sessionId, [
            "system_agent_process_exited_unexpectedly",
        ]);
        revalidatePath("/sessions");
        revalidatePath("/agent");
        revalidatePath("/alerts");
        return {};
    } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : "Unknown error occurred";
        return { error: msg };
    }
}

export async function analyzeSessionsAction(examId: string): Promise<AnalyzeSessionsResponse> {
    return await postToBackend<AnalyzeSessionsResponse>(`/analyze/${examId}`);
}
