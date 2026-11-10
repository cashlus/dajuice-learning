"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BookOpenCheck,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  ExternalLink,
  Flame,
  History,
  Lightbulb,
  ListChecks,
  Loader2,
  RefreshCw,
  Sparkles,
  Target,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  generateQuestions,
  getHint,
  getHotCase,
  gradeQuestion,
  readSelection,
  type GenerateResult,
  type GradeResult,
  type HintResult,
  type HotCaseResult,
  type QuestionType,
  type ReviewQuestion,
  type StoredScope,
} from "@/lib/library-api";
import { cn } from "@/lib/utils";

const QUESTION_TYPES: Array<{ type: QuestionType; label: string; note: string }> = [
  { type: "choice", label: "选择题", note: "辨析定义与易混概念" },
  { type: "short_answer", label: "简答题", note: "覆盖关键要点" },
  { type: "flashcard", label: "记忆卡", note: "主动回忆定义与特征" },
];

const TYPE_LABEL: Record<QuestionType, string> = {
  choice: "选择题",
  short_answer: "简答题",
  flashcard: "记忆卡",
};

function ScopeStrip({ scope }: { scope: StoredScope }) {
  return (
    <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] px-4 py-3 text-xs leading-6 text-slate-400">
      <div className="flex flex-wrap items-center gap-2 text-slate-300">
        <BookOpenCheck className="size-3.5 text-cyan-200" aria-hidden="true" />
        <span className="font-medium text-slate-200">当前考核范围</span>
        <Badge className="border-cyan-300/15 bg-cyan-300/[0.08] text-cyan-100">
          {scope.term_count} 个术语
        </Badge>
      </div>
      <p className="mt-2">{scope.summary || "已从预置知识库读取章节范围。"}</p>
    </div>
  );
}

