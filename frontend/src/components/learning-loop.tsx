"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  BrainCircuit,
  CircleAlert,
  BookOpen,
  BookOpenCheck,
  Loader2,
  RotateCcw,
  Send,
  Sparkles,
  WifiOff,
  X,
} from "lucide-react";
import { toast } from "sonner";

import {
  ChatMessage,
  type ChatMessageData,
} from "@/components/chat/chat-message";
import { ProgressPanel } from "@/components/progress/progress-panel";
import { DaJuiceLogo } from "@/components/y2k/dajuice-logo";
import { Y2KBackground } from "@/components/y2k/y2k-background";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ApiError,
  diagnose,
  getReadableError,
  resetSession,
  type LearningStatus,
} from "@/lib/api";
import { CONCEPT_NAME, CONCEPT_NAME_EN } from "@/lib/concept";
import { STATUS_PRESENTATION } from "@/lib/status";
import { cn } from "@/lib/utils";

const SESSION_STORAGE_KEY = "agenda-setting:v3:session-id";

function createId(prefix: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function getOrCreateSessionId(): string {
  try {
    const existing = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (existing) {
      return existing;
    }

    const sessionId = createId("session");
    window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
    return sessionId;
  } catch {
    return createId("session");
  }
}

function createInitialMessages(termName: string): ChatMessageData[] {
  return [
    {
      id: "welcome",
      role: "assistant",
      content:
        `你好，我是你的概念诊断助教。请先用你自己的话解释「${termName}」——不必背定义，我会根据你的回答逐项检查关键要素。`,
      animate: false,
    },
  ];
}

interface LearningLoopProps {
  termName?: string;
  termId?: string;
  bookId?: string;
  compact?: boolean;
}

export function LearningLoop({
  termName = CONCEPT_NAME,
  termId,
  bookId = "agenda-setting",
  compact = false,
}: LearningLoopProps) {
  const [messages, setMessages] = useState<ChatMessageData[]>(
    () => createInitialMessages(termName),
  );
  const [claim, setClaim] = useState("");
  const [status, setStatus] = useState<LearningStatus | null>(null);
  const [missingElements, setMissingElements] = useState<string[]>([]);
  const [hasDiagnosed, setHasDiagnosed] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [inlineError, setInlineError] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);
  const sessionIdRef = useRef<string | null>(null);

  const scrollToLatest = useCallback(
    (behavior: ScrollBehavior = "smooth", force = false) => {
      const viewport = viewportRef.current;
      if (!viewport) {
        return;
      }

      if (force) {
        stickToBottomRef.current = true;
      }

      if (!stickToBottomRef.current) {
        return;
      }

      requestAnimationFrame(() => {
        viewport.scrollTo({
          top: viewport.scrollHeight,
          behavior,
        });
      });
    },
    [],
  );

  useEffect(() => {
    scrollToLatest("smooth", true);
  }, [isSubmitting, messages.length, scrollToLatest]);

  const handleViewportScroll = useCallback(() => {
    const viewport = viewportRef.current;
    if (!viewport) {
      return;
    }

    stickToBottomRef.current =
      viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight < 140;
  }, []);

  const handleTypewriterReveal = useCallback(() => {
    scrollToLatest("auto", false);
  }, [scrollToLatest]);

  const focusInput = useCallback(() => {
    requestAnimationFrame(() => inputRef.current?.focus());
  }, []);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const answer = claim.trim();
    if (!answer) {
      toast.warning("先写下你的理解，再提交诊断。");
      focusInput();
      return;
    }

    if (isSubmitting || status === "PASS") {
      return;
    }

    let activeSessionId = sessionIdRef.current;
    if (!activeSessionId) {
      activeSessionId = getOrCreateSessionId();
      sessionIdRef.current = activeSessionId;
    }

    setClaim("");
    setInlineError(null);
    stickToBottomRef.current = true;
    setMessages((current) => [
      ...current,
      {
        id: createId("user"),
        role: "user",
        content: answer,
        animate: false,
      },
    ]);
    setIsSubmitting(true);

    try {
      const result = await diagnose(answer, activeSessionId);
      const searchNotice =
        result.search_notice ||
        (result.search_used
          ? "本轮参考了联网检索结果，请留意信息的时效与来源。"
          : undefined);

      setStatus(result.status);
      setMissingElements(result.missing_elements);
      setHasDiagnosed(true);
      stickToBottomRef.current = true;
      setMessages((current) => [
        ...current,
        {
          id: createId("assistant"),
          role: "assistant",
          content: result.feedback,
          animate: true,
          status: result.status,
          searchNotice,
        },
      ]);

      if (result.status === "PASS") {
        toast.success("这一题通过了", {
          description: "五个关键要素已经完整覆盖。",
        });
      } else if (result.status === "NEED_RECONFIRM") {
        toast.warning("先确认一下作答概念", {
          description: "这句话可能落在另一个概念上，看看助教怎么说。",
        });
      }
    } catch (error) {
      const message = getReadableError(error);
      const isTransportError =
        error instanceof ApiError &&
        (error.code === "NETWORK" || error.code === "TIMEOUT");

      setInlineError(message);
      setClaim(answer);
      toast.error(
        isTransportError
          ? "网络开小差了，请检查后端服务"
          : "诊断没有完成",
        {
          description: message,
          duration: 9_000,
        },
      );
    } finally {
      setIsSubmitting(false);
      focusInput();
    }
  };

  const handleReset = async () => {
    if (isSubmitting || isResetting) {
      return;
    }

    setIsResetting(true);
    setInlineError(null);

    try {
      let activeSessionId = sessionIdRef.current;
      if (!activeSessionId) {
        activeSessionId = getOrCreateSessionId();
        sessionIdRef.current = activeSessionId;
      }

      await resetSession(activeSessionId);
      setMessages(createInitialMessages(termName));
      setClaim("");
      setStatus(null);
      setMissingElements([]);
      setHasDiagnosed(false);
      stickToBottomRef.current = true;
      toast.success("学习进度已重置", {
        description: `可以重新解释「${termName}」了。`,
      });
      focusInput();
    } catch (error) {
      const message = getReadableError(error);
      setInlineError(message);
      toast.error("重置没有完成", {
        description: message,
        duration: 9_000,
      });
    } finally {
      setIsResetting(false);
    }
  };

  const statusMeta = status ? STATUS_PRESENTATION[status] : null;
  const isPassed = status === "PASS";
  const isSubmitDisabled =
    isSubmitting || isPassed || claim.trim().length === 0;

  return (
    <div
      className={cn(
        "y2k-page relative flex min-h-dvh flex-col overflow-x-hidden text-slate-100",
        compact && "practice-shell",
      )}
      data-term-id={termId}
    >
      <Y2KBackground />

      <header className="relative z-20 shrink-0 border-b border-fuchsia-300/15 bg-[#0a0610]/75 backdrop-blur-2xl">
        <div className={cn("mx-auto flex h-16 w-full items-center justify-between gap-3 px-4 sm:px-6", compact ? "max-w-[1280px]" : "max-w-[1480px]")}>
          <div className="flex min-w-0 items-center gap-3">
            {compact ? (
              <Button
                asChild
                variant="outline"
                size="sm"
                className="h-9 shrink-0 gap-1.5 rounded-lg border-fuchsia-300/25 bg-fuchsia-300/[0.06] px-2.5 text-fuchsia-100 hover:border-cyan-300/40 hover:bg-cyan-300/[0.08] hover:text-white"
              >
                <Link href={`/subject/${encodeURIComponent(bookId)}`} aria-label="返回科目概念墙">
                  <ArrowLeft className="size-4" aria-hidden="true" />
                  <span className="hidden sm:inline">返回科目</span>
                </Link>
              </Button>
            ) : (
              <div className="relative flex size-10 shrink-0 items-center justify-center rounded-2xl border border-cyan-300/20 bg-gradient-to-br from-cyan-400/20 via-sky-400/10 to-violet-500/20 text-cyan-200 shadow-lg shadow-cyan-500/10">
                <BrainCircuit className="size-5" aria-hidden="true" />
                <span className="absolute -right-0.5 -top-0.5 size-2 rounded-full border border-[#070b14] bg-cyan-300" />
              </div>
            )}
            {compact ? <DaJuiceLogo compact className="hidden sm:inline-flex" /> : null}
            <div className="min-w-0">
              {compact ? (
                <>
                  <h1 className="truncate text-base font-black tracking-tight text-white sm:text-lg">{termName}</h1>
                  <p className="mt-0.5 truncate font-terminal text-sm tracking-[0.18em] text-fuchsia-200/65">
                    FOCUS MODE · LEARNING LOOP V3
                  </p>
                </>
              ) : (
                <>
                  <h1 className="truncate text-sm font-semibold tracking-tight text-slate-100 sm:text-base">
                    新媒体广告前沿
                    <span className="mx-2 text-slate-600">/</span>
                    概念学习闭环
                  </h1>
                  <p className="mt-0.5 truncate text-[11px] tracking-wide text-slate-500">
                    {CONCEPT_NAME_EN} · Learning Loop V3
                  </p>
                </>
              )}
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2.5">
            {!compact ? (
              <div className="hidden items-center gap-2 rounded-full border border-white/[0.07] bg-white/[0.035] px-3 py-1.5 text-[11px] text-slate-400 md:flex">
                <span className="size-1.5 animate-pulse rounded-full bg-cyan-300" />
                逐点诊断引擎在线
              </div>
            ) : (
              <span
                className={cn(
                  "hidden items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-medium sm:inline-flex",
                  statusMeta
                    ? statusMeta.tone
                    : "border-white/10 bg-white/[0.04] text-slate-400",
                )}
              >
                <span className={cn("size-1.5 rounded-full", statusMeta ? statusMeta.dot : "bg-slate-500")} aria-hidden="true" />
                {statusMeta?.label ?? "等待作答"}
              </span>
            )}
            <Button
              asChild
              variant="outline"
              size="sm"
              className={cn(
                "h-9 gap-2 rounded-xl border-white/10 bg-white/[0.035] px-3 text-slate-200 hover:border-cyan-200/30 hover:bg-cyan-300/[0.07] hover:text-white",
                compact && "hidden",
              )}
            >
              <Link href="/library" aria-label="进入精准考核">
                <BookOpenCheck className="size-3.5" aria-hidden="true" />
                <span className="hidden whitespace-nowrap sm:inline">📚 精准考核</span>
                <span className="whitespace-nowrap sm:hidden">考核</span>
              </Link>
            </Button>
            <Button
              asChild
              variant="outline"
              size="sm"
              className={cn(
                "h-9 gap-2 rounded-xl border-cyan-300/20 bg-gradient-to-r from-cyan-300/10 via-sky-300/[0.07] to-violet-300/10 px-3 text-cyan-50 shadow-[0_0_24px_rgba(34,211,238,0.08)] hover:border-cyan-200/35 hover:from-cyan-300/15 hover:to-violet-300/15 hover:text-white",
                compact && "hidden",
              )}
            >
              <Link href="/history" aria-label="探索概念发展史">
                <BookOpen className="size-3.5" aria-hidden="true" />
                <span className="hidden whitespace-nowrap sm:inline">
                  📖 探索概念发展史
                </span>
                <span className="whitespace-nowrap sm:hidden">发展史</span>
              </Link>
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleReset}
              disabled={isResetting || isSubmitting}
              className="h-9 gap-2 rounded-xl border-white/10 bg-white/[0.035] px-3 text-slate-300 hover:border-white/[0.16] hover:bg-white/[0.065] hover:text-white"
            >
              {isResetting ? (
                <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <RotateCcw className="size-3.5" aria-hidden="true" />
              )}
              <span>重置概念</span>
            </Button>
          </div>
        </div>
      </header>

      <main className={cn("relative z-10 mx-auto flex w-full flex-1 flex-col gap-4 px-3 py-4 sm:px-5 lg:h-[calc(100dvh-4rem)] lg:flex-row lg:gap-5 lg:overflow-hidden lg:py-5", compact ? "max-w-[1280px] lg:px-5" : "max-w-[1480px] lg:px-6")}>
        <section className="y2k-panel flex min-h-[72dvh] min-w-0 flex-1 flex-col overflow-hidden rounded-3xl lg:min-h-0">
          <div className="shrink-0 border-b border-fuchsia-300/10 px-4 py-4 sm:px-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-medium tracking-wide text-slate-100">
                    诊断对话
                  </h2>
                  <span
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-medium",
                      statusMeta
                        ? statusMeta.tone
                        : "border-white/[0.08] bg-white/[0.035] text-slate-500",
                    )}
                  >
                    <span
                      className={cn(
                        "size-1.5 rounded-full",
                        statusMeta ? statusMeta.dot : "bg-slate-600",
                      )}
                      aria-hidden="true"
                    />
                    {statusMeta?.label ?? "等待作答"}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  每一轮只诊断当前回答，历史对话不会重复塞进模型上下文。
                </p>
              </div>
              <Sparkles
                className="mt-0.5 size-4 shrink-0 text-cyan-300/55"
                aria-hidden="true"
              />
            </div>

            <div className="mt-4 overflow-hidden rounded-2xl border border-cyan-300/[0.13] bg-gradient-to-br from-cyan-300/[0.075] via-sky-400/[0.04] to-violet-400/[0.055] px-4 py-3.5">
              <div className="flex items-center gap-2 text-[10px] font-medium tracking-[0.16em] text-cyan-200/65 uppercase">
                <span className="flex size-5 items-center justify-center rounded-md border border-cyan-300/15 bg-cyan-300/10">
                  <Sparkles className="size-2.5" aria-hidden="true" />
                </span>
                请用你自己的话解释
              </div>
              <p className="mt-1.5 text-lg font-semibold tracking-tight text-white">
                {termName}
                <span className="ml-2 text-xs font-normal tracking-wide text-slate-500">
                  {termName === CONCEPT_NAME ? CONCEPT_NAME_EN : "FOCUS CONCEPT"}
                </span>
              </p>
              <p className="mt-1 text-xs leading-5 text-slate-400">
                不用背定义。先说你的理解，系统会逐点检查关键要素是否覆盖。
              </p>
            </div>
          </div>

          <div
            ref={viewportRef}
            onScroll={handleViewportScroll}
            className="study-scrollbar min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-5 sm:px-5"
            aria-live="polite"
          >
            <div className="flex flex-col gap-5">
              {messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  onReveal={
                    message.animate ? handleTypewriterReveal : undefined
                  }
                />
              ))}

              {isSubmitting ? (
                <div className="message-enter flex items-start gap-3">
                  <div className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-2xl border border-cyan-300/20 bg-gradient-to-br from-cyan-400/20 to-violet-500/20 text-cyan-200">
                    <Sparkles className="size-4" aria-hidden="true" />
                  </div>
                  <div className="flex items-center gap-3 rounded-2xl rounded-tl-md border border-white/[0.08] bg-white/[0.055] px-4 py-3 text-sm text-slate-400 backdrop-blur-xl">
                    <span>正在逐点诊断</span>
                    <span className="flex items-center gap-1" aria-hidden="true">
                      <span className="typing-dot" />
                      <span className="typing-dot [animation-delay:140ms]" />
                      <span className="typing-dot [animation-delay:280ms]" />
                    </span>
                  </div>
                </div>
              ) : null}
              <div className="h-px w-full" />
            </div>
          </div>

          {inlineError ? (
            <div className="mx-3 mb-3 flex items-start gap-2.5 rounded-2xl border border-rose-300/15 bg-rose-400/[0.065] px-3.5 py-3 text-xs leading-5 text-rose-100/80 sm:mx-4">
              <WifiOff
                className="mt-0.5 size-4 shrink-0 text-rose-300"
                aria-hidden="true"
              />
              <p className="min-w-0 flex-1 break-words">{inlineError}</p>
              <button
                type="button"
                onClick={() => setInlineError(null)}
                className="mt-0.5 rounded-md p-0.5 text-rose-200/60 transition-colors hover:bg-white/[0.05] hover:text-rose-100"
                aria-label="关闭错误提示"
              >
                <X className="size-3.5" aria-hidden="true" />
              </button>
            </div>
          ) : null}

          <form
            onSubmit={handleSubmit}
            className="shrink-0 border-t border-white/[0.07] bg-[#080e1a]/45 px-3 pb-3 pt-3 backdrop-blur-xl sm:px-4 sm:pb-4"
          >
            <div className="flex items-center gap-2">
              <div className="relative min-w-0 flex-1">
                <Input
                  ref={inputRef}
                  value={claim}
                  onChange={(event) => setClaim(event.target.value)}
                  maxLength={4000}
                  disabled={isSubmitting || isPassed}
                  placeholder={
                    isPassed
                      ? "本概念已通过，重置后可以重新练习"
                      : "写下你的理解…"
                  }
                  aria-label={`输入你对${termName}的理解`}
                  className="h-12 rounded-2xl border-white/[0.09] bg-[#0b1220]/80 pr-14 pl-4 text-[15px] text-slate-100 shadow-inner shadow-black/20 placeholder:text-slate-600 focus-visible:border-cyan-300/30 focus-visible:ring-cyan-300/15 disabled:cursor-not-allowed disabled:opacity-60"
                />
                <Button
                  type="submit"
                  size="icon-lg"
                  disabled={isSubmitDisabled}
                  aria-label="提交诊断"
                  className="absolute top-1/2 right-1.5 size-9 -translate-y-1/2 rounded-xl border border-cyan-200/20 bg-gradient-to-br from-cyan-300 to-sky-400 text-slate-950 shadow-lg shadow-cyan-400/15 transition-all hover:brightness-110 disabled:border-white/[0.06] disabled:bg-white/[0.055] disabled:text-slate-600 disabled:shadow-none"
                >
                  {isSubmitting ? (
                    <Loader2
                      className="size-4 animate-spin"
                      aria-hidden="true"
                    />
                  ) : (
                    <Send className="size-4" aria-hidden="true" />
                  )}
                </Button>
              </div>
            </div>
            <div className="mt-2 flex items-center justify-between gap-3 px-1 text-[10px] text-slate-600">
              <span className="flex items-center gap-1.5">
                <CircleAlert className="size-3" aria-hidden="true" />
                Enter 提交 · 单次诊断约需数秒
              </span>
              <span className="font-mono text-slate-600">
                {claim.length} / 4000
              </span>
            </div>
          </form>
        </section>

        <ProgressPanel
          status={status}
          missingElements={missingElements}
          hasDiagnosed={hasDiagnosed}
        />
      </main>
    </div>
  );
}
