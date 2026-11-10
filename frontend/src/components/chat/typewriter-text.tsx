"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/utils";

interface TypewriterTextProps {
  text: string;
  animate?: boolean;
  className?: string;
  onReveal?: () => void;
}

export function TypewriterText({
  text,
  animate = false,
  className,
  onReveal,
}: TypewriterTextProps) {
  const characters = useMemo(() => Array.from(text), [text]);
  const [visibleCount, setVisibleCount] = useState(
    animate ? 0 : characters.length,
  );
  const onRevealRef = useRef(onReveal);

  useEffect(() => {
    onRevealRef.current = onReveal;
  }, [onReveal]);

  useEffect(() => {
    if (!animate || characters.length === 0) {
      return;
    }

    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const totalCharacters = characters.length;
    const duration = Math.min(3400, Math.max(700, totalCharacters * 13));
    let startedAt = 0;
    let frameId = 0;
    let lastRevealAt = 0;

    const tick = (now: number) => {
      const progress = Math.min(1, (now - startedAt) / duration);
      setVisibleCount(Math.ceil(progress * totalCharacters));

      if (now - lastRevealAt > 90) {
        lastRevealAt = now;
        onRevealRef.current?.();
      }

      if (progress < 1) {
        frameId = requestAnimationFrame(tick);
      } else {
        setVisibleCount(totalCharacters);
        onRevealRef.current?.();
      }
    };

    frameId = requestAnimationFrame((now) => {
      if (reduceMotion) {
        setVisibleCount(totalCharacters);
        onRevealRef.current?.();
        return;
      }

      startedAt = now;
      frameId = requestAnimationFrame(tick);
    });

    return () => cancelAnimationFrame(frameId);
  }, [animate, characters]);

  const displayedCount = animate ? visibleCount : characters.length;
  const visibleText = characters.slice(0, displayedCount).join("");
  const isTyping = animate && displayedCount < characters.length;

  return (
    <span
      className={cn("whitespace-pre-wrap break-words", className)}
      aria-label={text}
    >
      <span aria-hidden="true">{visibleText}</span>
      {isTyping ? (
        <span className="typewriter-caret" aria-hidden="true" />
      ) : null}
    </span>
  );
}