function GradePanel({
  grade,
  hint,
  hintLoading,
  onHint,
}: {
  grade: GradeResult;
  hint?: HintResult;
  hintLoading: boolean;
  onHint: () => void;
}) {
  return (
    <div
      className={cn(
        "mt-5 rounded-2xl border p-4 sm:p-5",
        grade.correct
          ? "border-emerald-300/20 bg-emerald-300/[0.055]"
          : "border-rose-300/20 bg-rose-300/[0.045]",
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        {grade.correct ? (
          <CheckCircle2 className="size-4 text-emerald-300" aria-hidden="true" />
        ) : (
          <XCircle className="size-4 text-rose-300" aria-hidden="true" />
        )}
        <p className="text-sm font-semibold text-white">
          {grade.correct ? "回答正确" : "这次没有答对"}
        </p>
        <span className="ml-auto font-mono text-xs text-slate-400">
          {grade.score} / 100
        </span>
      </div>

      <div className="mt-4 grid gap-3">
        <section>
          <p className="text-[10px] tracking-[0.16em] text-slate-500 uppercase">
            判分依据 · 知识库原文摘要
          </p>
          <p className="mt-1.5 whitespace-pre-wrap text-sm leading-7 text-slate-200">
            {grade.reference_excerpt}
          </p>
        </section>

        <section>
          <p className="text-[10px] tracking-[0.16em] text-slate-500 uppercase">
            判分说明
          </p>
          <p className="mt-1.5 text-sm leading-7 text-slate-300">
            {grade.grading_reason}
          </p>
        </section>

        {grade.covered_points.length > 0 ? (
          <section>
            <p className="text-[10px] tracking-[0.16em] text-emerald-200/60 uppercase">
              已覆盖要点
            </p>
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {grade.covered_points.map((point) => (
                <li
                  key={point}
                  className="rounded-full border border-emerald-300/15 bg-emerald-300/[0.06] px-2.5 py-1 text-[11px] text-emerald-100/85"
                >
                  {point}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {grade.missing_points.length > 0 ? (
          <section>
            <p className="text-[10px] tracking-[0.16em] text-amber-200/60 uppercase">
              漏掉的要点
            </p>
            <ul className="mt-2 grid gap-1.5 text-sm leading-6 text-amber-50/80">
              {grade.missing_points.map((point) => (
                <li key={point} className="flex gap-2">
                  <span className="mt-2 size-1 shrink-0 rounded-full bg-amber-300/70" />
                  {point}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {grade.common_confusion ? (
          <section className="rounded-xl border border-amber-300/15 bg-amber-300/[0.045] px-3.5 py-3">
            <p className="text-[10px] tracking-[0.16em] text-amber-200/65 uppercase">
              易混淆概念
            </p>
            <p className="mt-1.5 text-sm leading-6 text-amber-50/85">
              {grade.common_confusion}
            </p>
          </section>
        ) : null}

        {!grade.correct ? (
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
            <span>本题已自动加入错题本。</span>
            {grade.recorded_mistake_id ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onHint}
                disabled={hintLoading}
                className="h-8 gap-1.5 rounded-full border-white/10 bg-white/[0.03] text-slate-300 hover:text-white"
              >
                {hintLoading ? (
                  <Loader2 className="size-3 animate-spin" aria-hidden="true" />
                ) : (
                  <Lightbulb className="size-3" aria-hidden="true" />
                )}
                知识库提示
              </Button>
            ) : null}
          </div>
        ) : null}

        {hint ? (
          <section className="rounded-xl border border-cyan-300/15 bg-cyan-300/[0.045] px-3.5 py-3">
            <p className="flex items-center gap-1.5 text-[10px] tracking-[0.16em] text-cyan-200/70 uppercase">
              <Lightbulb className="size-3" aria-hidden="true" />
              基于知识库的重点难点提示
            </p>
            <p className="mt-2 text-sm leading-7 text-slate-200">
              {hint.definition}
            </p>
            <p className="mt-2 text-xs leading-6 text-cyan-50/75">
              {hint.suggested_review}
            </p>
            {hint.common_confusion ? (
              <p className="mt-2 text-xs leading-6 text-amber-100/75">
                易混：{hint.common_confusion}
              </p>
            ) : null}
          </section>
        ) : null}
      </div>
    </div>
  );
}

function HotCasePanel({ result }: { result: HotCaseResult }) {
  return (
    <section className="mt-5 overflow-hidden rounded-2xl border border-amber-300/25 bg-amber-300/[0.055]">
      <div className="flex flex-wrap items-center gap-2 border-b border-amber-300/15 px-4 py-3">
        <Flame className="size-4 text-amber-300" aria-hidden="true" />
        <p className="text-sm font-semibold text-amber-50">AI 联网外推案例</p>
        <Badge className="border-amber-300/25 bg-amber-300/10 text-amber-100">
          AI 联网外推，未核验，不参与判分
        </Badge>
        {result.cached ? (
          <span className="text-[10px] text-amber-100/50">缓存结果</span>
        ) : null}
      </div>
      <div className="px-4 py-4 text-sm leading-7 text-amber-50/85">
        {result.case_summary ? (
          <p className="whitespace-pre-wrap">{result.case_summary}</p>
        ) : (
          <p>{result.notice || "暂时没有检索到可用案例。"}</p>
        )}
        <p className="mt-3 rounded-xl border border-amber-300/15 bg-black/15 px-3 py-2 text-[11px] leading-5 text-amber-100/70">
          这不是教材原文，也不能作为判分依据。请优先依据上方教材摘要完成作答。
          {result.notice ? ` ${result.notice}` : ""}
        </p>
        {result.source_urls.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {result.source_urls.map((url, index) => (
              <a
                key={url}
                href={url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex max-w-full items-center gap-1 rounded-full border border-amber-300/15 bg-amber-300/[0.06] px-2.5 py-1 text-[10px] text-amber-100/70 transition hover:text-amber-50"
              >
                来源 {index + 1}
                <ExternalLink className="size-2.5 shrink-0" aria-hidden="true" />
              </a>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}

export default function ReviewPage() {
  const [selection, setSelection] = useState<StoredScope | null>(null);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [selectedTypes, setSelectedTypes] = useState<QuestionType[]>([
    "choice",
    "short_answer",
  ]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [grades, setGrades] = useState<Record<string, GradeResult>>({});
  const [submitting, setSubmitting] = useState(false);
  const [hints, setHints] = useState<Record<string, HintResult>>({});
  const [hintLoading, setHintLoading] = useState(false);
  const [hotCases, setHotCases] = useState<Record<string, HotCaseResult>>({});
  const [hotLoading, setHotLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      await Promise.resolve();
      if (cancelled) return;

      const stored = readSelection();
      setSelection(stored);
      if (!stored) {
        setLoading(false);
        return;
      }

      try {
        const value = await generateQuestions(
          stored.book_ids,
          stored.chapter_ids,
          ["choice", "short_answer"],
          6,
        );
        if (!cancelled) {
          setResult(value);
          setCurrentIndex(0);
        }
      } catch (reason: unknown) {
        const message = reason instanceof Error ? reason.message : "题目生成失败";
        if (!cancelled) {
          setError(message);
          toast.error(message);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const questions = useMemo(() => result?.questions ?? [], [result]);
  const currentQuestion = questions[currentIndex] as ReviewQuestion | undefined;
  const currentAnswer = currentQuestion ? answers[currentQuestion.question_id] ?? "" : "";
  const currentGrade = currentQuestion ? grades[currentQuestion.question_id] : undefined;
  const currentHint = currentQuestion ? hints[currentQuestion.question_id] : undefined;
  const currentHotCase = currentQuestion ? hotCases[currentQuestion.term_id] : undefined;
  const answeredCount = useMemo(
    () => questions.filter((question) => grades[question.question_id]).length,
    [grades, questions],
  );

  function toggleType(type: QuestionType) {
    setSelectedTypes((current) => {
      if (current.includes(type)) {
        if (current.length === 1) {
          toast.warning("至少保留一种题型。");
          return current;
        }
        return current.filter((item) => item !== type);
      }
      return [...current, type];
    });
  }

  async function regenerate() {
    if (!selection) return;
    setGenerating(true);
    setError(null);
    try {
      const value = await generateQuestions(
        selection.book_ids,
        selection.chapter_ids,
        selectedTypes,
        6,
      );
      setResult(value);
      setAnswers({});
      setGrades({});
      setHints({});
      setHotCases({});
      setCurrentIndex(0);
      toast.success(`已生成 ${value.question_count} 道题。`);
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "题目生成失败";
      setError(message);
      toast.error(message);
    } finally {
      setGenerating(false);
    }
  }

  async function submitAnswer() {
    if (!currentQuestion || !currentAnswer.trim()) {
      toast.warning("请先写下或选择你的答案。");
      return;
    }
    setSubmitting(true);
    try {
      const grade = await gradeQuestion(currentQuestion.question_id, currentAnswer);
      setGrades((current) => ({ ...current, [currentQuestion.question_id]: grade }));
      if (grade.correct) {
        toast.success("回答正确。");
      } else {
        toast.error("已记录到错题本，可对照教材依据再试一次。");
      }
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "判分失败";
      toast.error(message);
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  async function loadHint() {
    if (!selection || !currentQuestion || !currentGrade) return;
    setHintLoading(true);
    try {
      const hint = await getHint({
        book_ids: selection.book_ids,
        chapter_ids: selection.chapter_ids,
        term_id: currentQuestion.term_id,
        missing_points: currentGrade.missing_points,
      });
      setHints((current) => ({ ...current, [currentQuestion.question_id]: hint }));
    } catch (reason) {
      toast.error(reason instanceof Error ? reason.message : "提示加载失败");
    } finally {
      setHintLoading(false);
    }
  }

  async function loadHotCase() {
    if (!currentQuestion) return;
    setHotLoading(true);
    try {
      const value = await getHotCase(currentQuestion.term_id);
      setHotCases((current) => ({ ...current, [currentQuestion.term_id]: value }));
      if (!value.search_used) {
        toast.info(value.notice || "暂时没有联网案例，已保留知识库判分。");
      }
    } catch (reason) {
      toast.error(reason instanceof Error ? reason.message : "热点案例加载失败");
    } finally {
      setHotLoading(false);
    }
  }

  return (
    <div className="relative min-h-dvh overflow-x-hidden bg-[#070b14] text-slate-100">
      <div className="pointer-events-none fixed inset-0 z-0" aria-hidden="true">
        <div className="ambient-grid absolute inset-0 opacity-70" />
        <div className="absolute -left-40 top-[-16rem] size-[36rem] rounded-full bg-cyan-500/[0.08] blur-[140px]" />
        <div className="absolute right-[-12rem] top-[22%] size-[32rem] rounded-full bg-violet-500/[0.09] blur-[150px]" />
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
            <Button asChild variant="ghost" size="sm" className="text-slate-400 hover:text-white">
              <Link href="/mistakes">
                <ListChecks className="size-3.5" aria-hidden="true" />
                <span className="hidden sm:inline">错题本</span>
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
        <section className="max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-cyan-200/15 bg-cyan-300/[0.06] px-3 py-1 text-[11px] font-medium tracking-[0.18em] text-cyan-100/80 uppercase">
            <Target className="size-3" aria-hidden="true" />
            Scope-bound review
          </div>
          <h1 className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-white sm:text-5xl">
            精准考核：只考你选中的范围
          </h1>
          <p className="mt-3 text-sm leading-7 text-slate-400">
            题目、判分依据和错题记录都来自管理员预置知识库。AI 联网案例只用于联想，不参与判分。
          </p>
        </section>

        {!selection && !loading ? (
          <section className="mt-10 rounded-[1.75rem] border border-white/[0.08] bg-white/[0.035] p-8 text-center backdrop-blur-2xl">
            <CircleAlert className="mx-auto size-8 text-amber-300" aria-hidden="true" />
            <h2 className="mt-4 text-xl font-semibold text-white">还没有选择考核范围</h2>
            <p className="mx-auto mt-2 max-w-lg text-sm leading-7 text-slate-400">
              先到精准考核范围页勾选教材与章节，系统才能生成范围外零题目的考核。
            </p>
            <Button asChild className="mt-6 rounded-full">
              <Link href="/library">
                去选择范围
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
            </Button>
          </section>
        ) : null}

        {selection ? (
          <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_318px] lg:items-start">
            <section className="min-w-0 rounded-[1.75rem] border border-white/[0.09] bg-white/[0.035] p-4 shadow-[0_28px_90px_rgba(2,6,23,0.4)] backdrop-blur-2xl sm:p-6">
              <ScopeStrip scope={selection} />

              <div className="mt-5 flex flex-wrap items-center gap-2">
                <span className="text-[11px] text-slate-500">题型</span>
                {QUESTION_TYPES.map((item) => {
                  const active = selectedTypes.includes(item.type);
                  return (
                    <button
                      key={item.type}
                      type="button"
                      onClick={() => toggleType(item.type)}
                      className={cn(
                        "rounded-full border px-3 py-1.5 text-[11px] transition",
                        active
                          ? "border-cyan-300/25 bg-cyan-300/10 text-cyan-100"
                          : "border-white/[0.08] bg-white/[0.02] text-slate-500 hover:text-slate-200",
                      )}
                      title={item.note}
                    >
                      {item.label}
                    </button>
                  );
                })}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={regenerate}
                  disabled={generating || loading}
                  className="ml-auto h-8 gap-1.5 rounded-full border-white/10 bg-white/[0.03] text-slate-300 hover:text-white"
                >
                  {generating ? (
                    <Loader2 className="size-3 animate-spin" aria-hidden="true" />
                  ) : (
                    <RefreshCw className="size-3" aria-hidden="true" />
                  )}
                  重新出题
                </Button>
              </div>

              {loading ? (
                <div className="mt-6 flex items-center gap-3 rounded-2xl border border-white/[0.07] bg-black/15 px-4 py-8 text-sm text-slate-400">
                  <Loader2 className="size-4 animate-spin text-cyan-200" aria-hidden="true" />
                  正在生成考核题……
                </div>
              ) : null}

              {error && !currentQuestion ? (
                <div className="mt-6 rounded-2xl border border-rose-300/20 bg-rose-300/[0.05] px-4 py-4 text-sm leading-6 text-rose-100">
                  {error}
                </div>
              ) : null}

              {currentQuestion ? (
                <div className="mt-6">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge className="border-violet-300/15 bg-violet-300/[0.08] text-violet-100">
                      {TYPE_LABEL[currentQuestion.type]}
                    </Badge>
                    <span className="text-[11px] text-slate-500">
                      {currentQuestion.book_title} · {currentQuestion.chapter_title}
                    </span>
                    <span className="ml-auto font-mono text-[11px] text-slate-500">
                      {currentIndex + 1} / {questions.length}
                    </span>
                  </div>

                  <h2 className="mt-4 text-xl leading-8 font-semibold text-white sm:text-2xl">
                    {currentQuestion.question}
                  </h2>

                  {currentQuestion.type === "choice" ? (
                    <div className="mt-5 grid gap-2">
                      {currentQuestion.options.map((option, index) => {
                        const selected = currentAnswer === option;
                        return (
                          <button
                            key={`${currentQuestion.question_id}-${index}`}
                            type="button"
                            disabled={Boolean(currentGrade)}
                            onClick={() =>
                              setAnswers((current) => ({
                                ...current,
                                [currentQuestion.question_id]: option,
                              }))
                            }
                            className={cn(
                              "flex w-full items-start gap-3 rounded-2xl border px-4 py-3.5 text-left text-sm leading-6 transition",
                              selected
                                ? "border-cyan-300/30 bg-cyan-300/[0.08] text-cyan-50"
                                : "border-white/[0.07] bg-white/[0.02] text-slate-300 hover:border-white/[0.15] hover:bg-white/[0.04]",
                              currentGrade ? "cursor-default opacity-80" : "",
                            )}
                          >
                            <span
                              className={cn(
                                "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border font-mono text-[10px]",
                                selected
                                  ? "border-cyan-300/60 bg-cyan-300 text-slate-950"
                                  : "border-white/15 text-slate-500",
                              )}
                            >
                              {String.fromCharCode(65 + index)}
                            </span>
                            <span>{option}</span>
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <textarea
                      value={currentAnswer}
                      onChange={(event) =>
                        setAnswers((current) => ({
                          ...current,
                          [currentQuestion.question_id]: event.target.value,
                        }))
                      }
                      disabled={Boolean(currentGrade)}
                      rows={6}
                      placeholder="用自己的话完整作答；系统会按知识库关键要点判断覆盖情况。"
                      className="mt-5 w-full resize-y rounded-2xl border border-white/[0.09] bg-black/20 px-4 py-3 text-sm leading-7 text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-300/30 focus:ring-2 focus:ring-cyan-300/10 disabled:opacity-70"
                    />
                  )}

                  {!currentGrade ? (
                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      <Button
                        type="button"
                        onClick={submitAnswer}
                        disabled={submitting || !currentAnswer.trim()}
                        className="h-10 gap-2 rounded-xl border border-cyan-200/20 bg-gradient-to-r from-cyan-300 to-sky-400 px-5 text-slate-950 hover:brightness-110"
                      >
                        {submitting ? (
                          <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                        ) : (
                          <Sparkles className="size-4" aria-hidden="true" />
                        )}
                        提交判分
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={loadHotCase}
                        disabled={hotLoading}
                        className="h-10 gap-2 rounded-xl border-amber-300/20 bg-amber-300/[0.04] text-amber-100/80 hover:bg-amber-300/[0.08] hover:text-amber-50"
                      >
                        {hotLoading ? (
                          <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                        ) : (
                          <Flame className="size-4" aria-hidden="true" />
                        )}
                        AI 时事案例
                      </Button>
                    </div>
                  ) : (
                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        onClick={loadHotCase}
                        disabled={hotLoading}
                        className="h-9 gap-2 rounded-xl border-amber-300/20 bg-amber-300/[0.04] text-amber-100/80 hover:bg-amber-300/[0.08] hover:text-amber-50"
                      >
                        {hotLoading ? (
                          <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
                        ) : (
                          <Flame className="size-3.5" aria-hidden="true" />
                        )}
                        AI 时事案例
                      </Button>
                    </div>
                  )}

                  {currentGrade ? (
                    <GradePanel
                      grade={currentGrade}
                      hint={currentHint}
                      hintLoading={hintLoading}
                      onHint={loadHint}
                    />
                  ) : null}

                  {currentHotCase ? <HotCasePanel result={currentHotCase} /> : null}

                  <div className="mt-6 flex items-center justify-between border-t border-white/[0.06] pt-4">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={currentIndex === 0}
                      onClick={() => setCurrentIndex((index) => Math.max(0, index - 1))}
                      className="gap-1.5 text-slate-400 hover:text-white"
                    >
                      <ChevronLeft className="size-4" aria-hidden="true" />
                      上一题
                    </Button>
                    <span className="text-[11px] text-slate-500">
                      已完成 {answeredCount} / {questions.length}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={currentIndex >= questions.length - 1}
                      onClick={() =>
                        setCurrentIndex((index) => Math.min(questions.length - 1, index + 1))
                      }
                      className="gap-1.5 text-slate-400 hover:text-white"
                    >
                      下一题
                      <ChevronRight className="size-4" aria-hidden="true" />
                    </Button>
                  </div>
                </div>
              ) : null}
            </section>

            <aside className="grid gap-4 lg:sticky lg:top-24">
              <div className="rounded-[1.75rem] border border-white/[0.09] bg-gradient-to-b from-white/[0.06] to-white/[0.025] p-5 backdrop-blur-2xl">
                <div className="flex items-center gap-2 text-sm font-semibold text-white">
                  <Target className="size-4 text-cyan-200" aria-hidden="true" />
                  本轮考核
                </div>
                <div className="mt-4 grid grid-cols-2 gap-2">
                  <div className="rounded-xl border border-white/[0.07] bg-black/15 px-2 py-3 text-center">
                    <p className="text-xl font-semibold text-white">{questions.length}</p>
                    <p className="mt-1 text-[10px] text-slate-500">题目</p>
                  </div>
                  <div className="rounded-xl border border-white/[0.07] bg-black/15 px-2 py-3 text-center">
                    <p className="text-xl font-semibold text-white">{answeredCount}</p>
                    <p className="mt-1 text-[10px] text-slate-500">已判分</p>
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {questions.map((question, index) => {
                    const grade = grades[question.question_id];
                    return (
                      <button
                        key={question.question_id}
                        type="button"
                        onClick={() => setCurrentIndex(index)}
                        className={cn(
                          "flex size-7 items-center justify-center rounded-lg border font-mono text-[10px] transition",
                          index === currentIndex
                            ? "border-cyan-300/40 bg-cyan-300/15 text-cyan-50"
                            : grade
                              ? grade.correct
                                ? "border-emerald-300/20 bg-emerald-300/[0.07] text-emerald-100"
                                : "border-rose-300/20 bg-rose-300/[0.07] text-rose-100"
                              : "border-white/[0.08] bg-white/[0.02] text-slate-500 hover:text-slate-200",
                        )}
                      >
                        {index + 1}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 text-[11px] leading-6 text-slate-500">
                <p className="flex items-center gap-1.5 text-slate-300">
                  <BookOpenCheck className="size-3.5 text-cyan-200/80" aria-hidden="true" />
                  判分规则
                </p>
                <p className="mt-2">
                  题目只从已选章节的术语生成；判分结果附带教材定义与关键要点。AI 联网案例被强制隔离在判分链路之外。
                </p>
              </div>
            </aside>
          </div>
        ) : null}
      </main>
    </div>
  );
}
