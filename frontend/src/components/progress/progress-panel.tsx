"use client";

import {
  ArrowRightLeft,
  Check,
  CircleDashed,
  Layers3,
  Newspaper,
  ShieldCheck,
  Sparkles,
  UsersRound,
  type LucideIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { LearningStatus } from "@/lib/api";
import { CONCEPT_NAME, CONCEPT_NAME_EN, KEY_ELEMENTS } from "@/lib/concept";
import { STATUS_PRESENTATION } from "@/lib/status";
import { cn } from "@/lib/utils";

const ELEMENT_ICONS: Record<string, LucideIcon> = {
  K1: Newspaper,
  K2: UsersRound,
  K3: ArrowRightLeft,
  K4: Layers3,
  K5: ShieldCheck,
};

interface ProgressPanelProps {
  status: LearningStatus | null;
  missingElements: string[];
  hasDiagnosed: boolean;
}

export function ProgressPanel({
  status,
  missingElements,
  hasDiagnosed,
}: ProgressPanelProps) {
  const isReconfirm = status === "NEED_RECONFIRM";
  const missingSet = new Set(isReconfirm ? [] : missingElements);
  const coveredIds = new Set(
    hasDiagnosed && !isReconfirm
      ? KEY_ELEMENTS.filter((element) => !missingSet.has(element.id)).map(
          (element) => element.id,
        )
      : [],
  );
  const coveredCount = coveredIds.size;
  const progress =
    status === "PASS"
      ? 100
      : hasDiagnosed && !isReconfirm
        ? Math.round((coveredCount / KEY_ELEMENTS.length) * 100)
        : 0;
  const statusMeta = status ? STATUS_PRESENTATION[status] : null;

  return (
    <aside className="study-scrollbar flex w-full shrink-0 flex-col gap-4 lg:w-[360px] lg:overflow-y-auto xl:w-[390px]">
      <Card className="glass-panel gap-0 rounded-3xl border-white/[0.08] bg-white/[0.045] py-0 text-slate-100 ring-0 shadow-2xl shadow-black/20 backdrop-blur-2xl">
        <CardHeader className="border-b border-white/[0.07] px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle className="text-sm font-medium tracking-wide text-slate-100">
                学习进度
              </CardTitle>
              <p className="mt-1 text-xs text-slate-400">
                {CONCEPT_NAME} · {CONCEPT_NAME_EN}
              </p>
            </div>
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium",
                statusMeta
                  ? statusMeta.tone
                  : "border-white/10 bg-white/[0.045] text-slate-400",
              )}
            >
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  statusMeta ? statusMeta.dot : "bg-slate-500",
                )}
                aria-hidden="true"
              />
              {statusMeta ? statusMeta.label : "准备开始"}
            </span>
          </div>
        </CardHeader>

        <CardContent className="px-5 py-5">
          <div className="flex items-center gap-5">
            <div
              className="relative flex size-[88px] shrink-0 items-center justify-center rounded-full p-[6px]"
              style={{
                background: `conic-gradient(from -90deg, #22d3ee 0deg, #818cf8 ${progress * 3.6}deg, rgba(255, 255, 255, 0.065) ${progress * 3.6}deg 360deg)`,
              }}
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progress}
              aria-label={`学习进度 ${progress}%`}
            >
              <div className="flex size-full flex-col items-center justify-center rounded-full border border-white/[0.06] bg-[#0c1322] shadow-inner shadow-black/30">
                <span className="text-2xl font-semibold tracking-tight text-white">
                  {progress}
                  <span className="ml-0.5 text-xs font-normal text-slate-500">
                    %
                  </span>
                </span>
                <span className="mt-0.5 text-[10px] tracking-wide text-slate-500">
                  要素覆盖
                </span>
              </div>
            </div>

            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-200">
                {hasDiagnosed && !isReconfirm
                  ? `已覆盖 ${coveredCount} / ${KEY_ELEMENTS.length} 个要素`
                  : isReconfirm
                    ? "等待确认作答概念"
                    : "等待第一次诊断"}
              </p>
              <p className="mt-1.5 text-xs leading-5 text-slate-400">
                {statusMeta
                  ? statusMeta.caption
                  : "提交回答后，这里会逐项显示已覆盖与缺失的关键要素。"}
              </p>
            </div>
          </div>

          {isReconfirm ? (
            <div className="mt-4 rounded-2xl border border-orange-300/15 bg-orange-300/[0.055] px-3.5 py-3 text-xs leading-5 text-orange-100/75">
              先确认你要作答的概念。方向确认前，这一轮不累计要素进度。
            </div>
          ) : null}

          <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-white/[0.055]">
            <div
              className="h-full rounded-full bg-gradient-to-r from-cyan-300 via-sky-400 to-indigo-400 transition-[width] duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>

          <div className="mt-5 flex items-center justify-between text-[11px] tracking-wide">
            <span className="text-slate-500">关键要素检查</span>
            {hasDiagnosed && !isReconfirm ? (
              <span className="text-slate-400">
                <span className="text-emerald-300">{coveredCount} 已覆盖</span>
                <span className="mx-1.5 text-slate-600">/</span>
                <span className="text-amber-300">
                  {missingElements.length} 待补
                </span>
              </span>
            ) : (
              <span className="text-slate-500">共 {KEY_ELEMENTS.length} 项</span>
            )}
          </div>

          <ul className="mt-3 flex flex-col gap-2">
            {KEY_ELEMENTS.map((element) => {
              const Icon = ELEMENT_ICONS[element.id] ?? CircleDashed;
              const isCovered = coveredIds.has(element.id);
              const isMissing =
                hasDiagnosed && !isReconfirm && missingSet.has(element.id);

              return (
                <li
                  key={element.id}
                  className={cn(
                    "group flex items-center gap-3 rounded-2xl border px-3 py-2.5 transition-colors",
                    isCovered
                      ? "border-emerald-300/15 bg-emerald-300/[0.045]"
                      : isMissing
                        ? "border-amber-300/15 bg-amber-300/[0.04]"
                        : "border-white/[0.055] bg-white/[0.018]",
                  )}
                >
                  <div
                    className={cn(
                      "flex size-8 shrink-0 items-center justify-center rounded-xl border",
                      isCovered
                        ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-200"
                        : isMissing
                          ? "border-amber-300/20 bg-amber-300/10 text-amber-200"
                          : "border-white/[0.07] bg-white/[0.035] text-slate-500",
                    )}
                    aria-hidden="true"
                  >
                    <Icon className="size-4" />
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] font-medium tracking-wider text-slate-500">
                        {element.id}
                      </span>
                      <span
                        className={cn(
                          "truncate text-xs font-medium",
                          isCovered
                            ? "text-emerald-100/90"
                            : isMissing
                              ? "text-amber-100/90"
                              : "text-slate-300",
                        )}
                      >
                        {element.label}
                      </span>
                    </div>
                    <p className="mt-0.5 truncate text-[10px] text-slate-500">
                      {element.description}
                    </p>
                  </div>

                  {isCovered ? (
                    <Badge
                      variant="outline"
                      className="shrink-0 border-emerald-300/18 bg-emerald-300/[0.08] px-1.5 text-[10px] text-emerald-200"
                    >
                      <Check className="size-2.5" aria-hidden="true" />
                      已覆盖
                    </Badge>
                  ) : isMissing ? (
                    <Badge
                      variant="outline"
                      className="shrink-0 border-amber-300/20 bg-amber-300/[0.08] px-1.5 text-[10px] text-amber-200"
                    >
                      待补
                    </Badge>
                  ) : (
                    <Badge
                      variant="outline"
                      className="shrink-0 border-white/[0.07] px-1.5 text-[10px] text-slate-500"
                    >
                      待检测
                    </Badge>
                  )}
                </li>
              );
            })}
          </ul>
        </CardContent>
      </Card>

      <div className="glass-panel rounded-3xl border border-white/[0.07] bg-white/[0.035] p-4 text-xs leading-6 text-slate-400 backdrop-blur-xl">
        <div className="mb-1.5 flex items-center gap-2 text-slate-300">
          <Sparkles className="size-3.5 text-cyan-300" aria-hidden="true" />
          <span className="font-medium">诊断方式</span>
        </div>
        系统会把你的回答拆成要点，逐项核对关键要素。缺失的要素会在下一轮继续追踪，不会因为补充了后面的内容而自动补齐前面的空白。
      </div>
    </aside>
  );
}
