"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  ArrowUpRight,
  BookOpen,
  BrainCircuit,
  LibraryBig,
  Loader2,
  RefreshCw,
  Sparkles,
  Target,
  type LucideIcon,
} from "lucide-react";

import { DaJuiceLogo } from "@/components/y2k/dajuice-logo";
import { Y2KBackground } from "@/components/y2k/y2k-background";
import { Button } from "@/components/ui/button";
import { getBooks, type LibraryBook } from "@/lib/library-api";
import { cn } from "@/lib/utils";

const SUBJECT_META: Record<
  string,
  { icon: LucideIcon; code: string; accent: string; glow: string }
> = {
  "agenda-setting": {
    icon: BrainCircuit,
    code: "SIGNAL / 01",
    accent: "from-fuchsia-400 to-pink-500",
    glow: "shadow-[0_0_40px_rgba(255,46,166,0.2)]",
  },
  marketing: {
    icon: Target,
    code: "VALUE / 02",
    accent: "from-cyan-300 to-blue-500",
    glow: "shadow-[0_0_40px_rgba(61,231,255,0.18)]",
  },
  "consumer-psychology": {
    icon: Sparkles,
    code: "MIND / 03",
    accent: "from-lime-300 to-emerald-500",
    glow: "shadow-[0_0_40px_rgba(163,230,53,0.15)]",
  },
};

function SubjectCard({ book, index }: { book: LibraryBook; index: number }) {
  const meta = SUBJECT_META[book.book_id] ?? {
    icon: BookOpen,
    code: `FILE / 0${index + 1}`,
    accent: "from-violet-400 to-cyan-400",
    glow: "shadow-[0_0_40px_rgba(167,139,250,0.18)]",
  };
  const Icon = meta.icon;

  return (
    <motion.article
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.08 * index, duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      className={cn(
        "y2k-subject-card group relative min-h-[320px] overflow-hidden rounded-[1.6rem] border-2 border-white/20 bg-[#15101e]/85 p-5 backdrop-blur-xl sm:p-6",
        meta.glow,
      )}
    >
      <Link
        href={`/subject/${book.book_id}`}
        className="absolute inset-0 z-20"
        aria-label={`进入 ${book.title}`}
      />
      <div className="y2k-card-grid absolute inset-0 opacity-35" aria-hidden="true" />
      <div className="absolute -right-14 -top-12 size-44 rounded-full border border-white/10 bg-white/[0.025]" aria-hidden="true" />
      <div className="absolute bottom-5 right-5 font-terminal text-6xl leading-none text-white/[0.045]" aria-hidden="true">
        0{index + 1}
      </div>

      <div className="relative z-10 flex h-full flex-col">
        <div className="flex items-start justify-between gap-4">
          <div className={cn("flex size-12 items-center justify-center rounded-xl border-2 border-black/45 bg-gradient-to-br text-black shadow-[4px_4px_0_rgba(0,0,0,0.65)]", meta.accent)}>
            <Icon className="size-5" strokeWidth={2.4} aria-hidden="true" />
          </div>
          <span className="rounded-full border border-cyan-200/25 bg-cyan-300/10 px-2.5 py-1 font-pixel text-[7px] tracking-[0.12em] text-cyan-100">
            {meta.code}
          </span>
        </div>

        <div className="mt-8">
          <p className="font-terminal text-sm tracking-[0.28em] text-fuchsia-300/80 uppercase">
            {book.subject}
          </p>
          <h2 className="mt-2 max-w-[16rem] text-2xl font-black leading-[1.2] tracking-tight text-white sm:text-[1.7rem]">
            {book.title}
          </h2>
        </div>

        <div className="mt-auto pt-8">
          <div className="flex items-center gap-2 text-[11px] text-slate-400">
            <span className="rounded-md border border-white/10 bg-black/25 px-2 py-1">
              {book.chapter_count} CHAPTERS
            </span>
            <span className="rounded-md border border-white/10 bg-black/25 px-2 py-1">
              {book.term_count} TERMS
            </span>
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-4">
            <span className="font-pixel text-[8px] tracking-[0.16em] text-white/55 transition group-hover:text-fuchsia-200">
              OPEN FILE
            </span>
            <ArrowUpRight className="size-5 text-cyan-300 transition-transform duration-300 group-hover:-translate-y-1 group-hover:translate-x-1" aria-hidden="true" />
          </div>
        </div>
      </div>
    </motion.article>
  );
}

