"use server";
import { revalidatePath } from "next/cache";
import { markEventReviewed } from "@/lib/flaggedEvents";
export async function markReviewedAction(id: string): Promise<{ error?: string }> {
    try {
        await markEventReviewed(id);
        revalidatePath("/flagged");
        return {};
    } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : "An unknown error occurred.";
        return { error: msg };
    }
}
