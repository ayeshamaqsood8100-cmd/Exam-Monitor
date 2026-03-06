"use client";

import React, { useState } from "react";
import { type SessionSummaryData } from "@/lib/sessionSummary";
import { THEME } from "@/constants/theme";
import StatCard from "./StatCard";
import FlagCard from "./FlagCard";
import WindowRow from "./WindowRow";
import ClipboardEvent from "./ClipboardEvent";
import KeystrokeRow from "./KeystrokeRow";

interface SessionSummaryClientProps {
    data: SessionSummaryData;
}

export default function SessionSummaryClient({ data }: SessionSummaryClientProps): React.JSX.Element {
    const [tab, setTab] = useState<"overview" | "flags" | "windows" | "clipboard" | "keystrokes">("overview");

    // Format Helper avoiding hydration errors by extracting raw strings from DB cleanly
    const extractTime = (dateString: string) => {
        if (!dateString || dateString.includes("Unknown")) return "—";
        const parts = dateString.split(" ");
        return parts[1] || dateString;
    };

    const highFlags = data.flags.filter(f => f.severity === "HIGH").length;
    const medFlags = data.flags.filter(f => f.severity === "MED").length;
    const lowFlags = data.flags.filter(f => f.severity === "LOW").length;

    return (
        <div style={{ paddingBottom: "64px" }}>

            {/* Top nav / Breadcrumbs */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "40px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <div style={{
                        width: "32px", height: "32px", borderRadius: "8px",
                        background: `linear-gradient(135deg, ${THEME.cyan}, ${THEME.purple})`,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: "14px", fontWeight: 700, color: THEME.textPrimary
                    }}>
                        M
                    </div>
                    <span style={{ fontSize: "15px", fontWeight: 600, color: THEME.textPrimary }}>Markaz</span>
                    <span style={{ fontSize: "13px", color: THEME.textMuted, marginLeft: "4px" }}>/ Session Report</span>
                </div>

                <div style={{
                    display: "flex", alignItems: "center", gap: "8px",
                    background: data.session.status === "completed" ? `${THEME.cyan}0F` : `${THEME.yellow}0F`,
                    border: `1px solid ${data.session.status === "completed" ? THEME.cyan : THEME.yellow}26`,
                    borderRadius: "20px", padding: "5px 12px"
                }}>
                    <div
                        style={{
                            width: "8px", height: "8px", borderRadius: "50%",
                            background: data.session.status === "completed" ? THEME.cyan : THEME.yellow,
                            animation: data.session.status === "completed" ? "none" : "breathe 2.5s ease-in-out infinite",
                            boxShadow: `0 0 8px ${data.session.status === "completed" ? THEME.cyan : THEME.yellow}`
                        }}
                    />
                    <span style={{
                        fontSize: "12px",
                        color: data.session.status === "completed" ? THEME.cyan : THEME.yellow,
                        fontWeight: 500,
                        textTransform: "capitalize"
                    }}>
                        {data.session.status}
                    </span>
                </div>
            </div>

            {/* Hero section */}
            <div style={{ marginBottom: "32px" }}>
                <div style={{ fontSize: "12px", color: THEME.textSecondary, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "8px" }}>
                    {data.exam.class_number}
                </div>
                <h1 style={{ fontSize: "26px", fontWeight: 700, color: THEME.textPrimary, marginBottom: "16px", letterSpacing: "-0.02em", marginTop: 0 }}>
                    {data.exam.name}
                </h1>

                <div style={{ display: "flex", flexWrap: "wrap", gap: "24px" }}>
                    {[
                        { label: "Student", value: data.student.name },
                        { label: "ERP", value: data.student.erp },
                        { label: "Date", value: data.session.start.split(",")[0] || "Unknown" },
                        { label: "Window", value: `${extractTime(data.session.start)} – ${data.session.end ? extractTime(data.session.end) : "Active"}` }
                    ].map(item => (
                        <div key={item.label}>
                            <div style={{ fontSize: "11px", color: THEME.textSecondary, textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "3px" }}>
                                {item.label}
                            </div>
                            <div style={{ fontSize: "14px", color: THEME.textPrimary, fontWeight: 500 }}>
                                {item.value}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Alert banner */}
            {data.stats.flags > 0 && (
                <div style={{
                    background: `${THEME.pink}0F`,
                    border: `1px solid ${THEME.pink}33`,
                    borderRadius: "12px", padding: "14px 20px", marginBottom: "28px",
                    display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "16px"
                }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: THEME.pink, boxShadow: `0 0 8px ${THEME.pink}` }} />
                        <span style={{ fontSize: "13px", color: THEME.pink, fontWeight: 600 }}>
                            {data.stats.flags} event{data.stats.flags !== 1 && "s"} flagged for review
                        </span>
                    </div>
                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                        {[
                            { count: highFlags, label: "High", color: THEME.pink },
                            { count: medFlags, label: "Medium", color: THEME.yellow },
                            { count: lowFlags, label: "Low", color: THEME.cyan }
                        ].filter(s => s.count > 0).map((s) => (
                            <span key={s.label} style={{
                                fontSize: "11px", color: s.color, background: `${s.color}15`,
                                border: `1px solid ${s.color}30`, borderRadius: "6px",
                                padding: "3px 9px", fontWeight: 500
                            }}>
                                {s.count} {s.label}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Stat grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "12px", marginBottom: "32px" }}>
                <StatCard label="Keystrokes" value={data.stats.keystrokes.toLocaleString()} sub="logged" accent={THEME.cyan} />
                <StatCard label="Window Switches" value={data.stats.windows.toString()} sub="detected" accent={THEME.pink} />
                <StatCard label="Clipboard Events" value={data.stats.clipboard.toString()} sub="captured" accent={THEME.purple} />
                <StatCard label="Flagged Events" value={data.stats.flags.toString()} sub="need review" accent={data.stats.flags > 0 ? THEME.pink : THEME.textMuted} />
                <StatCard label="Sync Cycles" value={data.stats.syncs.toString()} sub="completed" accent={THEME.cyan} />
                <StatCard label="Offline Periods" value={data.stats.offline_periods.toString()} sub="brief gaps" accent={data.stats.offline_periods > 0 ? THEME.yellow : THEME.textMuted} />
            </div>

            {/* Tabs */}
            <div style={{
                display: "flex", gap: "4px", marginBottom: "20px",
                background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: "10px", padding: "4px", width: "fit-content",
                overflowX: "auto", maxWidth: "100%"
            }}>
                {(["overview", "flags", "windows", "clipboard", "keystrokes"] as const).map(t => (
                    <button
                        key={t}
                        onClick={() => setTab(t)}
                        style={{
                            padding: "8px 20px",
                            borderRadius: "8px",
                            fontSize: "13px",
                            fontWeight: 500,
                            cursor: "pointer",
                            border: "none",
                            background: tab === t ? `${THEME.cyan}1A` : "transparent",
                            color: tab === t ? THEME.cyan : THEME.textSecondary,
                            transition: "all 0.2s",
                            letterSpacing: "0.01em",
                            textTransform: "capitalize"
                        }}
                    >
                        {t}
                    </button>
                ))}
            </div>

            {/* Tab Content Areas */}

            {/* Overview Tab */}
            {tab === "overview" && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>

                    {/* Timeline Card */}
                    <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "16px", padding: "24px" }}>
                        <div style={{ fontSize: "11px", color: THEME.textSecondary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "18px" }}>
                            Session Timeline
                        </div>
                        {[
                            { label: "Session Start", val: extractTime(data.session.start), color: THEME.cyan },
                            { label: "Consent Recorded", val: data.health.consented_at ? extractTime(data.health.consented_at) : "Not recorded", color: data.health.consented_at ? THEME.cyan : THEME.yellow },
                            { label: "First Flag Raised", val: data.flags.length > 0 ? extractTime(data.flags[0].flagged_at) : "None", color: data.flags.length > 0 ? THEME.pink : THEME.textMuted },
                            { label: "Last Heartbeat", val: data.session.last_heartbeat ? extractTime(data.session.last_heartbeat) : "None", color: data.session.last_heartbeat ? THEME.cyan : THEME.textMuted },
                            { label: "Session End", val: data.session.end ? extractTime(data.session.end) : "In progress", color: data.session.end ? THEME.cyan : THEME.yellow },
                        ].map(row => (
                            <div key={row.label} style={{ display: "flex", justifyContent: "space-between", padding: "9px 0", borderBottom: "1px solid rgba(255,255,255,0.04)", fontSize: "13px" }}>
                                <span style={{ color: THEME.textSecondary }}>{row.label}</span>
                                <span style={{ color: row.color, fontFamily: THEME.fontMono, fontSize: "12px" }}>{row.val}</span>
                            </div>
                        ))}
                    </div>

                    {/* Health Card */}
                    <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "16px", padding: "24px" }}>
                        <div style={{ fontSize: "11px", color: THEME.textSecondary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "18px" }}>
                            Agent Health
                        </div>
                        {[
                            { label: "Heartbeat Interval", val: "30s", ok: true },
                            { label: "Sync Cycles", val: data.stats.syncs.toString(), ok: data.stats.syncs > 0 },
                            { label: "Offline Periods", val: data.stats.offline_periods.toString(), ok: data.stats.offline_periods === 0 },
                            { label: "Agent Version", val: data.health.agent_version, ok: data.health.agent_version !== "Unknown" },
                            { label: "Session Integrity", val: data.stats.offline_periods === 0 ? "Intact" : "Gap detected", ok: data.stats.offline_periods === 0 },
                        ].map(row => (
                            <div key={row.label} style={{ display: "flex", justifyContent: "space-between", padding: "9px 0", borderBottom: "1px solid rgba(255,255,255,0.04)", fontSize: "13px" }}>
                                <span style={{ color: THEME.textSecondary }}>{row.label}</span>
                                <span style={{ color: row.ok ? THEME.cyan : THEME.yellow, fontFamily: THEME.fontMono, fontSize: "12px" }}>{row.val}</span>
                            </div>
                        ))}
                    </div>

                </div>
            )}

            {/* Flags Tab */}
            {tab === "flags" && (
                <div>
                    {data.flags.length === 0 ? (
                        <div style={{ padding: "48px 0", textAlign: "center", color: THEME.textMuted }}>
                            No flagged events recorded for this session.
                        </div>
                    ) : (
                        data.flags.map(f => (
                            <FlagCard
                                key={f.id}
                                severity={f.severity}
                                type={f.flag_type}
                                time={extractTime(f.flagged_at)}
                                desc={f.description || "No description"}
                                evidence={f.evidence}
                            />
                        ))
                    )}
                </div>
            )}

            {/* Windows Tab */}
            {tab === "windows" && (
                <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "16px", padding: "24px" }}>
                    <div style={{ fontSize: "11px", color: THEME.textSecondary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "16px" }}>
                        Window Switch Log · {data.windows.length} entries
                    </div>
                    {data.windows.length === 0 ? (
                        <div style={{ padding: "32px 0", textAlign: "center", color: THEME.textMuted }}>
                            No window switches recorded.
                        </div>
                    ) : (
                        data.windows.map((w, i) => (
                            <WindowRow
                                key={i}
                                time={extractTime(w.switched_at)}
                                app={w.app_name}
                                title={w.window_title}
                            />
                        ))
                    )}
                </div>
            )}

            {/* Clipboard Tab */}
            {tab === "clipboard" && (
                <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "16px", padding: "24px" }}>
                    <div style={{ fontSize: "11px", color: THEME.textSecondary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "16px" }}>
                        Clipboard Events · {data.clipboard.length} captured
                    </div>
                    {data.clipboard.length === 0 ? (
                        <div style={{ padding: "32px 0", textAlign: "center", color: THEME.textMuted }}>
                            No clipboard activity recorded.
                        </div>
                    ) : (
                        data.clipboard.map((c) => (
                            <ClipboardEvent
                                key={c.id}
                                time={extractTime(c.captured_at)}
                                eventType={c.event_type}
                                src={c.source_app}
                                dst={c.destination_app}
                                content={c.content}
                            />
                        ))
                    )}
                </div>
            )}

            {/* Keystrokes Tab */}
            {tab === "keystrokes" && (
                <div style={{ background: THEME.cardBg, border: `1px solid ${THEME.cardBorder}`, borderRadius: "16px", padding: "24px" }}>
                    <div style={{ fontSize: "11px", color: THEME.textSecondary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "16px" }}>
                        Keystroke Log · {data.keystrokes.length} entries · key data hidden
                    </div>
                    {data.keystrokes.length === 0 ? (
                        <div style={{ padding: "32px 0", textAlign: "center", color: THEME.textMuted }}>
                            No keystrokes recorded.
                        </div>
                    ) : (
                        <div style={{
                            // We construct a specific wrapper CSS to remove the bottom border on the very last row,
                            // rather than passing an prop into KeystrokeRow since we have to wrap it somehow anyway.
                            // The easier fix since we can't do :last-child inline dynamically easily is just map the index.
                        }}>
                            {data.keystrokes.map((k, i) => (
                                <div key={k.id} style={{ borderBottom: i === data.keystrokes.length - 1 ? "none" : undefined }}>
                                    <KeystrokeRow
                                        time={extractTime(k.captured_at)}
                                        application={k.application}
                                    />
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Neon line divider */}
            <div style={{
                height: "1px",
                background: `linear-gradient(90deg, transparent, ${THEME.cyan}, transparent)`,
                opacity: 0.3, marginTop: "40px", marginBottom: "28px"
            }} />

            {/* Footer */}
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: THEME.textMuted }}>
                <span>Markaz · IBA Karachi</span>
                <span>Report generated · {data.session.start.split(",")[0]}</span>
            </div>

        </div>
    );
}
