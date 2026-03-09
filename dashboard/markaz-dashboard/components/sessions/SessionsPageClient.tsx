"use client";

import React, { useState, useEffect } from "react";
import { type ExamSummary, type SessionWithStudent } from "@/lib/sessions";
import { THEME } from "@/constants/theme";
import { useSessionPolling } from "@/hooks/useSessionPolling";
import SessionsTable from "@/components/sessions/SessionsTable";

interface SessionsPageClientProps {
    examId: string;
    initialSessions: SessionWithStudent[];
    exam: ExamSummary;
    onForceStopSession: (sessionId: string) => Promise<{ error?: string }>;
    onRestartSession: (sessionId: string) => Promise<{ error?: string }>;
}

export default function SessionsPageClient({ examId, initialSessions, exam, onForceStopSession, onRestartSession }: SessionsPageClientProps): React.JSX.Element {
    const { sessions, setSessions, lastRefreshed } = useSessionPolling(examId, initialSessions, 5000);
    const [stoppingIds, setStoppingIds] = useState<Set<string>>(new Set());
    const [restartingIds, setRestartingIds] = useState<Set<string>>(new Set());
    const [isMounted, setIsMounted] = useState(false);

    useEffect(() => {
        setIsMounted(true);
    }, []);

    const activeCount = sessions.filter(s => s.heartbeat_status === "active").length;
    const pausedCount = sessions.filter(s => s.heartbeat_status === "paused").length;
    const lostCount = sessions.filter(s => s.heartbeat_status === "heartbeat_lost").length;

    const handleForceStop = async (sessionId: string) => {
        setStoppingIds(prev => {
            const next = new Set(prev);
            next.add(sessionId);
            return next;
        });

        // Optimistic UI update
        setSessions(prev => prev.map(s =>
            s.id === sessionId ?
                { ...s, status: "paused", heartbeat_status: "paused" } : s
        ));

        await onForceStopSession(sessionId);

        setStoppingIds(prev => {
            const next = new Set(prev);
            next.delete(sessionId);
            return next;
        });
    };

    const handleRestart = async (sessionId: string) => {
        setRestartingIds(prev => {
            const next = new Set(prev);
            next.add(sessionId);
            return next;
        });

        // Optimistic UI update
        setSessions(prev => prev.map(s =>
            s.id === sessionId ?
                { ...s, status: "active", heartbeat_status: "active" } : s
        ));

        await onRestartSession(sessionId);

        setRestartingIds(prev => {
            const next = new Set(prev);
            next.delete(sessionId);
            return next;
        });
    };

    const formatTime = (d: Date) => {
        return d.toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false // Force 24 hr for technical readout
        });
    };

    return (
        <div>
            {/* Optional Top Warning Banner */}
            {exam.force_stop && (
                <div
                    style={{
                        background: `${THEME.pink}1A`, // ~10% opacity
                        border: `1px solid ${THEME.pink}4D`, // ~30% opacity
                        color: THEME.pink,
                        padding: "16px",
                        borderRadius: "8px",
                        marginBottom: "24px",
                        fontWeight: "bold",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        letterSpacing: "0.5px"
                    }}
                >
                    EXAM FORCE STOPPED — All sessions have been terminated.
                </div>
            )}

            {/* Header Area */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>

                <div>
                    <div style={{ color: THEME.textMuted, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" }}>
                        {exam.class_number}
                    </div>
                    <h1 style={{ color: THEME.textPrimary, fontSize: "26px", fontWeight: "bold", margin: 0 }}>
                        {exam.exam_name}
                    </h1>
                    <div style={{ color: THEME.textMuted, fontFamily: THEME.fontMono, fontSize: "12px", marginTop: "12px" }}>
                        Last refreshed: {isMounted ? formatTime(lastRefreshed) : null}
                    </div>
                </div>

                {/* Header Badges */}
                <div style={{ display: "flex", gap: "12px" }}>
                    <div
                        style={{
                            background: `${THEME.cyan}1A`,
                            border: `1px solid ${THEME.cyan}33`,
                            color: THEME.cyan,
                            padding: "6px 16px",
                            borderRadius: "20px",
                            fontSize: "14px",
                            fontWeight: 600,
                            display: "flex",
                            alignItems: "center",
                            gap: "8px"
                        }}
                    >
                        <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: THEME.cyan, animation: "breathe 2s infinite" }} />
                        {activeCount} Active
                    </div>

                    {lostCount > 0 && (
                        <div
                            style={{
                                background: `${THEME.pink}1A`,
                                border: `1px solid ${THEME.pink}33`,
                                color: THEME.pink,
                                padding: "6px 16px",
                                borderRadius: "20px",
                                fontSize: "14px",
                                fontWeight: 600,
                                display: "flex",
                                alignItems: "center",
                                gap: "8px"
                            }}
                        >
                            <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: THEME.pink }} />
                            {lostCount} Lost
                        </div>
                    )}

                    {pausedCount > 0 && (
                        <div
                            style={{
                                background: `${THEME.yellow}1A`,
                                border: `1px solid ${THEME.yellow}33`,
                                color: THEME.yellow,
                                padding: "6px 16px",
                                borderRadius: "20px",
                                fontSize: "14px",
                                fontWeight: 600,
                                display: "flex",
                                alignItems: "center",
                                gap: "8px"
                            }}
                        >
                            <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: THEME.yellow }} />
                            {pausedCount} Paused
                        </div>
                    )}
                </div>

            </div>

            {/* Neon divider line */}
            <div
                style={{
                    height: "1px",
                    background: `linear-gradient(90deg, transparent, ${THEME.cyan}26, transparent)`,
                    marginBottom: "32px",
                }}
            />

            <SessionsTable
                sessions={sessions}
                onForceStop={handleForceStop}
                stoppingIds={stoppingIds}
                onRestart={handleRestart}
                restartingIds={restartingIds}
            />
        </div>
    );
}
