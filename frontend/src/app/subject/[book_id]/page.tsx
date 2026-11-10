import type { Metadata } from "next";

import { SubjectExperience } from "@/components/subject/subject-experience";

export const metadata: Metadata = {
  title: "科目概念墙 · DaJuice",
  description: "浏览科目下的概念卡片，查看定义、边界、学者与历史脉络。",
};

function firstValue(value: string | string[] | undefined): string | null {
  if (Array.isArray(value)) return value[0] ?? null;
  return value ?? null;
}

interface SubjectPageProps {
  params: Promise<{ book_id: string }>;
  searchParams: Promise<{ term?: string | string[] }>;
}

export default async function SubjectPage({
  params,
  searchParams,
}: SubjectPageProps) {
  const { book_id: bookId } = await params;
  const query = await searchParams;

  return (
    <SubjectExperience
      bookId={bookId}
      initialTermId={firstValue(query.term)}
    />
  );
}
