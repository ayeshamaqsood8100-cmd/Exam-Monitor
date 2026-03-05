import { NextResponse } from "next/server";
import { getSessionsForExam } from "@/lib/sessions";
export async function GET(request: Request) {
    try {
        const { searchParams } = new URL(request.url);
        const examId = searchParams.get("exam_id");
        if (!examId) {
            return NextResponse.json({ error: "Missing exam_id parameter" }, { status: 400 });
        }
        const sessions = await getSessionsForExam(examId);
        return NextResponse.json(sessions, { status: 200 });
    } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : "Unknown error";
        return NextResponse.json({ error: msg }, { status: 500 });
    }
}
