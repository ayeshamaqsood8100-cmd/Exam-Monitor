"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { type LiveAgentAlert, type StoredAgentAlert } from "@/lib/alerts";
import { THEME } from "@/constants/theme";

interface AlertsClientProps {
    initialLiveAlerts: LiveAgentAlert[];
    initialStoredAlerts: StoredAgentAlert[];
    onMarkReviewed: (id: string) => Promise<{ error?: string }>;
}

interface AlertsResponse {
    liveAlerts: LiveAgentAlert[];
    storedAlerts: StoredAgentAlert[];
}

function prettifyType(flagType: string): string {
    switch (flagType) {
        case "system_agent_process_exited_unexpectedly":
            return "AGENT KILLED";
        case "system_agent_restarted_after_reboot":
            return "RESTARTED AFTER REBOOT";
        case "system_session_ended_before_exam_end":
            return "COMPLETED - ENDED EARLY";
        default:
            return flagType.replace(/^system_/, "").replaceAll("_", " ").toUpperCase();
    }
}

export default function AlertsClient({
    initialLiveAlerts,
    initialStoredAlerts,
    onMarkReviewed,
}: AlertsClientProps): React.JSX.Element {
    const [liveAlerts, setLiveAlerts] = useState(initialLiveAlerts);
    const [storedAlerts, setStoredAlerts] = useState(initialStoredAlerts);
    const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
    const [markingIds, setMarkingIds] = useState<Set<string>>(new Set());

    useEffect(() => {
        let mounted = true;
        const poll = async () => {
            try {
                const res = await fetch("/api/agent");
                if (!res.ok) return;
                const data: AlertsResponse = await res.json();
                if (!mounted) return;
                setLiveAlerts(data.liveAlerts);
                setStoredAlerts(data.storedAlerts);
                setLastRefreshed(new Date());
            } catch {
                // Keep stale data visible instead of blanking the page.
            }
        };

        const interval = setInterval(poll, 5000);
        return () => {
            mounted = false;
            clearInterval(interval);
        };
    }, []);

    const formatTime = (value: string | null): string => {
        if (!value) return "Never";
        return new Date(value).toLocaleString("en-US", {
            timeZone: "Asia/Karachi",
            month: "short",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
            second: "2-digit",
            hour12: true,
        });
    };

    const handleMarkReviewed = async (id: string) => {
        setStoredAlerts((prev) => prev.map((alert) => (alert.id === id ? { ...alert, reviewed: true } : alert)));
        setMarkingIds((prev) => new Set(prev).add(id));

        const result = await onMarkReviewed(id);

        setMarkingIds((prev) => {
            const next = new Set(prev);
            next.delete(id);
            return next;
        });

        if (result.error) {
            setStoredAlerts((prev) => prev.map((alert) => (alert.id === id ? { ...alert, reviewed: false } : alert)));
        }
    };

    return (
        <div style={{ paddingBottom: "64px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "24px", flexWrap: "wrap", gap: "16px" }}>
                <div>
                    <h1 style={{ fontSize: "26px", fontWeight: "bold", color: THEME.textPrimary, margin: 0 }}>Agent</h1>
                    <div style={{ color: THEME.textMuted, fontFamily: THEME.fontMono, fontSize: "12px", marginTop: "12px" }}>
                        Last refreshed: {lastRefreshed.toLocaleTimeString("en-US", { hour12: false })}
                    </div>
                </div>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    <span style={{ fontSize: "11px", fontWeight: 700, padding: "4px 10px", borderRadius: "16px", color: THEME.pink, background: `${THEME.pink}15`, border: `1px solid ${THEME.pink}30` }}>
                        {liveAlerts.length} LIVE
                    </span>
                    <span style={{ fontSize: "11px", fontWeight: 700, padding: "4px 10px", borderRadius: "16px", color: THEME.cyan, background: `${THEME.cyan}15`, border: `1px solid ${THEME.cyan}30` }}>
                        {storedAlerts.filter((alert) => !alert.reviewed).length} UNREVIEWED
                    </span>
                </div>
            </div>

            <div style={{ height: "1px", background: `linear-gradient(90deg, ${THEME.cyan}60, transparent)`, opacity: 0.3, marginBottom: "32px" }} />

            <section style={{ marginBottom: "32px" }}>
                <div style={{ fontSize: "13px", color: THEME.textPrimary, fontWeight: 700, marginBottom: "12px" }}>Live Agent Issues</div>
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    {liveAlerts.length === 0 ? (
                        <div style={{ background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.1)", borderRadius: "16px", padding: "32px", color: THEME.textMuted }}>
                            No live agent issues right now.
                        </div>
                    ) : (
                        liveAlerts.map((alert) => (
                            <div key={`${alert.alert_type}-${alert.session_id}`} style={{ background: THEME.cardBg, border: `1px solid ${THEME.cardBorder}`, borderRadius: "16px", padding: "20px 24px", position: "relative" }}>
                                <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: "3px", background: THEME.pink, boxShadow: `0 0 12px ${THEME.pink}60`, borderTopLeftRadius: "16px", borderBottomLeftRadius: "16px" }} />
                                <div style={{ display: "flex", justifyContent: "space-between", gap: "16px", flexWrap: "wrap" }}>
                                    <div>
                                        <div style={{ color: THEME.pink, fontSize: "12px", fontWeight: 700, marginBottom: "8px" }}>AGENT LOST</div>
                                        <div style={{ color: THEME.textPrimary, fontSize: "14px", fontWeight: 700 }}>{alert.student_name} ({alert.student_erp})</div>
                                        <div style={{ color: THEME.textSecondary, fontSize: "13px", marginTop: "4px" }}>{alert.exam_name} · {alert.class_number}</div>
                                        <div style={{ color: THEME.textSecondary, fontSize: "13px", marginTop: "10px" }}>{alert.description}</div>
                                    </div>
                                    <div style={{ textAlign: "right" }}>
                                        <div style={{ color: THEME.textMuted, fontFamily: THEME.fontMono, fontSize: "12px" }}>Last heartbeat</div>
                                        <div style={{ color: THEME.pink, fontFamily: THEME.fontMono, fontSize: "12px", marginTop: "4px" }}>
                                            {formatTime(alert.last_heartbeat_at)}
                                        </div>
                                        <Link href={`/sessions/${alert.session_id}`} style={{ color: THEME.cyan, fontFamily: THEME.fontMono, fontSize: "12px", textDecoration: "none", display: "inline-block", marginTop: "12px" }}>
                                            View Session →
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </section>

            <section>
                <div style={{ fontSize: "13px", color: THEME.textPrimary, fontWeight: 700, marginBottom: "12px" }}>Stored Agent Events</div>
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    {storedAlerts.length === 0 ? (
                        <div style={{ background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.1)", borderRadius: "16px", padding: "32px", color: THEME.textMuted }}>
                            No stored agent events yet.
                        </div>
                    ) : (
                        storedAlerts.map((alert) => (
                            <div key={alert.id} style={{ background: THEME.cardBg, border: `1px solid ${THEME.cardBorder}`, borderRadius: "16px", padding: "20px 24px", position: "relative", opacity: alert.reviewed ? 0.55 : 1 }}>
                                <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: "3px", background: alert.severity === "MED" ? THEME.yellow : THEME.cyan, boxShadow: `0 0 12px ${alert.severity === "MED" ? THEME.yellow : THEME.cyan}60`, borderTopLeftRadius: "16px", borderBottomLeftRadius: "16px" }} />
                                <div style={{ display: "flex", justifyContent: "space-between", gap: "16px", flexWrap: "wrap", marginBottom: "10px" }}>
                                    <div>
                                        <div style={{ color: alert.severity === "MED" ? THEME.yellow : THEME.cyan, fontSize: "11px", fontWeight: 700, marginBottom: "8px" }}>
                                            {prettifyType(alert.flag_type)}
                                        </div>
                                        <div style={{ color: THEME.textPrimary, fontSize: "14px", fontWeight: 700 }}>{alert.student.name} ({alert.student.erp})</div>
                                        <div style={{ color: THEME.textSecondary, fontSize: "13px", marginTop: "4px" }}>{alert.exam.exam_name} · {alert.exam.class_number}</div>
                                    </div>
                                    <div style={{ color: THEME.textMuted, fontFamily: THEME.fontMono, fontSize: "12px" }}>
                                        Last seen: {formatTime(alert.lastSeenAt)}
                                    </div>
                                </div>
                                <div style={{ color: THEME.textSecondary, fontSize: "13px", lineHeight: 1.5 }}>{alert.description}</div>
                                <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", marginTop: "10px", color: THEME.textMuted, fontFamily: THEME.fontMono, fontSize: "12px" }}>
                                    <span>Occurred: {alert.occurrenceCount} time{alert.occurrenceCount === 1 ? "" : "s"}</span>
                                    <span>First seen: {formatTime(alert.firstSeenAt)}</span>
                                </div>
                                {alert.evidence && (
                                    <div style={{ background: "rgba(0,0,0,0.3)", borderRadius: "8px", padding: "8px 12px", fontSize: "12px", fontFamily: THEME.fontMono, color: THEME.textMuted, marginTop: "8px", wordBreak: "break-all", whiteSpace: "pre-wrap" }}>
                                        {alert.evidence}
                                    </div>
                                )}
                                <div style={{ marginTop: "12px", display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
                                    <Link href={`/sessions/${alert.session_id}`} style={{ color: THEME.cyan, fontFamily: THEME.fontMono, fontSize: "12px", textDecoration: "none" }}>
                                        View Session →
                                    </Link>
                                    {!alert.reviewed && (
                                        <button
                                            onClick={() => handleMarkReviewed(alert.id)}
                                            disabled={markingIds.has(alert.id)}
                                            style={{
                                                background: "transparent",
                                                border: `1px solid ${THEME.cyan}`,
                                                color: THEME.cyan,
                                                padding: "6px 12px",
                                                borderRadius: "8px",
                                                fontSize: "12px",
                                                fontWeight: 600,
                                                cursor: markingIds.has(alert.id) ? "wait" : "pointer",
                                                opacity: markingIds.has(alert.id) ? 0.5 : 1,
                                            }}
                                        >
                                            {markingIds.has(alert.id) ? "Reviewing..." : "Mark Reviewed"}
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </section>
        </div>
    );
}
