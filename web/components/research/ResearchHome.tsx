"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronRight, Search, X } from "lucide-react";
import { setAskContext } from "@/components/shell/ui-store";
import { DEMO_TICKERS } from "@/lib/demo";
import { FALLBACK, useStored, write, type LocalHolding } from "@/lib/store";
import { companyName, searchSymbols, useSymbols } from "@/lib/symbols";

export function ResearchHome() {
  const list = useSymbols();
  const router = useRouter();
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const recent = useStored<string[]>("recent", FALLBACK.recent);
  const holdings = useStored<LocalHolding[]>("holdings", FALLBACK.holdings);
  const input = useRef<HTMLInputElement>(null);
  const hits = useMemo(() => (list ? searchSymbols(list, q) : []), [list, q]);
  const names = useMemo(() => new Map(list ?? []), [list]);

  const open = (sym: string) => {
    write("recent", [sym, ...recent.filter((s) => s !== sym)].slice(0, 6));
    router.push(`/research/${encodeURIComponent(sym)}`);
  };

  useEffect(() => {
    setAskContext({
      placeholder: "Ask about any company…",
      chips: [
        { label: "Did Bajaj Finance keep its promises?", run: () => open("BAJFINANCE") },
        { label: "What do analysts keep asking Infosys?", run: () => router.push("/research/INFY#analysts") },
        { label: "Research a company I hold", run: () => input.current?.focus() },
      ],
    });
    return () => setAskContext(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const Row = ({ sym, sub }: { sym: string; sub?: string }) => (
    <li>
      <button type="button" onClick={() => open(sym)} className="flex min-h-12 w-full items-center gap-3 px-4 py-2 text-left">
        <span className="min-w-0 flex-1">
          <span className="block text-[15px] font-semibold">{sym}</span>
          <span className="t-small block truncate text-ink-2">{sub ?? (names.get(sym) ? companyName(names.get(sym)!) : "")}</span>
        </span>
        <ChevronRight className="size-4 shrink-0 text-ink-3" />
      </button>
    </li>
  );

  return (
    <div className="pb-8">
      <header className="px-4 pb-3 pt-6">
        <h1 className="t-display">Research</h1>
        <p className="t-small mt-1 text-ink-2">
          Any NSE company, from primary sources only: call transcripts, annual reports, investor decks, exchange filings and
          screener&apos;s standardised tables. Every number opens its page.
        </p>
      </header>
      <form
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          const pick = hits[active]?.[0];
          if (pick) open(pick);
        }}
        className="sticky top-0 z-10 bg-paper px-4 pb-3 pt-1"
      >
        <label className="flex h-12 items-center gap-2 rounded-xl border border-rule bg-surface px-3 focus-within:border-ink-3">
          <Search className="size-[18px] shrink-0 text-ink-3" strokeWidth={1.75} />
          <input
            ref={input}
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setActive(0);
            }}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") setActive((a) => Math.min(a + 1, hits.length - 1));
              if (e.key === "ArrowUp") setActive((a) => Math.max(a - 1, 0));
            }}
            placeholder={list ? `Search ${list.length.toLocaleString("en-IN")} NSE companies` : "Search NSE companies"}
            className="h-full min-w-0 flex-1 bg-transparent text-[16px] outline-none placeholder:text-ink-3"
            autoCapitalize="characters"
            autoCorrect="off"
            spellCheck={false}
            enterKeyHint="search"
            role="combobox"
            aria-expanded={hits.length > 0}
            aria-controls="ticker-results"
          />
          {q && (
            <button type="button" onClick={() => setQ("")} aria-label="Clear" className="hit grid size-8 place-items-center text-ink-3">
              <X className="size-4" />
            </button>
          )}
        </label>
      </form>
      {q.trim() ? (
        hits.length ? (
          <ul id="ticker-results" role="listbox" className="divide-y divide-rule border-y border-rule bg-surface">
            {hits.map(([s, n], i) => (
              <li key={s} role="option" aria-selected={i === active}>
                <button
                  type="button"
                  onClick={() => open(s)}
                  className={`flex min-h-12 w-full items-center gap-3 px-4 py-2 text-left ${i === active ? "bg-surface-2" : ""}`}
                >
                  <span className="min-w-0 flex-1">
                    <span className="block text-[15px] font-semibold">{s}</span>
                    <span className="t-small block truncate text-ink-2">{companyName(n)}</span>
                  </span>
                  {(DEMO_TICKERS as readonly string[]).includes(s) && <span className="t-small text-ink-3">ready</span>}
                  <ChevronRight className="size-4 shrink-0 text-ink-3" />
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="t-small px-4 py-6 text-ink-2">
            {list ? `No NSE equity matches “${q.trim()}”. Try the NSE symbol (e.g. HDFCBANK) or part of the name.` : "Loading the NSE list…"}
          </p>
        )
      ) : (
        <>
          {recent.length > 0 && (
            <section className="mt-2">
              <h2 className="t-micro px-4 text-ink-3">Recent</h2>
              <ul className="mt-1 divide-y divide-rule border-y border-rule bg-surface">
                {recent.map((s) => (
                  <Row key={s} sym={s} />
                ))}
              </ul>
            </section>
          )}
          <section className="mt-6">
            <h2 className="t-micro px-4 text-ink-3">Ready now · built and checked</h2>
            <ul className="mt-1 divide-y divide-rule border-y border-rule bg-surface">
              {DEMO_TICKERS.map((s) => (
                <Row key={s} sym={s} />
              ))}
            </ul>
          </section>
          <section className="mt-6">
            <h2 className="t-micro px-4 text-ink-3">Your holdings</h2>
            <ul className="mt-1 divide-y divide-rule border-y border-rule bg-surface">
              {holdings.map((h) => (
                <Row key={h.symbol} sym={h.symbol} />
              ))}
            </ul>
          </section>
          <p className="t-small px-4 pt-4 text-ink-3">
            A company FINN hasn&apos;t read yet takes 2–4 minutes the first time; after that it opens instantly.{" "}
            <Link href="/research/INFY#ledger" className="underline underline-offset-4">
              See a Promise Ledger
            </Link>
          </p>
        </>
      )}
    </div>
  );
}
