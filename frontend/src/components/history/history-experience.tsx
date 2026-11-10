"use client";

import Image from "next/image";
import Link from "next/link";
import { useRef } from "react";
import { MotionConfig, motion, useScroll, useSpring } from "framer-motion";
import {
  ArrowDown,
  ArrowLeft,
  BookOpen,
  ChevronRight,
  Layers3,
  Network,
  Newspaper,
  Sparkles,
  Tag,
  UserRound,
  type LucideIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  CONCEPT_DEVELOPMENT,
  type ConceptDevelopmentStage,
} from "@/lib/concept";
import { cn } from "@/lib/utils";

interface StageAccent {
  icon: LucideIcon;
  layer: string;
  kicker: string;
  iconTone: string;
  chipTone: string;
  markerTone: string;
  markerGlow: string;
  imageOverlay: string;
}

const STAGE_ACCENTS: StageAccent[] = [
  {
    icon: Newspaper,
    layer: "LAYER 01",
    kicker: "对象显著性",
    iconTone: "border-cyan-300/25 bg-cyan-300/10 text-cyan-200",
    chipTone: "border-cyan-300/20 bg-cyan-300/[0.08] text-cyan-100",
    markerTone: "border-cyan-300/35 text-cyan-100",
    markerGlow:
      "shadow-[0_0_0_7px_rgba(34,211,238,0.055),0_0_36px_rgba(34,211,238,0.24)]",
    imageOverlay: "from-[#07131f] via-[#07131f]/20 to-transparent",
  },
  {
    icon: Tag,
    layer: "LAYER 02",
    kicker: "属性显著性",
    iconTone: "border-violet-300/25 bg-violet-300/10 text-violet-200",
    chipTone: "border-violet-300/20 bg-violet-300/[0.08] text-violet-100",
    markerTone: "border-violet-300/35 text-violet-100",
    markerGlow:
      "shadow-[0_0_0_7px_rgba(167,139,250,0.055),0_0_36px_rgba(167,139,250,0.24)]",
    imageOverlay: "from-[#0e1024] via-[#0e1024]/20 to-transparent",
  },
  {
    icon: Network,
    layer: "LAYER 03",
    kicker: "关联网络",
    iconTone: "border-fuchsia-300/25 bg-fuchsia-300/10 text-fuchsia-200",
    chipTone: "border-fuchsia-300/20 bg-fuchsia-300/[0.08] text-fuchsia-100",
    markerTone: "border-fuchsia-300/35 text-fuchsia-100",
    markerGlow:
      "shadow-[0_0_0_7px_rgba(232,121,249,0.055),0_0_36px_rgba(232,121,249,0.24)]",
    imageOverlay: "from-[#160d20] via-[#160d20]/20 to-transparent",
  },
];

const SCHOLAR_INITIALS: Record<string, string> = {
  "first-level": "MS",
  "second-level": "G",
  "network-level": "GM",
};

