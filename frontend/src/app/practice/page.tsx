import type { Metadata } from "next";

import { PracticeExperience } from "@/components/practice/practice-experience";

export const metadata: Metadata = {
  title: "专注练习 · DaJuice",
  description: "围绕单个概念进行逐点诊断与重答的专注练习模式。",
};

function firstValue(value: string | string[] | undefined): string | null {
  if (Array.isArray(value)) return value[0] ?? null;
  return value ?? null;
}

interface PracticePageProps {
  searchParams: Promise<{
    term_id?: string | string[];
    term?: string | string[];
    book_id?: string | string[];
  }>;
}

export default async function PracticePage({ searchParams }: PracticePageProps) {
  const query = await searchParams;
  const bookId = firstValue(query.book_id) ?? "agenda-setting";
  const termId = firstValue(query.term_id) ?? "agenda-setting-first-level";
  const termName = firstValue(query.term) ?? "议程设置";

  return (
    <PracticeExperience
      bookId={bookId}
      termId={termId}
      termName={termName}
    />
  );
}
