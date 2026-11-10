import type { Metadata } from "next";

import { LibraryHistoryExperience } from "@/components/history/library-history-experience";

export const metadata: Metadata = {
  title: "知识发展史 · 跨教材概念脉络",
  description:
    "从管理员预置的知识库中读取时间线，把不同教材的概念提出、研究转向与当代延伸放进同一条知识发展脉络。",
};

export default function HistoryPage() {
  return <LibraryHistoryExperience />;
}
