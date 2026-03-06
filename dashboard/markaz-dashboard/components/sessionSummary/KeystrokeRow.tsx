"use client";

import React from "react";
import { THEME } from "@/constants/theme";

interface KeystrokeRowProps {
    time: string;
    application: string;
}

export default function KeystrokeRow({ time, application }: KeystrokeRowProps): React.JSX.Element {
    const isChrome = application === "Chrome";

    // Derived badge styling based on design system rules and the locked THEME colors
    const badgeBg = isChrome ? `${THEME.blue}1A` : `${THEME.yellow}1A`; // 0.1 opacity
    const badgeBorder = isChrome ? `${THEME.blue}33` : `${THEME.yellow}33`; // 0.2 opacity 
    const badgeTextColor = isChrome ? THEME.blue : THEME.yellow;

    return (
        <div style={{
            display: "flex",
            alignItems: "center",
            gap: "14px",
            padding: "10px 0",
            borderBottom: `1px solid rgba(255,255,255,0.04)`
        }}>
            <span style={{
                fontFamily: THEME.fontMono,
                fontSize: "12px",
                color: THEME.textMuted,
                minWidth: "68px"
            }}>
                {time}
            </span>
            <span style={{
                fontSize: "12px",
                fontWeight: 600,
                color: badgeTextColor,
                background: badgeBg,
                border: `1px solid ${badgeBorder}`,
                borderRadius: "6px",
                padding: "3px 10px"
            }}>
                {application}
            </span>
        </div>
    );
}
