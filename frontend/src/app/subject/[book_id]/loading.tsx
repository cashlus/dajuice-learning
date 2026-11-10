import { Y2KBackground } from "@/components/y2k/y2k-background";

export default function SubjectLoading() {
  return (
    <div className="y2k-page relative min-h-dvh overflow-hidden px-4 py-6 text-slate-100 sm:px-8">
      <Y2KBackground />
      <div className="relative z-10 mx-auto w-full max-w-7xl">
        <div className="h-12 w-48 animate-pulse rounded-xl border border-white/10 bg-white/[0.035]" />
        <div className="mt-10 h-48 animate-pulse rounded-[2rem] border-2 border-white/10 bg-white/[0.035]" />
        <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2, 3, 4, 5].map((item) => (
            <div
              key={item}
              className="h-60 animate-pulse rounded-2xl border-2 border-white/10 bg-white/[0.035]"
            />
          ))}
        </div>
      </div>
    </div>
  );
}
