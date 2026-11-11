"use client";
import { undoToast, useToast } from "./ui-store";

export function ToastHost() {
  const t = useToast();
  if (!t) return null;
  return (
    <div
      className="pointer-events-none fixed inset-x-0 bottom-[calc(116px+env(safe-area-inset-bottom))] z-40 flex justify-center px-4"
      aria-live="polite"
    >
      <div
        key={t.id}
        className="pointer-events-auto flex w-full max-w-[398px] items-center gap-3 overflow-hidden rounded-xl bg-ink py-1 pl-4 pr-1 text-paper animate-in slide-in-from-bottom-4 fade-in-0 duration-200"
      >
        <span className="t-small min-w-0 flex-1 truncate">{t.text}</span>
        {t.actionLabel && (
          <button
            type="button"
            onClick={undoToast}
            className="h-11 shrink-0 rounded-lg px-3 text-[13px] font-semibold tracking-wide"
          >
            {t.actionLabel}
          </button>
        )}
        <span
          aria-hidden
          className="absolute bottom-0 left-0 h-0.5 bg-paper/50"
          style={{ animation: `finn-countdown ${t.ms}ms linear forwards`, width: "100%" }}
        />
      </div>
      <style>{`@keyframes finn-countdown{from{width:100%}to{width:0}}`}</style>
    </div>
  );
}
