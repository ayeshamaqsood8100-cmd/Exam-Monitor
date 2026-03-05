import React from "react";
import Link from "next/link";
import { getSessionSummary } from "@/lib/sessionSummary";
import SessionSummaryClient from "@/components/sessionSummary/SessionSummaryClient";
import Card from "@/components/ui/Card";
import { THEME } from "@/constants/theme";

export default async function SessionSummaryPage({ params }: { params: { sessionId: string } }): Promise<React.JSX.Element> {
    const data = await getSessionSummary(params.sessionId);

    if (!data) {
        return (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "50vh" }}>
                <Card style={{ padding: "48px", textAlign: "center", maxWidth: "400px" }}>
                    <div style={{ color: THEME.textSecondary, marginBottom: "24px", fontSize: "16px" }}>
                        Session not found or invalid ID.
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
                        &larr; Return to Dashboard
                    </Link>
                </Card>
            </div>
        );
    }

    return <SessionSummaryClient data={data} />;
}
