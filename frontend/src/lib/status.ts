import type { LearningStatus } from "@/lib/api";

export interface StatusPresentation {
  label: string;
  caption: string;
  tone: string;
  dot: string;
}

export const STATUS_PRESENTATION: Record<LearningStatus, StatusPresentation> = {
  PASS: {
    label: "已通过",
    caption: "五个关键要素已经完整覆盖。",
    tone: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200",
    dot: "bg-emerald-300",
  },
  NEED_RETRY: {
    label: "需要重答",
    caption: "还有关键要素没有覆盖，请根据反馈补充。",
    tone: "border-amber-400/25 bg-amber-400/10 text-amber-200",
    dot: "bg-amber-300",
  },
  NEED_RECONFIRM: {
    label: "概念待确认",
    caption: "这句话可能偏离了当前概念，请先确认作答方向。",
    tone: "border-orange-400/30 bg-orange-400/10 text-orange-200",
    dot: "bg-orange-300",
  },
};
