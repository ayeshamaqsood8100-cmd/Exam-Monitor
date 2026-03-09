"use client";

import React, { useState } from "react";
import { THEME } from "@/constants/theme";

interface AnalyzeButtonProps {
    examId: string;
    analyzeAction: (examId: string) => Promise<{
        sessions_total?: number;
        sessions_analyzed: number;
        sessions_failed?: number;
        failed_session_ids?: string[];
        flags_inserted: number;
    }>;
}

export default function AnalyzeButton({ examId, analyzeAction }: AnalyzeButtonProps): React.JSX.Element {
    const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
    const [result, setResult] = useState<string>("");

    const handleAnalyze = async () => {
        setStatus("loading");
        try {
            const res = await analyzeAction(examId);
            const failureSuffix = res.sessions_failed && res.sessions_failed > 0
                ? ` (${res.sessions_failed} failed)`
                : "";
            setResult(`${res.flags_inserted} flags found across ${res.sessions_analyzed} sessions${failureSuffix}`);
            setStatus("done");
        } catch (error) {
            console.error("Analysis failed:", error);
            setStatus("error");
        }
    };

    if (status === "done") {
        return (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
                <span style={{ color: THEME.cyan, fontWeight: "bold" }}>Analysis Complete ✓</span>
                <span style={{ color: THEME.textSecondary, fontSize: "12px", marginTop: "4px" }}>
                    {result}
                </span>
            </div>
        );
    }

    const isError = status === "error";
    const isLoading = status === "loading";

    return (
        <button
            onClick={handleAnalyze}
            disabled={isLoading}
            style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                background: THEME.bg,
                border: `1px solid ${isError ? THEME.pink : THEME.cyan}`,
                color: isError ? THEME.pink : THEME.cyan,
                padding: "8px 16px",
                borderRadius: "8px",
                fontWeight: 600,
                cursor: isLoading ? "not-allowed" : "pointer",
                opacity: isLoading ? 0.7 : 1,
                transition: "all 0.2s ease"
            }}
        >
            {isLoading && (
                <div style={{
                    width: "14px",
                    height: "14px",
                    border: `2px solid ${THEME.cyan}`,
                    borderTopColor: "transparent",
                    borderRadius: "50%",
                    animation: "spin 1s linear infinite"
                }}>
                    <style>{`
                        @keyframes spin {
                            to { transform: rotate(360deg); }
                        }
                    `}</style>
                </div>
            )}
            {isLoading ? "Analyzing..." : isError ? "Analysis Failed — Retry" : "Analyze Sessions"}
        </button>
    );
}
