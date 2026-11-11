// Shared card primitives: impact, verification, source chip, event-thread timeline. Pure presentational.
import { FileText } from "lucide-react";
import type { Citation, Impact, TimelineItem } from "@/lib/types";
import { istWhen, sourceHref, sourceLabel } from "@/lib/format";
import { ImpactLabel } from "@/components/ui/signal";

export function ImpactTag({ impact, title }: { impact: Impact | null; title?: string }) {
  return <ImpactLabel impact={impact} title={title} />;
}

export type Verification = "cross_checked" | "partial" | "pending" | "mismatch";

export const VERIFICATION: Record<Verification, { text: string; short: string; cls: string }> = {
  cross_checked: { text: "✓ Cross-checked", short: "✓ Cross-checked", cls: "text-pos" },
  partial: { text: "✓ Partly cross-checked", short: "✓ Partly checked", cls: "text-pos" },
  pending: { text: "Cross-check pending", short: "Check pending", cls: "text-warn" },
  mismatch: { text: "Couldn't verify — open filing", short: "Couldn't verify", cls: "text-neg" },
};

export function VerificationBadge({ state, note, short = false }: { state: Verification; note?: string | null; short?: boolean }) {
  const m = VERIFICATION[state];
  return (
    <span title={note ?? undefined} className={`t-small font-medium ${m.cls}`}>
      {short ? m.short : m.text}
    </span>
  );
}

export function SourceChip({ c, primary = false }: { c: Citation; primary?: boolean }) {
  return (
    <a
      href={sourceHref(c)}
      target="_blank"
      rel="noopener noreferrer"
      title={c.title ?? c.url}
      onClick={(e) => e.stopPropagation()}
      className={`t-small hit inline-flex h-7 max-w-full items-center gap-1 rounded-md border px-2 ${
        primary ? "border-ink-3/50 font-medium text-ink" : "border-rule text-ink-2"
      }`}
    >
      <FileText className="size-3.5 shrink-0" strokeWidth={1.75} />
      <span className="truncate">{sourceLabel(c)}</span>
    </a>
  );
}

const STAGE: Record<string, string> = {
  intimation: "Board meeting notice",
  outcome: "Outcome",
  presentation: "Investor deck",
  call: "Earnings call",
  transcript: "Transcript",
  newspaper_ad: "Newspaper ad",
  clarification: "Clarification",
  other: "Filing",
};

export function Timeline({ items }: { items: TimelineItem[] }) {
  if (items.length < 2) return null;
  const sorted = [...items].sort((a, b) => a.at.localeCompare(b.at));
  return (
    <div className="mt-4">
      <p className="t-micro text-ink-3">Event thread · {items.length} filings</p>
      <ol className="mt-2">
        {sorted.map((t, i) => (
          <li key={t.filing_id} className="relative flex gap-3 pb-2.5 last:pb-0">
            <span aria-hidden className="relative flex w-2.5 justify-center">
              <span className={`mt-1.5 size-2 rounded-full ${t.stage === "outcome" ? "bg-ink" : "border border-ink-3 bg-surface"}`} />
              {i < sorted.length - 1 && <span className="absolute top-4 bottom-[-6px] w-px bg-rule" />}
            </span>
            <span className="t-small min-w-0 flex-1">
              <span className="font-medium">{STAGE[t.stage] ?? t.stage}</span>
              <span className="text-ink-3"> · {istWhen(t.at)}</span>
              {t.label && t.label !== STAGE[t.stage] && <span className="block truncate text-ink-2">{t.label}</span>}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