function HistoryCard({
  stage,
  accent,
  index,
}: {
  stage: ConceptDevelopmentStage;
  accent: StageAccent;
  index: number;
}) {
  const Icon = accent.icon;
  const isLeft = index % 2 === 0;

  return (
    <div className="relative grid grid-cols-[52px_minmax(0,1fr)] gap-4 lg:grid-cols-[minmax(0,1fr)_112px_minmax(0,1fr)] lg:items-center lg:gap-0">
      <motion.div
        className="relative flex justify-center lg:col-start-2 lg:row-start-1"
        initial={{ opacity: 0, scale: 0.72 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true, amount: 0.6 }}
        transition={{ duration: 0.55, delay: 0.12, ease: [0.22, 1, 0.36, 1] }}
        aria-hidden="true"
      >
        <div
          className={cn(
            "relative z-10 flex size-14 items-center justify-center rounded-full border bg-[#080e1a]",
            accent.markerTone,
            accent.markerGlow,
          )}
        >
          <Icon className="size-5" />
          <span className="absolute -bottom-2 rounded-full border border-white/10 bg-[#0a111e] px-1.5 py-0.5 font-mono text-[8px] tracking-[0.16em] text-slate-400">
            0{index + 1}
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
        viewport={{ once: true, amount: 0.2 }}
        transition={{ duration: 0.72, ease: [0.22, 1, 0.36, 1] }}
      >
        <article className="group relative w-full max-w-[540px] rounded-[2rem] border border-white/[0.09] bg-white/[0.035] p-px shadow-[0_28px_90px_rgba(2,6,23,0.5)] backdrop-blur-2xl">
          <div className="pointer-events-none absolute inset-0 rounded-[2rem] bg-gradient-to-br from-white/[0.08] via-transparent to-transparent" />
          <div className="relative overflow-hidden rounded-[calc(2rem-1px)] bg-[#080d18]/86">
            <div className="relative aspect-[16/9] overflow-hidden">
              <Image
                src={stage.image}
                alt={stage.imageAlt}
                fill
                unoptimized
                sizes="(min-width: 1024px) 540px, calc(100vw - 84px)"
                className="object-cover transition-transform duration-700 ease-out group-hover:scale-[1.025]"
              />
              <div
                className={cn(
                  "pointer-events-none absolute inset-0 bg-gradient-to-t",
                  accent.imageOverlay,
                )}
              />
              <div className="absolute inset-x-0 bottom-0 flex items-end justify-between gap-4 p-5 sm:p-6">
                <div>
                  <p className="font-mono text-[10px] tracking-[0.24em] text-white/45">
                    {accent.layer} · AGENDA-SETTING
                  </p>
                  <p className="mt-1 text-4xl font-semibold tracking-[-0.055em] text-white sm:text-5xl">
                    {stage.period}
                  </p>
                </div>
                <span
                  className={cn(
                    "mb-1 rounded-full border px-3 py-1.5 text-[11px] font-medium backdrop-blur-xl",
                    accent.chipTone,
                  )}
                >
                  {stage.focus}
                </span>
              </div>
            </div>

            <div className="p-5 sm:p-7">
              <div className="flex items-start gap-3.5">
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
                    THEORETICAL LAYER
                  </p>
                  <h2 className="mt-1 text-xl font-semibold tracking-tight text-white sm:text-2xl">
                    {stage.stage}
                  </h2>
                </div>
              </div>

              <div className="mt-5 flex items-center gap-3 rounded-2xl border border-white/[0.065] bg-white/[0.025] px-3.5 py-3">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-full border border-white/10 bg-gradient-to-br from-white/12 to-white/[0.025] font-mono text-[10px] font-medium tracking-wide text-slate-200">
                  {SCHOLAR_INITIALS[stage.id] ?? "AS"}
                </div>
                <div className="min-w-0">
                  <p className="text-[10px] tracking-[0.12em] text-slate-500">
                    代表人物
                  </p>
                  <p className="mt-0.5 truncate text-sm font-medium text-slate-100">
                    {stage.scholars}
                  </p>
                </div>
                <UserRound
                  className="ml-auto size-3.5 shrink-0 text-slate-600"
                  aria-hidden="true"
                />
              </div>

              <p className="mt-5 text-[13px] leading-7 text-slate-300/90 sm:text-sm">
                {stage.contribution}
              </p>

              <div className="mt-5 flex items-center justify-between gap-4 border-t border-white/[0.065] pt-4">
                <span className="text-[10px] tracking-[0.18em] text-slate-600">
                  研究焦点
                </span>
                <span
                  className={cn(
                    "flex items-center gap-1.5 text-[11px] font-medium",
                    index === 0
                      ? "text-cyan-200/85"
                      : index === 1
                        ? "text-violet-200/85"
                        : "text-fuchsia-200/85",
                  )}
                >
                  {accent.kicker}
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

export function HistoryExperience() {
  const timelineRef = useRef<HTMLDivElement>(null);
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

  return (
    <MotionConfig reducedMotion="user">
      <div className="relative min-h-dvh overflow-x-hidden bg-[#060a12] text-slate-100">
        <div
          className="pointer-events-none fixed inset-0 z-0 overflow-hidden"
          aria-hidden="true"
        >
          <div className="ambient-grid absolute inset-0 opacity-65" />
          <div className="absolute -left-44 top-[-14rem] size-[42rem] rounded-full bg-cyan-500/[0.08] blur-[150px]" />
          <div className="absolute -right-56 top-[22%] size-[46rem] rounded-full bg-violet-500/[0.09] blur-[160px]" />
          <div className="absolute bottom-[-22rem] left-[24%] size-[44rem] rounded-full bg-fuchsia-500/[0.055] blur-[170px]" />
          <div className="absolute inset-x-0 top-0 h-[42rem] bg-[radial-gradient(ellipse_at_top,rgba(34,211,238,0.075),transparent_65%)]" />
        </div>

        <header className="relative z-30 border-b border-white/[0.06] bg-[#060a12]/55 backdrop-blur-2xl">
          <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
            <Button
              asChild
              variant="ghost"
              className="h-10 gap-2 rounded-full border border-white/[0.075] bg-white/[0.03] px-4 text-xs text-slate-300 hover:border-white/[0.14] hover:bg-white/[0.06] hover:text-white"
            >
              <Link href="/">
                <ArrowLeft className="size-3.5" aria-hidden="true" />
                返回学习主页
              </Link>
            </Button>

            <div className="flex items-center gap-2 text-[10px] tracking-[0.18em] text-slate-500">
              <BookOpen
                className="size-3.5 text-cyan-300/75"
                aria-hidden="true"
              />
              <span className="hidden sm:inline">CONCEPT ATLAS</span>
              <span className="hidden text-slate-700 sm:inline">/</span>
              <span>1972 — 2011</span>
            </div>
          </div>
        </header>

        <main className="relative z-10">
          <section className="relative mx-auto max-w-6xl px-5 pb-20 pt-16 text-center sm:px-8 sm:pb-24 sm:pt-24">
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              className="mx-auto flex w-fit items-center gap-2 rounded-full border border-cyan-300/15 bg-cyan-300/[0.055] px-3.5 py-1.5 text-[10px] font-medium tracking-[0.16em] text-cyan-100/75"
            >
              <Sparkles className="size-3" aria-hidden="true" />
              AGENDA-SETTING · CONCEPT DEVELOPMENT
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: 0.75,
                delay: 0.08,
                ease: [0.22, 1, 0.36, 1],
              }}
              className="mx-auto mt-7 max-w-5xl text-balance text-4xl leading-[1.12] font-semibold tracking-[-0.055em] text-white sm:text-6xl lg:text-7xl"
            >
              议程设置理论：
              <span className="mt-2 block bg-gradient-to-r from-cyan-200 via-sky-200 to-violet-300 bg-clip-text pb-1 text-transparent sm:mt-3">
                从第一层到网络议程设置
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: 0.7,
                delay: 0.18,
                ease: [0.22, 1, 0.36, 1],
              }}
              className="mx-auto mt-7 max-w-2xl text-sm leading-7 text-slate-400 sm:text-base sm:leading-8"
            >
              这不只是三个年份，而是一条研究重心不断迁移的线索：从媒体让我们
              <span className="text-slate-200">关注什么</span>，到如何
              <span className="text-slate-200">理解它</span>，再到这些议题如何
              <span className="text-slate-200">连成一张网络</span>。
            </motion.p>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.42 }}
              className="mt-10 flex flex-col items-center gap-4"
            >
              <div className="flex flex-wrap items-center justify-center gap-2 text-[11px] text-slate-500">
                <span className="rounded-full border border-white/[0.07] bg-white/[0.025] px-3 py-1.5">
                  3 个理论层级
                </span>
                <span className="rounded-full border border-white/[0.07] bg-white/[0.025] px-3 py-1.5">
                  关键学者群像
                </span>
                <span className="rounded-full border border-white/[0.07] bg-white/[0.025] px-3 py-1.5">
                  50 年研究演进
                </span>
              </div>
              <div className="mt-3 flex flex-col items-center gap-2 text-[10px] tracking-[0.18em] text-slate-600">
                <span>向下滚动，点亮概念脉络</span>
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
              </div>
            </motion.div>
          </section>

          <section
            aria-label="议程设置概念发展时间线"
            className="relative mx-auto max-w-[1180px] px-4 pb-28 sm:px-6 sm:pb-36 lg:px-8"
          >
            <div ref={timelineRef} className="relative">
              <div
                className="absolute top-0 bottom-0 left-[25px] w-px bg-white/[0.075] lg:left-1/2 lg:-translate-x-1/2"
                aria-hidden="true"
              />
              <motion.div
                className="absolute top-0 bottom-0 left-[25px] w-[2px] origin-top -translate-x-px bg-gradient-to-b from-cyan-300 via-violet-300 to-fuchsia-300 shadow-[0_0_24px_rgba(103,232,249,0.4)] lg:left-1/2 lg:-translate-x-1/2"
                style={{ scaleY: glowingLine }}
                aria-hidden="true"
              />
              <div
                className="absolute top-0 bottom-0 left-[25px] w-8 -translate-x-1/2 bg-cyan-400/[0.035] blur-xl lg:left-1/2"
                aria-hidden="true"
              />

              <div className="flex flex-col gap-20 sm:gap-28 lg:gap-40">
                {CONCEPT_DEVELOPMENT.map((stage, index) => (
                  <HistoryCard
                    key={stage.id}
                    stage={stage}
                    accent={STAGE_ACCENTS[index] ?? STAGE_ACCENTS[0]}
                    index={index}
                  />
                ))}
              </div>
            </div>
          </section>

          <section className="relative mx-auto max-w-5xl px-5 pb-24 sm:px-8 sm:pb-32">
            <div className="relative overflow-hidden rounded-[2rem] border border-white/[0.08] bg-gradient-to-br from-cyan-300/[0.055] via-white/[0.025] to-violet-300/[0.065] px-6 py-10 text-center shadow-[0_30px_100px_rgba(2,6,23,0.45)] backdrop-blur-2xl sm:px-12 sm:py-14">
              <div
                className="pointer-events-none absolute inset-x-16 top-0 h-px bg-gradient-to-r from-transparent via-cyan-200/50 to-transparent"
                aria-hidden="true"
              />
              <div className="mx-auto flex size-12 items-center justify-center rounded-2xl border border-cyan-200/15 bg-cyan-300/[0.07] text-cyan-100">
                <Layers3 className="size-5" aria-hidden="true" />
              </div>
              <h2 className="mt-5 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                一条脉络，三层问题
              </h2>
              <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-slate-400">
                第一层问“什么被看见”，第二层问“它被怎样理解”，网络议程设置则问“这些对象与属性如何彼此连接”。回到诊断时，试着把这层区分说清楚。
              </p>
              <Button
                asChild
                className="mt-7 h-11 rounded-full border border-cyan-200/20 bg-gradient-to-r from-cyan-300 to-sky-400 px-6 text-sm font-semibold text-slate-950 shadow-lg shadow-cyan-400/15 hover:brightness-110"
              >
                <Link href="/">
                  回到学习闭环
                  <ChevronRight className="size-4" aria-hidden="true" />
                </Link>
              </Button>
            </div>
          </section>
        </main>
      </div>
    </MotionConfig>
  );
}
