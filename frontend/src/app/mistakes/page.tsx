"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  BookOpenCheck,
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  ClipboardCheck,
  History,
  Lightbulb,
  ListChecks,
  Loader2,
  RefreshCw,
  RotateCcw,
  Sparkles,
  Target,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  formatDateTime,
  getDueMistakes,
  getHint,
  getMistakes,
  reviewMistake,
  type GradeResult,
  type HintResult,
  type Mistake,
} from "@/lib/library-api";
import { cn } from "@/lib/utils";

type MistakeReviewResult = Awaited<ReturnType<typeof reviewMistake>>;

const TYPE_LABEL: Record<Mistake["question_type"], string> = {
  choice: "选择题",
  short_answer: "简答题",
  flashcard: "记忆卡",
};

function GradeInline({ grade }: { grade: GradeResult }) {
  return (
    <div
      className={cn(
        "mt-3 rounded-xl border px-3.5 py-3 text-xs leading-6",
        grade.correct
          ? "border-emerald-300/20 bg-emerald-300/[0.05]"
          : "border-rose-300/20 bg-rose-300/[0.045]",
      )}
    >
      <p
        className={cn(
          "flex items-center gap-1.5 font-medium",
          grade.correct ? "text-emerald-100" : "text-rose-100",
        )}
      >
        {grade.correct ? (
          <CheckCircle2 className="size-3.5" aria-hidden="true" />
        ) : (
          <XCircle className="size-3.5" aria-hidden="true" />
        )}
        {grade.correct ? "这次答对了" : "仍需复习"}
        <span className="ml-auto font-mono text-[10px] text-slate-500">{grade.score} / 100</span>
      </p>
      <p className="mt-2 whitespace-pre-wrap text-slate-300">{grade.reference_excerpt}</p>
      <p className="mt-2 text-slate-400">{grade.grading_reason}</p>
      {grade.missing_points.length > 0 ? (
        <div className="mt-2 rounded-lg border border-amber-300/15 bg-amber-300/[0.04] px-2.5 py-2 text-amber-50/80">
          <p className="text-[10px] tracking-[0.14em] text-amber-200/70 uppercase">漏掉要点</p>
          <ul className="mt-1.5 space-y-1">
            {grade.missing_points.map((point) => (
              <li key={point}>· {point}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {grade.common_confusion ? (
        <p className="mt-2 rounded-lg border border-amber-300/15 bg-amber-300/[0.04] px-2.5 py-2 text-amber-50/80">
          易混：{grade.common_confusion}
        </p>
      ) : null}
    </div>
  );
}

function HintBox({
  hint,
  loading,
  onLoad,
}: {
  hint?: HintResult;
  loading: boolean;
  onLoad: () => void;
}) {
  return (
    <div className="mt-3">
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={onLoad}
        disabled={loading}
        className="h-8 gap-1.5 rounded-full border-cyan-300/15 bg-cyan-300/[0.04] text-cyan-100/80 hover:bg-cyan-300/[0.08] hover:text-cyan-50"
      >
        {loading ? (
          <Loader2 className="size-3 animate-spin" aria-hidden="true" />
        ) : (
          <Lightbulb className="size-3" aria-hidden="true" />
        )}
        知识库提示
      </Button>
      {hint ? (
        <div className="mt-2 rounded-xl border border-cyan-300/15 bg-cyan-300/[0.04] px-3 py-2.5 text-xs leading-6 text-slate-300">
          <p className="text-[10px] tracking-[0.14em] text-cyan-200/65 uppercase">
            基于知识库的重点难点提示
          </p>
          <p className="mt-1">{hint.definition}</p>
          <p className="mt-1 text-cyan-50/75">{hint.suggested_review}</p>
          {hint.common_confusion ? (
            <p className="mt-1 text-amber-100/75">易混：{hint.common_confusion}</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function MistakeCard({
  mistake,
  due,
  expanded,
  answer,
  submitting,
  result,
  hint,
  hintLoading,
  onToggle,
  onAnswerChange,
  onSubmit,
  onHint,
}: {
  mistake: Mistake;
  due: boolean;
  expanded: boolean;
  answer: string;
  submitting: boolean;
  result?: MistakeReviewResult;
  hint?: HintResult;
  hintLoading: boolean;
  onToggle: () => void;
  onAnswerChange: (value: string) => void;
  onSubmit: () => void;
  onHint: () => void;
}) {
  return (
    <article className="rounded-[1.5rem] border border-white/[0.08] bg-white/[0.03] p-4 shadow-[0_18px_60px_rgba(2,6,23,0.26)] backdrop-blur-xl sm:p-5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge
          className={cn(
            due
              ? "border-amber-300/25 bg-amber-300/[0.09] text-amber-100"
              : "border-slate-300/15 bg-slate-300/[0.05] text-slate-400",
          )}
        >
          {due ? "已到期" : "未到期"}
        </Badge>
        <Badge className="border-violet-300/15 bg-violet-300/[0.07] text-violet-100">
          {TYPE_LABEL[mistake.question_type]}
        </Badge>
        <span className="text-[11px] text-slate-500">
          {mistake.term_name || "未命名术语"}
        </span>
        <span className="ml-auto flex items-center gap-1 text-[10px] text-slate-500">
          <CalendarClock className="size-3" aria-hidden="true" />
          {formatDateTime(mistake.next_review_at)}
        </span>
      </div>

      <h2 className="mt-3 text-base leading-7 font-medium text-white sm:text-lg">
        {mistake.question}
      </h2>
      <p className="mt-1 text-[11px] text-slate-500">
        {mistake.book_title} · {mistake.chapter_title}
      </p>

      <div className="mt-4 grid gap-2 text-xs leading-6">
        <div className="rounded-xl border border-white/[0.06] bg-black/15 px-3 py-2">
          <span className="text-slate-500">你的原答案：</span>
          <span className="text-slate-300">{mistake.user_answer || "（空）"}</span>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-black/15 px-3 py-2">
          <span className="text-slate-500">教材依据：</span>
          <span className="whitespace-pre-wrap text-slate-300">{mistake.reference_excerpt}</span>
        </div>
        {mistake.reason ? (
          <p className="px-1 text-slate-400">当时判分：{mistake.reason}</p>
        ) : null}
      </div>

      {mistake.missing_points.length > 0 ? (
        <div className="mt-3 rounded-xl border border-amber-300/15 bg-amber-300/[0.04] px-3 py-2.5 text-xs leading-6 text-amber-50/80">
          <p className="text-[10px] tracking-[0.14em] text-amber-200/65 uppercase">上轮漏点</p>
          <ul className="mt-1 space-y-1">
            {mistake.missing_points.map((point) => (
              <li key={point}>· {point}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {mistake.common_confusions.length > 0 ? (
        <p className="mt-3 text-xs leading-6 text-slate-400">
          易混提醒：{mistake.common_confusions[0]}
        </p>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-white/[0.06] pt-3">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onToggle}
          className="h-8 gap-1.5 rounded-full border-white/10 bg-white/[0.03] text-slate-300 hover:text-white"
        >
          <RotateCcw className="size-3" aria-hidden="true" />
          {expanded ? "收起重考" : "重考错题"}
          <ChevronDown
            className={cn("size-3 transition", expanded ? "rotate-180" : "")}
            aria-hidden="true"
          />
        </Button>
        <span className="text-[10px] text-slate-600">
          已复习 {mistake.review_count} 次 · 创建于 {formatDateTime(mistake.created_at)}
        </span>
      </div>

      {expanded ? (
        <div className="mt-4 rounded-2xl border border-white/[0.07] bg-black/15 p-3.5">
          {mistake.options.length > 0 ? (
            <div className="grid gap-2">
              {mistake.options.map((option, index) => (
                <button
                  key={`${mistake.id}-${index}`}
                  type="button"
                  disabled={submitting}
                  onClick={() => onAnswerChange(option)}
                  className={cn(
                    "flex w-full items-start gap-2.5 rounded-xl border px-3 py-2.5 text-left text-xs leading-6 transition",
                    answer === option
                      ? "border-cyan-300/30 bg-cyan-300/[0.08] text-cyan-50"
                      : "border-white/[0.07] bg-white/[0.02] text-slate-300 hover:border-white/[0.14]",
                  )}
                >
                  <span className="mt-0.5 font-mono text-[10px] text-slate-500">
                    {String.fromCharCode(65 + index)}
                  </span>
                  {option}
                </button>
              ))}
            </div>
          ) : (
            <textarea
              value={answer}
              onChange={(event) => onAnswerChange(event.target.value)}
              rows={4}
              disabled={submitting}
              placeholder="重新作答；系统会和知识库关键要点逐项对照。"
              className="w-full resize-y rounded-xl border border-white/[0.08] bg-black/20 px-3 py-2.5 text-xs leading-6 text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-300/30"
            />
          )}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button
              type="button"
              onClick={onSubmit}
              disabled={submitting || !answer.trim()}
              className="h-8 gap-1.5 rounded-full px-4 text-xs"
            >
              {submitting ? (
                <Loader2 className="size-3 animate-spin" aria-hidden="true" />
              ) : (
                <ClipboardCheck className="size-3" aria-hidden="true" />
              )}
              提交重考
            </Button>
            <HintBox hint={hint} loading={hintLoading} onLoad={onHint} />
          </div>
          {result?.grade ? <GradeInline grade={result.grade} /> : null}
          {result && !result.grade ? (
            <p className="mt-2 text-xs text-slate-400">
              已更新复习记录：{result.correct ? "通过" : "未通过"}。
            </p>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

export default function MistakesPage() {
  const [mistakes, setMistakes] = useState<Mistake[]>([]);
  const [dueMistakes, setDueMistakes] = useState<Mistake[]>([]);
  const [stats, setStats] = useState({ total: 0, due: 0, reviewing: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "due">("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [results, setResults] = useState<Record<string, MistakeReviewResult>>({});
  const [submittingId, setSubmittingId] = useState<string | null>(null);
  const [hints, setHints] = useState<Record<string, HintResult>>({});
  const [hintLoadingId, setHintLoadingId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [all, due] = await Promise.all([getMistakes(), getDueMistakes()]);
      setMistakes(all.mistakes ?? []);
      setDueMistakes(due.mistakes ?? []);
      setStats(all.stats ?? { total: all.count ?? 0, due: due.count ?? 0, reviewing: 0 });
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "错题本加载失败";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      await Promise.resolve();
      if (!cancelled) {
        await refresh();
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const dueIds = useMemo(() => new Set(dueMistakes.map((item) => item.id)), [dueMistakes]);
  const visible = filter === "due" ? dueMistakes : mistakes;

  function setAnswer(id: string, value: string) {
    setAnswers((current) => ({ ...current, [id]: value }));
  }

  function toggleExpanded(id: string) {
    setExpandedId((current) => (current === id ? null : id));
  }

  async function submitReview(mistake: Mistake) {
    const answer = answers[mistake.id]?.trim() ?? "";
    if (!answer) {
      toast.warning("请先重新作答。");
      return;
    }
    setSubmittingId(mistake.id);
    try {
      const response = await reviewMistake(mistake.id, answer);
      setResults((current) => ({ ...current, [mistake.id]: response }));
      if (response.correct) {
        toast.success("重考通过，复习间隔已推进。");
      } else {
        toast.error("仍未答对，已重新安排明日复习。");
      }
      setExpandedId(null);
      await refresh();
    } catch (reason) {
      toast.error(reason instanceof Error ? reason.message : "重考失败");
    } finally {
      setSubmittingId(null);
    }
  }

  async function loadHint(mistake: Mistake) {
    setHintLoadingId(mistake.id);
    try {
      const hint = await getHint({
        book_ids: [mistake.book_id],
        chapter_ids: [mistake.chapter_id],
        term_id: mistake.term_id,
        missing_points: mistake.missing_points,
      });
      setHints((current) => ({ ...current, [mistake.id]: hint }));
    } catch (reason) {
      toast.error(reason instanceof Error ? reason.message : "提示加载失败");
    } finally {
      setHintLoadingId(null);
    }
  }

  return (
    <div className="relative min-h-dvh overflow-x-hidden bg-[#070b14] text-slate-100">
      <div className="pointer-events-none fixed inset-0 z-0" aria-hidden="true">
        <div className="ambient-grid absolute inset-0 opacity-70" />
        <div className="absolute -left-44 top-[-15rem] size-[38rem] rounded-full bg-amber-500/[0.055] blur-[150px]" />
        <div className="absolute right-[-14rem] top-[20%] size-[34rem] rounded-full bg-violet-500/[0.08] blur-[150px]" />
      </div>

      <header className="relative z-20 border-b border-white/[0.06] bg-[#070b14]/65 backdrop-blur-2xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link
            href="/library"
            className="flex items-center gap-2 text-sm text-slate-400 transition hover:text-white"
          >
            <ArrowLeft className="size-4" aria-hidden="true" />
            返回范围选择
          </Link>
          <div className="flex items-center gap-1 sm:gap-2">
            <Button asChild variant="ghost" size="sm" className="text-slate-400 hover:text-white">
              <Link href="/history">
                <History className="size-3.5" aria-hidden="true" />
                <span className="hidden sm:inline">历史脉络</span>
              </Link>
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => void refresh()}
              disabled={loading}
              className="text-slate-400 hover:text-white"
            >
              {loading ? (
                <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <RefreshCw className="size-3.5" aria-hidden="true" />
              )}
              <span className="hidden sm:inline">刷新</span>
            </Button>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
        <section className="max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-200/15 bg-amber-300/[0.06] px-3 py-1 text-[11px] font-medium tracking-[0.18em] text-amber-100/80 uppercase">
            <ListChecks className="size-3" aria-hidden="true" />
            Mistake review
          </div>
          <h1 className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-white sm:text-5xl">
            错题本：把漏掉的要点补回来
          </h1>
          <p className="mt-3 text-sm leading-7 text-slate-400">
            错题按到期时间排序，复习间隔为 1、3、7、15 天。重考判分仍只依据教材摘要；知识库提示不参与判分。
          </p>
        </section>

        <section className="mt-8 grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-3.5">
            <p className="text-[10px] tracking-[0.16em] text-slate-500 uppercase">错题总数</p>
            <p className="mt-1 text-2xl font-semibold text-white">{stats.total}</p>
          </div>
          <div className="rounded-2xl border border-amber-300/15 bg-amber-300/[0.045] px-4 py-3.5">
            <p className="text-[10px] tracking-[0.16em] text-amber-200/60 uppercase">今日到期</p>
            <p className="mt-1 text-2xl font-semibold text-amber-50">{stats.due}</p>
          </div>
          <div className="rounded-2xl border border-cyan-300/15 bg-cyan-300/[0.045] px-4 py-3.5">
            <p className="text-[10px] tracking-[0.16em] text-cyan-200/60 uppercase">已复习过</p>
            <p className="mt-1 text-2xl font-semibold text-cyan-50">{stats.reviewing}</p>
          </div>
        </section>

        <div className="mt-7 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setFilter("all")}
            className={cn(
              "rounded-full border px-3.5 py-1.5 text-xs transition",
              filter === "all"
                ? "border-cyan-300/25 bg-cyan-300/10 text-cyan-100"
                : "border-white/[0.08] bg-white/[0.02] text-slate-500 hover:text-slate-200",
            )}
          >
            全部错题 {mistakes.length}
          </button>
          <button
            type="button"
            onClick={() => setFilter("due")}
            className={cn(
              "rounded-full border px-3.5 py-1.5 text-xs transition",
              filter === "due"
                ? "border-amber-300/25 bg-amber-300/10 text-amber-100"
                : "border-white/[0.08] bg-white/[0.02] text-slate-500 hover:text-slate-200",
            )}
          >
            今日到期 {dueMistakes.length}
          </button>
          <Button asChild variant="ghost" size="sm" className="ml-auto text-slate-400 hover:text-white">
            <Link href="/review">
              <Target className="size-3.5" aria-hidden="true" />
              继续考核
            </Link>
          </Button>
        </div>

        {error ? (
          <div className="mt-6 rounded-2xl border border-rose-300/20 bg-rose-300/[0.05] px-4 py-4 text-sm text-rose-100">
            {error}。请确认后端服务已启动。
          </div>
        ) : null}

        {loading ? (
          <div className="mt-6 flex items-center gap-3 rounded-2xl border border-white/[0.07] bg-white/[0.025] px-4 py-10 text-sm text-slate-400">
            <Loader2 className="size-4 animate-spin text-cyan-200" aria-hidden="true" />
            正在读取错题本……
          </div>
        ) : visible.length === 0 ? (
          <div className="mt-6 rounded-[1.75rem] border border-white/[0.08] bg-white/[0.03] px-6 py-14 text-center backdrop-blur-xl">
            {filter === "due" ? (
              <CalendarClock className="mx-auto size-8 text-slate-600" aria-hidden="true" />
            ) : (
              <Sparkles className="mx-auto size-8 text-cyan-200/60" aria-hidden="true" />
            )}
            <h2 className="mt-4 text-lg font-semibold text-white">
              {filter === "due" ? "今天没有到期错题" : "错题本还是空的"}
            </h2>
            <p className="mt-2 text-sm text-slate-400">
              {filter === "due"
                ? "可以切回全部错题，或继续完成一轮新的精准考核。"
                : "答错的题会自动进入这里，并按 1、3、7、15 天安排复习。"}
            </p>
            <Button asChild className="mt-5 rounded-full">
              <Link href="/review">
                <BookOpenCheck className="size-4" aria-hidden="true" />
                去考核
              </Link>
            </Button>
          </div>
        ) : (
          <section className="mt-6 grid gap-4">
            {visible.map((mistake) => (
              <MistakeCard
                key={mistake.id}
                mistake={mistake}
                due={dueIds.has(mistake.id)}
                expanded={expandedId === mistake.id}
                answer={answers[mistake.id] ?? ""}
                submitting={submittingId === mistake.id}
                result={results[mistake.id]}
                hint={hints[mistake.id]}
                hintLoading={hintLoadingId === mistake.id}
                onToggle={() => toggleExpanded(mistake.id)}
                onAnswerChange={(value) => setAnswer(mistake.id, value)}
                onSubmit={() => void submitReview(mistake)}
                onHint={() => void loadHint(mistake)}
              />
            ))}
          </section>
        )}

        {mistakes.length > 0 ? (
          <div className="mt-8 flex items-start gap-2 rounded-2xl border border-white/[0.06] bg-white/[0.02] px-4 py-3 text-[11px] leading-6 text-slate-500">
            <CircleAlert className="mt-1 size-3.5 shrink-0 text-slate-600" aria-hidden="true" />
            重考结果会更新间隔复习计划；错题本只记录判断与知识库依据，不会把联网案例写进判分原因。
          </div>
        ) : null}
      </main>
    </div>
  );
}
