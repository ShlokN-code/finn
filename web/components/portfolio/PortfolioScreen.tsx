"use client";
// Portfolio: holdings with weight and their latest event from the Brief; paste/CSV import (stored on the phone).
// Prices, sparklines, the calendar and the scoreboard arrive with /portfolio (Friday); the season scoreboard is
// already one tap away in the Brief.
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { useBrief } from "@/components/brief/useBrief";
import { Sheet } from "@/components/shell/Sheet";
import { Notice, Skeleton } from "@/components/shell/StateView";
import { setAskContext } from "@/components/shell/ui-store";
import { Dot, IMPACT } from "@/components/ui/signal";
import { api } from "@/lib/client";
import { CATEGORY_LABEL, displayHeadline, istWhen } from "@/lib/format";
import { effectiveWeights, parseHoldings } from "@/lib/holdings";
import { FALLBACK, isDemoPortfolio, read, useHydrated, useStored, write, type LocalHolding } from "@/lib/store";
import type { Card } from "@/lib/types";

function latestAt(c: Card): string {
  return [...c.timeline.map((t) => t.at)].sort().at(-1) ?? c.as_of;
}

export function PortfolioScreen() {
  const holdings = useStored<LocalHolding[]>("holdings", FALLBACK.holdings);
  const enabled = useHydrated();
  const router = useRouter();
  const b = useBrief({ window: "7d", customSince: null, visit: null, showcase: false, enabled });
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
      <p className="t-micro px-4 pb-2 text-ink-3">Weight · latest material event, last 7 days</p>
      {!b.data && !b.error ? (
        <Skeleton rows={4} label="Loading holdings" />
      ) : (
        <ul id="holdings" className="divide-y divide-rule border-y border-rule bg-surface">
          {rows.map((h) => {
            const c = latest.get(h.symbol);
            const impact = c?.impact ? IMPACT[c.impact] : null;
            return (
              <li key={h.symbol}>
                <Link
                  href={c ? `/e/${encodeURIComponent(c.id)}` : `/research/${encodeURIComponent(h.symbol)}`}
                  className="flex min-h-14 items-start gap-3 px-4 py-3"
                >
                  <span className="min-w-0 flex-1">
                    <span className="flex items-baseline gap-2">
                      <span className="text-[15px] font-semibold">{h.symbol}</span>
                      {h.quantity !== null && <span className="t-small text-ink-3">{h.quantity.toLocaleString("en-IN")} sh</span>}
                    </span>
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
          Holdings entered as share quantities split the remaining weight equally until prices are wired in.
        </p>
      )}
      <section className="mt-8 px-4">
        <h2 className="t-micro text-ink-3">What you&apos;re watching</h2>
        <p className="t-small mt-1 text-ink-2">
          FINN suggests 2–3 drivers per holding from the company&apos;s own calls (margins, growth, asset quality…). Drivers appear after
          research — open a holding in Research to see its suggestions.
        </p>
      </section>
      <ImportSheet open={editing} onClose={() => setEditing(false)} current={holdings} demo={demo} />
    </div>
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
