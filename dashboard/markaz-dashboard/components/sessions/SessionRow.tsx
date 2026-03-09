"use client";
import React from "react";
import Link from "next/link";
import { type SessionWithStudent } from "@/lib/sessions";
import { THEME } from "@/constants/theme";
interface SessionRowProps {
    session: SessionWithStudent;
    onForceStop: (sessionId: string) => void;
    isStopping: boolean;
    onRestart: (sessionId: string) => void;
    isRestarting: boolean;
}
export default function SessionRow({ session, onForceStop, isStopping, onRestart, isRestarting }: SessionRowProps): React.JSX.Element {
    const { heartbeat_status, flag_count, student } = session;
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
    let badgeLabel = "COMPLETED";
    if (heartbeat_status === "active") {
        dotColor = THEME.cyan;
        dotAnimation = "breathe 2s infinite";
        badgeColor = THEME.cyan;
        badgeLabel = "ACTIVE";
    } else if (heartbeat_status === "paused") {
        dotColor = THEME.yellow;
        badgeColor = THEME.yellow;
        badgeLabel = "PAUSED";
    } else if (heartbeat_status === "heartbeat_lost") {
        dotColor = THEME.pink;
        badgeColor = THEME.pink;
        badgeLabel = "HEARTBEAT LOST";
    }
    const rowBaseStyle: React.CSSProperties = {
        borderBottom: "1px solid rgba(255,255,255,0.04)",
        transition: "background 0.15s ease",
    };
    const heartbeatLostStyle: React.CSSProperties = {
        ...rowBaseStyle,
        borderLeft: `3px solid ${THEME.pink}`,
        background: `${THEME.pink}08`,
    };
    const activeRowStyle = heartbeat_status === "heartbeat_lost" ? heartbeatLostStyle : rowBaseStyle;
    return (
        <tr
            style={activeRowStyle}
            onMouseEnter={(e) => {
                if (heartbeat_status !== "heartbeat_lost") {
                    e.currentTarget.style.background = "rgba(255,255,255,0.02)";
                }
            }}
            onMouseLeave={(e) => {
                if (heartbeat_status !== "heartbeat_lost") {
                    e.currentTarget.style.background = "transparent";
                }
            }}
        >
            <td style={{ padding: "14px 16px" }}>
                <div style={{ color: THEME.textPrimary, fontWeight: "bold", fontSize: "14px" }}>{student.name}</div>
                <div style={{ color: THEME.textSecondary, fontFamily: THEME.fontMono, fontSize: "12px", marginTop: "2px" }}>{student.erp}</div>
            </td>
            <td style={{ padding: "14px 16px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: dotColor, animation: dotAnimation }} />
                    <span style={{ fontSize: "11px", fontWeight: 700, padding: "2px 8px", borderRadius: "6px", color: badgeColor, backgroundColor: `${badgeColor}15`, border: `1px solid ${badgeColor}30` }}>
                        {badgeLabel}
                    </span>
                </div>
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
                    {session.status === "active" ? (
                        <button
                            onClick={() => onForceStop(session.id)}
                            disabled={isStopping || isRestarting}
                            style={{ background: "transparent", border: `1px solid ${THEME.pink}`, color: THEME.pink, padding: "4px 10px", borderRadius: "6px", fontSize: "11px", fontWeight: 600, cursor: (isStopping || isRestarting) ? "wait" : "pointer", opacity: (isStopping || isRestarting) ? 0.5 : 1 }}
                            onMouseEnter={(e) => { if (!isStopping && !isRestarting) e.currentTarget.style.background = `${THEME.pink}15`; }}
                            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                        >
                            {isStopping ? "Pausing..." : "Pause"}
                        </button>
                    ) : session.status === "paused" ? (
                        <button
                            onClick={async () => {
                                if (confirm("Resume this student's monitoring now?")) {
                                    onRestart(session.id);
                                }
                            }}
                            disabled={isRestarting || isStopping}
                            style={{ background: "transparent", border: `1px solid ${THEME.cyan}`, color: THEME.cyan, padding: "4px 10px", borderRadius: "6px", fontSize: "11px", fontWeight: 600, cursor: (isRestarting || isStopping) ? "wait" : "pointer", opacity: (isRestarting || isStopping) ? 0.5 : 1 }}
                            onMouseEnter={(e) => { if (!isRestarting && !isStopping) e.currentTarget.style.background = `${THEME.cyan}15`; }}
                            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                        >
                            {isRestarting ? "Resuming..." : "Resume"}
                        </button>
                    ) : (
                        <button
                            onClick={async () => {
                                if (confirm("Reopen this completed session?")) {
                                    onRestart(session.id);
                                }
                            }}
                            disabled={isRestarting || isStopping}
                            style={{ background: "transparent", border: `1px solid ${THEME.cyan}`, color: THEME.cyan, padding: "4px 10px", borderRadius: "6px", fontSize: "11px", fontWeight: 600, cursor: (isRestarting || isStopping) ? "wait" : "pointer", opacity: (isRestarting || isStopping) ? 0.5 : 1 }}
                            onMouseEnter={(e) => { if (!isRestarting && !isStopping) e.currentTarget.style.background = `${THEME.cyan}15`; }}
                            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                        >
                            {isRestarting ? "Restarting..." : "Restart"}
                        </button>
                    )}
                </div>
            </td>
        </tr>
    );
}
