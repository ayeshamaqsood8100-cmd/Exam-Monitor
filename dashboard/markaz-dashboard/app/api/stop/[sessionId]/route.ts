import { NextResponse } from "next/server";
import { BackendRequestError, postToBackend } from "@/lib/backendApi";

export async function POST(
    _request: Request,
    { params }: { params: { sessionId: string } }
) {
    try {
        const data = await postToBackend<{ status: string }>("/session/pause", {
            session_id: params.sessionId,
        });
        return NextResponse.json(data, { status: 200 });
    } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : "Unknown error";
        const status = error instanceof BackendRequestError ? error.status : 500;
        return NextResponse.json({ error: msg }, { status });
    }
}
