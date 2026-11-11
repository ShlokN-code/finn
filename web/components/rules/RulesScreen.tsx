"use client";
// Rules: every feedback adjustment is visible with Reset (PRODUCT §5), Telegram connect, and the alert rules.
import { useEffect } from "react";
import { TelegramConnect } from "@/components/telegram/TelegramConnect";
import { setAskContext } from "@/components/shell/ui-store";
import { CATEGORY_LABEL, CATEGORY_PLURAL, istDay } from "@/lib/format";
import { FALLBACK, resetRule, useStored } from "@/lib/store";
import type { FeedbackAction, WeightRule } from "@/lib/types";

function describe(r: WeightRule): string {
  const cat = r.category ? (CATEGORY_PLURAL[r.category] ?? (CATEGORY_LABEL[r.category] ?? r.category).toLowerCase()) : "";
  const verb = r.multiplier < 1 ? "Fewer" : "More";
  switch (r.scope) {
    case "stock":
      return `${verb} filings from ${r.symbol}`;
    case "category":
      return `${verb} ${cat}, all stocks`;
    case "stock_category":
      return `${verb} ${r.symbol} ${cat}`;
    case "event":
      return `One card hidden (${r.event_id?.split(":").slice(0, 2).join(" · ")})`;
  }
}

const ALERT_RULES: [string, string][] = [
  ["Price move", "±4% close to close, adjusted for dividends, bonuses and splits"],
  ["Volume", "2× the 20-day average"],
  ["Volatility-aware", "On — a move must also be unusual for that stock (z ≥ 2)"],
  ["Sector-relative", "On — the stock's own part of the move"],
  ["Push categories", "Results, M&A, management change, litigation, credit rating, pledging, price moves"],
  ["Budget", "5 messages a day; the rest wait for your next Brief"],
  ["Quiet hours", "22:00–07:00 IST; only M&A, a CEO/MD exit or a rating downgrade break through"],
  ["Snooze", "Per stock, 1 day or 1 week — from the alert's Snooze button in Telegram"],
];

export function RulesScreen() {
  const rules = useStored<WeightRule[]>("rules", FALLBACK.rules);
  const pending = useStored<FeedbackAction[]>("pending", FALLBACK.pending);
  useEffect(() => {
    setAskContext({
      placeholder: "Ask about your rules…",
      chips: [
        { label: "How do I see less of something?", run: () => document.getElementById("adjustments")?.scrollIntoView({ behavior: "smooth" }) },
        { label: "What gets sent to Telegram?", run: () => document.getElementById("telegram")?.scrollIntoView({ behavior: "smooth" }) },
        { label: "When will alerts stay quiet?", run: () => document.getElementById("alert-rules")?.scrollIntoView({ behavior: "smooth" }) },
      ],
    });
    return () => setAskContext(null);
  }, []);
  return (
    <div className="pb-8">
      <header className="px-4 pb-2 pt-6">
        <h1 className="t-display">Rules</h1>
        <p className="t-small mt-1 text-ink-2">Transparent multipliers, not a black box. Everything here stays on this phone.</p>
      </header>

      <section id="adjustments" className="mt-4 scroll-mt-4">
        <h2 className="t-micro px-4 text-ink-3">Your feedback adjustments</h2>
        {rules.length === 0 && pending.length === 0 ? (
          <p className="t-small px-4 py-3 text-ink-2">
            None yet. Swipe a Brief card left (“Not useful”) to see less of something — each adjustment shows up here with a Reset.
          </p>
        ) : (
          <ul className="mt-2 divide-y divide-rule border-y border-rule bg-surface">
            {rules.map((r) => (
              <li key={r.id} className="flex items-center gap-3 px-4 py-3">
                <span className="min-w-0 flex-1">
                  <span className="block text-[15px]">{describe(r)}</span>
                  <span className="t-small block text-ink-3">
                    weight ×{r.multiplier.toFixed(2)} · {r.not_useful_count} not useful
                    {r.useful_count ? ` · ${r.useful_count} useful` : ""} · {istDay(r.updated_at)}
                  </span>
                </span>
                <button type="button" onClick={() => resetRule(r.id)} className="t-small h-10 shrink-0 rounded-full border border-rule px-3 font-medium">
                  Reset
                </button>
              </li>
            ))}
            {pending.length > 0 && (
              <li className="t-small px-4 py-3 text-ink-3">{pending.length} adjustment(s) apply with your next Brief refresh.</li>
            )}
          </ul>
        )}
        {rules.length > 1 && (
          <button type="button" onClick={() => resetRule(null)} className="t-small mx-4 mt-2 h-10 font-medium text-ink-2 underline underline-offset-4">
            Reset all
          </button>
        )}
        <p className="t-small px-4 pt-2 text-ink-3">
          Not useful = ×0.8 per swipe; bounded 0.1–2.0. Results, M&amp;A, management changes and rating downgrades never drop below
          half their base weight.
        </p>
      </section>

      <section id="telegram" className="mt-8 scroll-mt-4 px-4">
        <h2 className="t-micro text-ink-3">Telegram alerts</h2>
        <div className="mt-2">
          <TelegramConnect />
        </div>
      </section>

      <section id="alert-rules" className="mt-8 scroll-mt-4">
        <h2 className="t-micro px-4 text-ink-3">Alert rules</h2>
        <dl className="mt-2 divide-y divide-rule border-y border-rule bg-surface">
          {ALERT_RULES.map(([k, v]) => (
            <div key={k} className="grid grid-cols-[112px_1fr] gap-3 px-4 py-2.5">
              <dt className="t-small font-medium">{k}</dt>
              <dd className="t-small text-ink-2">{v}</dd>
            </div>
          ))}
        </dl>
        <p className="t-small px-4 pt-2 text-ink-3">These are the defaults Telegram alerts use today; per-stock editing arrives with the next release.</p>
      </section>
    </div>
  );
}
