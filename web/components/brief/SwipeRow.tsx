"use client";
// Swipe right = Reviewed, left = Not useful. Commits only past 40% of the row; shorter drags spring back.
// A haptic tick marks the threshold (navigator.vibrate: Android; iOS has no web haptics). Vertical scroll wins
// ties (direction lock + touch-action: pan-y). The reveal is neutral; past the threshold its label inverts.
import { useRef, useState, type ReactNode } from "react";
import { animate, m, useMotionValue, useMotionValueEvent, useReducedMotion } from "framer-motion";
import { Check, ThumbsDown } from "lucide-react";

export type SwipeDir = "right" | "left";
const THRESHOLD = 0.4;

export function SwipeRow({
  children,
  onCommit,
  draggedRef,
}: {
  children: ReactNode;
  onCommit: (dir: SwipeDir) => void;
  draggedRef: React.MutableRefObject<boolean>;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const x = useMotionValue(0);
  const reduce = useReducedMotion();
  const [side, setSide] = useState<0 | 1 | -1>(0);
  const [armed, setArmed] = useState<SwipeDir | null>(null);
  const armedRef = useRef<SwipeDir | null>(null);

  useMotionValueEvent(x, "change", (v) => {
    const s = v > 4 ? 1 : v < -4 ? -1 : 0;
    setSide((p) => (p === s ? p : s));
    const w = ref.current?.offsetWidth ?? 375;
    const a: SwipeDir | null = v > w * THRESHOLD ? "right" : v < -w * THRESHOLD ? "left" : null;
    if (a !== armedRef.current) {
      armedRef.current = a;
      setArmed(a);
      if (a) {
        try {
          navigator.vibrate?.(10);
        } catch {}
      }
    }
  });

  return (
    <div ref={ref} className="relative overflow-hidden bg-surface-2">
      <div aria-hidden className="absolute inset-0 flex items-center justify-between px-5">
        <span
          className={`t-small inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 font-semibold transition-colors duration-100 ${
            side === 1 ? "opacity-100" : "opacity-0"
          } ${armed === "right" ? "bg-ink text-paper" : "text-ink-2"}`}
        >
          <Check className="size-4" strokeWidth={2.25} /> Reviewed
        </span>
        <span
          className={`t-small inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 font-semibold transition-colors duration-100 ${
            side === -1 ? "opacity-100" : "opacity-0"
          } ${armed === "left" ? "bg-ink text-paper" : "text-ink-2"}`}
        >
          Not useful <ThumbsDown className="size-4" strokeWidth={2} />
        </span>
      </div>
      <m.div
        drag="x"
        dragDirectionLock
        dragMomentum={false}
        style={{ x, touchAction: "pan-y" }}
        onDragStart={() => {
          draggedRef.current = true;
        }}
        onDragEnd={() => {
          const w = ref.current?.offsetWidth ?? 375;
          const dir = armedRef.current;
          setTimeout(() => (draggedRef.current = false), 50);
          if (dir) {
            // Commit on a timer, not on the animation's end: a throttled tab must never lose a swipe.
            animate(x, dir === "right" ? w * 1.05 : -w * 1.05, { duration: reduce ? 0 : 0.16, ease: "easeIn" });
            setTimeout(() => onCommit(dir), reduce ? 0 : 140);
          } else {
            animate(x, 0, reduce ? { duration: 0 } : { type: "spring", stiffness: 520, damping: 38 });
          }
        }}
        className={`relative bg-surface ${side !== 0 ? "rounded-xl" : ""}`}
      >
        {children}
      </m.div>
    </div>
  );
}
