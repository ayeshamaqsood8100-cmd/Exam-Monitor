import React from "react";
import Link from "next/link";
import { getExamById, getSessionsForExam } from "@/lib/sessions";
import SessionsPageClient from "@/components/sessions/SessionsPageClient";
import Card from "@/components/ui/Card";
import Breadcrumb from "@/components/ui/Breadcrumb";
import { THEME } from "@/constants/theme";
import { forceStopSessionAction, analyzeSessionsAction } from "@/app/sessions/actions";
import AnalyzeButton from "@/components/sessions/AnalyzeButton";

export const dynamic = "force-dynamic";

export default async function SessionsPage({ searchParams }: { searchParams: { exam_id?: string } }): Promise<React.JSX.Element> {
    const examId = searchParams.exam_id;

    if (!examId) {
        return (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "50vh" }}>
                <Card style={{ padding: "48px", textAlign: "center", maxWidth: "400px" }}>
                    <div style={{ color: THEME.textSecondary, marginBottom: "24px", fontSize: "16px" }}>
                        No exam selected. Go back to Exams.
                    </div>
                    <Link
                        href="/exams"
                        style={{
                            display: "inline-block",
                            background: THEME.cyan,
                            color: THEME.bg,
                            padding: "10px 24px",
                            borderRadius: "8px",
                            fontWeight: "bold",
                            textDecoration: "none"
                        }}
                    >
                        &larr; Return to Exams
                    </Link>
                </Card>
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
                <div style={{ padding: "24px 24px 0", maxWidth: "1200px", margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <Breadcrumb
                        segments={[
                            { label: "Exams", href: "/exams" },
                            { label: exam.exam_name, href: undefined }
                        ]}
                    />
                    <AnalyzeButton examId={examId} analyzeAction={analyzeSessionsAction} />
                </div>
                <SessionsPageClient
                    examId={examId}
                    initialSessions={initialSessions}
                    exam={exam}
                    onForceStopSession={forceStopSessionAction}
                />
            </div>
        );
    } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : "Unknown error";

        return (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "50vh" }}>
                <Card style={{ padding: "48px", textAlign: "center", maxWidth: "480px", borderLeft: `3px solid ${THEME.pink}` }}>
                    <h2 style={{ color: THEME.pink, fontSize: "20px", fontWeight: "bold", marginBottom: "16px", marginTop: 0 }}>
                        Error Loading Sessions
                    </h2>
                    <div style={{ color: THEME.textSecondary, marginBottom: "24px", wordBreak: "break-word" }}>
                        {msg}
                    </div>
                    <Link
                        href="/exams"
                        style={{
                            display: "inline-block",
                            background: "transparent",
                            border: `1px solid ${THEME.textMuted}`,
                            color: THEME.textPrimary,
                            padding: "10px 24px",
                            borderRadius: "8px",
                            fontWeight: "bold",
                            textDecoration: "none"
                        }}
                    >
                        &larr; Return to Exams
                    </Link>
                </Card>
            </div>
        );
    }
}
