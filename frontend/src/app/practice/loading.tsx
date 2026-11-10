import { Y2KBackground } from "@/components/y2k/y2k-background";

export default function PracticeLoading() {
  return (
    <div className="y2k-page relative min-h-dvh overflow-hidden px-4 py-6 text-slate-100 sm:px-8">
      <Y2KBackground />
      <div className="relative z-10 mx-auto w-full max-w-6xl">
        <div className="h-12 w-44 animate-pulse rounded-xl border border-white/10 bg-white/[0.035]" />
        <div className="mx-auto mt-16 w-full max-w-3xl rounded-[2rem] border-2 border-white/10 bg-white/[0.035] p-6 sm:p-9">
          <div className="h-8 w-40 animate-pulse rounded-lg bg-white/10" />
          <div className="mt-6 h-24 animate-pulse rounded-2xl bg-white/[0.055]" />
          <div className="mt-4 h-28 animate-pulse rounded-2xl bg-white/[0.04]" />
          <div className="mt-8 h-12 w-full animate-pulse rounded-xl bg-fuchsia-300/10" />
        </div>
      </div>
    </div>
  );
}
