"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AnimatePresence, m } from "framer-motion";
import { Check, ChevronRight, Info, RotateCcw, Send, ThumbsDown } from "lucide-react";
import { CardView } from "@/components/cards";
import { ErrorState, Notice, Skeleton } from "@/components/shell/StateView";
import { Tour } from "@/components/shell/Tour";
import { setAskContext, showToast } from "@/components/shell/ui-store";
import { SHOWCASE_LABEL } from "@/lib/demo";
import { CATEGORY_LABEL, CATEGORY_PLURAL, displayHeadline, isTodayIST, istClock, istDay, istTime, readTime } from "@/lib/format";
import { FALLBACK, queueFeedback, setMark, startVisit, touchVisit, useStored, write, type Mark, type Visit, type WindowKey } from "@/lib/store";
import type { BriefResponse, Card } from "@/lib/types";
import { CustomWindowSheet, HiddenSheet, ScopeSheet, SeasonSheet, TimeSavedSheet, WhySheet, type Scope } from "./sheets";
import { SwipeRow, type SwipeDir } from "./SwipeRow";
import { useBrief } from "./useBrief";
import { isStale } from "./stale";

const WINDOW_LABEL: Record<Exclude<WindowKey, "custom">, string> = { since: "Since last visit", "24h": "24h", "3d": "3d", "7d": "7d" };

