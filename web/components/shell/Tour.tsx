"use client";
// First-run tour: 3 skippable steps, shown once (localStorage). A spotlight over the real element, not a slideshow.
import { useEffect, useLayoutEffect, useState } from "react";
import { createPortal } from "react-dom";
import { write } from "@/lib/store";

type Step = { selector: string; title: string; body: string };
const STEPS: Step[] = [
  {
    selector: '[data-tour="top-card"]',
    title: "Swipe to triage",
    body: "Right = reviewed. Left = not useful — FINN shows less of it. Undo for 5 seconds. Tap a card to open it.",
  },
  {
    selector: '[data-tour="top-card"] [data-figure]',
    title: "Tap a number for its source",
    body: "Every figure opens its filing, page and the exact quote. If FINN couldn't verify it, it says so.",
  },
  {
    selector: '[data-tour="research-tab"]',
    title: "Research any NSE ticker",
    body: "A dossier from transcripts, annual reports and filings — with a Promise Ledger of what management said vs did.",
  },
];

export function Tour({ onDone }: { onDone: () => void }) {
  const [i, setI] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const step = STEPS[i];

  useLayoutEffect(() => {
    const el = document.querySelector(step.selector) as HTMLElement | null;
    if (!el) return;
    const r0 = el.getBoundingClientRect();
    if (r0.top < 60 || r0.bottom > window.innerHeight - 140) el.scrollIntoView({ block: "center" });
    const measure = () => {
      const cur = document.querySelector(step.selector) as HTMLElement | null; // the list may re-render
      if (cur) setRect(cur.getBoundingClientRect());
    };
    measure();
    const iv = setInterval(measure, 250); // content above can still be settling (header, season strip)
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => {
      clearInterval(iv);
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
    };
  }, [step.selector]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && finish();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  function finish() {
    write("tour", true);
    onDone();
  }

  const pad = 6;
  const below = rect ? rect.top < window.innerHeight / 2 : true;
  return createPortal(
    <div className="fixed inset-0 z-[60]" role="dialog" aria-modal aria-label="Quick tour">
      {rect ? (
        <div
          aria-hidden
          className="pointer-events-none absolute rounded-xl"
          style={{
            left: Math.max(4, rect.left - pad),
            top: rect.top - pad,
            width: Math.min(window.innerWidth - 8, rect.width + pad * 2),
            height: rect.height + pad * 2,
            boxShadow: "0 0 0 9999px rgba(15,15,14,0.55)",
          }}
        />
      ) : (
        <div className="absolute inset-0 bg-[rgba(15,15,14,0.55)]" />
      )}
      <div
        className="absolute inset-x-0 mx-auto w-[calc(100%-32px)] max-w-[398px] rounded-2xl bg-surface p-4 shadow-xl animate-in fade-in-0 slide-in-from-bottom-2"
        style={
          rect
            ? below
              ? { top: Math.min(rect.bottom + 14, window.innerHeight - 220) }
              : { top: Math.max(16, rect.top - 14 - 190) }
            : { bottom: 140 }
        }
      >
        <p className="t-micro text-ink-3">
          {i + 1} of {STEPS.length}
        </p>
        <p className="t-title mt-1">{step.title}</p>
        <p className="t-body mt-1 text-ink-2">{step.body}</p>
        {i === 0 && (
          <p aria-hidden className="mt-2 text-[22px] text-ink-3">
            <span className="inline-block animate-[finn-nudge_1.4s_ease-in-out_infinite]">⟷</span>
          </p>
        )}
        <div className="mt-3 flex items-center gap-2">
          <button type="button" onClick={finish} className="h-11 px-2 text-[14px] text-ink-2">
            Skip
          </button>
          <span className="flex-1" />
          <button
            type="button"
            onClick={() => (i < STEPS.length - 1 ? setI(i + 1) : finish())}
            className="h-11 rounded-full bg-ink px-5 text-[14px] font-medium text-paper"
            autoFocus
          >
            {i < STEPS.length - 1 ? "Next" : "Done"}
          </button>
        </div>
      </div>
      <style>{`@keyframes finn-nudge{0%,100%{transform:translateX(-6px)}50%{transform:translateX(6px)}}`}</style>
    </div>,
    document.body,
  );
}
