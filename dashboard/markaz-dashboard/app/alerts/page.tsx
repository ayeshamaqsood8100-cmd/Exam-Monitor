import React from "react";
import Link from "next/link";
import AlertsClient from "@/components/alerts/AlertsClient";
import { getAgentAlertsSnapshot } from "@/lib/alerts";
import { THEME } from "@/constants/theme";

export const dynamic = "force-dynamic";

export default async function AlertsPage(): Promise<React.JSX.Element> {
    try {
        const { liveAlerts, storedAlerts } = await getAgentAlertsSnapshot();
        return (
            <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "40px 24px" }}>
                <AlertsClient initialLiveAlerts={liveAlerts} initialStoredAlerts={storedAlerts} />
            </div>
        );
    } catch (error: unknown) {
        return (
            <div style={{ maxWidth: "600px", margin: "100px auto", padding: "32px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "16px", textAlign: "center" }}>
                <div style={{ width: "48px", height: "48px", borderRadius: "50%", background: `${THEME.pink}15`, color: THEME.pink, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px", fontSize: "24px" }}>!</div>
                <h2 style={{ color: THEME.textPrimary, marginBottom: "12px", fontSize: "20px" }}>Failed to load agent alerts</h2>
                <div style={{ color: THEME.textSecondary, marginBottom: "32px", fontSize: "14px", lineHeight: 1.5 }}>
                    {error instanceof Error ? error.message : "An unexpected error occurred."}
                </div>
                <Link href="/exams" style={{ display: "inline-block", background: THEME.cyan, color: "#000", padding: "10px 24px", borderRadius: "8px", fontWeight: 600, textDecoration: "none", fontSize: "14px" }}>Return to Exams</Link>
            </div>
        );
    }
}
