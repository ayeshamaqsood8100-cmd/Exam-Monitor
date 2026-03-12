import React from "react";
import Link from "next/link";
import { getSessionSummary } from "@/lib/sessionSummary";
import SessionSummaryClient from "@/components/sessionSummary/SessionSummaryClient";
import BackButton from "@/components/ui/BackButton";

export const dynamic = "force-dynamic";

export default async function SessionSummaryPage({ params }: { params: { sessionId: string } }): Promise<React.JSX.Element> {
    const data = await getSessionSummary(params.sessionId);

    if (!data) {
        return (
            <div className="flex justify-center items-center min-h-[50vh]">
                <div className="aesthetic-card p-12 text-center max-w-[400px]">
                    <div className="text-[var(--text-secondary)] mb-6 text-base">
                        Session not found or invalid ID.
                    </div>
                    <Link
                        href="/exams"
                        className="inline-block bg-transparent border border-[var(--text-muted)] text-[var(--text-primary)] px-6 py-2.5 rounded-lg font-bold no-underline hover:bg-[var(--surface-hover)] transition-colors"
                    >
                        &larr; Return to Dashboard
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div>
            <div className="pt-6 px-6 max-w-[1200px] mx-auto">
                <BackButton 
                    href={`/sessions?exam_id=${data.exam_id}`}
                    breadcrumbs={["Exams", data.exam.name, data.student.name]}
                />
            </div>
            <SessionSummaryClient data={data} />
        </div>
    );
}
