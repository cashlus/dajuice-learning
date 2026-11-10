"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BookMarked,
  BookOpenCheck,
  Check,
  History,
  Layers3,
  ListChecks,
  Loader2,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  getBooks,
  storeSelection,
  type LibraryBook,
} from "@/lib/library-api";
import { cn } from "@/lib/utils";

function BookCard({
  book,
  selected,
  onToggleChapter,
  onToggleBook,
}: {
  book: LibraryBook;
  selected: Set<string>;
  onToggleChapter: (chapterId: string) => void;
  onToggleBook: (book: LibraryBook) => void;
}) {
  const selectedCount = book.chapters.filter((chapter) =>
    selected.has(chapter.chapter_id),
  ).length;
  const allSelected = selectedCount === book.chapters.length;

  return (
    <article className="relative overflow-hidden rounded-[1.75rem] border border-white/[0.08] bg-white/[0.035] p-5 shadow-[0_24px_80px_rgba(2,6,23,0.34)] backdrop-blur-2xl sm:p-6">
      <div
        className="pointer-events-none absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-cyan-200/35 to-transparent"
        aria-hidden="true"
      />
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="border-cyan-300/15 bg-cyan-300/[0.08] text-cyan-100">
              {book.subject}
            </Badge>
            <span className="text-[11px] text-slate-500">
              {book.chapter_count} 章 · {book.term_count} 个术语
            </span>
          </div>
          <h2 className="mt-3 text-lg font-semibold tracking-tight text-white sm:text-xl">
            {book.title}
          </h2>
        </div>
        <button
          type="button"
          onClick={() => onToggleBook(book)}
          className={cn(
            "rounded-full border px-3 py-1.5 text-[11px] font-medium transition",
            allSelected
              ? "border-cyan-300/25 bg-cyan-300/10 text-cyan-100"
              : "border-white/10 bg-white/[0.03] text-slate-400 hover:border-white/20 hover:text-slate-200",
          )}
        >
          {allSelected ? "取消全选" : "全选本书"}
        </button>
      </div>

      <div className="mt-5 grid gap-2.5">
        {book.chapters.map((chapter) => {
          const checked = selected.has(chapter.chapter_id);
          return (
            <button
              key={chapter.chapter_id}
              type="button"
              role="checkbox"
              aria-checked={checked}
              onClick={() => onToggleChapter(chapter.chapter_id)}
              className={cn(
                "group flex w-full items-center gap-3 rounded-2xl border px-3.5 py-3 text-left transition",
                checked
                  ? "border-cyan-300/22 bg-cyan-300/[0.07] shadow-[inset_0_0_0_1px_rgba(103,232,249,0.035)]"
                  : "border-white/[0.065] bg-white/[0.018] hover:border-white/[0.13] hover:bg-white/[0.035]",
              )}
            >
              <span
                className={cn(
                  "flex size-5 shrink-0 items-center justify-center rounded-md border transition",
                  checked
                    ? "border-cyan-300/40 bg-cyan-300 text-slate-950"
                    : "border-white/15 bg-white/[0.02] text-transparent",
                )}
                aria-hidden="true"
              >
                <Check className="size-3.5" strokeWidth={3} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-slate-200">
                  {chapter.title}
                </span>
                <span className="mt-0.5 block truncate text-[11px] text-slate-500">
                  {chapter.terms.map((term) => term.name).join(" · ")}
                </span>
              </span>
              <span className="shrink-0 rounded-full border border-white/[0.07] bg-white/[0.025] px-2 py-0.5 text-[10px] text-slate-500">
                {chapter.term_count} 术语
              </span>
            </button>
          );
        })}
      </div>
    </article>
  );
}