export function SubjectPicker() {
  const [books, setBooks] = useState<LibraryBook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function loadBooks() {
      try {
        const items = await getBooks();
        if (!cancelled) {
          setBooks(items);
          setError(null);
        }
      } catch (reason) {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "科目加载失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadBooks();
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return (
    <div className="y2k-page relative min-h-dvh overflow-x-hidden text-foreground">
      <Y2KBackground />

      <header className="relative z-20 border-b border-white/10 bg-[#0a0711]/55 backdrop-blur-2xl">
        <div className="mx-auto flex min-h-20 w-full max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-8">
          <DaJuiceLogo />
          <nav className="flex items-center gap-1.5 text-[11px] sm:gap-2">
            <Link href="/library" className="y2k-nav-link">
              <LibraryBig className="size-3.5" aria-hidden="true" />
              <span>精准考核</span>
            </Link>
            <Link href="/mistakes" className="y2k-nav-link hidden sm:flex">
              错题本
            </Link>
            <Link href="/history" className="y2k-nav-link">
              <Sparkles className="size-3.5" aria-hidden="true" />
              <span>发展史</span>
            </Link>
          </nav>
        </div>
      </header>

      <main className="relative z-10 mx-auto w-full max-w-7xl px-4 pb-16 pt-12 sm:px-8 sm:pt-20">
        <section className="max-w-3xl">
          <div className="y2k-kicker">
            <span className="size-2 animate-pulse rounded-full bg-fuchsia-400 shadow-[0_0_10px_#ff2ea6]" />
            SUBJECT SELECTOR / 科目选择
          </div>
          <h1 className="mt-5 text-4xl font-black leading-[1.08] tracking-tight text-white sm:text-6xl">
            选一个科目，
            <span className="chrome-text mt-2 block pb-2">开始拆解概念。</span>
          </h1>
          <p className="mt-5 max-w-xl text-sm leading-7 text-slate-400 sm:text-base">
            从知识库打开概念卡片，先看清边界与脉络，再进入逐点诊断。
          </p>
        </section>

        <section className="mt-10 sm:mt-14" aria-label="学习科目">
          {loading ? (
            <div className="grid gap-5 md:grid-cols-3">
              {[0, 1, 2].map((item) => (
                <div key={item} className="y2k-loading-card h-[320px] rounded-[1.6rem] border-2 border-white/10 bg-white/[0.03]" />
              ))}
            </div>
          ) : error ? (
            <div className="y2k-panel max-w-2xl rounded-2xl p-6">
              <p className="font-pixel text-[9px] tracking-[0.18em] text-amber-300">CONNECTION LOST</p>
              <p className="mt-3 text-sm leading-6 text-slate-300">{error}</p>
              <Button
                type="button"
                onClick={() => {
                  setLoading(true);
                  setError(null);
                  setRefreshKey((value) => value + 1);
                }}
                className="mt-5 gap-2 bg-fuchsia-400 text-black hover:bg-fuchsia-300"
              >
                <RefreshCw className="size-4" aria-hidden="true" />
                重新连接
              </Button>
            </div>
          ) : books.length === 0 ? (
            <div className="y2k-panel max-w-2xl rounded-2xl p-6">
              <p className="font-pixel text-[9px] tracking-[0.18em] text-cyan-200">NO SUBJECTS FOUND</p>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                当前知识库还没有可展示的科目，请先检查管理员预置内容。
              </p>
            </div>
          ) : (
            <div className="grid gap-5 md:grid-cols-3">
              {books.map((book, index) => (
                <SubjectCard key={book.book_id} book={book} index={index} />
              ))}
            </div>
          )}
        </section>

        <section className="mt-12 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-6 text-[11px] text-slate-500">
          <span className="font-terminal tracking-[0.2em] text-slate-400">
            {loading ? "SCANNING LIBRARY..." : `${books.length} SUBJECTS / LOCAL KNOWLEDGE BASE`}
          </span>
          <span className="inline-flex items-center gap-2">
            <Loader2 className={cn("size-3.5 text-fuchsia-300", loading && "animate-spin")} aria-hidden="true" />
            DaJuice learning terminal // v3.1
          </span>
        </section>
      </main>
    </div>
  );
}
