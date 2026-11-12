"use client";
// Portfolio: holdings with weight, last close, day change, 1-month sparkline and a status dot (POST /portfolio, code
// only), their latest event from the Brief, upcoming events and the results-season scoreboard; paste/CSV import
// (stored on the phone).
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { useBrief } from "@/components/brief/useBrief";
import { Sheet } from "@/components/shell/Sheet";
import { Notice, Skeleton } from "@/components/shell/StateView";
import { setAskContext } from "@/components/shell/ui-store";
import { Dot, IMPACT, type Tone } from "@/components/ui/signal";
import { Sparkline } from "@/components/cards/Sparkline";
import { SeasonSheet } from "@/components/brief/sheets";
import { usePortfolio } from "./usePortfolio";
import { api } from "@/lib/client";
import { CATEGORY_LABEL, displayHeadline, istWhen } from "@/lib/format";
import { effectiveWeights, parseHoldings } from "@/lib/holdings";
import { FALLBACK, isDemoPortfolio, read, useHydrated, useStored, write, type LocalHolding } from "@/lib/store";
import type { Card, DriversSection, HoldingStatus, PortfolioResponse, PortfolioRow } from "@/lib/types";

const STATUS: Record<HoldingStatus["level"], { tone: Tone; word: string }> = {
  intact: { tone: "pos", word: "Intact" },
  watch: { tone: "warn", word: "Watch" },
  pressure: { tone: "neg", word: "Under pressure" },
  unknown: { tone: "muted", word: "No data" },
};
const inr = (v: number) => `₹${v.toLocaleString("en-IN", { maximumFractionDigits: v < 100 ? 2 : 1 })}`;
function Move({ pct }: { pct: number | null }) {
  if (pct === null) return <span className="text-ink-3">—</span>;
  return <span className="tabular-nums">{pct >= 0 ? "▲" : "▼"} {Math.abs(pct).toFixed(1)}%</span>;
}

function latestAt(c: Card): string {
  return [...c.timeline.map((t) => t.at)].sort().at(-1) ?? c.as_of;
}

