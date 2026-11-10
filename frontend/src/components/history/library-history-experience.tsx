"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { MotionConfig, motion, useScroll, useSpring } from "framer-motion";
import {
  ArrowDown,
  ArrowLeft,
  BookOpen,
  BookOpenCheck,
  CalendarRange,
  ChevronRight,
  Layers3,
  LibraryBig,
  Loader2,
  RefreshCw,
  Sparkles,
  UserRound,
  type LucideIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  getTimeline,
  readSelection,
  type StoredScope,
  type TimelineItem,
} from "@/lib/library-api";
import { cn } from "@/lib/utils";

interface TimelineAccent {
  icon: LucideIcon;
  label: string;
  iconTone: string;
  chipTone: string;
  markerTone: string;
  markerGlow: string;
  focusTone: string;
  imageOverlay: string;
}

const TIMELINE_ACCENTS: TimelineAccent[] = [
  {
    icon: CalendarRange,
    label: "ORIGIN",
    iconTone: "border-cyan-300/25 bg-cyan-300/10 text-cyan-200",
    chipTone: "border-cyan-300/20 bg-cyan-300/[0.08] text-cyan-100",
    markerTone: "border-cyan-300/35 text-cyan-100",
    markerGlow:
      "shadow-[0_0_0_7px_rgba(34,211,238,0.055),0_0_36px_rgba(34,211,238,0.24)]",
    focusTone: "text-cyan-200/85",
    imageOverlay: "from-[#06131e] via-[#06131e]/20 to-transparent",
  },
  {
    icon: Layers3,
    label: "SHIFT",
    iconTone: "border-violet-300/25 bg-violet-300/10 text-violet-200",
    chipTone: "border-violet-300/20 bg-violet-300/[0.08] text-violet-100",
    markerTone: "border-violet-300/35 text-violet-100",
    markerGlow:
      "shadow-[0_0_0_7px_rgba(167,139,250,0.055),0_0_36px_rgba(167,139,250,0.24)]",
    focusTone: "text-violet-200/85",
    imageOverlay: "from-[#0d1024] via-[#0d1024]/20 to-transparent",
  },
  {
    icon: Sparkles,
    label: "EXTENSION",
    iconTone: "border-amber-300/25 bg-amber-300/10 text-amber-200",
    chipTone: "border-amber-300/20 bg-amber-300/[0.08] text-amber-100",
    markerTone: "border-amber-300/35 text-amber-100",
    markerGlow:
      "shadow-[0_0_0_7px_rgba(252,211,77,0.055),0_0_36px_rgba(252,211,77,0.22)]",
    focusTone: "text-amber-200/85",
    imageOverlay: "from-[#171208] via-[#171208]/20 to-transparent",
  },
  {
    icon: BookOpenCheck,
    label: "CURRENT",
    iconTone: "border-fuchsia-300/25 bg-fuchsia-300/10 text-fuchsia-200",
    chipTone: "border-fuchsia-300/20 bg-fuchsia-300/[0.08] text-fuchsia-100",
    markerTone: "border-fuchsia-300/35 text-fuchsia-100",
    markerGlow:
      "shadow-[0_0_0_7px_rgba(232,121,249,0.055),0_0_36px_rgba(232,121,249,0.24)]",
    focusTone: "text-fuchsia-200/85",
    imageOverlay: "from-[#160d20] via-[#160d20]/20 to-transparent",
  },
];

function scholarInitials(scholars: string): string {
  const words = scholars
    .replace(/&/g, " ")
    .replace(/[，,、/]/g, " ")
    .split(/\s+/)
    .filter(Boolean);
  if (words.length === 0) return "KB";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return `${words[0][0] ?? ""}${words[words.length - 1][0] ?? ""}`.toUpperCase();
}

