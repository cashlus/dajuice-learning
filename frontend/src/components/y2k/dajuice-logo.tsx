import Link from "next/link";

import { cn } from "@/lib/utils";

interface DaJuiceLogoProps {
  className?: string;
  compact?: boolean;
}

export function DaJuiceLogo({ className, compact = false }: DaJuiceLogoProps) {
  return (
    <Link
      href="/"
      aria-label="DaJuice 首页"
      className={cn("dajuice-wrap group inline-flex items-end", className)}
    >
      <span
        className={cn(
          "dajuice-logo relative inline-block font-pixel leading-none",
          compact ? "text-[1.25rem] sm:text-[1.55rem]" : "text-[2.15rem] sm:text-[3.1rem]",
        )}
        data-text="DaJuice"
      >
        DaJuice
      </span>
    </Link>
  );
}
