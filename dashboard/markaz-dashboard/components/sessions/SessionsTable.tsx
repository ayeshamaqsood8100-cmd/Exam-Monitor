"use client";

import React from "react";
import { type SessionWithStudent } from "@/lib/sessions";
import SessionRow from "./SessionRow";

interface SessionsTableProps {
    sessions: SessionWithStudent[];
    onForceStop: (sessionId: string) => void;
    stoppingIds: Set<string>;
}

export default function SessionsTable({ sessions, onForceStop, stoppingIds }: SessionsTableProps): React.JSX.Element {
    return (
        <div className="aesthetic-card p-0 overflow-hidden">
            <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                    <thead>
                        <tr>
                            <th className="text-[var(--text-muted)] text-[11px] uppercase tracking-[0.08em] px-5 py-4 border-b border-[var(--border)] text-left font-semibold">Student</th>
                            <th className="text-[var(--text-muted)] text-[11px] uppercase tracking-[0.08em] px-5 py-4 border-b border-[var(--border)] text-left font-semibold">Status</th>
                            <th className="text-[var(--text-muted)] text-[11px] uppercase tracking-[0.08em] px-5 py-4 border-b border-[var(--border)] text-left font-semibold">Last Heartbeat</th>
                            <th className="text-[var(--text-muted)] text-[11px] uppercase tracking-[0.08em] px-5 py-4 border-b border-[var(--border)] text-left font-semibold">Session Start</th>
                            <th className="text-[var(--text-muted)] text-[11px] uppercase tracking-[0.08em] px-5 py-4 border-b border-[var(--border)] text-left font-semibold">Flags</th>
                            <th className="text-[var(--text-muted)] text-[11px] uppercase tracking-[0.08em] px-5 py-4 border-b border-[var(--border)] text-left font-semibold">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sessions.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="px-5 py-12 text-center text-[var(--text-muted)]">
                                    No sessions active for this configuration yet.
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
        </div>
    );
}
