"use client";

import React, { useState } from "react";
import { type Exam } from "@/lib/exams";

interface CreateExamModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (formData: FormData) => Promise<{ error?: string; exam?: Exam }>;
}

export default function CreateExamModal({ isOpen, onClose, onSubmit }: CreateExamModalProps): React.JSX.Element | null {
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setIsSubmitting(true);
        setErrorMsg(null);

        const formData = new FormData(e.currentTarget);
        const result = await onSubmit(formData);

        setIsSubmitting(false);

        if (result.error) {
            setErrorMsg(result.error);
        } else {
            onClose();
        }
    };

    return (
        <div
            className="fixed inset-0 bg-[#000000]/75 backdrop-blur-md z-[100] flex items-center justify-center p-5"
            onClick={onClose}
        >
            <div
                onClick={(e) => e.stopPropagation()}
                className="w-full max-w-[500px] z-[101]"
            >
                <div className="aesthetic-card p-7 gap-6">
                    <h2 className="text-[var(--text-primary)] font-semibold text-[21px] tracking-[-0.01em] m-0">
                        Deploy New Configuration
                    </h2>

                    {errorMsg && (
                        <div className="text-[var(--accent-pink)] text-sm bg-[var(--accent-pink)]/10 border border-[var(--accent-pink)]/30 p-3 rounded-lg">
                            {errorMsg}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="m-0">
                        <div className="mb-[18px]">
                            <label className="block text-[var(--text-secondary)] text-[13px] font-medium mb-2">Configuration Name</label>
                            <input name="exam_name" type="text" required className="w-full bg-[var(--surface-hover)] border border-[var(--border)] rounded-lg px-3.5 py-2.5 text-[var(--text-primary)] font-sans text-sm focus:outline-none focus:border-[var(--border-hover)] transition-colors" />
                        </div>

                        <div className="mb-[18px]">
                            <label className="block text-[var(--text-secondary)] text-[13px] font-medium mb-2">Target Audience / Class</label>
                            <input name="class_number" type="text" placeholder="e.g. BS-CS Section B" required className="w-full bg-[var(--surface-hover)] border border-[var(--border)] rounded-lg px-3.5 py-2.5 text-[var(--text-primary)] font-sans text-sm focus:outline-none focus:border-[var(--border-hover)] transition-colors" />
                        </div>

                        <div className="grid grid-cols-2 gap-4 mb-[18px]">
                            <div>
                                <label className="block text-[var(--text-secondary)] text-[13px] font-medium mb-2">Deploy Time</label>
                                <input name="start_time" type="datetime-local" required className="w-full bg-[var(--surface-hover)] border border-[var(--border)] rounded-lg px-3.5 py-2.5 text-[var(--text-primary)] font-sans text-sm focus:outline-none focus:border-[var(--border-hover)] transition-colors" />
                            </div>
                            <div>
                                <label className="block text-[var(--text-secondary)] text-[13px] font-medium mb-2">Termination Time</label>
                                <input name="end_time" type="datetime-local" required className="w-full bg-[var(--surface-hover)] border border-[var(--border)] rounded-lg px-3.5 py-2.5 text-[var(--text-primary)] font-sans text-sm focus:outline-none focus:border-[var(--border-hover)] transition-colors" />
                            </div>
                        </div>

                        <div className="mb-6">
                            <label className="block text-[var(--text-secondary)] text-[13px] font-medium mb-2">Terminal Access Code</label>
                            <input name="access_code" type="text" placeholder="e.g. SPRING25" required className="w-full bg-[var(--surface-hover)] border border-[var(--border)] rounded-lg px-3.5 py-2.5 text-[var(--text-primary)] font-sans text-sm focus:outline-none focus:border-[var(--border-hover)] transition-colors" />
                        </div>

                        <div className="flex justify-end gap-3 flex-wrap">
                            <button
                                type="button"
                                onClick={onClose}
                                disabled={isSubmitting}
                                className="min-w-[110px] bg-transparent border border-[var(--border)] text-[var(--text-secondary)] rounded-lg px-4 py-2.5 font-semibold transition-colors hover:text-[var(--text-primary)] hover:border-[var(--border-hover)] disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                disabled={isSubmitting}
                                className="min-w-[140px] bg-[var(--text-primary)] border-none text-[var(--bg)] rounded-lg px-4 py-2.5 font-semibold transition-all hover:-translate-y-px hover:shadow-[0_4px_12px_rgba(255,255,255,0.1)] disabled:opacity-70 disabled:cursor-not-allowed"
                            >
                                {isSubmitting ? "Deploying..." : "Deploy Config"}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}
