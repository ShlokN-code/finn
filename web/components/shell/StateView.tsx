// Loading, empty, error and stale states — every screen uses these so they look and read the same.
import type { ReactNode } from "react";
import { AlertTriangle, CloudOff, RotateCcw } from "lucide-react";

export function Skeleton({ rows = 3, label }: { rows?: number; label?: string }) {
  return (
    <div aria-busy className="divide-y divide-rule border-y border-rule bg-surface" role="status">
      {label && <span className="sr-only">{label}</span>}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="animate-pulse px-4 py-4">
          <div className="h-2.5 w-28 rounded bg-surface-2" />
          <div className="mt-3 h-4 w-4/5 rounded bg-surface-2" />
          <div className="mt-2 h-3 w-3/5 rounded bg-surface-2" />
          <div className="mt-3 h-3 w-2/5 rounded bg-surface-2" />
        </div>
      ))}
    </div>
  );
}

export function Empty({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="px-4 py-10">
      <p className="t-headline">{title}</p>
      {children && <div className="t-body mt-1 text-ink-2">{children}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({
  title = "Couldn't load this",
  detail,
  onRetry,
  offline,
}: {
  title?: string;
  detail?: string;
  onRetry?: () => void;
  offline?: boolean;
}) {
  const Icon = offline ? CloudOff : AlertTriangle;
  return (
    <div className="px-4 py-8" role="alert">
      <div className="flex items-start gap-3">
        <Icon className="mt-0.5 size-5 shrink-0 text-warn" strokeWidth={1.75} />
        <div className="min-w-0">
          <p className="t-headline">{title}</p>
          {detail && <p className="t-small mt-1 text-ink-2">{detail}</p>}
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 inline-flex h-11 items-center gap-2 rounded-full border border-rule px-4 text-[14px] font-medium"
            >
              <RotateCcw className="size-4" strokeWidth={1.75} /> Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/** A quiet one-line banner over content that is shown but not current. */
export function Notice({
  tone = "neutral",
  children,
  action,
}: {
  tone?: "neutral" | "warn";
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div
      className={`t-small flex items-center gap-3 px-4 py-2.5 ${
        tone === "warn" ? "bg-warn-bg text-warn" : "bg-surface-2 text-ink-2"
      }`}
    >
      <div className="min-w-0 flex-1">{children}</div>
      {action}
    </div>
  );
}
