"use client";

import React, { useState } from "react";
import Link from "next/link";
import { type Exam } from "@/lib/exams";
import { THEME } from "@/constants/theme";
import Card from "@/components/ui/Card";

interface ExamCardProps {
    exam: Exam;
    onForceStopToggle: (id: string, current: boolean) => void;
}

export default function ExamCard({ exam, onForceStopToggle }: ExamCardProps): React.JSX.Element {
    const [isHovered, setIsHovered] = useState(false);
    const [isToggling, setIsToggling] = useState(false);

    const formatDate = (dateString: string): string => {
        return new Date(dateString).toLocaleString("en-US", {
            timeZone: "Asia/Karachi",
            dateStyle: "medium",
            timeStyle: "short",
        });
    };

    const handleToggle = async () => {
        setIsToggling(true);
        // Since the parent handles the optimistic UI wrapper, we just call the prop and wait for it to resolve
        await onForceStopToggle(exam.id, exam.force_stop);
        setIsToggling(false);
    };

    const accentColor = exam.force_stop ? THEME.pink : THEME.cyan;
    const isStopped = exam.force_stop;

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
                    padding: "24px",
                    display: "flex",
                    flexDirection: "column",
                    height: "100%",
                    position: "relative",
                    borderLeft: "none",
                }}
            >
                {/* 1. Accent Bar */}
                <div
                    style={{
                        position: "absolute",
                        left: 0,
                        top: 0,
                        bottom: 0,
                        width: "3px",
                        borderRadius: "4px 0 0 4px",
                        background: accentColor,
                        boxShadow: `0 0 12px ${accentColor}60`,
                    }}
                />

                {/* 2. Header block */}
                <div style={{ paddingLeft: "16px" }}>
                    <div style={{ color: THEME.textMuted, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" }}>
                        {exam.class_number}
                    </div>
                    <div style={{ color: "#f1f5f9", fontSize: "20px", fontWeight: 700, letterSpacing: "-0.01em" }}>
                        {exam.exam_name}
                    </div>
                </div>

                {/* 3. Neon divider line */}
                <div
                    style={{
                        height: "1px",
                        background: `linear-gradient(90deg, transparent, ${THEME.cyan}26, transparent)`, // ~0.15 opacity hex
                        margin: "16px 0",
                    }}
                />

                {/* 4. Info grid */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", paddingLeft: "16px" }}>
                    <div>
                        <div style={{ color: THEME.textMuted, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "4px" }}>Start Time</div>
                        <div style={{ color: THEME.cyan, fontFamily: THEME.fontMono, fontSize: "14px", fontWeight: 500 }}>{formatDate(exam.start_time)}</div>
                    </div>
                    <div>
                        <div style={{ color: THEME.textMuted, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "4px" }}>End Time</div>
                        <div style={{ color: THEME.cyan, fontFamily: THEME.fontMono, fontSize: "14px", fontWeight: 500 }}>{formatDate(exam.end_time)}</div>
                    </div>
                    <div>
                        <div style={{ color: THEME.textMuted, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "4px" }}>Access Code</div>
                        <div style={{ color: THEME.yellow, fontFamily: THEME.fontMono, fontSize: "14px", fontWeight: 500 }}>{exam.access_code}</div>
                    </div>
                    <div>
                        <div style={{ color: THEME.textMuted, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "4px" }}>Created</div>
                        <div style={{ color: THEME.textSecondary, fontFamily: THEME.fontMono, fontSize: "12px", fontWeight: 500 }}>{formatDate(exam.created_at)}</div>
                    </div>
                </div>

                {/* 5. Footer row */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "20px", paddingLeft: "16px" }}>

                    {/* Left side: Badges & Toggle */}
                    <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                        {/* Status Badge inline implementation (to bypass StatusBadge component constraints) */}
                        <span
                            style={{
                                fontSize: "11px",
                                fontWeight: 700,
                                padding: "2px 8px",
                                borderRadius: "6px",
                                color: isStopped ? THEME.pink : THEME.textSecondary,
                                backgroundColor: isStopped ? `${THEME.pink}15` : "rgba(255,255,255,0.04)",
                                border: isStopped ? `1px solid ${THEME.pink}30` : "1px solid rgba(255,255,255,0.08)",
                                display: "inline-flex",
                                alignItems: "center",
                                justifyContent: "center"
                            }}
                        >
                            {isStopped ? "FORCE STOP" : "RUNNING"}
                        </span>

                        {/* Toggle Button */}
                        <button
                            onClick={handleToggle}
                            disabled={isToggling}
                            style={{
                                background: "transparent",
                                border: `1px solid ${isStopped ? THEME.cyan : THEME.pink}`,
                                color: isStopped ? THEME.cyan : THEME.pink,
                                padding: "5px 14px",
                                borderRadius: "6px",
                                fontSize: "12px",
                                fontWeight: 600,
                                cursor: isToggling ? "wait" : "pointer",
                                opacity: isToggling ? 0.5 : 1,
                                transition: "background 0.2s ease"
                            }}
                            onMouseEnter={(e) => {
                                if (!isToggling) {
                                    e.currentTarget.style.background = isStopped ? `${THEME.cyan}15` : `${THEME.pink}15`;
                                }
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.background = "transparent";
                            }}
                        >
                            {isStopped ? "Resume" : "Force Stop"}
                        </button>
                    </div>

                    {/* Right side: View Link */}
                    <Link
                        href={`/sessions?exam_id=${exam.id}`}
                        style={{
                            color: THEME.cyan,
                            fontFamily: THEME.fontMono,
                            fontSize: "12px",
                            textDecoration: "none",
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                            transition: "opacity 0.2s ease"
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.8")}
                        onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
                    >
                        View Sessions &rarr;
                    </Link>
                </div>
            </Card>
        </div>
    );
}
