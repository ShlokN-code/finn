"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { LedgerSection } from "@/components/ledger/Ledger";
import { ErrorState, Notice, Skeleton } from "@/components/shell/StateView";
import { setAskContext } from "@/components/shell/ui-store";
import { FIXTURE_DATE } from "@/lib/demo";
import { istDay, istTime } from "@/lib/format";
import { companyName } from "@/lib/symbols";
import type { Dossier } from "@/lib/types";
import { BuildProgress } from "./BuildProgress";
import {
  AnalystsSectionView,
  BullBearSectionView,
  DriversSectionView,
  ExchangeSectionView,
  RedFlagsSectionView,
  SeriesSectionView,
  SnapshotSection,
  SourcesSection,
  TrajectorySection,
} from "./sections";
import { isActive, useDossier } from "./useDossier";

const TABS: [string, string][] = [
  ["snapshot", "Snapshot"],
  ["trajectory", "Trajectory"],
  ["ledger", "Ledger"],
  ["cash", "Cash"],
  ["balance-sheet", "Balance sheet"],
  ["analysts", "Analysts"],
  ["red-flags", "Red flags"],
  ["bull-bear", "Bull vs bear"],
  ["drivers", "Drivers"],
  ["exchange", "Exchange"],
  ["sources", "Sources"],
];

const TEMPLATE = { bank: "Bank", nbfc: "NBFC", standard: null } as const;

// Sections not built in this release (annual-report red flags, on-demand NSE exchange data) are hidden, not shown
// as "Coming soon" (product owner, Phase 5). They reappear by themselves once a build fills them.
const notBuilt = (m: { status: string; reason?: string | null }) => m.status === "building" && m.reason === "not_built_yet";
function hiddenTabs(d: Dossier | null): Set<string> {
  const out = new Set<string>();
  if (d && notBuilt(d.red_flags.meta)) out.add("red-flags");
  if (d && notBuilt(d.exchange_data.meta)) out.add("exchange");
  return out;
}

function readyCount(d: Dossier | null): number {
  if (!d) return 0;
  const metas = [d.snapshot, d.trajectory, d.ledger, d.cash_quality, d.balance_sheet, d.analysts, d.bull_bear, d.drivers].map((s) => s.meta);
  return metas.filter((m) => m.status === "ready" || m.status === "partial").length;
}

