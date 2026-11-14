"use client";
// Bottom sheet: provenance, scope choice, Why #1, hidden drawer, import. Thumb-zone actions, Esc/backdrop closes.
import { useEffect, useEffectEvent, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { useHydrated } from "@/lib/store";

export function Sheet({
  open,
  onClose,
  title,
  eyebrow,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  eyebrow?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const hydrated = useHydrated();
  const panel = useRef<HTMLDivElement>(null);
  // Callers pass a fresh `onClose` arrow on every render. If the effect below depended on it, every keystroke in an
  // input inside the sheet (which re-renders the caller) would re-run it: focus jumped to the panel and back, and
  // Android closed the keyboard after each key. The effect runs once per open; Escape reads the latest onClose.
  const closeOnEscape = useEffectEvent((e: KeyboardEvent) => {
    if (e.key === "Escape") onClose();
  });
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    const onKey = (e: KeyboardEvent) => closeOnEscape(e);
    window.addEventListener("keydown", onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
      prev?.focus?.();
    };
  }, [open]);
  if (!hydrated || !open) return null;
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center" role="dialog" aria-modal>
      <button
        type="button"
        aria-label="Close"
        onClick={onClose}
        className="absolute inset-0 bg-black/35 animate-in fade-in-0 duration-150"
      />
      <div
        ref={panel}
        tabIndex={-1}
        className="relative flex max-h-[86dvh] w-full max-w-[430px] flex-col rounded-t-2xl bg-surface outline-none animate-in slide-in-from-bottom-8 fade-in-0 duration-200"
      >
        <div className="mx-auto mt-2 h-1 w-9 rounded-full bg-rule" aria-hidden />
        <header className="flex items-start gap-3 px-4 pb-2 pt-3">
          <div className="min-w-0 flex-1">
            {eyebrow && <p className="t-micro text-ink-3">{eyebrow}</p>}
            {title && <h2 className="t-title mt-0.5">{title}</h2>}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="hit -mr-1 grid size-9 place-items-center rounded-full text-ink-2 hover:bg-surface-2"
            aria-label="Close"
          >
            <X className="size-5" strokeWidth={1.75} />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 pb-4">{children}</div>
        {footer && (
          <div className="border-t border-rule px-4 pb-[calc(12px+env(safe-area-inset-bottom))] pt-3">{footer}</div>
        )}
      </div>
    </div>,
    document.body,
  );
}
