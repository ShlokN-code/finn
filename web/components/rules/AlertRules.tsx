"use client";
// Editable alert rules (PRODUCT §6): thresholds, push categories, budget, quiet hours, snoozes. Stored on this phone;
// when Telegram is connected they are the server copy's rules too (PUT /api/subscriptions/me with the subscriber
// secret), loaded from the server first so a change made elsewhere isn't overwritten. Server-side validation is the
// AlertSettings contract (Pydantic); the inputs here only keep values in range.
import { useEffect, useRef, useState } from "react";
import { CATEGORY_LABEL } from "@/lib/format";
import { FALLBACK, read, useStored, write, type LocalHolding } from "@/lib/store";
import type { AlertSettings, Category } from "@/lib/types";

export const SECRET_KEY = "finn.telegram.secret";
export const DEFAULT_SETTINGS: AlertSettings = {
  price_move_pct: 4,
  per_stock_pct: {},
  volume_multiple: 2,
  volatility_aware: true,
  sector_relative: true,
  push_categories: ["results", "mna", "management_change", "litigation", "credit_rating", "pledging", "price_volume"],
  daily_budget: 5,
  batching: true,
  quiet_start: "22:00",
  quiet_end: "07:00",
};
const PUSHABLE: Category[] = [
  "results", "mna", "management_change", "litigation", "credit_rating", "pledging", "price_volume",
  "capex", "fund_raise", "insider_trading", "press_release", "dividend", "bonus_split",
];
type Snoozes = Record<string, string>; // symbol → until (ISO, UTC)
type Sync = "local" | "loading" | "saving" | "synced" | "error";

function secret(): string | null {
  try {
    return localStorage.getItem(SECRET_KEY);
  } catch {
    return null;
  }
}

