import { NextResponse } from "next/server";
import { getAgentAlertsSnapshot } from "@/lib/alerts";

export async function GET() {
    try {
        const data = await getAgentAlertsSnapshot();
        return NextResponse.json(data, { status: 200 });
    } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : "Unknown error";
        return NextResponse.json({ error: msg }, { status: 500 });
    }
}
