"use client";

import React, { useState } from "react";
import Link from "next/link";
import { type Exam } from "@/lib/exams";
import { THEME } from "@/constants/theme";
import Card from "@/components/ui/Card";

interface ExamCardProps {
    exam: Exam;
    onEndAndRemove: (id: string) => void;
}

export default function ExamCard({ exam, onEndAndRemove }: ExamCardProps): React.JSX.Element {
    const [isHovered, setIsHovered] = useState(false);
    const [isToggling, setIsToggling] = useState(false);

    const formatDate = (dateString: string): string => {
        return new Date(dateString).toLocaleString("en-US", {
            timeZone: "Asia/Karachi",
            dateStyle: "medium",
            timeStyle: "short",
        });
    };

    const handleEndRemove = async () => {
        setIsToggling(true);
        await onEndAndRemove(exam.id);
        setIsToggling(false);
    };

    const isStopped = exam.force_stop;
    const badgeColor = isStopped ? THEME.pink : THEME.cyan;

    const secondaryButtonStyle: React.CSSProperties = {
        background: "transparent",
        border: `1px solid ${THEME.cardBorder}`,
        color: THEME.textPrimary,
        padding: "9px 14px",
        borderRadius: "8px",
        fontSize: "13px",
        fontWeight: 600,
        textDecoration: "none",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
    };

    return (
        <div
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            style={{
                transform: isHovered ? "translateY(-2px)" : "none",
                transition: "transform 0.2s ease",
                height: "100%",
            }}
        >
            <Card
                style={{
                    padding: "22px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "18px",
                    height: "100%",
                    borderColor: isHovered ? "rgba(255,255,255,0.12)" : THEME.cardBorder,
                    transition: "border-color 0.2s ease",
                }}
            >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px" }}>
                    <div>
                        <div style={{ color: THEME.textMuted, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" }}>
                            {exam.class_number}
                        </div>
                        <div style={{ color: THEME.textPrimary, fontSize: "20px", fontWeight: 600, letterSpacing: "-0.01em", lineHeight: 1.25 }}>
                            {exam.exam_name}
                        </div>
                    </div>

                    <span
                        style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            padding: "4px 10px",
                            borderRadius: "999px",
                            color: badgeColor,
                            backgroundColor: `${badgeColor}12`,
                            border: `1px solid ${badgeColor}30`,
                            whiteSpace: "nowrap",
                        }}
                    >
                        {isStopped ? "ENDED" : "RUNNING"}
                    </span>
                </div>

                <div
                    style={{
                        height: "1px",
                        background: "rgba(255,255,255,0.06)",
                    }}
                />

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                    <div>
                        <div style={{ color: THEME.textMuted, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "4px" }}>Start Time</div>
                        <div style={{ color: THEME.textPrimary, fontFamily: THEME.fontMono, fontSize: "13px", lineHeight: 1.5 }}>{formatDate(exam.start_time)}</div>
                    </div>
                    <div>
                        <div style={{ color: THEME.textMuted, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "4px" }}>End Time</div>
                        <div style={{ color: THEME.textPrimary, fontFamily: THEME.fontMono, fontSize: "13px", lineHeight: 1.5 }}>{formatDate(exam.end_time)}</div>
                    </div>
                    <div>
                        <div style={{ color: THEME.textMuted, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "4px" }}>Access Code</div>
                        <div style={{ color: THEME.yellow, fontFamily: THEME.fontMono, fontSize: "13px", fontWeight: 500 }}>{exam.access_code}</div>
                    </div>
                    <div>
                        <div style={{ color: THEME.textMuted, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "4px" }}>Created</div>
                        <div style={{ color: THEME.textSecondary, fontFamily: THEME.fontMono, fontSize: "12px", lineHeight: 1.5 }}>{formatDate(exam.created_at)}</div>
                    </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap", marginTop: "auto" }}>
                    <button
                        onClick={handleEndRemove}
                        disabled={isToggling || isStopped}
                        style={{
                            ...secondaryButtonStyle,
                            border: `1px solid ${isStopped ? THEME.cardBorder : THEME.pink}`,
                            color: isStopped ? THEME.textMuted : THEME.pink,
                            cursor: isToggling ? "wait" : "pointer",
                            opacity: isToggling ? 0.5 : 1,
                        }}
                    >
                        {isStopped ? "Ended" : "End & Remove All"}
                    </button>

                    <Link
                        href={`/sessions?exam_id=${exam.id}`}
                        style={{
                            ...secondaryButtonStyle,
                            color: THEME.cyan,
                        }}
                    >
                        View Sessions
                    </Link>
                </div>
            </Card>
        </div>
    );
}
