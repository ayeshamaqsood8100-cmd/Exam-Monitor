"use client";
import React from "react";
import Link from "next/link";
import { type FlaggedEventWithContext } from "@/lib/flaggedEvents";
import { THEME } from "@/constants/theme";
interface FlaggedEventCardProps {
    event: FlaggedEventWithContext;
    onMarkReviewed: (id: string) => void;
    isMarking: boolean;
}
export default function FlaggedEventCard({ event, onMarkReviewed, isMarking }: FlaggedEventCardProps): React.JSX.Element {
    const c = (() => {
        switch (event.severity) {
            case "HIGH": return { text: THEME.pink, bg: `${THEME.pink}15`, border: `${THEME.pink}30`, shadow: THEME.pink };
            case "MED": return { text: THEME.yellow, bg: `${THEME.yellow}15`, border: `${THEME.yellow}30`, shadow: THEME.yellow };
            case "LOW": return { text: THEME.cyan, bg: `${THEME.cyan}15`, border: `${THEME.cyan}30`, shadow: THEME.cyan };
            default: return { text: THEME.textMuted, bg: "rgba(255,255,255,0.05)", border: "rgba(255,255,255,0.1)", shadow: THEME.textMuted };
        }
    })();
    const formatTime = (isoString: string) => {
        try {
            return new Date(isoString).toLocaleString("en-US", { timeZone: "Asia/Karachi", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", second: "2-digit", hour12: true });
        } catch { return isoString; }
    };
    return (
        <div
            style={{ position: "relative", background: THEME.cardBg, border: `1px solid ${THEME.cardBorder}`, borderRadius: "16px", padding: "20px 24px", backdropFilter: "blur(8px)", opacity: event.reviewed ? 0.6 : 1, transition: "transform 0.15s ease, opacity 0.2s ease" }}
            onMouseEnter={(e) => { e.currentTarget.style.transform = "translateY(-1px)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.transform = "translateY(0px)"; }}
        >
            <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: "3px", background: c.text, boxShadow: `0 0 12px ${c.shadow}60`, borderTopLeftRadius: "16px", borderBottomLeftRadius: "16px" }} />
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: c.text, background: c.bg, border: `1px solid ${c.border}`, borderRadius: "6px", padding: "2px 8px" }}>{event.severity}</span>
                    <span style={{ fontSize: "14px", fontWeight: "bold", color: THEME.textPrimary }}>{event.flag_type}</span>
                </div>
                <span style={{ fontFamily: THEME.fontMono, fontSize: "12px", color: THEME.textMuted, textAlign: "right" }}>{formatTime(event.flagged_at)}</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px", flexWrap: "wrap" }}>
                <span style={{ fontSize: "13px", fontWeight: "bold", color: THEME.textPrimary }}>{event.student.name}</span>
                <span style={{ fontFamily: THEME.fontMono, fontSize: "12px", color: THEME.textSecondary }}>{event.student.erp}</span>
                <span style={{ color: THEME.textMuted }}>·</span>
                <span style={{ fontSize: "13px", color: THEME.textSecondary }}>{event.exam.exam_name}</span>
                <span style={{ fontSize: "12px", color: THEME.textMuted }}>{event.exam.class_number}</span>
            </div>
            <div style={{ fontSize: "13px", color: THEME.textSecondary, marginTop: "10px", lineHeight: 1.5 }}>{event.description}</div>
            {event.evidence && event.evidence.trim() !== "N/A" && event.evidence.trim() !== "" && (
                <div style={{ background: "rgba(0,0,0,0.3)", borderRadius: "8px", padding: "8px 12px", fontSize: "12px", fontFamily: THEME.fontMono, color: THEME.textMuted, marginTop: "8px", wordBreak: "break-all", whiteSpace: "pre-wrap" }}>
                    {event.evidence}
                </div>
            )}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "14px" }}>
                <div>
                    {event.reviewed ? (
                        <span style={{ fontSize: "11px", fontWeight: 700, color: THEME.cyan, background: `${THEME.cyan}15`, border: `1px solid ${THEME.cyan}30`, borderRadius: "6px", padding: "2px 8px" }}>REVIEWED</span>
                    ) : (
                        <span style={{ fontSize: "11px", fontWeight: 700, color: THEME.textMuted, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", padding: "2px 8px" }}>PENDING REVIEW</span>
                    )}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                    <Link
                        href={`/sessions/${event.session_id}`}
                        style={{ color: THEME.cyan, fontFamily: THEME.fontMono, fontSize: "12px", textDecoration: "none", background: "transparent", border: "none", transition: "opacity 0.2s ease" }}
                        onMouseEnter={(e) => { e.currentTarget.style.opacity = "0.7"; }}
                        onMouseLeave={(e) => { e.currentTarget.style.opacity = "1"; }}
                    >
                        View Session &rarr;
                    </Link>
                    {!event.reviewed && (
                        <button onClick={() => onMarkReviewed(event.id)} disabled={isMarking}
                            style={{ background: "transparent", border: `1px solid ${THEME.cyan}60`, color: THEME.cyan, padding: "6px 14px", borderRadius: "6px", fontSize: "12px", fontWeight: 600, cursor: isMarking ? "not-allowed" : "pointer", opacity: isMarking ? 0.5 : 1, transition: "background 0.2s ease" }}
                            onMouseEnter={(e) => { if (!isMarking) e.currentTarget.style.background = `${THEME.cyan}1A`; }}
                            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}>
                            {isMarking ? "Marking..." : "Mark Reviewed"}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
