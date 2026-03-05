"use client";

import React from "react";
import { THEME } from "@/constants/theme";

export interface ClipboardEventProps {
    time: string;
    eventType: "COPY" | "PASTE";
    src: string;
    dst: string | null;
    content: string;
}

export default function ClipboardEvent({ time, eventType, src, dst, content }: ClipboardEventProps): React.JSX.Element {
    const isPaste = eventType === "PASTE";
    const badgeColor = isPaste ? THEME.pink : THEME.cyan;
    const badgeBg = isPaste ? `${THEME.pink}1A` : `${THEME.cyan}1A`;
    const badgeBorder = isPaste ? `${THEME.pink}33` : `${THEME.cyan}33`;

    return (
        <div style={{ padding: "14px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                <span style={{ fontFamily: THEME.fontMono, fontSize: "12px", color: THEME.textMuted }}>
                    {time}
                </span>
                <span
                    style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        padding: "2px 8px",
                        borderRadius: "6px",
                        background: badgeBg,
                        color: badgeColor,
                        border: `1px solid ${badgeBorder}`
                    }}
                >
                    {eventType}
                </span>
                <span style={{ fontSize: "13px", color: THEME.textSecondary }}>
                    {src} → {dst || "—"}
                </span>
            </div>
            {content && (
                <div
                    style={{
                        background: "rgba(0,0,0,0.3)",
                        borderRadius: "8px",
                        padding: "8px 12px",
                        fontSize: "12px",
                        color: THEME.textSecondary,
                        fontFamily: THEME.fontMono,
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-all"
                    }}
                >
                    {content}
                </div>
            )}
        </div>
    );
}
