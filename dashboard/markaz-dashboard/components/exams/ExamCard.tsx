"use client";

import React, { useState } from "react";
import Link from "next/link";
import { type Exam } from "@/lib/exams";

interface ExamCardProps {
    exam: Exam;
    onEndAndRemove: (id: string) => void;
}

export default function ExamCard({ exam, onEndAndRemove }: ExamCardProps): React.JSX.Element {
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

    return (
        <div className="aesthetic-card p-7 gap-6">
            {/* Header Section */}
            <div className="flex justify-between items-start">
                <div className="flex flex-col gap-1">
                    <span className="text-[12px] font-medium text-[var(--text-secondary)] uppercase tracking-[0.05em]">
                        {exam.class_number}
                    </span>
                    <h2 className="text-[20px] font-semibold text-[var(--text-primary)] leading-[1.3] tracking-[-0.01em]">
                        {exam.exam_name}
                    </h2>
                </div>
                
                {/* Status Badge */}
                <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-[12px] font-semibold tracking-[0.02em] ${isStopped ? 'bg-[var(--accent-pink)]/5 border-[var(--accent-pink)]/20 text-[var(--text-primary)]' : 'bg-white/5 border-[var(--border)] text-[var(--text-primary)]'}`}>
                    <div className={`w-2 h-2 rounded-full ${isStopped ? 'bg-[var(--accent-pink)]' : 'bg-[var(--accent-cyan)] shadow-[0_0_10px_var(--accent-cyan)]'}`}></div>
                    {isStopped ? "Ended" : "Live"}
                </div>
            </div>

            {/* Data Grid Section */}
            <div className="grid grid-cols-2 gap-5 pt-5 border-t border-[var(--border)]">
                <div className="flex flex-col gap-1.5">
                    <span className="text-[12px] font-medium text-[var(--text-muted)] uppercase tracking-[0.05em]">Start Time</span>
                    <span className="text-[15px] font-medium text-[var(--text-primary)] font-mono">{formatDate(exam.start_time)}</span>
                </div>
                
                <div className="flex flex-col gap-1.5">
                    <span className="text-[12px] font-medium text-[var(--text-muted)] uppercase tracking-[0.05em]">End Time</span>
                    <span className="text-[15px] font-medium text-[var(--text-primary)] font-mono">{formatDate(exam.end_time)}</span>
                </div>

                <div className="flex flex-col gap-1.5 col-span-2 sm:col-span-1">
                    <span className="text-[12px] font-medium text-[var(--text-muted)] uppercase tracking-[0.05em]">Keys</span>
                    <span className="text-[15px] font-medium text-[var(--accent-cyan)] font-mono drop-shadow-[0_0_12px_rgba(6,182,212,0.3)]">{exam.access_code}</span>
                </div>

                <div className="flex flex-col gap-1.5 col-span-2 sm:col-span-1">
                    <span className="text-[12px] font-medium text-[var(--text-muted)] uppercase tracking-[0.05em]">Created</span>
                    <span className="text-[14px] font-medium text-[var(--text-secondary)] font-mono">{formatDate(exam.created_at)}</span>
                </div>
            </div>

            {/* Actions Section */}
            <div className="flex justify-between items-center mt-auto pt-6">
                <button
                    onClick={handleEndRemove}
                    disabled={isToggling || isStopped}
                    className={`bg-transparent border-none font-sans text-[14px] font-medium transition-colors duration-200 ${isStopped ? 'text-[var(--text-muted)] cursor-not-allowed' : 'text-[var(--text-muted)] hover:text-[var(--accent-pink)] cursor-pointer'}`}
                >
                    {isStopped ? "Already Ended" : "End Deployment"}
                </button>

                <Link
                    href={`/sessions?exam_id=${exam.id}`}
                    className="flex items-center gap-1.5 bg-transparent border-none font-sans text-[14px] font-medium cursor-pointer text-[var(--text-primary)] hover:text-[var(--accent-purple)] transition-colors duration-200"
                >
                    Enter Stream →
                </Link>
            </div>
        </div>
    );
}