export function PortfolioScreen() {
  const holdings = useStored<LocalHolding[]>("holdings", FALLBACK.holdings);
  const enabled = useHydrated();
  const router = useRouter();
  const b = useBrief({ window: "7d", customSince: null, visit: null, showcase: false, enabled });
  const [retry, setRetry] = useState(0);
  const pf = usePortfolio(holdings, enabled, retry);
  const prow = useMemo(() => new Map((pf.data?.rows ?? []).map((r) => [r.symbol, r])), [pf.data]);
  const [season, setSeason] = useState(false);
  const [editing, setEditing] = useState(false);
  const demo = isDemoPortfolio(holdings);
  const weights = useMemo(() => effectiveWeights(holdings), [holdings]);

  const latest = useMemo(() => {
    const m = new Map<string, Card>();
    for (const c of b.data?.cards ?? []) {
      if (c.card_type === "inline_chip") continue;
      const cur = m.get(c.symbol);
      if (!cur || latestAt(c) > latestAt(cur)) m.set(c.symbol, c);
    }
    return m;
  }, [b.data]);

  const rows = [...weights].sort((a, b2) => (b2.weight_pct ?? 0) - (a.weight_pct ?? 0) || a.symbol.localeCompare(b2.symbol));

  useEffect(() => {
    const top = rows[0]?.symbol;
    setAskContext({
      placeholder: "Ask about your holdings…",
      chips: [
        ...(top ? [{ label: `Research ${top}, your largest holding`, run: () => router.push(`/research/${top}`) }] : []),
        { label: "Which holdings had news this week?", run: () => document.getElementById("holdings")?.scrollIntoView({ behavior: "smooth" }) },
        { label: "Change my holdings", run: () => setEditing(true) },
      ],
    });
    return () => setAskContext(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows[0]?.symbol]);

  return (
    <div className="pb-8">
      <header className="px-4 pb-3 pt-6">
        <h1 className="t-display">Portfolio</h1>
        <p className="t-small mt-1 text-ink-2">
          {holdings.length} holdings · {demo ? "demo portfolio" : "yours"} · stored only on this phone
        </p>
        <div className="mt-3 flex gap-2">
          <button type="button" onClick={() => setEditing(true)} className="h-10 rounded-full border border-rule px-4 text-[14px] font-medium">
            {demo ? "Use my holdings" : "Edit holdings"}
          </button>
          {!demo && (
            <button
              type="button"
              onClick={() => write("holdings", null)}
              className="h-10 rounded-full px-3 text-[14px] text-ink-2 underline underline-offset-4"
            >
              Back to demo
            </button>
          )}
        </div>
      </header>
      {b.error && !b.data && <Notice tone="warn">Couldn&apos;t load this week&apos;s events — {b.error.waking ? "the server is waking up" : b.error.message}.</Notice>}
      {pf.error && (
        <Notice tone="warn">
          {pf.data ? "Showing prices saved on this phone" : "Prices didn't load"} —{" "}
          {pf.error.waking ? "the server is waking up" : pf.error.message}.{" "}
          <button type="button" className="underline underline-offset-4" onClick={() => setRetry((n) => n + 1)}>
            Retry
          </button>
        </Notice>
      )}
      <p className="t-micro px-4 pb-2 text-ink-3">
        Weight · close · day · 1 month
        {pf.data?.prices_as_of
          ? ` · ${new Date(`${pf.data.prices_as_of}T00:00:00+05:30`).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" })} close`
          : ""}
        {pf.loading && !pf.data ? " · loading prices…" : pf.loading && pf.cached ? " · updating…" : ""}
      </p>
      {!b.data && !b.error ? (
        <Skeleton rows={4} label="Loading holdings" />
      ) : (
        <ul id="holdings" className="divide-y divide-rule border-y border-rule bg-surface">
          {rows.map((h) => {
            const c = latest.get(h.symbol);
            const impact = c?.impact ? IMPACT[c.impact] : null;
            const p = prow.get(h.symbol);
            return (
              <li key={h.symbol}>
                <Link
                  href={c ? `/e/${encodeURIComponent(c.id)}` : `/research/${encodeURIComponent(h.symbol)}`}
                  className="flex min-h-14 items-start gap-3 px-4 py-3"
                >
                  <span className="min-w-0 flex-1">
                    <span className="flex items-baseline gap-2">
                      {p && <StatusDot p={p} />}
                      <span className="text-[15px] font-semibold">{h.symbol}</span>
                      {h.quantity !== null && <span className="t-small text-ink-3">{h.quantity.toLocaleString("en-IN")} sh</span>}
                    </span>
                    {p && <PriceLine p={p} />}
                    {p && p.status.level !== "intact" && p.status.level !== "unknown" && (
                      <span className="t-small block text-ink-3">{p.status.reason}</span>
                    )}
                    {c ? (
                      <span className="t-small mt-0.5 flex items-start gap-1.5 text-ink-2">
                        {impact && <Dot tone={impact.tone} className="mt-[7px]" />}
                        <span className="min-w-0">
                          <span className="line-clamp-2">
                            {CATEGORY_LABEL[c.category] ?? c.category}: {displayHeadline(c).headline}
                          </span>
                          <span className="text-ink-3">{istWhen(latestAt(c))}</span>
                        </span>
                      </span>
                    ) : (
                      <span className="t-small mt-0.5 block text-ink-3">Nothing material in the last 7 days</span>
                    )}
                  </span>
                  <span className="t-figure shrink-0 text-[14px]">{h.weight_pct !== null ? `${h.weight_pct}%` : "—"}</span>
                  <ChevronRight className="mt-0.5 size-4 shrink-0 text-ink-3" />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
      {holdings.some((h) => h.weight_pct === null) && (
        <p className="t-small px-4 pt-2 text-ink-3">
          Holdings entered as share quantities split the remaining weight equally.
        </p>
      )}
      {pf.data && <Upcoming data={pf.data} />}
      {pf.data?.season && (
        <section className="pt-6">
          <p className="t-micro px-4 pb-2 text-ink-3">Results season</p>
          <button type="button" onClick={() => setSeason(true)} className="flex w-full items-center gap-2 border-y border-rule bg-surface px-4 py-3 text-left">
            <span className="flex-1 text-[15px]">
              {pf.data.season.quarter.label}: {pf.data.season.reported}/{pf.data.season.total} reported ·{" "}
              {pf.data.season.cross_checked} cross-checked · PAT up {pf.data.season.pat_up}, down {pf.data.season.pat_down}
            </span>
            <ChevronRight className="size-4 shrink-0 text-ink-3" />
          </button>
          <SeasonSheet open={season} season={pf.data.season} onClose={() => setSeason(false)} />
        </section>
      )}
      <Watching symbols={rows.map((r) => r.symbol)} />

      <ImportSheet open={editing} onClose={() => setEditing(false)} current={holdings} demo={demo} />
    </div>
  );
}

function StatusDot({ p }: { p: PortfolioRow }) {
  const s = STATUS[p.status.level];
  return (
    <span aria-label={`${s.word}: ${p.status.reason}`} title={p.status.reason} className="self-center">
      <Dot tone={s.tone} />
    </span>
  );
}

function PriceLine({ p }: { p: PortfolioRow }) {
  if (p.last_close === null) return <span className="t-small block text-ink-3">No prices yet — FINN tracks prices for the demo portfolio and Telegram holdings</span>;
  return (
    <span className="t-small mt-0.5 flex items-center gap-2 text-ink-2">
      <span className="tabular-nums">{inr(p.last_close)}</span>
      <Move pct={p.day_change_pct} />
      <Sparkline values={p.spark} width={64} height={16} className="text-ink-3" />
      <span className="text-ink-3">
        1M <Move pct={p.month_change_pct} />
      </span>
      {p.ex_date_today && <span className="text-ink-3">· {p.ex_date_today}</span>}
    </span>
  );
}

const KIND: Record<string, string> = { results: "Results", board_meeting: "Board", dividend: "Dividend", bonus_split: "Bonus/split", agm: "AGM", other: "Action" };

function Upcoming({ data }: { data: PortfolioResponse }) {
  return (
    <section className="pt-6">
      <p className="t-micro px-4 pb-2 text-ink-3">Coming up · next 60 days</p>
      {data.calendar.length === 0 ? (
        <p className="t-small px-4 text-ink-3">No board meetings or ex-dates announced for your holdings yet.</p>
      ) : (
        <ul className="divide-y divide-rule border-y border-rule bg-surface">
          {data.calendar.map((c, i) => (
            <li key={i} className="flex items-baseline gap-3 px-4 py-2.5">
              <span className="t-small w-14 shrink-0 tabular-nums text-ink-2">
                {new Date(`${c.on}T00:00:00+05:30`).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" })}
              </span>
              <span className="min-w-0 flex-1 text-[14px]">
                <span className="font-semibold">{c.symbol}</span> · {KIND[c.kind] ?? c.kind}
                <span className="t-small block truncate text-ink-3">
                  {c.url ? (
                    <a href={c.url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-4">
                      {c.label}
                    </a>
                  ) : (
                    c.label
                  )}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// "What you're watching": 2–3 drivers per holding suggested from the company's own calls (counted in code);
// one tap confirms. Confirmed drivers stay on this phone.
function Watching({ symbols }: { symbols: string[] }) {
  const [drivers, setDrivers] = useState<Record<string, DriversSection | null> | null>(null);
  const [failed, setFailed] = useState(false);
  const confirmed = useStored<Record<string, string[]>>("drivers", FALLBACK.drivers);
  const key = symbols.join(",");
  useEffect(() => {
    let cancelled = false;
    api
      .drivers(key.split(","))
      .then((r) => !cancelled && setDrivers(r.drivers))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [key]);
  const toggle = (sym: string, id: string) => {
    const cur = read<Record<string, string[]>>("drivers", FALLBACK.drivers);
    const list = cur[sym] ?? [];
    write("drivers", { ...cur, [sym]: list.includes(id) ? list.filter((i) => i !== id) : [...list, id] });
  };
  const withItems = symbols.filter((s) => drivers?.[s]?.items.length);
  const without = symbols.filter((s) => !drivers?.[s]?.items.length);
  return (
    <section className="mt-8" id="watching">
      <h2 className="t-micro px-4 text-ink-3">What you&apos;re watching</h2>
      <p className="t-small mt-1 px-4 text-ink-2">
        Suggested from each company&apos;s own calls — what management guides on and analysts ask about most. Tap to watch.
      </p>
      {!drivers && !failed && <Skeleton rows={2} label="Loading drivers" />}
      {failed && <p className="t-small px-4 pt-2 text-ink-3">Couldn&apos;t load drivers right now.</p>}
      {drivers && (
        <ul className="mt-2 divide-y divide-rule border-y border-rule bg-surface">
          {withItems.map((s) => (
            <li key={s} className="px-4 py-3">
              <p className="text-[15px] font-semibold">{s}</p>
              <div className="mt-1.5 flex flex-wrap gap-2">
                {drivers[s]!.items.map((d) => {
                  const on = (confirmed[s] ?? []).includes(d.id);
                  return (
                    <button
                      key={d.id}
                      type="button"
                      aria-pressed={on}
                      title={d.description}
                      onClick={() => toggle(s, d.id)}
                      className={`hit h-8 rounded-full border px-3 text-[13px] ${on ? "border-ink bg-ink font-medium text-paper" : "border-rule text-ink-2"}`}
                    >
                      {on ? "✓ " : ""}
                      {d.label}
                    </button>
                  );
                })}
              </div>
            </li>
          ))}
          {without.length > 0 && (
            <li className="t-small px-4 py-3 text-ink-3">
              {without.join(", ")}: drivers appear after research
              {without.some((s) => drivers[s]?.meta.reason === "no_transcripts") ? " (some publish no call transcripts)" : ""}.
            </li>
          )}
        </ul>
      )}
    </section>
  );
}

function ImportSheet({ open, onClose, current, demo }: { open: boolean; onClose: () => void; current: LocalHolding[]; demo: boolean }) {
  const [text, setText] = useState("");
  const [known, setKnown] = useState<Set<string> | null>(null);
  useEffect(() => {
    if (!open) return;
    // Opening the sheet seeds the editor from the stored holdings (an external store) — once per open.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setText(
      demo
        ? ""
        : current.map((h) => `${h.symbol} ${h.weight_pct !== null ? `${h.weight_pct}%` : (h.quantity ?? "")}`.trim()).join("\n"),
    );
    const cached = read<{ list: [string, string][] } | null>("symbols", null);
    if (cached) setKnown(new Set(cached.list.map((s) => s[0])));
    else
      api
        .staticSymbols()
        .then((r) => setKnown(new Set(r.symbols.map((s) => s[0]))))
        .catch(() => setKnown(null));
  }, [open, current, demo]);
  const parsed = useMemo(() => parseHoldings(text, known), [text, known]);
  const total = parsed.holdings.reduce((a, h) => a + (h.weight_pct ?? 0), 0);
  const ok = parsed.holdings.length > 0 && parsed.holdings.length <= 40 && parsed.unknown.length === 0 && parsed.errors.length === 0;
  return (
    <Sheet
      open={open}
      onClose={onClose}
      eyebrow="Holdings"
      title={demo ? "Use my holdings" : "Edit holdings"}
      footer={
        <button
          type="button"
          disabled={!ok}
          onClick={() => {
            const at = new Date().toISOString();
            write("holdings", parsed.holdings.map((h) => ({ ...h, added_at: at })));
            for (const k of ["since", "24h", "3d", "7d", "custom"]) write(`brief.${k}`, null);
            onClose();
          }}
          className="h-12 w-full rounded-xl bg-ink text-[15px] font-medium text-paper disabled:opacity-40"
        >
          Save {parsed.holdings.length > 0 ? `${parsed.holdings.length} holdings` : ""}
        </button>
      }
    >
      <p className="t-small text-ink-2">
        One per line: <span className="font-mono text-[12px]">SYMBOL 6%</span> for a weight, or{" "}
        <span className="font-mono text-[12px]">SYMBOL 120</span> for shares. Paste from a spreadsheet or CSV. Stays on this phone.
      </p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={9}
        placeholder={"HDFCBANK 8%\nINFY 7%\nTRENT 40"}
        className="mt-3 w-full rounded-xl border border-rule bg-paper p-3 font-mono text-[14px] leading-[20px] outline-none focus:border-ink-3"
        autoCapitalize="characters"
        spellCheck={false}
      />
      <div className="t-small mt-2 space-y-1">
        <p className="text-ink-2">
          {parsed.holdings.length} holdings{total > 0 ? ` · weights add to ${Math.round(total * 10) / 10}%` : ""}
          {parsed.holdings.length > 40 ? " · at most 40" : ""}
        </p>
        {parsed.unknown.length > 0 && <p className="text-neg">Not on NSE&apos;s equity list: {parsed.unknown.join(", ")}</p>}
        {parsed.errors.length > 0 && <p className="text-neg">Couldn&apos;t read: {parsed.errors.slice(0, 3).join(" · ")}</p>}
      </div>
    </Sheet>
  );
}
