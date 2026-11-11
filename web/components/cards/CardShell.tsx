"use client";
// The frame every card shares. Collapsed: eyebrow · serif headline · so-what · key figures · source/verification.
// Expanded (tap): the full body, event thread, next action, Ask chips, and Reviewed / Not useful buttons.
// No data fetching and no gestures here: the Brief wraps this with swipe/undo.
import type { ReactNode } from "react";
import { ChevronRight, Eye } from "lucide-react";
import type { Card, Figure } from "@/lib/types";
import { CATEGORY_LABEL, displayHeadline, istWhen } from "@/lib/format";
import { ImpactLabel } from "@/components/ui/signal";
import { FigureValue } from "./FigureValue";
import { SourceChip, Timeline, VerificationBadge } from "./primitives";
import { ClaimText } from "./ClaimLink";

function cardTime(card: Card): string | null {
  const t = card.timeline;
  if (!t.length) return null;
  const outcome = t.filter((x) => x.stage === "outcome").map((x) => x.at).sort()[0];
  const latest = [...t].map((x) => x.at).sort().at(-1)!;
  return outcome ?? latest;
}

function line(card: Card, metric: string) {
  const d = card.detail;
  return d?.kind === "results" ? d.lines.find((l) => l.metric === metric) : undefined;
}

function KeyFigures({ card }: { card: Card }) {
  const d = card.detail;
  const items: { label: string; f: Figure; delta?: Figure | null }[] = [];
  if (d?.kind === "results") {
    if (d.verification === "mismatch") return null;
    const top = line(card, "PAT") ?? d.lines[0];
    const second = line(card, "EBITDA margin") ?? line(card, "NII") ?? line(card, "Revenue");
    if (top) items.push({ label: top.metric, f: top.current, delta: top.yoy });
    if (second && second !== top) items.push({ label: second.metric, f: second.current, delta: second.yoy });
  } else if (d?.kind === "price_volume") {
    items.push({ label: "Move", f: d.move_pct });
    if (d.volume_ratio) items.push({ label: "Volume", f: d.volume_ratio });
  } else {
    for (const f of card.key_figures.slice(0, 2)) items.push({ label: f.label, f });
  }
  if (!items.length) return null;
  return (
    <p className="t-small mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
      {items.map(({ label, f, delta }) => (
        <span key={label} className="whitespace-nowrap">
          <span className="text-ink-3">{label} </span>
          <FigureValue f={f} signed={d?.kind === "price_volume" && label === "Move"} className="t-figure text-[14px]" />
          {delta && delta.value !== null && (
            <>
              {" "}
              <FigureValue f={delta} signed className="text-[13px] text-ink-2" />
              <span className="text-[12px] text-ink-3"> YoY</span>
            </>
          )}
        </span>
      ))}
    </p>
  );
}

export function CardShell({
  card,
  rank,
  expanded = true,
  onToggle,
  onWhy,
  actions,
  children,
}: {
  card: Card;
  rank?: number;
  expanded?: boolean;
  onToggle?: () => void;
  onWhy?: () => void;
  actions?: ReactNode;
  children?: ReactNode;
}) {
  const { headline, sub } = displayHeadline(card);
  const d = card.detail;
  const period = d?.kind === "results" ? d.quarter.label : null;
  const when = cardTime(card);
  const verification = d?.kind === "results" ? d.verification : null;
  const Head = onToggle ? "button" : "div";
  return (
    <article className="bg-surface px-4 py-3.5" data-card={card.id}>
      <div className="flex gap-3">
        {rank !== undefined && (
          <span className="t-small w-4 shrink-0 pt-px text-right font-medium text-ink-3">{rank}</span>
        )}
        <div className="min-w-0 flex-1">
          <header className="flex items-center gap-2">
            <p className="t-micro min-w-0 flex-1 truncate text-ink-3">
              <span className="text-ink">{card.symbol}</span> · {CATEGORY_LABEL[card.category] ?? card.category}
              {period ? ` · ${period}` : ""}
              {card.card_type === "what_to_watch" ? " · upcoming" : ""}
            </p>
            <ImpactLabel impact={card.impact} title={card.impact_reason?.text} />
          </header>
          <Head
            {...(onToggle ? { type: "button" as const, onClick: onToggle, "aria-expanded": expanded } : {})}
            className="mt-1 block w-full text-left"
          >
            <h3 className="t-headline text-ink">{headline}</h3>
            {sub && <p className="t-body mt-0.5 text-ink-2">{sub}</p>}
          </Head>
          {card.affects_drivers.length > 0 && (
            <p className="t-small mt-1 inline-flex items-center gap-1 text-ink-2">
              <Eye className="size-3.5" strokeWidth={1.75} /> affects: {card.affects_drivers.join(", ")}
            </p>
          )}
          {!expanded && <KeyFigures card={card} />}
          {expanded && children && <div className="mt-3">{children}</div>}
          {expanded && card.impact_reason && (
            <p className="t-small mt-3 text-ink-2">
              <span className="text-ink-3">Why {card.impact}: </span>
              <ClaimText claim={card.impact_reason} />
            </p>
          )}
          <footer className="t-small mt-2.5 flex flex-wrap items-center gap-x-2.5 gap-y-1.5 text-ink-3">
            {card.sources[0] && <SourceChip c={card.sources[0]} primary />}
            {expanded && card.sources.slice(1).map((s, i) => <SourceChip key={i} c={s} />)}
            {verification && <VerificationBadge state={verification} short={!expanded} />}
            {when && <span>{istWhen(when)}</span>}
            {onWhy && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onWhy();
                }}
                className="hit ml-auto inline-flex items-center font-medium text-ink-2"
              >
                Why #{rank ?? ""}
                <ChevronRight className="size-3.5" />
              </button>
            )}
          </footer>
          {expanded && <Timeline items={card.timeline} />}
          {expanded && card.next_action && (
            <p className="t-small mt-3">
              <span className="text-ink-3">Next: </span>
              {card.next_action}
            </p>
          )}
          {expanded && actions}
        </div>
      </div>
    </article>
  );
}
