"use client";

import Link from "next/link";
import {
  ArrowLeft,
  BookOpenCheck,
  CircleAlert,
  Rocket,
  Sparkles,
} from "lucide-react";

import { LearningLoop } from "@/components/learning-loop";
import { DaJuiceLogo } from "@/components/y2k/dajuice-logo";
import { Y2KBackground } from "@/components/y2k/y2k-background";

interface PracticeExperienceProps {
  termId: string;
  termName: string;
  bookId: string;
}

export function PracticeExperience({
  termId,
  termName,
  bookId,
}: PracticeExperienceProps) {
  if (bookId === "agenda-setting") {
    return (
      <div className="relative">
        <LearningLoop
          termName={termName}
          termId={termId}
          bookId={bookId}
          compact
        />
        {termName !== "议程设置" ? (
          <div className="pointer-events-none fixed inset-x-0 bottom-3 z-30 flex justify-center px-4">
            <p className="rounded-full border border-amber-300/20 bg-[#120c18]/90 px-3 py-1.5 text-center text-[10px] leading-5 text-amber-100/70 shadow-[0_0_24px_rgba(0,0,0,0.45)] backdrop-blur-xl">
              本轮诊断规则基于议程设置核心知识卡；术语卡片用于定位练习主题。
            </p>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="y2k-page relative min-h-dvh overflow-x-hidden px-4 py-6 text-slate-100 sm:px-8">
      <Y2KBackground />
      <header className="relative z-20 mx-auto flex w-full max-w-6xl items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link href={`/subject/${encodeURIComponent(bookId)}`} className="y2k-back-link">
            <ArrowLeft className="size-4" aria-hidden="true" />
            <span>返回概念墙</span>
          </Link>
          <span className="hidden h-5 w-px bg-white/10 sm:block" aria-hidden="true" />
          <DaJuiceLogo compact className="hidden sm:inline-flex" />
        </div>
        <span className="font-terminal text-sm tracking-[0.2em] text-fuchsia-200/65">
          FOCUS PRACTICE
        </span>
      </header>

      <main className="relative z-10 mx-auto flex min-h-[calc(100dvh-7rem)] w-full max-w-3xl items-center py-10">
        <section className="y2k-panel w-full rounded-[2rem] p-6 sm:p-9">
          <div className="flex size-14 items-center justify-center rounded-2xl border-2 border-fuchsia-300/30 bg-fuchsia-400/10 text-fuchsia-200 shadow-[0_0_34px_rgba(255,46,166,0.14)]">
            <Rocket className="size-6" aria-hidden="true" />
          </div>
          <p className="y2k-kicker mt-6">
            <Sparkles className="size-3" aria-hidden="true" />
            CAPABILITY BOUNDARY
          </p>
          <h1 className="mt-4 text-3xl font-black leading-tight tracking-tight text-white sm:text-5xl">
            「{termName}」暂未接入逐点诊断。
          </h1>
          <p className="mt-5 text-sm leading-7 text-slate-300">
            当前后端的诊断与反馈引擎固定覆盖议程设置概念，不能把其他科目的术语硬塞进同一套判分规则。这一页只保留清晰的能力边界，
            不伪造判定结果。
          </p>
          <div className="mt-6 flex items-start gap-3 rounded-2xl border border-amber-300/20 bg-amber-300/[0.055] p-4 text-xs leading-6 text-amber-100/80">
            <CircleAlert className="mt-0.5 size-4 shrink-0 text-amber-300" aria-hidden="true" />
            <p>
              你可以继续阅读「{termName}」的定义、边界与脉络，或使用精准考核模块练习该科目的知识库题目。
            </p>
          </div>
          <div className="mt-7 flex flex-col gap-3 sm:flex-row">
            <Link href={`/subject/${encodeURIComponent(bookId)}`} className="y2k-primary inline-flex h-11 items-center justify-center gap-2 rounded-xl px-5 text-sm font-bold">
              <ArrowLeft className="size-4" aria-hidden="true" />
              返回概念卡片
            </Link>
            <Link href="/library" className="y2k-secondary inline-flex h-11 items-center justify-center gap-2 rounded-xl px-5 text-sm font-bold">
              <BookOpenCheck className="size-4" aria-hidden="true" />
              打开精准考核
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
