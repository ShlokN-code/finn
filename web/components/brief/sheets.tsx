"use client";
// Brief sheets: Why #N, Not-useful scope, est. time saved, hidden drawer, season scoreboard, custom window.
import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, ChevronDown, ChevronRight } from "lucide-react";
import { Sheet } from "@/components/shell/Sheet";
import { FigureValue, VERIFICATION } from "@/components/cards";
import { CATEGORY_LABEL, CATEGORY_PLURAL, istDay, istWhen, readTime } from "@/lib/format";
import type { BriefCounts, BriefResponse, Card, ScoreBreakdown, SeasonStrip } from "@/lib/types";

const FACTORS: { key: keyof ScoreBreakdown; label: string; what: string }[] = [
  { key: "category_weight", label: "Category", what: "How much this kind of filing usually matters, after your feedback" },
  { key: "position_weight", label: "Position", what: "Grows with the holding's share of your portfolio" },
  { key: "relevance", label: "Relevance", what: "Impact on the business; drivers you watch" },
  { key: "novelty", label: "Novelty", what: "New information beats repeat filings" },
  { key: "surprise", label: "Surprise", what: "Deviation from the stock's own trend" },
];

export function WhySheet({ card, rank, onClose }: { card: Card | null; rank: number; onClose: () => void }) {
  const s = card?.score;
  return (
    <Sheet open={!!card} onClose={onClose} eyebrow={`Why is this #${rank}?`} title={card ? `${card.symbol} · ${CATEGORY_LABEL[card.category] ?? card.category}` : ""}>
      {s && (
        <div>
          <p className="t-small text-ink-2">Ranked by importance, not time. Each factor is a plain multiplier, computed on the server.</p>
          <ul className="mt-3 divide-y divide-rule border-y border-rule">
            {FACTORS.map((f) => (
              <li key={f.key} className="flex items-baseline gap-3 py-2.5">
                <div className="min-w-0 flex-1">
                  <p className="text-[15px]">{f.label}</p>
                  <p className="t-small text-ink-3">{f.what}</p>
                </div>
                <span className="t-figure">×{(s[f.key] as number).toFixed(2)}</span>
              </li>
            ))}
            <li className="flex items-baseline gap-3 py-2.5">
              <p className="min-w-0 flex-1 text-[15px] font-semibold">Score</p>
              <span className="t-figure font-semibold">{s.total.toFixed(2)}</span>
            </li>
          </ul>
          {s.notes.length > 0 && (
            <ul className="t-small mt-3 space-y-1 text-ink-2">
              {s.notes.map((n, i) => (
                <li key={i}>· {n}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Sheet>
  );
}

export type Scope = "stock_category" | "category" | "event";
export function ScopeSheet({
  card,
  onChoose,
}: {
  card: Card | null;
  onChoose: (scope: Scope) => void;
}) {
  const cat = card ? (CATEGORY_PLURAL[card.category] ?? (CATEGORY_LABEL[card.category] ?? card.category).toLowerCase()) : "";
  const critical = card && ["results", "mna", "management_change"].includes(card.category);
  const opts: { scope: Scope; label: string; sub: string }[] = card
    ? [
        { scope: "event", label: "Just this one", sub: "Hide this card only" },
        { scope: "stock_category", label: `This stock`, sub: `Fewer ${cat} from ${card.symbol}` },
        { scope: "category", label: "All stocks", sub: `Fewer ${cat} from every holding` },
      ]
    : [];
  return (
    <Sheet open={!!card} onClose={() => onChoose("event")} eyebrow="Not useful" title="Show less of…">
      <ul className="space-y-2">
        {opts.map((o) => (
          <li key={o.scope}>
            <button
              type="button"
              onClick={() => onChoose(o.scope)}
              className="flex min-h-14 w-full items-center gap-3 rounded-xl border border-rule px-4 py-2.5 text-left hover:bg-surface-2"
            >
              <span className="min-w-0 flex-1">
                <span className="block text-[15px] font-medium">{o.label}</span>
                <span className="t-small block text-ink-2">{o.sub}</span>
              </span>
              <ChevronRight className="size-4 text-ink-3" />
            </button>
          </li>
        ))}
      </ul>
      <p className="t-small mt-3 text-ink-3">
        Each tap lowers the weight ×0.8 after the 5-second undo. Every adjustment is listed in Rules with Reset.
        {critical && " Results, M&A and management changes keep a floor — they can never be fully hidden."}
      </p>
    </Sheet>
  );
}

export function TimeSavedSheet({ open, counts, onClose }: { open: boolean; counts: BriefCounts | null; onClose: () => void }) {
  return (
    <Sheet open={open} onClose={onClose} eyebrow="How we estimate it" title={counts ? `est. ${counts.est_minutes_saved} min saved` : ""}>
      {counts && (
        <div className="space-y-3">
          <dl className="t-small grid grid-cols-[1fr_auto] gap-x-3 gap-y-1.5">
            <dt className="text-ink-2">Routine filings hidden</dt>
            <dd className="t-figure text-[13px]">{counts.hidden_filings}</dd>
            <dt className="text-ink-2">Material filings in this window</dt>
            <dd className="t-figure text-[13px]">{counts.material_filings}</dd>
            <dt className="text-ink-2">Cards · one-liners · chips</dt>
            <dd className="t-figure text-[13px]">
              {counts.cards} · {counts.one_liners} · {counts.chips}
            </dd>
            <dt className="text-ink-2">Time to read this Brief</dt>
            <dd className="t-figure text-[13px]">{readTime(counts.read_seconds)}</dd>
          </dl>
          <p className="rounded-xl bg-surface-2 p-3 font-mono text-[12px] leading-[18px]">{counts.formula}</p>
          <p className="t-small text-ink-3">An estimate, not a measurement — it assumes you&apos;d otherwise open each filing.</p>
        </div>
      )}
    </Sheet>
  );
}

export function HiddenSheet({ open, data, onClose }: { open: boolean; data: BriefResponse | null; onClose: () => void }) {
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const groups = data ? Object.entries(data.hidden) : [];
  return (
    <Sheet open={open} onClose={onClose} eyebrow="Hidden" title={`${data?.hidden_total ?? 0} routine filings`}>
      <p className="t-small text-ink-2">Kept out of your Brief because they don&apos;t change the picture. Every one still opens.</p>
      <ul className="mt-3 divide-y divide-rule border-y border-rule">
        {groups.map(([g, n]) => {
          const items = data!.hidden_items.filter((i) => i.group === g);
          const isOpen = openGroup === g;
          return (
            <li key={g}>
              <button
                type="button"
                onClick={() => setOpenGroup(isOpen ? null : g)}
                className="flex min-h-12 w-full items-center gap-3 py-2 text-left"
                aria-expanded={isOpen}
              >
                <span className="min-w-0 flex-1 text-[15px]">{g}</span>
                <span className="t-figure text-[13px] text-ink-2">{n}</span>
                <ChevronDown className={`size-4 text-ink-3 transition-transform ${isOpen ? "rotate-180" : ""}`} />
              </button>
              {isOpen && (
                <ul className="pb-2">
                  {items.map((i) => (
                    <li key={i.id}>
                      <a
                        href={i.url ?? "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="t-small flex gap-3 rounded-lg px-2 py-2 hover:bg-surface-2"
                      >
                        <span className="w-24 shrink-0 font-semibold">{i.symbol}</span>
                        <span className="min-w-0 flex-1 text-ink-2">
                          <span className="line-clamp-2">{i.subject}</span>
                          <span className="text-ink-3">
                            {istWhen(i.filed_at)}
                            {i.url?.includes("/ixbrl/") ? " · iXBRL view" : i.url?.toLowerCase().endsWith(".xml") ? " · raw XBRL" : ""}
                          </span>
                        </span>
                        <ArrowUpRight className="mt-0.5 size-3.5 shrink-0 text-ink-3" />
                      </a>
                    </li>
                  ))}
                  {items.length < (n ?? 0) && <li className="t-small px-2 py-1 text-ink-3">Showing the newest {items.length}.</li>}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
    </Sheet>
  );
}

const STATUS_LABEL = { reported: "Reported", scheduled: "Board meeting set", awaited: "Awaited" } as const;

export function SeasonSheet({ open, season, onClose }: { open: boolean; season: SeasonStrip | null; onClose: () => void }) {
  return (
    <Sheet open={open} onClose={onClose} eyebrow="Results season" title={season ? `${season.quarter.label} scoreboard` : ""}>
      {season && (
        <>
          <p className="t-small text-ink-2">
            {season.reported} of {season.total} holdings reported · {season.cross_checked} cross-checked against screener.
            YoY, consolidated. Tap a number for its source.
          </p>
          <table className="mt-3 w-full text-[13px] leading-[18px]">
            <thead>
              <tr className="text-left text-ink-3">
                <th className="py-1.5 font-normal">Stock</th>
                <th className="py-1.5 text-right font-normal">Revenue</th>
                <th className="py-1.5 text-right font-normal">PAT</th>
                <th className="py-1.5 text-right font-normal">Margin</th>
              </tr>
            </thead>
            <tbody>
              {season.rows.map((r) => (
                <tr key={r.symbol} className="border-t border-rule align-top">
                  <td className="py-2 pr-2">
                    {r.event_id ? (
                      <Link href={`/e/${encodeURIComponent(r.event_id)}`} className="font-semibold underline decoration-ink-3/40 underline-offset-4">
                        {r.symbol}
                      </Link>
                    ) : (
                      <span className="font-semibold">{r.symbol}</span>
                    )}
                    <span className="block text-ink-3">
                      {r.status === "reported" && r.reported_at ? istDay(r.reported_at) : STATUS_LABEL[r.status]}
                      {r.verification && (
                        <span className={VERIFICATION[r.verification].cls}> · {VERIFICATION[r.verification].short}</span>
                      )}
                    </span>
                  </td>
                  {r.status === "reported" && !r.verification ? (
                    <td colSpan={3} className="py-2 text-right text-ink-3">
                      Numbers being checked
                    </td>
                  ) : r.status === "reported" && r.verification !== "mismatch" ? (
                    <>
                      <td className="py-2 text-right">{r.revenue_yoy ? <FigureValue f={r.revenue_yoy} signed /> : <span className="text-ink-3">n/m</span>}</td>
                      <td className="py-2 text-right">{r.pat_yoy ? <FigureValue f={r.pat_yoy} signed /> : <span className="text-ink-3">n/m</span>}</td>
                      <td className="py-2 text-right">{r.margin_yoy ? <FigureValue f={r.margin_yoy} signed /> : <span className="text-ink-3">—</span>}</td>
                    </>
                  ) : (
                    <td colSpan={3} className="py-2 text-right text-ink-3">
                      {r.verification === "mismatch" ? "Open the filing" : "—"}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="t-small mt-3 text-ink-3">Banks and NBFCs show NII instead of revenue and no EBITDA margin.</p>
        </>
      )}
    </Sheet>
  );
}

export function CustomWindowSheet({ open, onClose, onPick }: { open: boolean; onClose: () => void; onPick: (iso: string) => void }) {
  const [d, setD] = useState("");
  return (
    <Sheet
      open={open}
      onClose={onClose}
      eyebrow="Custom window"
      title="Show everything since…"
      footer={
        <button
          type="button"
          disabled={!d}
          onClick={() => onPick(new Date(`${d}T00:00:00+05:30`).toISOString())}
          className="h-12 w-full rounded-xl bg-ink text-[15px] font-medium text-paper disabled:opacity-40"
        >
          Show Brief
        </button>
      }
    >
      <label className="t-micro text-ink-3" htmlFor="since-date">
        Start date (IST)
      </label>
      <input
        id="since-date"
        type="date"
        value={d}
        onChange={(e) => setD(e.target.value)}
        className="mt-1 h-12 w-full rounded-xl border border-rule bg-paper px-3 text-[16px]"
      />
    </Sheet>
  );
}
