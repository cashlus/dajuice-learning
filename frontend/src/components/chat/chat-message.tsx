"use client";

import { Search, Sparkles, UserRound } from "lucide-react";

import { TypewriterText } from "@/components/chat/typewriter-text";
import type { LearningStatus } from "@/lib/api";
import { STATUS_PRESENTATION } from "@/lib/status";
import { cn } from "@/lib/utils";

export interface ChatMessageData {
  id: string;
  role: "user" | "assistant";
  content: string;
  animate?: boolean;
  status?: LearningStatus;
  searchNotice?: string;
}

interface ChatMessageProps {
  message: ChatMessageData;
  onReveal?: () => void;
}

export function ChatMessage({ message, onReveal }: ChatMessageProps) {
  const isUser = message.role === "user";
  const statusMeta = message.status
    ? STATUS_PRESENTATION[message.status]
    : null;

  return (
    <article
      className={cn(
        "message-enter flex w-full items-start gap-3",
        isUser ? "flex-row-reverse" : "flex-row",
      )}
    >
      <div
        className={cn(
          "mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-2xl border shadow-lg",
          isUser
            ? "border-white/10 bg-white/[0.07] text-slate-200"
            : "border-cyan-300/20 bg-gradient-to-br from-cyan-400/20 to-violet-500/20 text-cyan-200",
        )}
        aria-hidden="true"
      >
        {isUser ? (
          <UserRound className="size-4" />
        ) : (
          <Sparkles className="size-4" />
        )}
      </div>

      <div
        className={cn(
          "flex min-w-0 max-w-[86%] flex-col gap-2 sm:max-w-[78%]",
          isUser ? "items-end" : "items-start",
        )}
      >
        <div className="flex items-center gap-2 px-1 text-[11px] tracking-wide text-slate-400">
          <span>{isUser ? "你的回答" : "诊断助教"}</span>
          {statusMeta ? (
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium",
                statusMeta.tone,
              )}
            >
              <span
                className={cn("size-1.5 rounded-full", statusMeta.dot)}
                aria-hidden="true"
              />
              {statusMeta.label}
            </span>
          ) : null}
        </div>

        <div
          className={cn(
            "w-fit rounded-2xl px-4 py-3 text-[15px] leading-7 shadow-xl",
            isUser
              ? "rounded-tr-md bg-gradient-to-br from-cyan-300 via-sky-300 to-blue-400 font-medium text-slate-950 shadow-cyan-500/10"
              : "rounded-tl-md border border-white/[0.08] bg-white/[0.055] text-slate-100 shadow-black/20 backdrop-blur-xl",
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          ) : (
            <TypewriterText
              text={message.content}
              animate={message.animate}
              onReveal={onReveal}
            />
          )}
        </div>

        {message.searchNotice ? (
          <div className="flex max-w-full items-start gap-2 rounded-xl border border-sky-300/10 bg-sky-300/[0.045] px-3 py-2 text-xs leading-5 text-sky-200/75">
            <Search className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
            <span className="break-words">{message.searchNotice}</span>
          </div>
        ) : null}
      </div>
    </article>
  );
}
