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
