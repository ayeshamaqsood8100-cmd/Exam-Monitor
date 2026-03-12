"use client";

import React, { useState } from "react";

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
            <div className="flex flex-col items-end">
                <span className="text-[var(--accent-cyan)] font-bold">Analysis Complete ✓</span>
                <span className="text-[var(--text-secondary)] text-xs mt-1">
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
            className={`flex items-center gap-2 bg-[var(--surface-hover)] border px-4 py-2 rounded-lg font-semibold cursor-pointer transition-all duration-200 
                ${isError ? 'border-[var(--accent-pink)] text-[var(--accent-pink)] hover:bg-[var(--accent-pink)]/10' : 'border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-hover)]'} 
                ${isLoading ? 'opacity-70 cursor-not-allowed' : ''}`}
        >
            {isLoading && (
                <div className="w-3.5 h-3.5 border-2 border-[var(--text-secondary)] border-t-transparent rounded-full animate-spin" />
            )}
            {isLoading ? "Analyzing..." : isError ? "Analysis Failed — Retry" : "Analyze AI Flags"}
        </button>
    );
}
