"use client";

import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowUpRight,
  BookOpen,
  CalendarRange,
  ChevronRight,
  CircleAlert,
  RefreshCw,
  Rocket,
  Sparkles,
  UserRound,
  X,
} from "lucide-react";

import { DaJuiceLogo } from "@/components/y2k/dajuice-logo";
import { Y2KBackground } from "@/components/y2k/y2k-background";
import { Button } from "@/components/ui/button";
import {
  getChapters,
  getSelection,
  getTimeline,
  type LibraryBook,
  type LibraryChapter,
  type ScopeTerm,
  type TimelineItem,
} from "@/lib/library-api";
import { cn } from "@/lib/utils";

interface ChapterWithTerms extends LibraryChapter {
  terms: ScopeTerm[];
}

interface SubjectExperienceProps {
  bookId: string;
  initialTermId?: string | null;
}

function ModalSection({
  label,
  children,
  tone = "cyan",
}: {
  label: string;
  children: ReactNode;
  tone?: "cyan" | "pink" | "amber";
}) {
  const tones = {
    cyan: "border-cyan-300/20 bg-cyan-300/[0.045]",
    pink: "border-fuchsia-300/20 bg-fuchsia-300/[0.045]",
    amber: "border-amber-300/20 bg-amber-300/[0.045]",
  };
  const labels = {
    cyan: "text-cyan-200/75",
    pink: "text-fuchsia-200/75",
    amber: "text-amber-200/80",
  };
  return (
    <section className={cn("rounded-2xl border p-4", tones[tone])}>
      <p className={cn("font-pixel text-[8px] tracking-[0.16em]", labels[tone])}>{label}</p>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function TermModal({
  term,
  timeline,
  bookId,
  onClose,
}: {
  term: ScopeTerm;
  timeline: TimelineItem[];
  bookId: string;
  onClose: () => void;
}) {
  const relatedTimeline = useMemo(() => {
    const matched = timeline.filter(
      (item) =>
        term.name.includes(item.title) ||
        item.title.includes(term.name) ||
        item.points.some((point) => term.name.includes(point)),
    );
    return matched.length > 0 ? matched : timeline;
  }, [term.name, timeline]);
  const scholars = Array.from(new Set(timeline.map((item) => item.scholars).filter(Boolean)));
  const isAgenda = bookId === "agenda-setting";
  const practiceHref = `/practice?term_id=${encodeURIComponent(term.term_id)}&book_id=${encodeURIComponent(bookId)}&term=${encodeURIComponent(term.name)}`;

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-end justify-center bg-[#05020a]/75 p-0 backdrop-blur-md sm:items-center sm:p-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    >
      <motion.div
        role="dialog"
        aria-modal="true"
        aria-labelledby="term-modal-title"
        initial={{ opacity: 0, y: 60, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 40, scale: 0.98 }}
        transition={{ type: "spring", stiffness: 330, damping: 32 }}
        onClick={(event) => event.stopPropagation()}
        className="y2k-modal study-scrollbar relative max-h-[92dvh] w-full max-w-4xl overflow-y-auto rounded-t-[2rem] border-2 border-white/20 bg-[#130d1c]/95 p-5 shadow-[0_0_0_1px_rgba(255,46,166,0.25),0_30px_100px_rgba(0,0,0,0.7)] sm:rounded-[2rem] sm:p-7"
      >
        <div className="pointer-events-none absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-fuchsia-300/80 to-transparent" aria-hidden="true" />
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 z-10 flex size-9 items-center justify-center rounded-full border border-white/15 bg-black/30 text-slate-300 transition hover:rotate-90 hover:border-fuchsia-300/40 hover:text-fuchsia-200"
          aria-label="关闭概念卡片"
        >
          <X className="size-4" aria-hidden="true" />
        </button>

        <div className="pr-10">
          <div className="flex flex-wrap items-center gap-2">
            <span className="y2k-chip border-fuchsia-300/25 bg-fuchsia-300/10 text-fuchsia-100">
              CONCEPT FILE
            </span>
            <span className="font-terminal text-sm tracking-[0.16em] text-slate-500">
              {term.chapter_title}
            </span>
          </div>
          <h2 id="term-modal-title" className="mt-4 text-3xl font-black tracking-tight text-white sm:text-5xl">
            {term.name}
          </h2>
          <p className="mt-3 text-sm leading-7 text-slate-300">{term.definition}</p>
        </div>

        <div className="mt-7 grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="space-y-4">
            <ModalSection label="KEY POINTS / 关键要点" tone="cyan">
              <ul className="space-y-3">
                {term.key_points.map((point, index) => (
                  <li key={`${term.term_id}-key-${index}`} className="flex gap-3 text-sm leading-6 text-slate-200">
                    <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-md border border-cyan-300/25 bg-cyan-300/10 font-pixel text-[7px] text-cyan-200">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </ModalSection>

            <ModalSection label="DON'T CONFUSE / 易混淆点" tone="amber">
              {term.common_confusions.length > 0 ? (
                <ul className="space-y-3">
                  {term.common_confusions.map((item, index) => (
                    <li key={`${term.term_id}-confusion-${index}`} className="flex gap-2.5 text-sm leading-6 text-amber-50/85">
                      <CircleAlert className="mt-1 size-4 shrink-0 text-amber-300" aria-hidden="true" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-400">知识卡未额外列出易混淆点。</p>
              )}
            </ModalSection>
          </div>

          <div className="space-y-4">
            <ModalSection label="SCHOLARS / 学科脉络人物" tone="pink">
              <div className="flex flex-wrap gap-2">
                {scholars.map((scholar) => (
                  <span key={scholar} className="inline-flex items-center gap-1.5 rounded-full border border-fuchsia-300/20 bg-black/20 px-3 py-1.5 text-xs text-fuchsia-50">
                    <UserRound className="size-3.5 text-fuchsia-300" aria-hidden="true" />
                    {scholar}
                  </span>
                ))}
              </div>
              <p className="mt-3 text-[11px] leading-5 text-slate-500">
                学者来自本科目的学科时间线，标注的是研究脉络，不把某位学者硬绑成这个术语的唯一提出者。
              </p>
            </ModalSection>

            <ModalSection label="TIMELINE / 历史脉络" tone="cyan">
              <div className="space-y-3">
                {relatedTimeline.map((item) => (
                  <article key={`${item.book_id}-${item.year}-${item.title}`} className="flex gap-3 rounded-xl border border-white/10 bg-black/15 p-3">
                    <div className="relative size-16 shrink-0 overflow-hidden rounded-lg border border-white/10 bg-white/5">
                      <Image src={item.image} alt={item.imageAlt} fill className="object-cover" sizes="64px" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-terminal text-lg leading-none text-cyan-200">{item.year}</span>
                        <span className="truncate text-xs font-semibold text-slate-200">{item.title}</span>
                      </div>
                      <p className="mt-1 line-clamp-2 text-[11px] leading-5 text-slate-400">{item.summary}</p>
                    </div>
                  </article>
                ))}
              </div>
            </ModalSection>
          </div>
        </div>

        <div className="mt-6 flex flex-col gap-3 border-t border-white/10 pt-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-[11px] leading-5 text-slate-500">
            {isAgenda
              ? "本术语已接入逐点诊断闭环。"
              : "当前诊断引擎固定为议程设置；本页保留概念阅读，练习入口会显示能力边界。"}
          </p>
          <Link
            href={practiceHref}
            className="y2k-primary inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-xl px-5 text-sm font-bold"
          >
            <Rocket className="size-4" aria-hidden="true" />
            🚀 进入专注练习
          </Link>
        </div>
      </motion.div>
    </motion.div>
  );
}

function TermCard({
  term,
  index,
  onOpen,
}: {
  term: ScopeTerm;
  index: number;
  onOpen: () => void;
}) {
  return (
    <motion.button
      type="button"
      onClick={onOpen}
      whileHover={{ y: -7, rotateX: 2.5, rotateY: -1.5 }}
      transition={{ type: "spring", stiffness: 300, damping: 24 }}
      style={{ transformPerspective: 900 }}
      className="y2k-term-card group relative flex min-h-[245px] w-full flex-col overflow-hidden rounded-2xl border-2 border-white/15 bg-[#171021]/80 p-4 text-left shadow-[7px_7px_0_rgba(0,0,0,0.38)] backdrop-blur-md sm:p-5"
    >
      <div className="y2k-card-grid pointer-events-none absolute inset-0 opacity-25" aria-hidden="true" />
      <div className="pointer-events-none absolute -right-10 -top-10 size-28 rounded-full border border-fuchsia-300/15 bg-fuchsia-400/5" aria-hidden="true" />
      <div className="relative z-10 flex items-center justify-between gap-3">
        <span className="font-pixel text-[7px] tracking-[0.18em] text-cyan-200/70">
          TERM / {String(index + 1).padStart(2, "0")}
        </span>
        <span className="flex size-7 items-center justify-center rounded-md border border-white/10 bg-black/25 text-slate-400 transition group-hover:border-fuchsia-300/30 group-hover:text-fuchsia-200">
          <ArrowUpRight className="size-3.5" aria-hidden="true" />
        </span>
      </div>
      <h3 className="relative z-10 mt-5 text-xl font-black leading-tight tracking-tight text-white sm:text-2xl">
        {term.name}
      </h3>
      <p className="relative z-10 mt-2 line-clamp-3 text-xs leading-6 text-slate-400">
        {term.definition}
      </p>
      <div className="relative z-10 mt-auto flex items-center gap-2 pt-5">
        <span className="rounded-md border border-cyan-300/15 bg-cyan-300/[0.06] px-2 py-1 text-[10px] text-cyan-100/75">
          {term.key_points.length} 要点
        </span>
        <span className="rounded-md border border-amber-300/15 bg-amber-300/[0.05] px-2 py-1 text-[10px] text-amber-100/70">
          {term.common_confusions.length} 易混
        </span>
        <span className="ml-auto font-terminal text-xs tracking-[0.16em] text-slate-600 transition group-hover:text-cyan-200">
          OPEN ↗
        </span>
      </div>
    </motion.button>
  );
}

export function SubjectExperience({ bookId, initialTermId }: SubjectExperienceProps) {
  const [book, setBook] = useState<LibraryBook | null>(null);
  const [terms, setTerms] = useState<ScopeTerm[]>([]);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [activeTermId, setActiveTermId] = useState<string | null>(
    initialTermId ?? null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [detail, timelineItems] = await Promise.all([
          getChapters(bookId),
          getTimeline([bookId]),
        ]);
        const chapterIds = detail.chapters.map((chapter) => chapter.chapter_id);
        const selection = chapterIds.length
          ? await getSelection([bookId], chapterIds)
          : null;
        if (cancelled) return;
        setBook(detail);
        setTimeline(timelineItems);
        setTerms(selection?.terms ?? []);
      } catch (reason) {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "科目内容加载失败");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [bookId, refreshKey]);

  const activeTerm = useMemo(
    () => terms.find((term) => term.term_id === activeTermId) ?? null,
    [activeTermId, terms],
  );

  useEffect(() => {
    if (!activeTerm) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setActiveTermId(null);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [activeTerm]);

  const groupedChapters = useMemo<ChapterWithTerms[]>(() => {
    if (!book) return [];
    return book.chapters.map((chapter) => ({
      ...chapter,
      terms: terms.filter((term) => term.chapter_id === chapter.chapter_id),
    }));
  }, [book, terms]);

  return (
    <div className="y2k-page relative min-h-dvh overflow-x-hidden text-foreground">
      <Y2KBackground />

      <header className="relative z-20 border-b border-white/10 bg-[#0a0711]/55 backdrop-blur-2xl">
        <div className="mx-auto flex min-h-20 w-full max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-8">
          <div className="flex items-center gap-3">
            <Link href="/" className="y2k-back-link" aria-label="返回科目选择">
              <ArrowLeft className="size-4" aria-hidden="true" />
              <span>科目选择</span>
            </Link>
            <span className="hidden h-5 w-px bg-white/10 sm:block" aria-hidden="true" />
            <DaJuiceLogo compact className="hidden sm:inline-flex" />
          </div>
          <nav className="flex items-center gap-1.5 text-[11px] sm:gap-2">
            <Link href="/history" className="y2k-nav-link">
              <CalendarRange className="size-3.5" aria-hidden="true" />
              <span>学科脉络</span>
            </Link>
            <Link href="/library" className="y2k-nav-link hidden sm:flex">
              <BookOpen className="size-3.5" aria-hidden="true" />
              <span>精准考核</span>
            </Link>
          </nav>
        </div>
      </header>

      <main className="relative z-10 mx-auto w-full max-w-7xl px-4 pb-20 pt-10 sm:px-8 sm:pt-16">
        {loading ? (
          <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
            <div className="space-y-5">
              <div className="h-48 animate-pulse rounded-[2rem] border-2 border-white/10 bg-white/[0.03]" />
              <div className="grid gap-4 sm:grid-cols-2">
                {[0, 1, 2, 3].map((item) => (
                  <div key={item} className="h-60 animate-pulse rounded-2xl border-2 border-white/10 bg-white/[0.03]" />
                ))}
              </div>
            </div>
            <div className="h-80 animate-pulse rounded-2xl border-2 border-white/10 bg-white/[0.03]" />
          </div>
        ) : error ? (
          <div className="y2k-panel max-w-2xl rounded-2xl p-6">
            <p className="font-pixel text-[9px] tracking-[0.18em] text-amber-300">SUBJECT FILE LOST</p>
            <p className="mt-3 text-sm leading-6 text-slate-300">{error}</p>
            <Button type="button" onClick={() => setRefreshKey((value) => value + 1)} className="mt-5 gap-2 bg-cyan-300 text-black hover:bg-cyan-200">
              <RefreshCw className="size-4" aria-hidden="true" />
              重新加载
            </Button>
          </div>
        ) : book ? (
          <>
            <section className="grid gap-5 lg:grid-cols-[1fr_340px] lg:items-stretch">
              <div className="y2k-panel relative overflow-hidden rounded-[2rem] p-6 sm:p-8">
                <div className="pointer-events-none absolute right-[-8rem] top-[-10rem] size-72 rounded-full bg-fuchsia-500/10 blur-[80px]" aria-hidden="true" />
                <div className="flex flex-wrap items-center gap-2">
                  <span className="y2k-chip border-cyan-300/25 bg-cyan-300/10 text-cyan-100">
                    {book.subject}
                  </span>
                  <span className="font-terminal text-sm tracking-[0.18em] text-slate-500">
                    CONCEPT WALL / {bookId.toUpperCase()}
                  </span>
                </div>
                <h1 className="mt-6 max-w-3xl text-3xl font-black leading-[1.15] tracking-tight text-white sm:text-5xl">
                  {book.title}
                </h1>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400">
                  先读概念卡片，再进入专注练习。卡片里的定义、边界和脉络都来自当前知识库。
                </p>
                <div className="mt-7 flex flex-wrap gap-2 text-[11px]">
                  <span className="y2k-stat"><BookOpen className="size-3.5 text-cyan-300" aria-hidden="true" />{book.chapter_count} 章</span>
                  <span className="y2k-stat"><Sparkles className="size-3.5 text-fuchsia-300" aria-hidden="true" />{terms.length} 个概念</span>
                  <span className="y2k-stat"><CalendarRange className="size-3.5 text-amber-300" aria-hidden="true" />{timeline.length} 个脉络节点</span>
                </div>
              </div>

              <aside className="y2k-panel rounded-[2rem] p-5">
                <div className="flex items-center justify-between">
                  <p className="font-pixel text-[8px] tracking-[0.18em] text-fuchsia-200/80">FIELD NOTES</p>
                  <Sparkles className="size-4 text-cyan-300/65" aria-hidden="true" />
                </div>
                <div className="mt-5 space-y-4">
                  {timeline.slice(0, 3).map((item, index) => (
                    <div key={`${item.year}-${item.title}`} className="relative border-l border-white/15 pl-4">
                      <span className="absolute -left-[3px] top-1 size-1.5 rounded-full bg-cyan-300 shadow-[0_0_10px_#3de7ff]" aria-hidden="true" />
                      <p className="font-terminal text-lg leading-none text-cyan-200">{item.year}</p>
                      <p className="mt-1 text-xs font-semibold text-slate-200">{item.title}</p>
                      <p className="mt-1 line-clamp-2 text-[11px] leading-5 text-slate-500">{item.summary}</p>
                      {index < Math.min(timeline.length, 3) - 1 ? <span className="absolute -bottom-3 left-[-4px] h-3 w-px bg-white/10" aria-hidden="true" /> : null}
                    </div>
                  ))}
                </div>
                <Link href="/history" className="mt-5 flex items-center justify-between border-t border-white/10 pt-4 text-[11px] text-slate-400 transition hover:text-cyan-200">
                  查看完整发展史
                  <ChevronRight className="size-4" aria-hidden="true" />
                </Link>
              </aside>
            </section>

            <section className="mt-12" aria-label="名词概念卡片">
              {groupedChapters.map((chapter, chapterIndex) => (
                <div key={chapter.chapter_id} className="mb-12 last:mb-0">
                  <div className="mb-5 flex flex-wrap items-end justify-between gap-3 border-b border-white/10 pb-3">
                    <div>
                      <p className="font-pixel text-[8px] tracking-[0.18em] text-fuchsia-300/70">
                        CHAPTER / {String(chapterIndex + 1).padStart(2, "0")}
                      </p>
                      <h2 className="mt-2 text-xl font-black tracking-tight text-white sm:text-2xl">
                        {chapter.title}
                      </h2>
                    </div>
                    <span className="font-terminal text-sm tracking-[0.14em] text-slate-500">
                      {chapter.terms.length} TERMS
                    </span>
                  </div>
                  {chapter.terms.length > 0 ? (
                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                      {chapter.terms.map((term, termIndex) => (
                        <TermCard
                          key={term.term_id}
                          term={term}
                          index={termIndex}
                          onOpen={() => setActiveTermId(term.term_id)}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-2xl border border-dashed border-white/10 p-5 text-sm text-slate-500">
                      这一章暂时没有概念卡片。
                    </div>
                  )}
                </div>
              ))}
            </section>
          </>
        ) : null}
      </main>

      <AnimatePresence>
        {activeTerm ? (
          <TermModal
            term={activeTerm}
            timeline={timeline}
            bookId={bookId}
            onClose={() => setActiveTermId(null)}
          />
        ) : null}
      </AnimatePresence>
    </div>
  );
}
