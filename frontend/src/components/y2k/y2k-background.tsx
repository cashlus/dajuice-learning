export function Y2KBackground() {
  return (
    <div
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden"
      aria-hidden="true"
    >
      <div className="y2k-base absolute inset-0" />
      <div className="y2k-grid absolute inset-0 opacity-70" />
      <div className="y2k-scanlines absolute inset-0 opacity-35" />
      <div className="absolute -left-40 top-[-14rem] size-[34rem] rounded-full bg-fuchsia-500/15 blur-[130px]" />
      <div className="absolute right-[-12rem] top-[18%] size-[30rem] rounded-full bg-cyan-400/12 blur-[130px]" />
      <div className="absolute bottom-[-18rem] left-[34%] size-[32rem] rounded-full bg-violet-500/10 blur-[150px]" />
      <div className="y2k-chrome-orb absolute right-[8%] top-[12%] size-40 opacity-25 sm:size-64" />
    </div>
  );
}
