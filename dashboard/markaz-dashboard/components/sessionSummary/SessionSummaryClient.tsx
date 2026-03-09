"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { type SessionSummaryData } from "@/lib/sessionSummary";
import { THEME } from "@/constants/theme";
import StatCard from "./StatCard";
import FlagCard from "./FlagCard";
import WindowRow from "./WindowRow";
import ClipboardEvent from "./ClipboardEvent";
import KeystrokeGroup from "./KeystrokeGroup";

interface SessionSummaryClientProps {
    data: SessionSummaryData;
}

export default function SessionSummaryClient({ data }: SessionSummaryClientProps): React.JSX.Element {
    const router = useRouter();
    const [tab, setTab] = useState<"overview" | "flags" | "windows" | "clipboard" | "keystrokes">("overview");
    const [analyzing, setAnalyzing] = useState(false);
    const [analyzeResult, setAnalyzeResult] = useState<string | null>(null);
    const [stopping, setStopping] = useState(false);
    const [stopResult, setStopResult] = useState<string | null>(null);

    // Format Helper avoiding hydration errors by extracting raw strings from DB cleanly
    const extractTime = (dateString: string) => {
        if (!dateString || dateString.includes("Unknown")) return "—";
        const parts = dateString.split(" ");
        return parts[1] || dateString;
    };

    const handleAnalyze = async () => {
        setAnalyzing(true);
        setAnalyzeResult(null);
        try {
            const res = await fetch(`/api/analyze/${data.sessionId}`, { method: "POST" });
            if (!res.ok) {
                const err = await res.json();
                setAnalyzeResult(`Error: ${err.error || "Unknown error"}`);
            } else {
                const result = await res.json();
                setAnalyzeResult(`✓ ${result.flags_inserted} flag${result.flags_inserted !== 1 ? "s" : ""} detected`);
                // Refresh the page to show new flags
                setTimeout(() => router.refresh(), 500);
            }
        } catch {
            setAnalyzeResult("Error: Network error");
        } finally {
            setAnalyzing(false);
        }
    };

    const handleStop = async () => {
        if (!confirm("Pause this student's monitoring now? The widget should disappear almost immediately.")) return;
        setStopping(true);
        setStopResult(null);
        try {
            const res = await fetch(`/api/stop/${data.sessionId}`, { method: "POST" });
            if (!res.ok) {
                const err = await res.json();
                setStopResult(`Error: ${err.error || "Unknown error"}`);
            } else {
                setStopResult("✓ Session paused");
                setTimeout(() => router.refresh(), 1000);
            }
        } catch {
            setStopResult("Error: Network error");
        } finally {
            setStopping(false);
        }
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

                <div style={{ display: "flex", flexWrap: "wrap", gap: "24px", alignItems: "flex-end" }}>
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

                    {/* Analyze with AI button */}
                    <button
                        onClick={handleAnalyze}
                        disabled={analyzing}
                        style={{
                            display: "flex", alignItems: "center", gap: "8px",
                            background: analyzing ? "rgba(255,255,255,0.05)" : `linear-gradient(135deg, ${THEME.purple}40, ${THEME.cyan}40)`,
                            border: `1px solid ${analyzing ? "rgba(255,255,255,0.1)" : `${THEME.purple}60`}`,
                            color: analyzing ? THEME.textMuted : THEME.textPrimary,
                            padding: "10px 20px", borderRadius: "10px",
                            fontSize: "13px", fontWeight: 600,
                            cursor: analyzing ? "not-allowed" : "pointer",
                            transition: "all 0.2s ease",
                            marginLeft: "auto"
                        }}
                        onMouseEnter={(e) => { if (!analyzing) e.currentTarget.style.boxShadow = `0 0 20px ${THEME.purple}30`; }}
                        onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "none"; }}
                    >
                        {analyzing ? (
                            <>
                                <span style={{ display: "inline-block", width: "14px", height: "14px", border: "2px solid rgba(255,255,255,0.2)", borderTopColor: THEME.cyan, borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                                Analyzing...
                            </>
                        ) : (
                            <>🔍 Analyze with AI</>
                        )}
                    </button>

                    {/* Pause Session button — only for active sessions */}
                    {data.session.status === "active" && (
                        <button
                            onClick={handleStop}
                            disabled={stopping}
                            style={{
                                display: "flex", alignItems: "center", gap: "8px",
                                background: stopping ? "rgba(255,255,255,0.05)" : `${THEME.pink}15`,
                                border: `1px solid ${stopping ? "rgba(255,255,255,0.1)" : `${THEME.pink}40`}`,
                                color: stopping ? THEME.textMuted : THEME.pink,
                                padding: "10px 20px", borderRadius: "10px",
                                fontSize: "13px", fontWeight: 600,
                                cursor: stopping ? "not-allowed" : "pointer",
                                transition: "all 0.2s ease"
                            }}
                            onMouseEnter={(e) => { if (!stopping) e.currentTarget.style.boxShadow = `0 0 20px ${THEME.pink}20`; }}
                            onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "none"; }}
                        >
                            {stopping ? (
                                <>
                                    <span style={{ display: "inline-block", width: "14px", height: "14px", border: "2px solid rgba(255,255,255,0.2)", borderTopColor: THEME.pink, borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                                    Pausing...
                                </>
                            ) : (
                                <>⛔ Pause Session</>
                            )}
                        </button>
                    )}
                </div>

                {/* Analysis result message */}
                {analyzeResult && (
                    <div style={{
                        marginTop: "12px",
                        fontSize: "13px",
                        fontWeight: 500,
                        color: analyzeResult.startsWith("✓") ? THEME.cyan : THEME.pink,
                        padding: "8px 14px",
                        background: analyzeResult.startsWith("✓") ? `${THEME.cyan}10` : `${THEME.pink}10`,
                        border: `1px solid ${analyzeResult.startsWith("✓") ? `${THEME.cyan}30` : `${THEME.pink}30`}`,
                        borderRadius: "8px",
                        display: "inline-block",
                        marginRight: "8px"
                    }}>
                        {analyzeResult}
                    </div>
                )}

                {/* Stop result message */}
                {stopResult && (
                    <div style={{
                        marginTop: "12px",
                        fontSize: "13px",
                        fontWeight: 500,
                        color: stopResult.startsWith("✓") ? THEME.cyan : THEME.pink,
                        padding: "8px 14px",
                        background: stopResult.startsWith("✓") ? `${THEME.cyan}10` : `${THEME.pink}10`,
                        border: `1px solid ${stopResult.startsWith("✓") ? `${THEME.cyan}30` : `${THEME.pink}30`}`,
                        borderRadius: "8px",
                        display: "inline-block"
                    }}>
                        {stopResult}
                    </div>
                )}
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
                    <div style={{ fontSize: "11px", color: THEME.textSecondary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "8px" }}>
                        Keystroke Log · {data.keystrokeGroups.length} groups
                    </div>
                    {/* Legend */}
                    <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", marginBottom: "16px", paddingBottom: "16px", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                        {[
                            { symbol: "[ENTER]", desc: "Enter key" },
                            { symbol: "[BS]", desc: "Backspace" },
                            { symbol: "[TAB]", desc: "Tab" },
                            { symbol: "[DEL]", desc: "Delete" },
                            { symbol: "[ESC]", desc: "Escape" }
                        ].map(legend => (
                            <div key={legend.symbol} style={{ fontSize: "11px", fontFamily: THEME.fontMono }}>
                                <span style={{ color: THEME.cyan }}>{legend.symbol}</span>
                                <span style={{ color: THEME.textMuted }}> = {legend.desc}</span>
                            </div>
                        ))}
                    </div>
                    {data.keystrokeGroups.length === 0 ? (
                        <div style={{ padding: "32px 0", textAlign: "center", color: THEME.textMuted }}>
                            No keystrokes recorded.
                        </div>
                    ) : (
                        <div>
                            {data.keystrokeGroups.map((k, i) => (
                                <KeystrokeGroup
                                    key={i}
                                    startTime={k.startTime}
                                    endTime={k.endTime}
                                    application={k.application}
                                    text={k.text}
                                />
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
