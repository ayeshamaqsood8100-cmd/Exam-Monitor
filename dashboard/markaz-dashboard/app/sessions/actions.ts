"use server";
import { revalidatePath } from "next/cache";
import { forceStopSession } from "@/lib/sessions";
export async function forceStopSessionAction(sessionId: string): Promise<{ error?: string }> {
    try {
        await forceStopSession(sessionId);
        revalidatePath("/sessions");
        return {};
    } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : "Unknown error occurred";
        return { error: msg };
    }
}

export async function analyzeSessionsAction(examId: string): Promise<{ sessions_analyzed: number; flags_inserted: number }> {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    const apiKey = process.env.API_KEY || "";

    const res = await fetch(`${backendUrl}/analyze/${examId}`, {
        method: "POST",
        headers: {
            "API-KEY": apiKey,
            "Content-Type": "application/json"
        }
    });

    if (!res.ok) {
        throw new Error(`Failed to analyze sessions: ${res.statusText}`);
    }

    return await res.json();
}
