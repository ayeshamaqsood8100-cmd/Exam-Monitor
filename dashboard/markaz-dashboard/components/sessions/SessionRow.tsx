"use client";

import React from "react";
import Link from "next/link";
import { type SessionWithStudent } from "@/lib/sessions";

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

    let dotColorClass = "bg-[#a1a1aa]";
    let badgeColorClass = "text-[#a1a1aa] bg-[#a1a1aa]/10 border-[#a1a1aa]/30";
    let pulseClass = "";

    switch (session.display_status) {
        case "ACTIVE":
            dotColorClass = "bg-[#06b6d4] shadow-[0_0_8px_#06b6d4]";
            badgeColorClass = "text-[#06b6d4] bg-[#06b6d4]/10 border-[#06b6d4]/30";
            pulseClass = "badge-pulse";
            break;
        case "PAUSED":
            dotColorClass = "bg-[#ffd166]";
            badgeColorClass = "text-[#ffd166] bg-[#ffd166]/10 border-[#ffd166]/30";
            break;
        case "COMPLETED":
        case "COMPLETED - ENDED EARLY":
            dotColorClass = "bg-[#8b5cf6]";
            badgeColorClass = "text-[#8b5cf6] bg-[#8b5cf6]/10 border-[#8b5cf6]/30";
            break;
        case "COMPLETED - ENDED LATE":
            dotColorClass = "bg-[#3b82f6]";
            badgeColorClass = "text-[#3b82f6] bg-[#3b82f6]/10 border-[#3b82f6]/30";
            break;
        case "TERMINATED":
        case "AGENT KILLED":
            dotColorClass = "bg-[#ef4444]";
            badgeColorClass = "text-[#ef4444] bg-[#ef4444]/10 border-[#ef4444]/30";
            if (session.display_status === "AGENT KILLED") pulseClass = "animate-pulse";
            break;
        case "AGENT LOST":
            dotColorClass = "bg-[#ec4899]";
            badgeColorClass = "text-[#ec4899] bg-[#ec4899]/10 border-[#ec4899]/30";
            pulseClass = "animate-pulse";
            break;
        case "RESTARTED AFTER REBOOT":
            dotColorClass = "bg-[#ffd166]";
            badgeColorClass = "text-[#ffd166] bg-[#ffd166]/10 border-[#ffd166]/30";
            break;
    }

    const needsAttention = session.needs_attention;
    
    return (
        <tr className={`border-b border-white/5 transition-colors duration-150 ${needsAttention ? 'border-l-[3px] border-l-[#ef4444] bg-[#ef4444]/5 hover:bg-[#ef4444]/10' : 'hover:bg-white/[0.02]'}`}>
            <td className="px-5 py-4">
                <div className="text-[var(--text-primary)] font-bold text-sm">{student.name}</div>
                <div className="text-[var(--text-secondary)] font-mono text-xs mt-0.5">{student.erp}</div>
                {needsAttention && (
                    <div className="mt-2">
                        <span className="text-[10px] font-bold tracking-[0.04em] px-2 py-0.5 rounded-full text-[#ef4444] bg-[#ef4444]/10 border border-[#ef4444]/30">
                            NEEDS ATTENTION
                        </span>
                    </div>
                )}
            </td>
            
            <td className="px-5 py-4">
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${dotColorClass} ${pulseClass}`} />
                    <span className={`text-[11px] font-bold px-2 py-0.5 rounded-md border ${badgeColorClass}`}>
                        {session.display_status}
                    </span>
                </div>
                {session.attention_reason && (
                    <div className="mt-2 text-xs text-[var(--text-secondary)] max-w-[280px]">
                        {session.attention_reason}
                    </div>
                )}
            </td>
            
            <td className="px-5 py-4">
                <div className="text-[var(--text-primary)] font-mono text-xs opacity-90">
                    {formatDate(session.last_heartbeat_at)}
                </div>
            </td>
            
            <td className="px-5 py-4">
                <div className="text-[var(--text-secondary)] font-mono text-xs">
                    {formatDate(session.session_start)}
                </div>
            </td>
            
            <td className="px-5 py-4">
                {flag_count > 0 ? (
                    <span className="inline-flex items-center justify-center whitespace-nowrap text-[11px] font-bold px-2 py-0.5 rounded-md text-[#ec4899] bg-[#ec4899]/10 border border-[#ec4899]/30 tracking-wide">
                        {flag_count} {flag_count === 1 ? "flag" : "flags"}
                    </span>
                ) : (
                    <span className="text-[var(--text-muted)] font-mono text-xs">—</span>
                )}
            </td>
            
            <td className="px-5 py-4">
                <div className="flex items-center gap-3">
                    <Link href={`/sessions/${session.id}`} className="text-[var(--accent-cyan)] hover:text-white font-medium text-xs no-underline transition-colors">
                        View Feed
                    </Link>
                    {!isTerminated && (
                        <button
                            onClick={() => {
                                if (confirm("End & remove this student's agent now? This cannot be restarted.")) {
                                    onForceStop(session.id);
                                }
                            }}
                            disabled={isStopping}
                            className={`bg-transparent border border-[var(--accent-pink)] text-[var(--accent-pink)] px-2.5 py-1 rounded-md text-[11px] font-bold transition-colors ${isStopping ? 'opacity-50 cursor-wait' : 'hover:bg-[var(--accent-pink)]/10 cursor-pointer'}`}
                        >
                            {isStopping ? "Ending..." : "End Session"}
                        </button>
                    )}
                </div>
            </td>
        </tr>
    );
}
