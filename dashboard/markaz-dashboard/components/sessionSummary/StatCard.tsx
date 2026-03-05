"use client";

import React from "react";
import { THEME } from "@/constants/theme";

interface StatCardProps {
    label: string;
    value: string;
    sub: string;
    accent: string;
}

export default function StatCard({ label, value, sub, accent }: StatCardProps): React.JSX.Element {
    return (
        <div
            style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.07)",
                borderRadius: "16px",
                padding: "24px",
                backdropFilter: "blur(8px)",
                display: "flex",
                alignItems: "flex-start",
                gap: "16px"
            }}
        >
            <div
                style={{
                    width: "3px",
                    height: "40px",
                    borderRadius: "4px",
                    background: accent,
                    boxShadow: `0 0 12px ${accent}60`,
                    flexShrink: 0,
                    marginTop: "2px"
                }}
            />
            <div>
                <div style={{ fontSize: "26px", fontWeight: 700, color: accent, lineHeight: 1, fontFamily: THEME.fontMono }}>
                    {value}
                </div>
                <div style={{ fontSize: "12px", color: THEME.textSecondary, marginTop: "5px" }}>
                    {label} <span style={{ opacity: 0.6, fontStyle: "italic" }}>{sub}</span>
                </div>
            </div>
        </div>
    );
}
