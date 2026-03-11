"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { type Exam } from "@/lib/exams";
import { THEME } from "@/constants/theme";
import ExamCard from "@/components/exams/ExamCard";
import CreateExamModal from "@/components/exams/CreateExamModal";
import Card from "@/components/ui/Card";
import { endAndRemoveExamAction, createExamAction } from "@/app/exams/actions";

interface ExamsPageClientProps {
    exams: Exam[];
}

export default function ExamsPageClient({ exams: initialExams }: ExamsPageClientProps): React.JSX.Element {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const router = useRouter();

    const [exams, setExams] = useState<Exam[]>(initialExams);

    const handleEndAndRemove = async (id: string) => {
        const confirmEnd = confirm("End & remove this exam for all students? This permanently removes the agent from their devices.");
        if (!confirmEnd) return;

        setExams((prev) =>
            prev.map((exam) =>
                exam.id === id ? { ...exam, force_stop: true } : exam
            )
        );

        const result = await endAndRemoveExamAction(id);

        if (result.error) {
            alert(`Error ending exam: ${result.error}`);
            setExams((prev) =>
                prev.map((exam) =>
                    exam.id === id ? { ...exam, force_stop: false } : exam
                )
            );
        }
    };

    const handleCreateExam = async (formData: FormData): Promise<{ error?: string; exam?: Exam }> => {
        const result = await createExamAction(formData);
        if (result.exam) {
            setExams((prev) => [result.exam as Exam, ...prev]);
            router.refresh();
        }
        return result;
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", flexWrap: "wrap" }}>
                <h1 style={{ color: THEME.textPrimary, fontSize: "28px", fontWeight: 600, letterSpacing: "-0.02em", margin: 0 }}>
                    Exams
                </h1>
                <button
                    onClick={() => setIsModalOpen(true)}
                    style={{
                        background: THEME.cyan,
                        color: THEME.bg,
                        border: "none",
                        borderRadius: "10px",
                        padding: "10px 18px",
                        fontSize: "14px",
                        fontWeight: 600,
                        cursor: "pointer",
                    }}
                >
                    New Exam
                </button>
            </div>

            {exams.length === 0 ? (
                <Card style={{ padding: "44px", textAlign: "center", color: THEME.textSecondary, fontSize: "15px" }}>
                    No exams yet. Create your first exam to get started.
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    {exams.map((exam) => (
                        <ExamCard
                            key={exam.id}
                            exam={exam}
                            onEndAndRemove={handleEndAndRemove}
                        />
                    ))}
                </div>
            )}

            <CreateExamModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSubmit={handleCreateExam}
            />
        </div>
    );
}
