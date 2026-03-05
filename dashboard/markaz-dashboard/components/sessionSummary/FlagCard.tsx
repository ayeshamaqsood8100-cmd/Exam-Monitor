"use client";

import React from "react";
import { THEME } from "@/constants/theme";

export interface FlagCardProps {
    severity: "HIGH" | "MED" | "LOW";
    type: string;
    time: string;
    desc: string;
    evidence: string | null;
}

export default function FlagCard({ severity, type, time, desc, evidence }: FlagCardProps): React.JSX.Element {

    // Derived severity thematic coloring mapped exactly from design specifications
    const c = (() => {
        switch (severity) {
            case "HIGH": return { text: THEME.pink, bg: `${THEME.pink}14`, border: `${THEME.pink}40` };
            case "MED": return { text: THEME.yellow, bg: `${THEME.yellow}14`, border: `${THEME.yellow}40` };
            case "LOW": return { text: THEME.cyan, bg: `${THEME.cyan}14`, border: `${THEME.cyan}40` };
            default: return { text: THEME.textMuted, bg: "rgba(255,255,255,0.05)", border: "rgba(255,255,255,0.1)" };
        }
    })();

    return (
        <div
            style={{
                borderRadius: "12px",
                padding: "18px 20px",
                marginBottom: "10px",
                border: `1px solid ${c.border}`,
                background: c.bg,
                transition: "transform 0.15s ease",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.transform = "translateX(3px)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.transform = "translateX(0px)"; }}
        >
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                <span
                    style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        color: c.text,
                        background: `${c.text}15`,
                        border: `1px solid ${c.border}`,
                        borderRadius: "6px",
                        padding: "2px 8px"
                    }}
                >
                    {severity}
                </span>

                <span style={{ fontSize: "14px", fontWeight: 600, color: THEME.textPrimary }}>
                    {type}
                </span>

                <span style={{ marginLeft: "auto", fontSize: "12px", color: THEME.textMuted, fontFamily: THEME.fontMono }}>
                    {time}
                </span>
            </div>

            <div style={{ fontSize: "13px", color: THEME.textSecondary, marginBottom: "10px" }}>
                {desc}
            </div>

            {evidence && (
                <div
                    style={{
                        background: "rgba(0,0,0,0.3)",
                        borderRadius: "8px",
                        padding: "8px 12px",
                        fontSize: "12px",
                        color: THEME.textSecondary,
                        fontFamily: THEME.fontMono,
                        wordWrap: "break-word"
                    }}
                >
                    {evidence}
                </div>
            )}
        </div>
    );
}
