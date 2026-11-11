"use client";
// Tiny global UI state: the undo toast and the Ask bar's context. Module-level + useSyncExternalStore (no deps).
import { useSyncExternalStore } from "react";

type Listener = () => void;
function createStore<T>(initial: T) {
  let state = initial;
  const ls = new Set<Listener>();
  return {
    get: () => state,
    set: (next: T) => {
      state = next;
      ls.forEach((l) => l());
    },
    sub: (l: Listener) => {
      ls.add(l);
      return () => {
        ls.delete(l);
      };
    },
  };
}

// --- Undo toast: one at a time; a new toast (or leaving the page) commits the previous one. -------------------

export type Toast = { id: number; text: string; actionLabel?: string; ms: number };
type ToastSpec = { text: string; actionLabel?: string; onAction?: () => void; onExpire?: () => void; ms?: number };

const toast = createStore<Toast | null>(null);
let current: { spec: ToastSpec; timer: ReturnType<typeof setTimeout>; id: number } | null = null;
let seq = 0;

function finish(commit: boolean) {
  if (!current) return;
  const c = current;
  current = null;
  clearTimeout(c.timer);
  toast.set(null);
  if (commit) c.spec.onExpire?.();
}

export function showToast(spec: ToastSpec) {
  finish(true);
  const ms = spec.ms ?? 5000;
  const id = ++seq;
  current = { spec, id, timer: setTimeout(() => finish(true), ms) };
  toast.set({ id, text: spec.text, actionLabel: spec.actionLabel, ms });
}

export function undoToast() {
  if (!current) return;
  const c = current;
  finish(false);
  c.spec.onAction?.();
}

export function dismissToast() {
  finish(true);
}

if (typeof window !== "undefined") {
  // Closing the app inside the undo window still commits (the user didn't undo).
  window.addEventListener("pagehide", () => finish(true));
}

export const useToast = () => useSyncExternalStore(toast.sub, toast.get, () => null);

// --- Ask bar context -----------------------------------------------------------------------------------------

export type AskChip = { label: string; run: () => void };
export type AskContext = { placeholder: string; chips: AskChip[] };
const DEFAULT_ASK: AskContext = { placeholder: "Ask FINN…", chips: [] };
const ask = createStore<AskContext>(DEFAULT_ASK);
export const setAskContext = (c: AskContext | null) => ask.set(c ?? DEFAULT_ASK);
export const useAskContext = () => useSyncExternalStore(ask.sub, ask.get, () => DEFAULT_ASK);
