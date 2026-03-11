"use client";

import React, { useState } from "react";
import { THEME } from "@/constants/theme";
import Card from "@/components/ui/Card";

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

    const inputStyle: React.CSSProperties = {
        width: "100%",
        background: "rgba(255,255,255,0.04)",
        border: `1px solid ${THEME.cardBorder}`,
        borderRadius: "10px",
        padding: "11px 14px",
        color: THEME.textPrimary,
        fontFamily: THEME.fontSans,
        fontSize: "14px",
        outline: "none",
        marginBottom: "18px",
    };

    const labelStyle: React.CSSProperties = {
        display: "block",
        color: THEME.textSecondary,
        fontSize: "13px",
        fontWeight: 500,
        marginBottom: "8px",
    };

    const secondaryButtonStyle: React.CSSProperties = {
        minWidth: "110px",
        background: "transparent",
        border: `1px solid ${THEME.cardBorder}`,
        color: THEME.textSecondary,
        borderRadius: "10px",
        padding: "11px 16px",
        fontWeight: 600,
        cursor: isSubmitting ? "not-allowed" : "pointer",
    };

    return (
        <div
            style={{
                position: "fixed",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: "rgba(0,0,0,0.72)",
                backdropFilter: "blur(4px)",
                zIndex: 100,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "20px",
            }}
            onClick={onClose}
        >
            <div
                onClick={(e) => e.stopPropagation()}
                style={{
                    width: "100%",
                    maxWidth: "500px",
                    zIndex: 101,
                }}
            >
                <Card style={{ padding: "28px", display: "flex", flexDirection: "column", gap: "22px" }}>
                    <h2 style={{ color: THEME.textPrimary, fontWeight: 600, fontSize: "21px", letterSpacing: "-0.01em", margin: 0 }}>
                        Create New Exam
                    </h2>

                    {errorMsg && (
                        <div style={{ color: THEME.pink, fontSize: "14px", background: `${THEME.pink}12`, border: `1px solid ${THEME.pink}30`, padding: "12px", borderRadius: "10px" }}>
                            {errorMsg}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} style={{ margin: 0 }}>
                        <div>
                            <label style={labelStyle}>Exam Name</label>
                            <input name="exam_name" type="text" required style={inputStyle} />
                        </div>

                        <div>
                            <label style={labelStyle}>Class Number</label>
                            <input name="class_number" type="text" placeholder="e.g. BS-CS Section B" required style={inputStyle} />
                        </div>

                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                            <div>
                                <label style={labelStyle}>Start Time</label>
                                <input name="start_time" type="datetime-local" required style={inputStyle} />
                            </div>
                            <div>
                                <label style={labelStyle}>End Time</label>
                                <input name="end_time" type="datetime-local" required style={inputStyle} />
                            </div>
                        </div>

                        <div>
                            <label style={labelStyle}>Access Code</label>
                            <input name="access_code" type="text" placeholder="e.g. SPRING25" required style={{ ...inputStyle, marginBottom: "24px" }} />
                        </div>

                        <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", flexWrap: "wrap" }}>
                            <button
                                type="button"
                                onClick={onClose}
                                disabled={isSubmitting}
                                style={secondaryButtonStyle}
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                disabled={isSubmitting}
                                style={{
                                    minWidth: "140px",
                                    background: THEME.cyan,
                                    border: "none",
                                    color: THEME.bg,
                                    borderRadius: "10px",
                                    padding: "11px 16px",
                                    fontWeight: 600,
                                    cursor: isSubmitting ? "wait" : "pointer",
                                    opacity: isSubmitting ? 0.7 : 1,
                                }}
                            >
                                {isSubmitting ? "Creating..." : "Create Exam"}
                            </button>
                        </div>
                    </form>
                </Card>
            </div>
        </div>
    );
}
