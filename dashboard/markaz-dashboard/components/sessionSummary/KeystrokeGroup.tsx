"use client";

import React from "react";
import { THEME } from "@/constants/theme";

interface KeystrokeGroupProps {
    startTime: string;
    endTime: string;
    application: string;
    text: string;
}

export default function KeystrokeGroup({ startTime, endTime, application, text }: KeystrokeGroupProps): React.JSX.Element {
    const isChrome = application === "Chrome";

    const badgeBg = isChrome ? `${THEME.blue}1A` : `${THEME.yellow}1A`;
    const badgeBorder = isChrome ? `${THEME.blue}33` : `${THEME.yellow}33`;
    const badgeTextColor = isChrome ? THEME.blue : THEME.yellow;

    return (
        <div style={{
            display: "flex",
            gap: "14px",
            padding: "12px 0",
            borderBottom: `1px solid rgba(255,255,255,0.04)`
        }}>
            <span style={{
                fontFamily: THEME.fontMono,
                fontSize: "12px",
                color: THEME.textMuted,
                minWidth: "140px"
            }}>
                {startTime} — {endTime}
            </span>
            <div>
                <span style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    color: badgeTextColor,
                    background: badgeBg,
                    border: `1px solid ${badgeBorder}`,
                    borderRadius: "6px",
                    padding: "3px 10px",
                    whiteSpace: "nowrap"
                }}>
                    {application}
                </span>
            </div>
            <span style={{
                fontFamily: THEME.fontMono,
                fontSize: "13px",
                color: THEME.textSecondary,
                flex: 1,
                wordBreak: "break-word"
            }}>
                "{text}"
            </span>
        </div>
    );
}