function TimelineCard({
  item,
  accent,
  index,
}: {
  item: TimelineItem;
  accent: TimelineAccent;
  index: number;
}) {
  const Icon = accent.icon;
  const isLeft = index % 2 === 0;
  const imageSrc = item.image || "/history/history-default.svg";
  const points = item.points ?? [];

  return (
    <div className="relative grid grid-cols-[44px_minmax(0,1fr)] gap-3 sm:grid-cols-[52px_minmax(0,1fr)] sm:gap-4 lg:grid-cols-[minmax(0,1fr)_112px_minmax(0,1fr)] lg:items-center lg:gap-0">
      <motion.div
        className="relative flex justify-center lg:col-start-2 lg:row-start-1"
        initial={{ opacity: 0, scale: 0.72 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true, amount: 0.55 }}
        transition={{ duration: 0.55, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
        aria-hidden="true"
      >
        <div
          className={cn(
            "relative z-10 flex size-12 items-center justify-center rounded-full border bg-[#080e1a] sm:size-14",
            accent.markerTone,
            accent.markerGlow,
          )}
        >
          <Icon className="size-[18px] sm:size-5" />
          <span className="absolute -bottom-2 rounded-full border border-white/10 bg-[#0a111e] px-1.5 py-0.5 font-mono text-[8px] tracking-[0.16em] text-slate-400">
            {String(index + 1).padStart(2, "0")}
          </span>
        </div>
      </motion.div>

      <motion.div
        className={cn(
          "min-w-0 lg:row-start-1",
          isLeft
            ? "lg:col-start-1 lg:flex lg:justify-end lg:pr-10"
            : "lg:col-start-3 lg:pl-10",
        )}
        initial={{ opacity: 0, x: isLeft ? -54 : 54, y: 22 }}
        whileInView={{ opacity: 1, x: 0, y: 0 }}
        viewport={{ once: true, amount: 0.18 }}
        transition={{ duration: 0.72, ease: [0.22, 1, 0.36, 1] }}
      >
        <article className="group relative w-full min-w-0 max-w-[560px] overflow-hidden rounded-[1.75rem] border border-white/[0.09] bg-white/[0.035] p-px shadow-[0_28px_90px_rgba(2,6,23,0.5)] backdrop-blur-2xl sm:rounded-[2rem]">
          <div className="pointer-events-none absolute inset-0 rounded-[inherit] bg-gradient-to-br from-white/[0.08] via-transparent to-transparent" />
          <div className="relative overflow-hidden rounded-[calc(1.75rem-1px)] bg-[#080d18]/86 sm:rounded-[calc(2rem-1px)]">
            <div className="relative aspect-[16/9] overflow-hidden">
              <Image
                src={imageSrc}
                alt={item.imageAlt || `${item.title}的抽象知识发展插画`}
                fill
                unoptimized
                sizes="(min-width: 1024px) 560px, calc(100vw - 64px)"
                className="object-cover transition-transform duration-700 ease-out group-hover:scale-[1.025]"
              />
              <div
                className={cn(
                  "pointer-events-none absolute inset-0 bg-gradient-to-t",
                  accent.imageOverlay,
                )}
              />
              <div className="absolute inset-x-0 top-0 flex items-center justify-between gap-3 p-4 sm:p-5">
                <span className="max-w-[70%] truncate rounded-full border border-white/10 bg-slate-950/35 px-2.5 py-1 text-[10px] text-white/65 backdrop-blur-xl">
                  {item.book_title}
                </span>
                <span
                  className={cn(
                    "rounded-full border px-2.5 py-1 text-[10px] font-medium backdrop-blur-xl",
                    accent.chipTone,
                  )}
                >
                  {accent.label}
                </span>
              </div>
              <div className="absolute inset-x-0 bottom-0 flex items-end justify-between gap-3 p-4 sm:p-6">
                <p className="min-w-0 break-words text-3xl font-semibold tracking-[-0.045em] text-white sm:text-5xl">
                  {item.year}
                </p>
                <span className="mb-1 hidden shrink-0 rounded-full border border-white/10 bg-slate-950/30 px-3 py-1.5 text-[10px] text-white/65 backdrop-blur-xl sm:inline">
                  知识脉络节点
                </span>
              </div>
            </div>

            <div className="p-4 sm:p-7">
              <div className="flex items-start gap-3">
                <div
                  className={cn(
                    "flex size-10 shrink-0 items-center justify-center rounded-2xl border",
                    accent.iconTone,
                  )}
                  aria-hidden="true"
                >
                  <Icon className="size-[18px]" />
                </div>
                <div className="min-w-0">
                  <p className="font-mono text-[9px] tracking-[0.22em] text-slate-500">
                    CONCEPT NODE · {String(index + 1).padStart(2, "0")}
                  </p>
                  <h2 className="mt-1 break-words text-xl font-semibold tracking-tight text-white sm:text-2xl">
                    {item.title}
                  </h2>
                </div>
              </div>

              <div className="mt-4 flex items-center gap-3 rounded-2xl border border-white/[0.065] bg-white/[0.025] px-3.5 py-3">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-full border border-white/10 bg-gradient-to-br from-white/12 to-white/[0.025] font-mono text-[10px] font-medium tracking-wide text-slate-200">
                  {scholarInitials(item.scholars)}
                </div>
                <div className="min-w-0">
                  <p className="text-[10px] tracking-[0.12em] text-slate-500">
                    代表人物 / 研究群体
                  </p>
                  <p className="mt-0.5 break-words text-sm font-medium text-slate-100">
                    {item.scholars || "研究群体"}
                  </p>
                </div>
                <UserRound
                  className="ml-auto size-3.5 shrink-0 text-slate-600"
                  aria-hidden="true"
                />
              </div>

              <p className="mt-4 text-[13px] leading-7 text-slate-300/90 sm:text-sm">
                {item.summary}
              </p>

              {points.length > 0 ? (
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {points.map((point) => (
                    <span
                      key={point}
                      className="max-w-full rounded-full border border-white/[0.07] bg-white/[0.025] px-2.5 py-1 text-[10px] leading-5 text-slate-400"
                    >
                      {point}
                    </span>
                  ))}
                </div>
              ) : null}

              <div className="mt-5 flex items-center justify-between gap-3 border-t border-white/[0.065] pt-4">
                <span className="flex min-w-0 items-center gap-1.5 text-[10px] text-slate-600">
                  <LibraryBig className="size-3 shrink-0" aria-hidden="true" />
                  <span className="truncate">来源：{item.book_title}</span>
                </span>
                <span
                  className={cn(
                    "flex shrink-0 items-center gap-1 text-[10px] font-medium",
                    accent.focusTone,
                  )}
                >
                  阅读节点
                  <ChevronRight className="size-3" aria-hidden="true" />
                </span>
              </div>
            </div>
          </div>
        </article>
      </motion.div>
    </div>
  );
}

function LoadingTimeline() {
  return (
    <div className="mx-auto max-w-[1180px] px-4 sm:px-6 lg:px-8" aria-live="polite">
      <div className="rounded-[2rem] border border-white/[0.07] bg-white/[0.025] px-5 py-16 text-center backdrop-blur-2xl">
        <Loader2 className="mx-auto size-6 animate-spin text-cyan-200" aria-hidden="true" />
        <p className="mt-4 text-sm text-slate-300">正在读取知识库中的时间线……</p>
        <p className="mt-1 text-xs text-slate-600">管理员预置内容，不依赖用户上传。</p>
      </div>
    </div>
  );
}

export function LibraryHistoryExperience() {
  const timelineRef = useRef<HTMLDivElement>(null);
  const [items, setItems] = useState<TimelineItem[]>([]);
  const [scope, setScope] = useState<StoredScope | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      await Promise.resolve();
      if (cancelled) return;

      const stored = readSelection();
      setScope(stored);
      setLoading(true);
      setError(null);

      try {
        const timelineItems = await getTimeline(stored?.book_ids);
        if (!cancelled) setItems(timelineItems);
      } catch (reason: unknown) {
        if (!cancelled) {
          setError(
            reason instanceof Error
              ? reason.message
              : "知识库时间线加载失败，请确认后端服务已启动。",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const { scrollYProgress } = useScroll({
    target: timelineRef,
    offset: ["start 0.72", "end 0.6"],
  });
  const glowingLine = useSpring(scrollYProgress, {
    stiffness: 90,
    damping: 28,
    mass: 0.35,
    restDelta: 0.001,
  });

  const firstYear = items[0]?.year ?? "—";
  const lastYear = items[items.length - 1]?.year ?? "—";
  const bookCount = new Set(items.map((item) => item.book_id)).size;
  const rangeLabel = items.length ? `${firstYear} — ${lastYear}` : "知识库时间线";

  return (
    <MotionConfig reducedMotion="user">
      <div className="relative min-h-dvh overflow-x-clip bg-[#060a12] text-slate-100">
        <div
          className="pointer-events-none fixed inset-0 z-0 overflow-hidden"
          aria-hidden="true"
        >
          <div className="ambient-grid absolute inset-0 opacity-65" />
          <div className="absolute -left-44 top-[-14rem] size-[42rem] rounded-full bg-cyan-500/[0.08] blur-[150px]" />
          <div className="absolute -right-56 top-[22%] size-[46rem] rounded-full bg-violet-500/[0.09] blur-[160px]" />
          <div className="absolute bottom-[-22rem] left-[24%] size-[44rem] rounded-full bg-amber-500/[0.045] blur-[170px]" />
          <div className="absolute inset-x-0 top-0 h-[42rem] bg-[radial-gradient(ellipse_at_top,rgba(34,211,238,0.075),transparent_65%)]" />
        </div>

        <header className="relative z-30 border-b border-white/[0.06] bg-[#060a12]/55 backdrop-blur-2xl">
          <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between gap-3 px-3 sm:px-6 lg:px-8">
            <Button
              asChild
              variant="ghost"
              className="h-10 shrink-0 gap-2 rounded-full border border-white/[0.075] bg-white/[0.03] px-3 text-xs text-slate-300 hover:border-white/[0.14] hover:bg-white/[0.06] hover:text-white sm:px-4"
            >
              <Link href="/">
                <ArrowLeft className="size-3.5" aria-hidden="true" />
                返回学习主页
              </Link>
            </Button>

            <div className="flex min-w-0 items-center gap-2 text-[10px] tracking-[0.16em] text-slate-500">
              <BookOpen className="size-3.5 shrink-0 text-cyan-300/75" aria-hidden="true" />
              <span className="hidden sm:inline">KNOWLEDGE ATLAS</span>
              <span className="hidden text-slate-700 sm:inline">/</span>
              <span className="truncate">{rangeLabel}</span>
            </div>
          </div>
        </header>

        <main className="relative z-10">
          <section className="relative mx-auto max-w-6xl px-4 pb-16 pt-12 text-center sm:px-8 sm:pb-24 sm:pt-20">
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              className="mx-auto flex w-fit max-w-full items-center gap-2 rounded-full border border-cyan-300/15 bg-cyan-300/[0.055] px-3 py-1.5 text-[10px] font-medium tracking-[0.14em] text-cyan-100/75"
            >
              <Sparkles className="size-3 shrink-0" aria-hidden="true" />
              <span className="truncate">CURATED LIBRARY · CONCEPT DEVELOPMENT</span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.75, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
              className="mx-auto mt-6 max-w-5xl text-balance text-4xl leading-[1.14] font-semibold tracking-[-0.055em] text-white sm:mt-7 sm:text-6xl lg:text-7xl"
            >
              概念如何长成：
              <span className="mt-2 block bg-gradient-to-r from-cyan-200 via-sky-200 to-violet-300 bg-clip-text pb-1 text-transparent sm:mt-3">
                一张跨教材的知识地图
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.18, ease: [0.22, 1, 0.36, 1] }}
              className="mx-auto mt-6 max-w-2xl text-sm leading-7 text-slate-400 sm:mt-7 sm:text-base sm:leading-8"
            >
              从管理员预置教材的章节中抽取时间节点，把理论提出、研究重心迁移与当代延伸放在同一条脉络里。这里只展示知识库内容，不拼接未经核验的外部叙事。
            </motion.p>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.34 }}
              className="mt-8 flex flex-wrap items-center justify-center gap-2 text-[11px] text-slate-500"
            >
              <span className="max-w-full truncate rounded-full border border-white/[0.07] bg-white/[0.025] px-3 py-1.5">
                {scope ? `本次范围：${scope.summary}` : "未限定范围 · 展示全部预置知识库"}
              </span>
              <span className="rounded-full border border-white/[0.07] bg-white/[0.025] px-3 py-1.5">
                {items.length} 个时间节点
              </span>
              <span className="rounded-full border border-white/[0.07] bg-white/[0.025] px-3 py-1.5">
                {bookCount} 本教材
              </span>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.42 }}
              className="mt-7 flex flex-wrap items-center justify-center gap-2.5"
            >
              <Button
                asChild
                className="h-10 gap-2 rounded-full border border-cyan-200/20 bg-gradient-to-r from-cyan-300 to-sky-400 px-5 text-sm font-semibold text-slate-950 shadow-lg shadow-cyan-400/15 hover:brightness-110"
              >
                <Link href="/library">
                  <BookOpenCheck className="size-4" aria-hidden="true" />
                  调整考核范围
                </Link>
              </Button>
              <Button
                asChild
                variant="outline"
                className="h-10 gap-2 rounded-full border-white/[0.09] bg-white/[0.03] px-5 text-sm text-slate-300 hover:border-white/[0.16] hover:bg-white/[0.06] hover:text-white"
              >
                <Link href="/review">
                  进入精准考核
                  <ChevronRight className="size-4" aria-hidden="true" />
                </Link>
              </Button>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.52 }}
              className="mt-9 flex flex-col items-center gap-2 text-[10px] tracking-[0.18em] text-slate-600"
            >
              <span>向下滚动，点亮知识脉络</span>
              <motion.span
                animate={{ y: [0, 6, 0] }}
                transition={{
                  duration: 1.8,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "easeInOut",
                }}
                className="flex size-8 items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.025]"
                aria-hidden="true"
              >
                <ArrowDown className="size-3.5 text-cyan-200/70" />
              </motion.span>
            </motion.div>
          </section>

          <section
            aria-label="知识库概念发展时间线"
            className="relative mx-auto max-w-[1180px] px-3 pb-24 sm:px-6 sm:pb-32 lg:px-8"
          >
            <div ref={timelineRef} className="min-w-0">
              {loading ? (
                <LoadingTimeline />
              ) : error ? (
                <div className="mx-auto max-w-2xl rounded-[2rem] border border-rose-300/15 bg-rose-300/[0.045] px-6 py-12 text-center backdrop-blur-2xl">
                  <p className="text-sm font-medium text-rose-100">时间线暂时没有加载出来</p>
                  <p className="mt-2 text-xs leading-6 text-rose-100/65">{error}</p>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setReloadKey((value) => value + 1)}
                    className="mt-5 h-9 gap-2 rounded-full border-white/10 bg-white/[0.03] text-slate-200 hover:bg-white/[0.07]"
                  >
                    <RefreshCw className="size-3.5" aria-hidden="true" />
                    重新加载
                  </Button>
                </div>
              ) : items.length === 0 ? (
                <div className="mx-auto max-w-2xl rounded-[2rem] border border-white/[0.08] bg-white/[0.025] px-6 py-12 text-center backdrop-blur-2xl">
                  <Layers3 className="mx-auto size-6 text-slate-500" aria-hidden="true" />
                  <p className="mt-4 text-sm text-slate-300">当前范围还没有可展示的时间线。</p>
                  <p className="mt-2 text-xs text-slate-600">
                    请选择包含时间线内容的管理员预置章节，或查看全部知识库。
                  </p>
                  <Button
                    asChild
                    className="mt-5 h-9 rounded-full bg-cyan-300 px-5 text-slate-950 hover:bg-cyan-200"
                  >
                    <Link href="/library">返回选择范围</Link>
                  </Button>
                </div>
              ) : (
                <div className="relative min-w-0">
                <div
                  className="absolute top-0 bottom-0 left-[21px] w-px bg-white/[0.075] sm:left-[25px] lg:left-1/2 lg:-translate-x-1/2"
                  aria-hidden="true"
                />
                <motion.div
                  className="absolute top-0 bottom-0 left-[21px] w-[2px] origin-top -translate-x-px bg-gradient-to-b from-cyan-300 via-violet-300 to-amber-300 shadow-[0_0_24px_rgba(103,232,249,0.4)] sm:left-[25px] lg:left-1/2 lg:-translate-x-1/2"
                  style={{ scaleY: glowingLine }}
                  aria-hidden="true"
                />
                <div
                  className="absolute top-0 bottom-0 left-[21px] w-8 -translate-x-1/2 bg-cyan-400/[0.035] blur-xl sm:left-[25px] lg:left-1/2"
                  aria-hidden="true"
                />

                <div className="flex flex-col gap-16 sm:gap-24 lg:gap-36">
                  {items.map((item, index) => (
                    <TimelineCard
                      key={`${item.book_id}-${item.year}-${item.title}-${index}`}
                      item={item}
                      accent={TIMELINE_ACCENTS[index % TIMELINE_ACCENTS.length]}
                      index={index}
                    />
                  ))}
                </div>
                </div>
              )}
            </div>
          </section>

          <section className="relative mx-auto max-w-5xl px-4 pb-20 sm:px-8 sm:pb-28">
            <div className="relative overflow-hidden rounded-[2rem] border border-white/[0.08] bg-gradient-to-br from-cyan-300/[0.055] via-white/[0.025] to-violet-300/[0.065] px-5 py-9 text-center shadow-[0_30px_100px_rgba(2,6,23,0.45)] backdrop-blur-2xl sm:px-12 sm:py-12">
              <div
                className="pointer-events-none absolute inset-x-16 top-0 h-px bg-gradient-to-r from-transparent via-cyan-200/50 to-transparent"
                aria-hidden="true"
              />
              <div className="mx-auto flex size-12 items-center justify-center rounded-2xl border border-cyan-200/15 bg-cyan-300/[0.07] text-cyan-100">
                <LibraryBig className="size-5" aria-hidden="true" />
              </div>
              <h2 className="mt-5 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                让脉络回到考核
              </h2>
              <p className="mx-auto mt-3 max-w-2xl text-sm leading-7 text-slate-400">
                时间线只负责把知识放回历史位置；真正的掌握，还要能用自己的话解释概念、补全关键要素，并在错题复习中把遗漏逐一补齐。
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2.5">
                <Button
                  asChild
                  className="h-10 rounded-full border border-cyan-200/20 bg-gradient-to-r from-cyan-300 to-sky-400 px-5 text-sm font-semibold text-slate-950 shadow-lg shadow-cyan-400/15 hover:brightness-110"
                >
                  <Link href="/library">
                    选择考核范围
                    <ChevronRight className="size-4" aria-hidden="true" />
                  </Link>
                </Button>
                <Button
                  asChild
                  variant="outline"
                  className="h-10 rounded-full border-white/[0.09] bg-white/[0.03] px-5 text-sm text-slate-300 hover:bg-white/[0.06] hover:text-white"
                >
                  <Link href="/mistakes">温习错题</Link>
                </Button>
              </div>
            </div>
          </section>
        </main>
      </div>
    </MotionConfig>
  );
}
