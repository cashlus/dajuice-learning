"use client";

import { useEffect } from "react";
import { RefreshCcw, TriangleAlert } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-[#070b14] px-5 text-slate-100">
      <div
        className="pointer-events-none absolute inset-0 ambient-grid opacity-70"
        aria-hidden="true"
      />
      <div className="glass-panel relative w-full max-w-lg rounded-3xl border border-white/[0.08] bg-white/[0.04] p-7 shadow-2xl shadow-black/30 backdrop-blur-2xl">
        <div className="flex size-11 items-center justify-center rounded-2xl border border-rose-300/20 bg-rose-400/10 text-rose-200">
          <TriangleAlert className="size-5" aria-hidden="true" />
        </div>
        <h1 className="mt-5 text-xl font-semibold tracking-tight">
          页面暂时没有加载成功
        </h1>
        <p className="mt-2 text-sm leading-6 text-slate-400">
          这不是白屏，页面错误已经被接住。可以先重试；如果仍然失败，请检查后端服务是否在
          <span className="mx-1 font-mono text-xs text-slate-300">
            127.0.0.1:8000
          </span>
          正常运行。
        </p>
        <Button
          type="button"
          onClick={reset}
          className="mt-6 h-10 gap-2 rounded-xl bg-gradient-to-r from-cyan-300 to-sky-400 px-4 text-slate-950 hover:brightness-110"
        >
          <RefreshCcw className="size-4" aria-hidden="true" />
          重新加载页面
        </Button>
      </div>
    </main>
  );
}
