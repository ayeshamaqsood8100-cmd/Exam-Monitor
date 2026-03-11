"use client";
import React from "react";
import Link from "next/link";
import { type SessionWithStudent } from "@/lib/sessions";
import { THEME } from "@/constants/theme";
interface SessionRowProps {
    session: SessionWithStudent;
    onForceStop: (sessionId: string) => void;
    isStopping: boolean;
}
export default function SessionRow({ session, onForceStop, isStopping }: SessionRowProps): React.JSX.Element {
    const { flag_count, student } = session;
    const isTerminated = session.display_status === "TERMINATED";
    const formatDate = (dateString: string | null): string => {
        if (!dateString) return "Never";
        return new Date(dateString).toLocaleTimeString("en-US", {
            timeZone: "Asia/Karachi",
            hour: "numeric",
            minute: "2-digit",
            second: "2-digit"
        });
    };
    let dotColor = THEME.textMuted;
    let dotAnimation = "none";
    let badgeColor = THEME.textMuted;
    const badgeLabel = session.display_status;
    switch (session.display_status) {
        case "ACTIVE":
            dotColor = THEME.cyan;
            dotAnimation = "breathe 2s infinite";
            badgeColor = THEME.cyan;
            break;
        case "PAUSED":
            dotColor = THEME.yellow;
            badgeColor = THEME.yellow;
            break;
        case "COMPLETED":
            dotColor = THEME.cyan;
            badgeColor = THEME.cyan;
            break;
        case "COMPLETED - ENDED EARLY":
            dotColor = THEME.yellow;
            badgeColor = THEME.yellow;
            break;
        case "COMPLETED - ENDED LATE":
            dotColor = THEME.blue;
            badgeColor = THEME.blue;
            break;
        case "TERMINATED":
            dotColor = THEME.pink;
            badgeColor = THEME.pink;
            break;
        case "AGENT LOST":
        case "AGENT KILLED":
            dotColor = THEME.pink;
            badgeColor = THEME.pink;
            dotAnimation = "breathe 2s infinite";
            break;
        case "RESTARTED AFTER REBOOT":
            dotColor = THEME.yellow;
            badgeColor = THEME.yellow;
            break;
        default:
            break;
    }
    const rowBaseStyle: React.CSSProperties = {
        borderBottom: "1px solid rgba(255,255,255,0.04)",
        transition: "background 0.15s ease",
    };
    const attentionStyle: React.CSSProperties = {
        ...rowBaseStyle,
        borderLeft: `3px solid ${THEME.pink}`,
        background: `${THEME.pink}08`,
    };
    const activeRowStyle = session.needs_attention ? attentionStyle : rowBaseStyle;
    return (
        <tr
            style={activeRowStyle}
            onMouseEnter={(e) => {
                if (!session.needs_attention) {
                    e.currentTarget.style.background = "rgba(255,255,255,0.02)";
                }
            }}
            onMouseLeave={(e) => {
                if (!session.needs_attention) {
                    e.currentTarget.style.background = "transparent";
                }
            }}
        >
            <td style={{ padding: "14px 16px" }}>
                <div style={{ color: THEME.textPrimary, fontWeight: "bold", fontSize: "14px" }}>{student.name}</div>
                <div style={{ color: THEME.textSecondary, fontFamily: THEME.fontMono, fontSize: "12px", marginTop: "2px" }}>{student.erp}</div>
                {session.needs_attention && (
                    <div style={{ marginTop: "8px" }}>
                        <span style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.04em", padding: "3px 8px", borderRadius: "999px", color: THEME.pink, backgroundColor: `${THEME.pink}15`, border: `1px solid ${THEME.pink}30` }}>
                            NEEDS ATTENTION
                        </span>
                    </div>
                )}
            </td>
            <td style={{ padding: "14px 16px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: dotColor, animation: dotAnimation }} />
                    <span style={{ fontSize: "11px", fontWeight: 700, padding: "2px 8px", borderRadius: "6px", color: badgeColor, backgroundColor: `${badgeColor}15`, border: `1px solid ${badgeColor}30` }}>
                        {badgeLabel}
                    </span>
                </div>
                {session.attention_reason && (
                    <div style={{ marginTop: "8px", fontSize: "12px", color: THEME.textSecondary, maxWidth: "280px" }}>
                        {session.attention_reason}
                    </div>
                )}
            </td>
            <td style={{ padding: "14px 16px" }}>
                <div style={{ color: badgeColor, fontFamily: THEME.fontMono, fontSize: "12px" }}>
                    {formatDate(session.last_heartbeat_at)}
                </div>
            </td>
            <td style={{ padding: "14px 16px" }}>
                <div style={{ color: THEME.textSecondary, fontFamily: THEME.fontMono, fontSize: "12px" }}>
                    {formatDate(session.session_start)}
                </div>
            </td>
            <td style={{ padding: "14px 16px" }}>
                {flag_count > 0 ? (
                    <span style={{ fontSize: "11px", fontWeight: 700, padding: "2px 8px", borderRadius: "6px", color: THEME.pink, backgroundColor: `${THEME.pink}15`, border: `1px solid ${THEME.pink}30` }}>
                        {flag_count} {flag_count === 1 ? "flag" : "flags"}
                    </span>
                ) : (
                    <span style={{ color: THEME.textMuted, fontFamily: THEME.fontMono, fontSize: "12px" }}>—</span>
                )}
            </td>
            <td style={{ padding: "14px 16px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <Link href={`/sessions/${session.id}`} style={{ color: THEME.cyan, fontFamily: THEME.fontMono, fontSize: "12px", textDecoration: "none" }}>
                        View
                    </Link>
                    {isTerminated ? null : (
                        <button
                            onClick={() => {
                                if (confirm("End & remove this student's agent now? This cannot be restarted.")) {
                                    onForceStop(session.id);
                                }
                            }}
                            disabled={isStopping}
                            style={{ background: "transparent", border: `1px solid ${THEME.pink}`, color: THEME.pink, padding: "4px 10px", borderRadius: "6px", fontSize: "11px", fontWeight: 600, cursor: isStopping ? "wait" : "pointer", opacity: isStopping ? 0.5 : 1 }}
                            onMouseEnter={(e) => { if (!isStopping) e.currentTarget.style.background = `${THEME.pink}15`; }}
                            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                        >
                            {isStopping ? "Ending..." : "End & Remove"}
                        </button>
                    )}
                </div>
            </td>
        </tr>
    );
}
