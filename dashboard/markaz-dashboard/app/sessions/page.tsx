import React from "react";
import Link from "next/link";
import { getExamById, getSessionsForExam } from "@/lib/sessions";
import SessionsPageClient from "@/components/sessions/SessionsPageClient";
import BackButton from "@/components/ui/BackButton";
import { forceStopSessionAction, terminateExamAction, acknowledgeSessionAction } from "@/app/sessions/actions";

export const dynamic = "force-dynamic";

export default async function SessionsPage({ searchParams }: { searchParams: { exam_id?: string } }): Promise<React.JSX.Element> {
    const examId = searchParams.exam_id;

    if (!examId) {
        return (
            <div className="flex justify-center items-center min-h-[50vh]">
                <div className="aesthetic-card p-12 text-center max-w-[400px]">
                    <div className="text-[var(--text-secondary)] mb-6 text-base">
                        No exam selected. Go back to Exams.
                    </div>
                    <Link
                        href="/exams"
                        className="inline-block bg-[var(--accent-cyan)] text-[var(--bg)] px-6 py-2.5 rounded-lg font-bold no-underline hover:-translate-y-0.5 transition-transform"
                    >
                        &larr; Return to Exams
                    </Link>
                </div>
            </div>
        );
    }

    try {
        const [exam, initialSessions] = await Promise.all([
            getExamById(examId),
            getSessionsForExam(examId)
        ]);

        return (
            <div>
                <div className="flex justify-between items-center mb-0">
                    <BackButton href="/exams" breadcrumbs={["Surveillance", exam.exam_name]} />
                </div>
                <SessionsPageClient
                    examId={examId}
                    initialSessions={initialSessions}
                    exam={exam}
                    onForceStopSession={forceStopSessionAction}
                    onTerminateExam={terminateExamAction}
                    onAcknowledgeSession={acknowledgeSessionAction}
                />
            </div>
        );
    } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : "Unknown error";

        return (
            <div className="flex justify-center items-center min-h-[50vh]">
                <div className="aesthetic-card p-12 text-center max-w-[480px] border-l-[3px] border-l-[var(--accent-pink)]">
                    <h2 className="text-[var(--accent-pink)] text-xl font-bold mb-4 mt-0">
                        Error Loading Sessions
                    </h2>
                    <div className="text-[var(--text-secondary)] mb-6 break-words">
                        {msg}
                    </div>
                    <Link
                        href="/exams"
                        className="inline-block bg-transparent border border-[var(--text-muted)] text-[var(--text-primary)] px-6 py-2.5 rounded-lg font-bold no-underline hover:bg-[var(--surface-hover)] transition-colors"
                    >
                        &larr; Return to Exams
                    </Link>
                </div>
            </div>
        );
    }
}