export function AlertRules() {
  const stored = useStored<AlertSettings | null>("alertSettings", null);
  const snoozes = useStored<Snoozes>("snoozes", {});
  const holdings = useStored<LocalHolding[]>("holdings", FALLBACK.holdings);
  const s = { ...DEFAULT_SETTINGS, ...(stored ?? {}) };
  const [sync, setSync] = useState<Sync>("local");
  const [msg, setMsg] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Expired snoozes are dropped once on load (no clock reads during render: the page is prerendered).
  useEffect(() => {
    const cur = read<Snoozes>("snoozes", {});
    const live = Object.fromEntries(Object.entries(cur).filter(([, u]) => new Date(u).getTime() > Date.now()));
    if (Object.keys(live).length !== Object.keys(cur).length) write("snoozes", live);
  }, []);

  // Connected: the server copy is the truth on load.
  useEffect(() => {
    const sec = secret();
    if (!sec) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reflect the fetch that starts here
    setSync("loading");
    fetch("/api/subscriptions/me", { headers: { authorization: `Bearer ${sec}` } })
      .then(async (r) => {
        if (r.status === 404) return setSync("local"); // disconnected from Telegram (/stop)
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const me = await r.json();
        write("alertSettings", me.settings);
        write("snoozes", me.snoozed ?? {});
        setSync("synced");
      })
      .catch(() => {
        setSync("error");
        setMsg("Couldn't load your Telegram rules — showing this phone's copy.");
      });
  }, []);

  function save(nextSettings: AlertSettings, nextSnoozes: Snoozes) {
    write("alertSettings", nextSettings);
    write("snoozes", nextSnoozes);
    const sec = secret();
    if (!sec) return;
    if (timer.current) clearTimeout(timer.current);
    setSync("saving");
    timer.current = setTimeout(async () => {
      try {
        const r = await fetch("/api/subscriptions/me", {
          method: "PUT",
          headers: { "content-type": "application/json", authorization: `Bearer ${sec}` },
          body: JSON.stringify({ settings: nextSettings, snoozes: nextSnoozes }),
        });
        if (!r.ok) throw new Error((await r.json().catch(() => ({})))?.detail ?? `HTTP ${r.status}`);
        setSync("synced");
        setMsg(null);
      } catch (e) {
        setSync("error");
        setMsg(`Saved on this phone; Telegram didn't take it (${e instanceof Error ? e.message : "error"}). Try again.`);
      }
    }, 600);
  }
  const set = (patch: Partial<AlertSettings>) => save({ ...s, ...patch }, snoozes);
  const liveSnoozes = Object.entries(snoozes);
  const held = holdings.map((h) => h.symbol).filter((x) => !snoozes[x]);

  return (
    <div>
      <p className="t-small px-4 pt-1 text-ink-3" role="status">
        {sync === "local" && "Stored on this phone — used for Telegram alerts once you connect."}
        {sync === "loading" && "Loading your Telegram rules…"}
        {sync === "saving" && "Saving to Telegram…"}
        {sync === "synced" && "✓ Synced with your Telegram alerts."}
        {sync === "error" && (msg ?? "Couldn't sync.")}
      </p>
      <dl className="mt-2 divide-y divide-rule border-y border-rule bg-surface">
        <Row label="Price move" hint="close to close, adjusted for dividends, bonuses and splits">
          <Num value={s.price_move_pct} min={1} max={20} step={0.5} suffix="%" prefix="±" onChange={(v) => set({ price_move_pct: v })} />
        </Row>
        <Row label="Volume" hint="times the 20-day average">
          <Num value={s.volume_multiple} min={1.5} max={10} step={0.5} suffix="×" onChange={(v) => set({ volume_multiple: v })} />
        </Row>
        <Row label="Volatility-aware" hint="the move must also be unusual for that stock (z ≥ 2)">
          <Toggle on={s.volatility_aware} onChange={(v) => set({ volatility_aware: v })} />
        </Row>
        <Row label="Sector-relative" hint="only the stock's own part of the move">
          <Toggle on={s.sector_relative} onChange={(v) => set({ sector_relative: v })} />
        </Row>
        <Row label="Budget" hint="messages a day; the rest wait for your next Brief (results never count)">
          <Num value={s.daily_budget} min={1} max={20} step={1} onChange={(v) => set({ daily_budget: Math.round(v) })} />
        </Row>
        <Row label="Batching" hint="several alerts at once arrive as one message">
          <Toggle on={s.batching} onChange={(v) => set({ batching: v })} />
        </Row>
        <Row label="Quiet hours" hint="IST; only M&A, a CEO/MD exit or a rating downgrade break through">
          <span className="flex items-center gap-1.5">
            <input type="time" aria-label="Quiet from" value={s.quiet_start} onChange={(e) => e.target.value && set({ quiet_start: e.target.value })} className="h-9 rounded-lg border border-rule bg-paper px-2 text-[14px]" />
            <span className="t-small text-ink-3">to</span>
            <input type="time" aria-label="Quiet until" value={s.quiet_end} onChange={(e) => e.target.value && set({ quiet_end: e.target.value })} className="h-9 rounded-lg border border-rule bg-paper px-2 text-[14px]" />
          </span>
        </Row>
      </dl>

      <p className="t-micro px-4 pb-2 pt-5 text-ink-3">Push categories</p>
      <ul className="flex flex-wrap gap-2 px-4">
        {PUSHABLE.map((c) => {
          const on = s.push_categories.includes(c);
          return (
            <li key={c}>
              <button
                type="button"
                aria-pressed={on}
                onClick={() => set({ push_categories: on ? s.push_categories.filter((x) => x !== c) : [...s.push_categories, c] })}
                className={`h-9 rounded-full border px-3 text-[13px] ${on ? "border-ink bg-ink text-paper" : "border-rule text-ink-2"}`}
              >
                {c === "price_volume" ? "Price moves" : (CATEGORY_LABEL[c] ?? c)}
              </button>
            </li>
          );
        })}
      </ul>

      <p className="t-micro px-4 pb-2 pt-5 text-ink-3">Snooze</p>
      {liveSnoozes.length === 0 ? (
        <p className="t-small px-4 text-ink-3">No stock is snoozed. Snooze from here or from an alert&apos;s Snooze button.</p>
      ) : (
        <ul className="divide-y divide-rule border-y border-rule bg-surface">
          {liveSnoozes.map(([sym, until]) => (
            <li key={sym} className="flex items-center gap-3 px-4 py-2.5">
              <span className="flex-1 text-[14px]">
                <b className="font-semibold">{sym}</b> · quiet until{" "}
                {new Date(until).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kolkata" })} IST
              </span>
              <button
                type="button"
                onClick={() => {
                  const next = { ...snoozes };
                  delete next[sym];
                  save(s, next);
                }}
                className="t-small h-9 rounded-full border border-rule px-3 font-medium"
              >
                Unsnooze
              </button>
            </li>
          ))}
        </ul>
      )}
      <SnoozeAdd symbols={held} onAdd={(sym, days) => save(s, { ...snoozes, [sym]: new Date(Date.now() + days * 864e5).toISOString() })} />
    </div>
  );
}

function SnoozeAdd({ symbols, onAdd }: { symbols: string[]; onAdd: (sym: string, days: number) => void }) {
  const [sym, setSym] = useState("");
  const pick = sym || symbols[0] || "";
  if (!symbols.length) return null;
  return (
    <div className="flex items-center gap-2 px-4 pt-2">
      <select aria-label="Stock to snooze" value={pick} onChange={(e) => setSym(e.target.value)} className="h-9 min-w-0 flex-1 rounded-lg border border-rule bg-paper px-2 text-[14px]">
        {symbols.map((x) => (
          <option key={x}>{x}</option>
        ))}
      </select>
      <button type="button" onClick={() => onAdd(pick, 1)} className="t-small h-9 rounded-full border border-rule px-3 font-medium">
        1 day
      </button>
      <button type="button" onClick={() => onAdd(pick, 7)} className="t-small h-9 rounded-full border border-rule px-3 font-medium">
        1 week
      </button>
    </div>
  );
}

function Row({ label, hint, children }: { label: string; hint: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 px-4 py-2.5">
      <div className="min-w-0 flex-1">
        <dt className="t-small font-medium">{label}</dt>
        <dd className="t-small text-ink-3">{hint}</dd>
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

function Num({ value, min, max, step, prefix = "", suffix = "", onChange }: {
  value: number; min: number; max: number; step: number; prefix?: string; suffix?: string; onChange: (v: number) => void;
}) {
  const clamp = (v: number) => Math.min(max, Math.max(min, Math.round(v / step) * step));
  return (
    <span className="flex items-center gap-1">
      <button type="button" aria-label="Less" onClick={() => onChange(clamp(value - step))} className="size-9 rounded-full border border-rule text-[16px]">−</button>
      <span className="t-figure w-14 text-center text-[14px]">{prefix}{Number(value.toFixed(1))}{suffix}</span>
      <button type="button" aria-label="More" onClick={() => onChange(clamp(value + step))} className="size-9 rounded-full border border-rule text-[16px]">+</button>
    </span>
  );
}

function Toggle({ on, onChange }: { on: boolean; onChange: (v: boolean) => void }) {
  return (
    <button type="button" role="switch" aria-checked={on} onClick={() => onChange(!on)} className={`h-7 w-12 rounded-full p-0.5 transition-colors ${on ? "bg-ink" : "bg-rule"}`}>
      <span className={`block size-6 rounded-full bg-paper transition-transform ${on ? "translate-x-5" : ""}`} />
    </button>
  );
}

/** The settings to upload when connecting Telegram (this phone's edits, or the defaults). */
export function localAlertSettings(): AlertSettings {
  return { ...DEFAULT_SETTINGS, ...(read<AlertSettings | null>("alertSettings", null) ?? {}) };
}
