"use client";
import React, { useState, useMemo } from "react";
import { type FlaggedEventWithContext } from "@/lib/flaggedEvents";
import FlaggedEventCard from "./FlaggedEventCard";
import { THEME } from "@/constants/theme";
interface FlaggedEventsClientProps {
    events: FlaggedEventWithContext[];
    onMarkReviewed: (id: string) => Promise<{ error?: string }>;
}
type SeverityFilter = "ALL" | "HIGH" | "MED" | "LOW";
type ReviewedFilter = "ALL" | "unreviewed" | "reviewed";
export default function FlaggedEventsClient({ events: initialEvents, onMarkReviewed }: FlaggedEventsClientProps): React.JSX.Element {
    const [events, setEvents] = useState<FlaggedEventWithContext[]>(initialEvents);
    const [markingIds, setMarkingIds] = useState<Set<string>>(new Set());
    const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("ALL");
    const [reviewedFilter, setReviewedFilter] = useState<ReviewedFilter>("ALL");
    const [markError, setMarkError] = useState<string | null>(null);
    const handleMarkReviewed = async (id: string) => {
        setEvents(prev => prev.map(ev => ev.id === id ? { ...ev, reviewed: true } : ev));
        setMarkingIds(prev => new Set(prev).add(id));
        const result = await onMarkReviewed(id);
        setMarkingIds(prev => { const next = new Set(prev); next.delete(id); return next; });
        if (result.error) {
            setEvents(prev => prev.map(ev => ev.id === id ? { ...ev, reviewed: false } : ev));
            setMarkError(result.error);
            setTimeout(() => setMarkError(null), 4000);
        }
    };
    const stats = useMemo(() => {
        let unreviewedCount = 0, highCount = 0, medCount = 0, lowCount = 0;
        events.forEach(ev => { if (!ev.reviewed) { unreviewedCount++; if (ev.severity === "HIGH") highCount++; if (ev.severity === "MED") medCount++; if (ev.severity === "LOW") lowCount++; } });
        return { unreviewedCount, highCount, medCount, lowCount };
    }, [events]);
    const filteredEvents = useMemo(() => {
        return events.filter(ev => {
            if (severityFilter !== "ALL" && ev.severity !== severityFilter) return false;
            if (reviewedFilter === "unreviewed" && ev.reviewed) return false;
            if (reviewedFilter === "reviewed" && !ev.reviewed) return false;
            return true;
        });
    }, [events, severityFilter, reviewedFilter]);
    return (
        <div style={{ paddingBottom: "64px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "24px", flexWrap: "wrap", gap: "16px" }}>
                <h1 style={{ fontSize: "26px", fontWeight: "bold", color: THEME.textPrimary, margin: 0, letterSpacing: "-0.02em" }}>Flagged Events</h1>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    {stats.unreviewedCount > 0 && (
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", background: `${THEME.pink}1A`, border: `1px solid ${THEME.pink}33`, padding: "4px 12px", borderRadius: "16px" }}>
                            <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: THEME.pink, boxShadow: `0 0 8px ${THEME.pink}` }} />
                            <span style={{ fontSize: "12px", fontWeight: 700, color: THEME.pink }}>{stats.unreviewedCount} UNREVIEWED</span>
                        </div>
                    )}
                    {stats.highCount > 0 && <span style={{ fontSize: "11px", fontWeight: 700, padding: "4px 10px", borderRadius: "16px", color: THEME.pink, background: `${THEME.pink}15`, border: `1px solid ${THEME.pink}30` }}>{stats.highCount} HIGH</span>}
                    {stats.medCount > 0 && <span style={{ fontSize: "11px", fontWeight: 700, padding: "4px 10px", borderRadius: "16px", color: THEME.yellow, background: `${THEME.yellow}15`, border: `1px solid ${THEME.yellow}30` }}>{stats.medCount} MED</span>}
                    {stats.lowCount > 0 && <span style={{ fontSize: "11px", fontWeight: 700, padding: "4px 10px", borderRadius: "16px", color: THEME.cyan, background: `${THEME.cyan}15`, border: `1px solid ${THEME.cyan}30` }}>{stats.lowCount} LOW</span>}
                </div>
            </div>
            <div style={{ height: "1px", background: `linear-gradient(90deg, ${THEME.cyan}60, transparent)`, opacity: 0.3, marginBottom: "32px" }} />

            {markError && (
                <div style={{ background: `${THEME.pink}1A`, border: `1px solid ${THEME.pink}33`, color: THEME.pink, padding: "10px 16px", borderRadius: "8px", fontSize: "13px", marginBottom: "16px" }}>
                    Failed to update: {markError}
                </div>
            )}

            <div style={{ display: "flex", flexWrap: "wrap", gap: "24px", marginBottom: "32px" }}>
                <div>
                    <div style={{ fontSize: "11px", color: THEME.textSecondary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "8px" }}>Severity</div>
                    <div style={{ display: "flex", gap: "6px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "10px", padding: "4px" }}>
                        {(["ALL", "HIGH", "MED", "LOW"] as SeverityFilter[]).map(sev => (
                            <button key={sev} onClick={() => setSeverityFilter(sev)} style={{ padding: "6px 16px", borderRadius: "6px", fontSize: "12px", fontWeight: 600, cursor: "pointer", border: "none", background: severityFilter === sev ? `${THEME.cyan}1A` : "transparent", color: severityFilter === sev ? THEME.cyan : THEME.textMuted, transition: "all 0.2s" }}>{sev}</button>
                        ))}
                    </div>
                </div>
                <div>
                    <div style={{ fontSize: "11px", color: THEME.textSecondary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "8px" }}>Status</div>
                    <div style={{ display: "flex", gap: "6px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "10px", padding: "4px" }}>
                        {[{ value: "ALL", label: "All" }, { value: "unreviewed", label: "Unreviewed" }, { value: "reviewed", label: "Reviewed" }].map(stat => (
                            <button key={stat.value} onClick={() => setReviewedFilter(stat.value as ReviewedFilter)} style={{ padding: "6px 16px", borderRadius: "6px", fontSize: "12px", fontWeight: 600, cursor: "pointer", border: "none", background: reviewedFilter === stat.value ? `${THEME.cyan}1A` : "transparent", color: reviewedFilter === stat.value ? THEME.cyan : THEME.textMuted, transition: "all 0.2s" }}>{stat.label}</button>
                        ))}
                    </div>
                </div>
            </div>
            <div style={{ fontSize: "13px", color: THEME.textMuted, marginBottom: "16px" }}>Showing {filteredEvents.length} event{filteredEvents.length !== 1 ? "s" : ""}</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {filteredEvents.length === 0 ? (
                    <div style={{ background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.1)", borderRadius: "16px", padding: "64px 0", textAlign: "center", color: THEME.textMuted }}>
                        No flagged events match the current filters.
                    </div>
                ) : (
                    filteredEvents.map(event => (
                        <FlaggedEventCard key={event.id} event={event} onMarkReviewed={handleMarkReviewed} isMarking={markingIds.has(event.id)} />
                    ))
                )}
            </div>
        </div>
    );
}
