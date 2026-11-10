// The frame every card shares: ticker · category · impact, headline, so-what, body, sources, timeline, freshness.
// No data fetching and no gestures: the Brief wraps this with swipe/undo.
import type { ReactNode } from "react";
import type { Card } from "@/lib/types";
import { CATEGORY_LABEL, ist } from "@/lib/format";
import { ImpactTag, SourceChip, Timeline } from "./primitives";

export function CardShell({ card, children, showTimeline = true }: { card: Card; children?: ReactNode; showTimeline?: boolean }) {
  return (
    <article className="rounded-2xl border bg-card p-4 text-card-foreground shadow-sm">
      <header className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-semibold tracking-wide">{card.symbol}</span>
        <span className="text-muted-foreground">· {CATEGORY_LABEL[card.category] ?? card.category}</span>
        <ImpactTag impact={card.impact} title={card.impact_reason?.text} />
        {card.affects_drivers.length > 0 && (
          <span className="text-muted-foreground">👁 affects: {card.affects_drivers.join(", ")}</span>
        )}
      </header>
      <h2 className="mt-2 text-base font-semibold leading-snug">{card.headline}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{card.so_what}</p>
      {card.impact_reason && (
        <p className="mt-1 text-xs text-muted-foreground">
          Why {card.impact}: {card.impact_reason.text}
          {card.impact_reason.status !== "verified" && " (unverified)"}
        </p>
      )}
      {children && <div className="mt-3">{children}</div>}
      {card.sources.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {card.sources.map((s, i) => (
            <SourceChip key={`${s.url}-${i}`} c={s} primary={i === 0} />
          ))}
        </div>
      )}
      {showTimeline && <Timeline items={card.timeline} />}
      <footer className="mt-3 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground">
        {card.next_action ? <span>Next: {card.next_action}</span> : <span />}
        <span>Data as of {ist(card.as_of)}</span>
      </footer>
    </article>
  );
}
