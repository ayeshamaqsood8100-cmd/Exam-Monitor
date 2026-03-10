"use server";

import { revalidatePath } from "next/cache";
import { createExam, toggleForceStop, type CreateExamPayload } from "@/lib/exams";

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

export async function toggleForceStopAction(id: string, current: boolean): Promise<{ error?: string }> {
    try {
        await toggleForceStop(id, current);
        revalidatePath("/exams");
        return {};
    } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : "Unknown error occurred";
        return { error: msg };
    }
}