export function DossierScreen({ symbol }: { symbol: string }) {
  const [mock, setMock] = useState(false);
  const [focus, setFocus] = useState<string | null>(null);
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    // Query flags are read after hydration so the route stays prerenderable.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (process.env.NODE_ENV !== "production" && q.get("mock") === "build") setMock(true);
    setFocus(q.get("focus"));
  }, []);
  const x = useDossier(symbol, mock);
  const d = x.resp?.dossier ?? null;
  const job = x.resp?.job ?? null;
  const active = isActive(job);

  // Scroll to a #section once content exists.
  useEffect(() => {
    if (!d || !window.location.hash) return;
    const el = document.getElementById(window.location.hash.slice(1));
    if (el) setTimeout(() => el.scrollIntoView({ block: "start" }), 50);
  }, [d]);

  const jump = (id: string, f?: string) => {
    if (f) setFocus(f);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  useEffect(() => {
    if (!d) return setAskContext({ placeholder: `Ask about ${symbol}…`, chips: [], symbol });
    const chips = d.ask_chips.map((label) => {
      const l = label.toLowerCase();
      const theme = d.drivers.items.find((dr) => l.includes(dr.label.toLowerCase()))?.label;
      if (l.includes("miss") || l.includes("promise") || l.includes("guidance") || l.includes("said about"))
        return { label, run: () => jump("ledger", theme ?? undefined) };
      if (l.includes("analyst") || l.includes("ask")) return { label, run: () => jump("analysts") };
      if (l.includes("cash")) return { label, run: () => jump("cash") };
      if (l.includes("debt") || l.includes("borrow")) return { label, run: () => jump("balance-sheet") };
      if (l.includes("risk") || l.includes("bear")) return { label, run: () => jump("bull-bear") };
      return { label, run: () => jump("snapshot") };
    });
    setAskContext({ placeholder: `Ask about ${symbol}…`, chips: chips.slice(0, 3), symbol });
    return () => setAskContext(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [d?.symbol, d?.ask_chips.join("|")]);

  const sub = useMemo(() => {
    if (!d) return null;
    return [TEMPLATE[d.template], d.basis, `as of ${istDay(d.as_of)} ${istTime(d.as_of)} IST`].filter(Boolean).join(" · ");
  }, [d]);

  return (
    <div className="pb-8">
      <div className="flex h-12 items-center gap-1 px-2">
        <Link href="/research" className="inline-flex h-11 items-center gap-0.5 rounded-full px-2 text-[15px] text-ink-2">
          <ChevronLeft className="size-5" strokeWidth={1.75} /> Research
        </Link>
        <span className="flex-1" />
        <span className="t-micro pr-2 text-ink-3">{symbol}</span>
      </div>
      <header className="px-4 pb-3">
        <h1 className="t-title">{d ? companyName(d.name) : symbol}</h1>
        {sub && <p className="t-small mt-0.5 text-ink-2">{sub}</p>}
      </header>

      {x.source === "fixture" && (
        <Notice tone="warn" action={<button type="button" onClick={x.reload} className="h-9 shrink-0 font-semibold underline underline-offset-4">Retry</button>}>
          Saved copy from {FIXTURE_DATE} — FINN&apos;s server didn&apos;t answer.
        </Notice>
      )}
      {x.source === "mock" && <Notice>Dev preview: scripted build progress (no API calls).</Notice>}

      {x.status === "loading" && (
        <>
          <p className="t-small px-4 pb-2 text-ink-3">{x.slow ? "Waking FINN's server — up to a minute on the free tier…" : "Opening the dossier…"}</p>
          <Skeleton rows={4} label="Loading dossier" />
        </>
      )}
      {x.status === "notfound" && (
        <ErrorState title={`${symbol} isn't on NSE's equity list`} detail="Check the symbol — FINN researches NSE-listed equities only." />
      )}
      {x.status === "error" && !d && (
        <ErrorState
          title={x.error?.waking ? "FINN's server is waking up" : "Couldn't open this dossier"}
          detail={x.error?.waking ? "The free-tier server sleeps when idle and takes up to a minute to wake." : x.error?.message}
          offline={x.error?.status === 0}
          onRetry={x.reload}
        />
      )}

      {job && (active || job.status === "failed") && <BuildProgress job={job} readyCount={readyCount(d)} />}

      {x.status === "ready" && !d && !active && (
        <section className="mx-4 mt-2 rounded-xl border border-rule bg-surface p-4">
          <p className="t-headline">FINN hasn&apos;t researched {symbol} yet</p>
          <p className="t-small mt-1.5 text-ink-2">
            It reads up to 8 earnings-call transcripts, the latest annual report and investor decks, checks every quote against its page, and
            scores management&apos;s promises. About 2–4 minutes; then it opens instantly for everyone.
          </p>
          <p className="t-small mt-2 text-ink-3">
            If today&apos;s AI quota is used up, numbers and the numeric ledger come first; the summary and qualitative verdicts finish after
            13:30 IST.
          </p>
          <button
            type="button"
            onClick={x.build}
            disabled={x.building}
            className="mt-4 h-12 w-full rounded-xl bg-ink text-[15px] font-medium text-paper disabled:opacity-50"
          >
            {x.building ? "Starting…" : `Research ${symbol}`}
          </button>
          {x.buildError && <p className="t-small mt-2 text-neg">{x.buildError}</p>}
        </section>
      )}

      {d && (
        <>
          <nav aria-label="Sections" className="no-scrollbar sticky top-0 z-10 mt-2 flex gap-1 overflow-x-auto border-b border-rule bg-paper/95 px-3 backdrop-blur-sm">
            {TABS.filter(([id]) => !hiddenTabs(d).has(id)).map(([id, label]) => (
              <a key={id} href={`#${id}`} onClick={(e) => (e.preventDefault(), jump(id))} className="t-small inline-flex h-11 shrink-0 items-center px-2 text-ink-2">
                {label}
              </a>
            ))}
          </nav>
          <SnapshotSection d={d} />
          <TrajectorySection d={d} />
          <LedgerSection d={d} focus={focus} />
          <SeriesSectionView id="cash" title="Cash quality" section={d.cash_quality} />
          <SeriesSectionView id="balance-sheet" title="Balance sheet" section={d.balance_sheet} />
          <AnalystsSectionView d={d} />
          {!notBuilt(d.red_flags.meta) && <RedFlagsSectionView d={d} />}
          <BullBearSectionView d={d} />
          <DriversSectionView d={d} />
          {!notBuilt(d.exchange_data.meta) && <ExchangeSectionView d={d} />}
          <SourcesSection d={d} />
          <p className="t-small px-4 text-ink-3">
            Primary sources only — no news, broker notes or model memory. Unsupported claims are removed; gaps say so.
          </p>
        </>
      )}
    </div>
  );
}