export function BriefScreen({ gateDesktop = false }: { gateDesktop?: boolean }) {
  const [visit, setVisit] = useState<Visit | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [window_, setWindow] = useState<WindowKey>("since");
  const [customSince, setCustomSince] = useState<string | null>(null);
  const showcase = useStored<boolean>("showcase", FALLBACK.showcase);
  const tourDone = useStored<boolean>("tour", FALLBACK.tour);
  const [tourOpen, setTourOpen] = useState(true);

  useEffect(() => {
    // On "/" at desktop widths the landing shows instead; don't fetch for a hidden Brief.
    if (gateDesktop && window.matchMedia("(min-width: 1024px)").matches) return;
    const v = startVisit();
    // Visits live in localStorage (an external store) and can only be read after hydration.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setVisit(v);
    if (!v.previous) setWindow("7d");
    setEnabled(true);
    const onVis = () => document.visibilityState === "visible" && touchVisit();
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, [gateDesktop]);

  const b = useBrief({ window: window_, customSince, visit, showcase, enabled });
  const data = b.data;
  const marks = useStored<Record<string, Mark>>("marks", FALLBACK.marks);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [why, setWhy] = useState<{ card: Card; rank: number } | null>(null);
  const [scopeFor, setScopeFor] = useState<Card | null>(null);
  const [sheet, setSheet] = useState<null | "time" | "hidden" | "season" | "custom">(null);
  const dragged = useRef(false);

  const cards = data?.cards ?? [];
  const visible = cards.filter((c) => c.card_type !== "inline_chip" && !marks[c.id]);
  const chips = cards.filter((c) => c.card_type === "inline_chip" && !marks[c.id]);
  const reviewedToday = useMemo(
    () => Object.entries(marks).filter(([, mk]) => isTodayIST(mk.at)).sort((a, b2) => b2[1].at.localeCompare(a[1].at)),
    [marks],
  );

  const toggle = (id: string) => {
    if (dragged.current) return;
    setExpanded((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  };

  const markReviewed = useCallback((card: Card) => {
    setMark(card.id, { kind: "reviewed", at: new Date().toISOString(), symbol: card.symbol, category: card.category, headline: displayHeadline(card).headline });
    showToast({ text: `${card.symbol} marked reviewed`, actionLabel: "UNDO", onAction: () => setMark(card.id, null) });
  }, []);

  const markNotUseful = useCallback((card: Card) => {
    setMark(card.id, { kind: "not_useful", at: new Date().toISOString(), symbol: card.symbol, category: card.category, headline: displayHeadline(card).headline });
    setScopeFor(card);
  }, []);

  const chooseScope = useCallback(
    (scope: Scope) => {
      const card = scopeFor;
      setScopeFor(null);
      if (!card) return;
      const cat = CATEGORY_PLURAL[card.category] ?? (CATEGORY_LABEL[card.category] ?? card.category).toLowerCase();
      const text =
        scope === "event" ? `Hidden: this ${card.symbol} card` : scope === "category" ? `Fewer ${cat}, all stocks` : `Fewer ${card.symbol} ${cat}`;
      setMark(card.id, { kind: "not_useful", at: new Date().toISOString(), symbol: card.symbol, category: card.category, headline: displayHeadline(card).headline, scope });
      showToast({
        text,
        actionLabel: "UNDO",
        onAction: () => setMark(card.id, null),
        // The weight change applies only once the undo window has passed (PRODUCT §4).
        onExpire: () => {
          queueFeedback({
            useful: false,
            scope,
            symbol: scope === "category" ? null : card.symbol,
            category: scope === "event" ? null : card.category,
            event_id: scope === "event" ? card.event_id : null,
            at: new Date().toISOString(),
          });
        },
      });
    },
    [scopeFor],
  );

  const onCommit = (card: Card) => (dir: SwipeDir) => (dir === "right" ? markReviewed(card) : markNotUseful(card));

  // Ask bar: three suggestions that jump to the answer on this screen.
  useEffect(() => {
    const top = visible[0];
    setAskContext({
      placeholder: "Ask about today's Brief…",
      chips: [
        ...(top
          ? [{ label: `What's behind #1 — ${top.symbol}?`, run: () => { setExpanded((s) => new Set(s).add(top.id)); document.querySelector(`[data-card="${CSS.escape(top.id)}"]`)?.scrollIntoView({ behavior: "smooth", block: "start" }); } }]
          : []),
        ...(data?.season ? [{ label: `Who has reported ${data.season.quarter.label}?`, run: () => setSheet("season") }] : []),
        { label: "What did FINN hide, and why?", run: () => setSheet("hidden") },
      ].slice(0, 3),
    });
    return () => setAskContext(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible[0]?.id, data?.season?.quarter.label]);

  const sinceIso = b.since;
  const title = showcase
    ? "Showcase replay"
    : window_ === "since" && sinceIso
      ? "Since your last visit"
      : window_ === "custom" && customSince
        ? `Since ${istDay(customSince)}`
        : window_ === "24h"
          ? "Last 24 hours"
          : window_ === "3d"
            ? "Last 3 days"
            : "Last 7 days";
  const sinceLabel = showcase && data?.showcase ? SHOWCASE_LABEL : window_ === "since" && sinceIso ? (isTodayIST(sinceIso) ? istClock(sinceIso) : `${istDay(sinceIso)}, ${istClock(sinceIso)}`) : null;
  const n = visible.length;
  const stale = data && !showcase && b.source !== "fallback" ? isStale(data.data_as_of) : false;

  return (
    <div className="flex flex-1 flex-col">
      <TopBar showcase={showcase} />
      {showcase && (
        <Notice
          tone="warn"
          action={
            <button type="button" onClick={() => write("showcase", false)} className="h-9 shrink-0 font-semibold underline underline-offset-4">
              Back to live
            </button>
          }
        >
          Showcase replay · {SHOWCASE_LABEL} · a saved results day, not live
        </Notice>
      )}
      {b.source === "fallback" && (
        <Notice
          tone="warn"
          action={
            b.liveReady ? (
              <button type="button" onClick={b.showLive} className="h-9 shrink-0 rounded-full bg-ink px-3 font-semibold text-paper">
                Show live
              </button>
            ) : undefined
          }
        >
          {b.liveReady ? "Your live Brief is ready." : `Showing the saved showcase day (${SHOWCASE_LABEL}) while live data loads…`}
        </Notice>
      )}

      <header className="px-4 pb-3 pt-4">
        <h1 className="t-display">{title}</h1>
        {data ? (
          <>
            <p className="t-small mt-1.5 text-ink-2">
              {sinceLabel && <>{sinceLabel} · </>}
              {n === 0 ? "nothing new matters" : `${n} ${n === 1 ? "thing matters" : "things matter"}`}
              {n > 0 && <> · {readTime(data.counts.read_seconds)}</>}
            </p>
            <button type="button" onClick={() => setSheet("time")} className="t-small mt-0.5 inline-flex items-center gap-1 text-left text-ink-2">
              {data.hidden_total} routine filings hidden · est. {data.counts.est_minutes_saved} min saved
              <Info className="size-3.5 text-ink-3" strokeWidth={1.75} />
            </button>
            <Freshness b={b} data={data} stale={stale} />
          </>
        ) : (
          <div className="mt-2 space-y-1.5" aria-hidden>
            <div className="h-3 w-56 animate-pulse rounded bg-surface-2" />
            <div className="h-3 w-44 animate-pulse rounded bg-surface-2" />
          </div>
        )}
      </header>

      {!showcase && (
        <div className="no-scrollbar flex gap-2 overflow-x-auto px-4 pb-3" role="tablist" aria-label="Window">
          {(visit?.previous ? (["since", "24h", "3d", "7d"] as const) : (["24h", "3d", "7d"] as const)).map((w) => (
            <Chip key={w} on={window_ === w} onClick={() => setWindow(w)}>
              {WINDOW_LABEL[w]}
            </Chip>
          ))}
          <Chip on={window_ === "custom"} onClick={() => setSheet("custom")}>
            {window_ === "custom" && customSince ? `Since ${istDay(customSince)}` : "Custom"}
          </Chip>
        </div>
      )}

      {data?.season && data.season.reported + data.season.rows.filter((r) => r.status === "scheduled").length > 0 && (
        <button
          type="button"
          onClick={() => setSheet("season")}
          className="flex min-h-12 items-center gap-3 border-y border-rule px-4 py-2 text-left"
        >
          <span className="min-w-0 flex-1">
            <span className="t-small block">
              <span className="font-semibold">{data.season.quarter.label} results</span>
              <span className="text-ink-2"> · {data.season.reported} of {data.season.total} reported</span>
            </span>
            <span className="t-small block text-ink-2">
              PAT ▲{data.season.pat_up} ▼{data.season.pat_down} · EBITDA margin ▲{data.season.margin_up} ▼{data.season.margin_down} YoY
            </span>
          </span>
          <ChevronRight className="size-4 shrink-0 text-ink-3" />
        </button>
      )}

      <main className="flex-1">
        {!data && !b.error && <Skeleton rows={3} label="Loading your Brief" />}
        {!data && b.error && (
          <ErrorState
            title={b.error.waking ? "FINN's server is waking up" : "Couldn't load your Brief"}
            detail={b.error.waking ? "The free-tier server sleeps when idle and takes up to a minute to wake." : b.error.message}
            offline={b.error.status === 0}
            onRetry={b.refresh}
          />
        )}
        {data && (
          <>
            <ol className="divide-y divide-rule border-b border-rule" data-tour="brief-list">
              <AnimatePresence initial={false}>
                {visible.map((card, i) => (
                  <m.li
                    key={card.id}
                    exit={{ height: 0, opacity: 0, transition: { duration: 0.2 } }}
                    className="overflow-hidden"
                    data-tour={i === 0 ? "top-card" : undefined}
                  >
                    <SwipeRow onCommit={onCommit(card)} draggedRef={dragged}>
                      <CardView
                        card={card}
                        rank={i + 1}
                        expanded={expanded.has(card.id)}
                        onToggle={() => toggle(card.id)}
                        onWhy={() => setWhy({ card, rank: i + 1 })}
                        actions={<CardActions onReviewed={() => markReviewed(card)} onNotUseful={() => markNotUseful(card)} />}
                      />
                    </SwipeRow>
                  </m.li>
                ))}
              </AnimatePresence>
            </ol>
            {chips.length > 0 && (
              <section className="border-b border-rule bg-surface px-4 py-3">
                <p className="t-micro text-ink-3">Also</p>
                <ul className="mt-1.5 space-y-1.5">
                  {chips.map((c) => (
                    <li key={c.id}>
                      <CardView card={c} />
                    </li>
                  ))}
                </ul>
              </section>
            )}
            <CaughtUp n={n} sinceLabel={sinceLabel} window={window_} showcase={showcase} onWiden={() => setWindow("7d")} />
            <div className="border-t border-rule">
              <ReviewedToday entries={reviewedToday} cards={cards} />
              <button type="button" onClick={() => setSheet("hidden")} className="flex min-h-12 w-full items-center gap-2 border-t border-rule px-4 text-left">
                <span className="flex-1 text-[15px]">Hidden ({data.hidden_total})</span>
                <span className="t-small text-ink-3">routine filings</span>
                <ChevronRight className="size-4 text-ink-3" />
              </button>
            </div>
            {!showcase && (
              <Link href="/rules#telegram" className="mx-4 mt-6 flex min-h-12 items-center gap-3 rounded-xl border border-rule px-4 py-2.5">
                <Send className="size-[18px] shrink-0 text-ink-2" strokeWidth={1.5} />
                <span className="min-w-0 flex-1">
                  <span className="block text-[15px] font-medium">Get these on Telegram</span>
                  <span className="t-small block text-ink-2">Results and big moves on your holdings, at most 5 a day.</span>
                </span>
                <ChevronRight className="size-4 text-ink-3" />
              </Link>
            )}
            <p className="t-small px-4 pb-6 pt-4 text-ink-3">
              FINN reads exchange filings only. Every number opens its source; tap it.
            </p>
          </>
        )}
      </main>

      {data && visible.length > 0 && !tourDone && tourOpen && <Tour onDone={() => setTourOpen(false)} />}
      <WhySheet card={why?.card ?? null} rank={why?.rank ?? 1} onClose={() => setWhy(null)} />
      <ScopeSheet card={scopeFor} onChoose={chooseScope} />
      <TimeSavedSheet open={sheet === "time"} counts={data?.counts ?? null} onClose={() => setSheet(null)} />
      <HiddenSheet open={sheet === "hidden"} data={data} onClose={() => setSheet(null)} />
      <SeasonSheet open={sheet === "season"} season={data?.season ?? null} onClose={() => setSheet(null)} />
      <CustomWindowSheet
        open={sheet === "custom"}
        onClose={() => setSheet(null)}
        onPick={(iso) => {
          setCustomSince(iso);
          setWindow("custom");
          setSheet(null);
        }}
      />
    </div>
  );
}

function TopBar({ showcase }: { showcase: boolean }) {
  return (
    <div className="flex h-12 items-center gap-2 px-4">
      <span className="font-serif text-[22px] font-semibold tracking-tight">FINN</span>
      <span className="flex-1" />
      <label className="t-small inline-flex h-11 cursor-pointer items-center gap-2 text-ink-2" data-tour="showcase">
        Showcase replay
        <button
          type="button"
          role="switch"
          aria-checked={showcase}
          onClick={() => write("showcase", !showcase)}
          className={`relative h-6 w-10 rounded-full transition-colors ${showcase ? "bg-ink" : "bg-rule"}`}
        >
          <span className={`absolute top-0.5 size-5 rounded-full bg-surface shadow-sm transition-transform ${showcase ? "translate-x-[18px]" : "translate-x-0.5"}`} />
        </button>
      </label>
    </div>
  );
}

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={on}
      onClick={onClick}
      className={`hit h-8 shrink-0 rounded-full border px-3.5 text-[13px] ${on ? "border-ink bg-ink font-medium text-paper" : "border-rule text-ink-2"}`}
    >
      {children}
    </button>
  );
}

function Freshness({ b, data, stale }: { b: ReturnType<typeof useBrief>; data: BriefResponse; stale: boolean }) {
  const asOf = data.data_as_of;
  const label = data.showcase ? `Saved day · data as of ${istDay(asOf ?? data.showcase)} ${asOf ? istTime(asOf) : ""} IST` : asOf ? `Data as of ${isTodayIST(asOf) ? "" : istDay(asOf) + " "}${istTime(asOf)} IST` : "Freshness unknown";
  return (
    <p className={`t-micro mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 ${stale ? "text-warn" : "text-ink-3"}`}>
      <span>{label}</span>
      {stale && <span>· filings may be behind</span>}
      {!data.showcase && b.refreshing && <span className="normal-case tracking-normal">· {b.slow ? "waking the server…" : "updating…"}</span>}
      {!data.showcase && !b.refreshing && b.error && (
        <button type="button" onClick={b.refresh} className="hit inline-flex items-center gap-1 normal-case tracking-normal text-warn">
          · couldn&apos;t refresh <RotateCcw className="size-3" /> retry
        </button>
      )}
    </p>
  );
}

function CardActions({ onReviewed, onNotUseful }: { onReviewed: () => void; onNotUseful: () => void }) {
  return (
    <div className="mt-4 grid grid-cols-2 gap-2">
      <button type="button" onClick={onReviewed} className="inline-flex h-11 items-center justify-center gap-1.5 rounded-xl border border-rule text-[14px] font-medium">
        <Check className="size-4" strokeWidth={2} /> Reviewed
      </button>
      <button type="button" onClick={onNotUseful} className="inline-flex h-11 items-center justify-center gap-1.5 rounded-xl border border-rule text-[14px] text-ink-2">
        <ThumbsDown className="size-4" strokeWidth={1.75} /> Not useful
      </button>
    </div>
  );
}

function CaughtUp({ n, sinceLabel, window, showcase, onWiden }: { n: number; sinceLabel: string | null; window: WindowKey; showcase: boolean; onWiden: () => void }) {
  const span = showcase ? "on this day" : window === "since" && sinceLabel ? `since ${sinceLabel}` : window === "24h" ? "in the last 24 hours" : window === "3d" ? "in the last 3 days" : window === "7d" ? "in the last 7 days" : "in this window";
  return (
    <section className={n === 0 ? "px-4 py-10" : "px-4 py-6"}>
      <p className={n === 0 ? "t-title" : "t-headline"}>You&apos;re caught up.</p>
      <p className="t-small mt-1 text-ink-2">Nothing {n === 0 ? "" : "else "}material {span}.</p>
      {n === 0 && !showcase && window !== "7d" && (
        <button type="button" onClick={onWiden} className="t-small mt-3 inline-flex h-10 items-center rounded-full border border-rule px-4 font-medium">
          See the last 7 days
        </button>
      )}
    </section>
  );
}

function ReviewedToday({ entries, cards }: { entries: [string, Mark][]; cards: Card[] }) {
  const [open, setOpen] = useState(false);
  if (!entries.length) return null;
  return (
    <div>
      <button type="button" onClick={() => setOpen(!open)} className="flex min-h-12 w-full items-center gap-2 px-4 text-left" aria-expanded={open}>
        <span className="flex-1 text-[15px]">Reviewed today ({entries.length})</span>
        <ChevronRight className={`size-4 text-ink-3 transition-transform ${open ? "rotate-90" : ""}`} />
      </button>
      {open && (
        <ul className="divide-y divide-rule border-t border-rule">
          {entries.map(([id, mk]) => {
            const card = cards.find((c) => c.id === id);
            return (
              <li key={id} className="flex items-center gap-3 px-4 py-2.5">
                <span className="min-w-0 flex-1">
                  <span className="t-micro text-ink-3">
                    <span className="text-ink">{mk.symbol}</span> · {mk.kind === "reviewed" ? "Reviewed" : "Not useful"} · {istTime(mk.at)}
                  </span>
                  <span className="t-small block truncate text-ink-2">{card ? displayHeadline(card).headline : mk.headline}</span>
                </span>
                <button type="button" onClick={() => setMark(id, null)} className="t-small h-10 shrink-0 rounded-full border border-rule px-3 font-medium">
                  Restore
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
