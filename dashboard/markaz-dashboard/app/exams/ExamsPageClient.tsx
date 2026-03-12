"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { type Exam } from "@/lib/exams";
import ExamCard from "@/components/exams/ExamCard";
import CreateExamModal from "@/components/exams/CreateExamModal";
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
        <div className="flex flex-col gap-10">
            <div className="flex justify-between items-center mb-2">
                <h1 className="text-[28px] font-semibold tracking-[-0.03em] text-[var(--text-primary)]">
                    Active Configurations
                </h1>
                <button
                    onClick={() => setIsModalOpen(true)}
                    className="flex items-center gap-2 bg-[var(--text-primary)] text-[var(--bg)] border-none px-5 py-2.5 rounded-lg text-sm font-semibold cursor-pointer transition-all duration-200 hover:-translate-y-px hover:shadow-[0_4px_12px_rgba(255,255,255,0.1)]"
                >
                    Deploy Exam
                </button>
            </div>

            {exams.length === 0 ? (
                <div className="aesthetic-card p-11 text-center text-[15px] text-[var(--text-secondary)]">
                    No active configurations found. Deploy an exam to begin monitoring.
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
