"use server";

import { revalidatePath } from "next/cache";
import { createExam, terminateExamDirectly, type CreateExamPayload } from "@/lib/exams";
import { postToBackend } from "@/lib/backendApi";

export async function createExamAction(formData: FormData): Promise<{ error?: string; exam?: Awaited<ReturnType<typeof createExam>> }> {
    try {
        const payload: CreateExamPayload = {
            exam_name: formData.get("exam_name") as string,
            class_number: formData.get("class_number") as string,
            start_time: formData.get("start_time") as string,
            end_time: formData.get("end_time") as string,
            access_code: formData.get("access_code") as string,
        };

        if (!payload.exam_name || !payload.class_number || !payload.start_time || !payload.end_time || !payload.access_code) {
            return { error: "All fields are required." };
        }

        const exam = await createExam(payload);
        revalidatePath("/exams");
        return { exam };
    } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : "Unknown error occurred";
        return { error: msg };
    }
}

export async function endAndRemoveExamAction(id: string): Promise<{ error?: string }> {
    try {
        await postToBackend<{ status: string }>("/exam/terminate", { exam_id: id });
        revalidatePath("/exams");
        return {};
    } catch (error: unknown) {
        try {
            await terminateExamDirectly(id);
            revalidatePath("/exams");
            revalidatePath("/sessions");
            revalidatePath("/agent");
            revalidatePath("/alerts");
            return {};
        } catch (fallbackError: unknown) {
            const primaryMsg = error instanceof Error ? error.message : "Unknown backend error occurred";
            const fallbackMsg = fallbackError instanceof Error ? fallbackError.message : "Unknown fallback error occurred";
            return { error: `${primaryMsg}. Direct fallback also failed: ${fallbackMsg}` };
        }
    }
}
