"use server";

import { revalidatePath } from "next/cache";
import { markAgentAlertReviewed } from "@/lib/alerts";

export async function markAgentReviewedAction(id: string): Promise<{ error?: string }> {
    try {
        await markAgentAlertReviewed(id);
        revalidatePath("/agent");
        revalidatePath("/alerts");
        revalidatePath("/sessions");
        return {};
    } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : "An unknown error occurred.";
        return { error: msg };
    }
}
