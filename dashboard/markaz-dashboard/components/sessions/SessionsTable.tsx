"use client";
import React from "react";
import { type SessionWithStudent } from "@/lib/sessions";
import { THEME } from "@/constants/theme";
import Card from "@/components/ui/Card";
import SessionRow from "./SessionRow";
interface SessionsTableProps {
    sessions: SessionWithStudent[];
    onForceStop: (sessionId: string) => void;
    stoppingIds: Set<string>;
}
export default function SessionsTable({ sessions, onForceStop, stoppingIds }: SessionsTableProps): React.JSX.Element {
    const thStyle: React.CSSProperties = {
        color: THEME.textMuted,
        fontSize: "11px",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        padding: "12px 16px",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        textAlign: "left",
        fontWeight: 600
    };
    return (
        <Card style={{ padding: 0, overflow: "hidden" }}>
            <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                        <tr>
                            <th style={thStyle}>Student</th>
                            <th style={thStyle}>Status</th>
                            <th style={thStyle}>Last Heartbeat</th>
                            <th style={thStyle}>Session Start</th>
                            <th style={thStyle}>Flags</th>
                            <th style={thStyle}>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sessions.length === 0 ? (
                            <tr>
                                <td colSpan={6} style={{ padding: "48px 16px", textAlign: "center" }}>
                                    <div style={{ color: THEME.textMuted }}>No sessions yet for this exam.</div>
                                </td>
                            </tr>
                        ) : (
                            sessions.map((session) => (
                                <SessionRow
                                    key={session.id}
                                    session={session}
                                    onForceStop={onForceStop}
                                    isStopping={stoppingIds.has(session.id)}
                                />
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </Card>
    );
}
