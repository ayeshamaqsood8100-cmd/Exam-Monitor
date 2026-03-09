import React from "react";
import { getAllExams } from "@/lib/exams";
import ExamsPageClient from "@/app/exams/ExamsPageClient";

export const dynamic = "force-dynamic";

export default async function ExamsPage(): Promise<React.JSX.Element> {
    const exams = await getAllExams();

    return <ExamsPageClient exams={exams} />;
}
