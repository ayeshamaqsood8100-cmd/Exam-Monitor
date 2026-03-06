"use client";

import React from "react";
import { THEME } from "@/constants/theme";

export interface WindowRowProps {
    time: string;
    app: string;
    title: string;
}

export default function WindowRow({ time, app, title }: WindowRowProps): React.JSX.Element {

    // Dynamic badges per design doc: Chrome = Blue, Others = Yellow, Unknown = System (gray)
    const isUnknown = !app || app === "Unknown";
    const displayApp = isUnknown ? "System" : app;
    const isChrome = !isUnknown && app.toLowerCase().includes("chrome");

    const badgeColor = isUnknown ? THEME.textSecondary : (isChrome ? THEME.blue : THEME.yellow);
    const badgeBg = isUnknown ? "rgba(255,255,255,0.05)" : (isChrome ? `${THEME.blue}1A` : `${THEME.yellow}1A`);
    const badgeBorder = isUnknown ? "rgba(255,255,255,0.1)" : (isChrome ? `${THEME.blue}33` : `${THEME.yellow}33`);

    return (
        <div
            style={{
                display: "flex",
                alignItems: "center",
                gap: "14px",
                padding: "11px 0",
                borderBottom: "1px solid rgba(255,255,255,0.04)",
                fontSize: "13px"
            }}
        >
            <span style={{ color: THEME.textMuted, fontFamily: THEME.fontMono, fontSize: "12px", minWidth: "68px" }}>
                {time}
            </span>
            <span
                style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    padding: "3px 10px",
                    borderRadius: "6px",
                    background: badgeBg,
                    color: badgeColor,
                    border: `1px solid ${badgeBorder}`,
                    minWidth: "72px",
                    textAlign: "center"
                }}
            >
                {displayApp}
            </span>
            <span style={{ color: THEME.textSecondary, fontSize: "13px", flex: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {title}
            </span>
        </div>
    );
}
