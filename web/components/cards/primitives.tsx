// Shared card primitives: impact tag, verification badge, source chip, timeline. Pure presentational.
import type { Citation, Impact, TimelineItem } from "@/lib/types";
import { ist } from "@/lib/format";

const IMPACT: Record<Impact, { dot: string; label: string; cls: string }> = {
  positive: { dot: "🟢", label: "Positive", cls: "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200" },
  negative: { dot: "🔴", label: "Negative", cls: "bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-200" },
  mixed: { dot: "🟡", label: "Mixed", cls: "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200" },
  neutral: { dot: "⚪", label: "Neutral", cls: "bg-muted text-muted-foreground" },
};

export function ImpactTag({ impact, title }: { impact: Impact | null; title?: string }) {
  if (!impact) return null;
  const i = IMPACT[impact];
  return (
    <span title={title} className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${i.cls}`}>
      <span aria-hidden>{i.dot}</span>
      {i.label}
    </span>
  );
}

export type Verification = "cross_checked" | "partial" | "pending" | "mismatch";

export function VerificationBadge({ state, note }: { state: Verification; note?: string | null }) {
  const map = {
    cross_checked: { text: "✓ Cross-checked", cls: "text-emerald-700 dark:text-emerald-300" },
    partial: { text: "✓ Partly cross-checked", cls: "text-emerald-700 dark:text-emerald-300" },
    pending: { text: "Cross-check pending", cls: "text-amber-700 dark:text-amber-300" },
    mismatch: { text: "Couldn't verify — open filing", cls: "text-red-700 dark:text-red-300" },
  }[state];
  return (
    <span title={note ?? undefined} className={`text-xs font-medium ${map.cls}`}>
      {map.text}
    </span>
  );
}

export function SourceChip({ c, primary = false }: { c: Citation; primary?: boolean }) {
  const label =
    c.source_type === "exchange_filing"
      ? `${c.exchange ?? "NSE"} filing${c.page ? ` · p.${c.page}` : ""}`
      : c.source_type === "xbrl"
        ? "XBRL"
        : c.source_type === "screener_table"
          ? "screener"
          : c.source_type === "web_profile"
            ? "Web"
            : c.source_type === "price_feed"
              ? "Prices"
              : c.source_type.replace("_", " ");
  return (
    <a
      href={c.url}
      target="_blank"
      rel="noopener noreferrer"
      title={c.title ?? c.url}
      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs ${
        primary ? "border-foreground/30 font-medium" : "border-border text-muted-foreground"
      }`}
    >
      📄 {label}
    </a>
  );
}

export function Timeline({ items }: { items: TimelineItem[] }) {
  if (items.length < 2) return null;
  return (
    <ol className="mt-3 space-y-1 border-l pl-3 text-xs text-muted-foreground">
      {items.map((t) => (
        <li key={t.filing_id}>
          <span className="font-medium capitalize text-foreground">{t.stage.replace("_", " ")}</span> ·{" "}
          {ist(t.at)} · {t.label}
        </li>
      ))}
    </ol>
  );
}
