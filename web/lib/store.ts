"use client";
// Everything the phone remembers lives here, in localStorage under versioned keys (finn.v1.*). No login.
// Holdings (with any quantities) never leave the phone except as symbols + weights in a /brief request.
// Every access is wrapped: private mode or a full quota falls back to memory for the session.
import { useSyncExternalStore } from "react";
import { DEMO_WEIGHTS } from "@/lib/demo";
import type { BriefResponse, Category, FeedbackAction, WeightRule } from "@/lib/types";

const PREFIX = "finn.v1.";

export type LocalHolding = { symbol: string; weight_pct: number | null; quantity: number | null; added_at: string };
export type MarkKind = "reviewed" | "not_useful";
export type Mark = { kind: MarkKind; at: string; symbol: string; category: Category; headline: string; scope?: string };
export type Visit = { current: string; previous: string | null; active: string };
export type CachedBrief = { resp: BriefResponse; at: string; sig: string };
export type WindowKey = "since" | "24h" | "3d" | "7d" | "custom";

const DEMO_HOLDINGS: LocalHolding[] = Object.entries(DEMO_WEIGHTS).map(([symbol, w]) => ({
  symbol,
  weight_pct: w,
  quantity: null,
  added_at: "2026-11-01T00:00:00Z",
}));

// Stable fallbacks (useSyncExternalStore needs referentially stable snapshots).
export const FALLBACK = {
  holdings: DEMO_HOLDINGS,
  rules: [] as WeightRule[],
  pending: [] as FeedbackAction[],
  marks: {} as Record<string, Mark>,
  visit: null as Visit | null,
  tour: false,
  showcase: false,
  drivers: {} as Record<string, string[]>,
  recent: [] as string[],
  symbols: null as { at: string; list: [string, string][] } | null,
  brief: null as CachedBrief | null,
};

const mem = new Map<string, string>();
const parsed = new Map<string, { raw: string | null; value: unknown }>();
const listeners = new Map<string, Set<() => void>>();

function rawGet(key: string): string | null {
  try {
    const v = localStorage.getItem(PREFIX + key);
    return v ?? mem.get(key) ?? null;
  } catch {
    return mem.get(key) ?? null;
  }
}

export function read<T>(key: string, fallback: T): T {
  const raw = rawGet(key);
  const hit = parsed.get(key);
  if (hit && hit.raw === raw) return (raw === null ? fallback : hit.value) as T;
  let value: unknown = fallback;
  if (raw !== null) {
    try {
      value = JSON.parse(raw);
    } catch {
      value = fallback;
    }
  }
  parsed.set(key, { raw, value });
  return value as T;
}

function notify(key: string) {
  listeners.get(key)?.forEach((l) => l());
}

export function write<T>(key: string, value: T | null) {
  if (value === null) {
    mem.delete(key);
    try {
      localStorage.removeItem(PREFIX + key);
    } catch {}
    parsed.delete(key);
    notify(key);
    return;
  }
  const raw = JSON.stringify(value);
  mem.set(key, raw);
  try {
    localStorage.setItem(PREFIX + key, raw);
  } catch {
    // Quota: drop cached Briefs (they're re-fetchable), then retry once.
    try {
      for (let i = localStorage.length - 1; i >= 0; i--) {
        const k = localStorage.key(i);
        if (k?.startsWith(PREFIX + "brief.")) localStorage.removeItem(k);
      }
      localStorage.setItem(PREFIX + key, raw);
    } catch {}
  }
  parsed.set(key, { raw, value });
  notify(key);
}

function subscribe(key: string) {
  return (cb: () => void) => {
    let set = listeners.get(key);
    if (!set) listeners.set(key, (set = new Set()));
    set.add(cb);
    const onStorage = (e: StorageEvent) => {
      if (e.key === PREFIX + key) cb();
    };
    window.addEventListener("storage", onStorage);
    return () => {
      set!.delete(cb);
      window.removeEventListener("storage", onStorage);
    };
  };
}

const subs = new Map<string, (cb: () => void) => () => void>();
function sub(key: string) {
  let s = subs.get(key);
  if (!s) subs.set(key, (s = subscribe(key)));
  return s;
}

/** Read a stored value reactively. The server (prerender) always sees the fallback. */
export function useStored<T>(key: string, fallback: T): T {
  return useSyncExternalStore(
    sub(key),
    () => read(key, fallback),
    () => fallback,
  );
}

/** True only after hydration — for UI that must not differ between the prerendered shell and the client. */
const noop = () => () => {};
export function useHydrated(): boolean {
  return useSyncExternalStore(
    noop,
    () => true,
    () => false,
  );
}

/** Cache one Brief at a time (a 7-day Brief is ~1 MB uncompressed; localStorage holds ~5 MB). */
export function cacheBrief(key: string, value: CachedBrief) {
  for (const k of ["since", "24h", "3d", "7d", "custom"]) if (`brief.${k}` !== key) write(`brief.${k}`, null);
  write(key, value);
}

// --- Visits ("Since your last visit") ---------------------------------------------------------------------

const SESSION_GAP_MS = 30 * 60 * 1000;

/** Called once per app load. A new visit starts after 30 idle minutes; "since last visit" = when you were last active. */
export function startVisit(now = Date.now()): Visit {
  const v = read<Visit | null>("visit", null);
  const iso = new Date(now).toISOString();
  let next: Visit;
  if (!v) next = { current: iso, previous: null, active: iso };
  else if (now - Date.parse(v.active) > SESSION_GAP_MS) next = { current: iso, previous: v.active, active: iso };
  else next = { ...v, active: iso };
  write("visit", next);
  return next;
}

export function touchVisit() {
  const v = read<Visit | null>("visit", null);
  if (v) write("visit", { ...v, active: new Date().toISOString() });
}

// --- Marks (Reviewed / Not useful) ---------------------------------------------------------------------------

const MARK_TTL_MS = 14 * 24 * 3600 * 1000;

export function setMark(id: string, mark: Mark | null) {
  const cur = read<Record<string, Mark>>("marks", FALLBACK.marks);
  const now = Date.now();
  const next: Record<string, Mark> = {};
  for (const [k, m] of Object.entries(cur)) if (now - Date.parse(m.at) < MARK_TTL_MS && k !== id) next[k] = m;
  if (mark) next[id] = mark;
  write("marks", next);
}

// --- Feedback --------------------------------------------------------------------------------------------------

export function queueFeedback(a: FeedbackAction) {
  write("pending", [...read<FeedbackAction[]>("pending", FALLBACK.pending), a]);
}

/** After a Brief response: the server applied every pending action it was sent; keep only newer ones. */
export function settleFeedback(rules: WeightRule[], sentUpTo: string | null) {
  write("rules", rules);
  if (sentUpTo) write("pending", read<FeedbackAction[]>("pending", FALLBACK.pending).filter((a) => a.at > sentUpTo));
}

export function resetRule(id: string | null) {
  write("rules", id === null ? [] : read<WeightRule[]>("rules", FALLBACK.rules).filter((r) => r.id !== id));
}

// --- Holdings ----------------------------------------------------------------------------------------------------

export function holdingsSignature(h: LocalHolding[], rules: WeightRule[]): string {
  const hs = h.map((x) => `${x.symbol}:${x.weight_pct ?? ""}`).sort().join(",");
  const rs = rules.map((r) => `${r.id}:${r.multiplier}`).sort().join(",");
  return `${hs}|${rs}`;
}

export const isDemoPortfolio = (h: LocalHolding[]) =>
  h.length === DEMO_HOLDINGS.length && h.every((x) => DEMO_WEIGHTS[x.symbol] === x.weight_pct);