export default function LibraryPage() {
  const router = useRouter();
  const [books, setBooks] = useState<LibraryBook[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getBooks()
      .then((items) => {
        if (!cancelled) setBooks(items);
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          const message = reason instanceof Error ? reason.message : "教材加载失败";
          setError(message);
          toast.error(message);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedSet = useMemo(() => new Set(selected), [selected]);
  const selectedBooks = useMemo(
    () =>
      books.filter((book) =>
        book.chapters.some((chapter) => selectedSet.has(chapter.chapter_id)),
      ),
    [books, selectedSet],
  );
  const termCount = useMemo(
    () =>
      selectedBooks.reduce(
        (total, book) =>
          total +
          book.chapters
            .filter((chapter) => selectedSet.has(chapter.chapter_id))
            .reduce((sum, chapter) => sum + chapter.term_count, 0),
        0,
      ),
    [selectedBooks, selectedSet],
  );
  const summary = `已选择 ${selectedBooks.length} 本教材、${selected.length} 个章节、${termCount} 个术语。`;

  function toggleChapter(chapterId: string) {
    setSelected((current) =>
      current.includes(chapterId)
        ? current.filter((item) => item !== chapterId)
        : [...current, chapterId],
    );
  }

  function toggleBook(book: LibraryBook) {
    const ids = book.chapters.map((chapter) => chapter.chapter_id);
    const allSelected = ids.every((id) => selectedSet.has(id));
    setSelected((current) =>
      allSelected
        ? current.filter((id) => !ids.includes(id))
        : Array.from(new Set([...current, ...ids])),
    );
  }

  function persistScope(): boolean {
    if (selectedBooks.length === 0 || selected.length === 0) {
      toast.warning("请先勾选至少一个章节。");
      return false;
    }
    storeSelection({
      book_ids: selectedBooks.map((book) => book.book_id),
      chapter_ids: selected,
      summary,
      term_count: termCount,
    });
    return true;
  }

  function startReview() {
    if (persistScope()) router.push("/review");
  }

  function openHistory() {
    if (selectedBooks.length > 0) persistScope();
    router.push("/history");
  }

  return (
    <div className="relative min-h-dvh overflow-x-hidden bg-[#070b14] text-slate-100">
      <div className="pointer-events-none fixed inset-0 z-0" aria-hidden="true">
        <div className="ambient-grid absolute inset-0 opacity-75" />
        <div className="absolute -left-40 top-[-16rem] size-[36rem] rounded-full bg-cyan-500/[0.08] blur-[140px]" />
        <div className="absolute right-[-12rem] top-[20%] size-[32rem] rounded-full bg-violet-500/[0.09] blur-[150px]" />
      </div>

      <header className="relative z-20 border-b border-white/[0.06] bg-[#070b14]/65 backdrop-blur-2xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm text-slate-400 transition hover:text-white"
          >
            <ArrowLeft className="size-4" aria-hidden="true" />
            返回学习闭环
          </Link>
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost" size="sm" className="text-slate-400 hover:text-white">
              <Link href="/history">
                <History className="size-3.5" aria-hidden="true" />
                历史脉络
              </Link>
            </Button>
            <Button asChild variant="ghost" size="sm" className="text-slate-400 hover:text-white">
              <Link href="/mistakes">
                <ListChecks className="size-3.5" aria-hidden="true" />
                错题本
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-7xl px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        <section className="max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-cyan-200/15 bg-cyan-300/[0.06] px-3 py-1 text-[11px] font-medium tracking-[0.18em] text-cyan-100/80 uppercase">
            <Sparkles className="size-3" aria-hidden="true" />
            Admin-curated library
          </div>
          <h1 className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-white sm:text-5xl">
            从预置教材中，组合你的考核范围
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400 sm:text-base">
            知识库由管理员预置。你可以跨教材、跨章节自由勾选范围；系统只会依据所选章节中的术语与教材摘要出题、判分和记录错题。
          </p>
          <div className="mt-5 flex flex-wrap gap-2 text-[11px] text-slate-500">
            <span className="rounded-full border border-white/[0.07] bg-white/[0.025] px-3 py-1.5">
              仅支持预置教材
            </span>
            <span className="rounded-full border border-white/[0.07] bg-white/[0.025] px-3 py-1.5">
              不接收用户上传内容
            </span>
            <span className="rounded-full border border-white/[0.07] bg-white/[0.025] px-3 py-1.5">
              判分必须引用教材摘要
            </span>
          </div>
        </section>

        {error ? (
          <div className="mt-10 rounded-2xl border border-rose-300/20 bg-rose-400/[0.06] p-5 text-sm text-rose-100">
            教材加载失败：{error}。请确认后端服务已启动。
          </div>
        ) : null}

        <div className="mt-10 grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px] lg:items-start">
          <section aria-label="预置教材列表" className="grid gap-5">
            {loading ? (
              <div className="flex items-center gap-3 rounded-2xl border border-white/[0.08] bg-white/[0.03] px-5 py-8 text-sm text-slate-400">
                <Loader2 className="size-4 animate-spin text-cyan-200" aria-hidden="true" />
                正在读取管理员预置教材……
              </div>
            ) : (
              books.map((book) => (
                <BookCard
                  key={book.book_id}
                  book={book}
                  selected={selectedSet}
                  onToggleChapter={toggleChapter}
                  onToggleBook={toggleBook}
                />
              ))
            )}
          </section>

          <aside className="lg:sticky lg:top-24">
            <div className="rounded-[1.75rem] border border-white/[0.09] bg-gradient-to-b from-white/[0.06] to-white/[0.025] p-5 shadow-[0_28px_90px_rgba(2,6,23,0.42)] backdrop-blur-2xl">
              <div className="flex items-center gap-2 text-sm font-semibold text-white">
                <BookOpenCheck className="size-4 text-cyan-200" aria-hidden="true" />
                本次考核范围
              </div>
              <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                <div className="rounded-xl border border-white/[0.07] bg-black/15 px-2 py-2.5">
                  <p className="text-lg font-semibold text-white">{selectedBooks.length}</p>
                  <p className="mt-0.5 text-[10px] text-slate-500">教材</p>
                </div>
                <div className="rounded-xl border border-white/[0.07] bg-black/15 px-2 py-2.5">
                  <p className="text-lg font-semibold text-white">{selected.length}</p>
                  <p className="mt-0.5 text-[10px] text-slate-500">章节</p>
                </div>
                <div className="rounded-xl border border-white/[0.07] bg-black/15 px-2 py-2.5">
                  <p className="text-lg font-semibold text-white">{termCount}</p>
                  <p className="mt-0.5 text-[10px] text-slate-500">术语</p>
                </div>
              </div>

              <p className="mt-4 text-xs leading-6 text-slate-400">{summary}</p>

              <div className="mt-4 max-h-56 space-y-2 overflow-y-auto pr-1 study-scrollbar">
                {selectedBooks.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-white/[0.08] px-3 py-6 text-center text-xs text-slate-600">
                    尚未选择章节
                  </div>
                ) : (
                  selectedBooks.map((book) => {
                    const chapters = book.chapters.filter((chapter) =>
                      selectedSet.has(chapter.chapter_id),
                    );
                    return (
                      <div
                        key={book.book_id}
                        className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3"
                      >
                        <p className="flex items-center gap-1.5 text-[11px] font-medium text-slate-300">
                          <BookMarked className="size-3 text-cyan-200/75" aria-hidden="true" />
                          {book.title}
                        </p>
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {chapters.map((chapter) => (
                            <span
                              key={chapter.chapter_id}
                              className="max-w-full truncate rounded-md border border-white/[0.06] bg-black/15 px-2 py-1 text-[10px] text-slate-500"
                            >
                              {chapter.title}
                            </span>
                          ))}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              <div className="mt-5 grid gap-2">
                <Button
                  type="button"
                  onClick={startReview}
                  disabled={loading || selected.length === 0}
                  className="h-10 gap-2 rounded-xl border border-cyan-200/20 bg-gradient-to-r from-cyan-300 to-sky-400 text-slate-950 shadow-lg shadow-cyan-400/10 hover:brightness-110"
                >
                  <Layers3 className="size-4" aria-hidden="true" />
                  开始考核
                  <ArrowRight className="ml-auto size-4" aria-hidden="true" />
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={openHistory}
                  className="h-10 gap-2 rounded-xl border-white/[0.09] bg-white/[0.03] text-slate-300 hover:bg-white/[0.06] hover:text-white"
                >
                  <History className="size-4" aria-hidden="true" />
                  查看历史脉络
                </Button>
                <Button
                  asChild
                  variant="ghost"
                  className="h-10 gap-2 rounded-xl text-slate-400 hover:bg-white/[0.04] hover:text-white"
                >
                  <Link href="/mistakes">
                    <ListChecks className="size-4" aria-hidden="true" />
                    温习错题
                  </Link>
                </Button>
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}