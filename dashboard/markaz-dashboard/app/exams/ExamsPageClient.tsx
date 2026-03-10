"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { type Exam } from "@/lib/exams";
import { THEME } from "@/constants/theme";
import ExamCard from "@/components/exams/ExamCard";
import CreateExamModal from "@/components/exams/CreateExamModal";
import Card from "@/components/ui/Card";
import { toggleForceStopAction, createExamAction } from "@/app/exams/actions";

interface ExamsPageClientProps {
    exams: Exam[];
}

export default function ExamsPageClient({ exams: initialExams }: ExamsPageClientProps): React.JSX.Element {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const router = useRouter();

    // Optimistic UI state locally to avoid needing immediate full page reload wait on toggle
    const [exams, setExams] = useState<Exam[]>(initialExams);

    const handleForceStopToggle = async (id: string, current: boolean) => {
        // Optimistic cache update
        setExams((prev) =>
            prev.map((exam) =>
                exam.id === id ? { ...exam, force_stop: !current } : exam
            )
        );

        const result = await toggleForceStopAction(id, current);

        // Revert state strictly on error
        if (result.error) {
            alert(`Error toggling force stop: ${result.error}`);
            setExams((prev) =>
                prev.map((exam) =>
                    exam.id === id ? { ...exam, force_stop: current } : exam
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
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "32px" }}>
                <h1 style={{ color: THEME.textPrimary, fontSize: "26px", fontWeight: "bold", margin: 0 }}>
                    Exams
                </h1>
                <button
                    onClick={() => setIsModalOpen(true)}
                    style={{
                        background: THEME.cyan,
                        color: THEME.bg,
                        border: "none",
                        borderRadius: "8px",
                        padding: "10px 20px",
                        fontWeight: "bold",
                        cursor: "pointer",
                    }}
                >
                    New Exam +
                </button>
            </div>

            {exams.length === 0 ? (
                <Card style={{ padding: "48px", textAlign: "center", color: THEME.textMuted }}>
                    No exams yet. Create your first exam to get started.
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {exams.map((exam) => (
                        <ExamCard
                            key={exam.id}
                            exam={exam}
                            onForceStopToggle={handleForceStopToggle}
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
