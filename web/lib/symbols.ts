"use client";
// NSE equity list for autocomplete: the committed static copy (instant, CDN), refreshed from the API once a day.
import { useEffect, useState } from "react";
import { api } from "@/lib/client";
import { read, write } from "@/lib/store";

type Cached = { at: string; list: [string, string][] };
const DAY = 24 * 3600 * 1000;

export function useSymbols(): [string, string][] | null {
  const [list, setList] = useState<[string, string][] | null>(null);
  useEffect(() => {
    let cancelled = false;
    const cached = read<Cached | null>("symbols", null);
    // localStorage is only readable after hydration; the prerendered shell shows the empty state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (cached) setList(cached.list);
    const fresh = cached && Date.now() - Date.parse(cached.at) < DAY;
    if (!cached)
      api
        .staticSymbols()
        .then((r) => !cancelled && setList((cur) => cur ?? r.symbols))
        .catch(() => {});
    if (!fresh)
      api
        .symbols()
        .then((r) => {
          if (cancelled || !r.symbols?.length) return;
          write<Cached>("symbols", { at: new Date().toISOString(), list: r.symbols });
          setList(r.symbols);
        })
        .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);
  return list;
}

export function searchSymbols(list: [string, string][], q: string, limit = 8): [string, string][] {
  const Q = q.trim().toUpperCase();
  if (!Q) return [];
  const hits: [number, number, string, string][] = [];
  for (const [s, n] of list) {
    const N = n.toUpperCase();
    let score = -1;
    if (s === Q) score = 0;
    else if (s.startsWith(Q)) score = 1;
    else if (N.startsWith(Q)) score = 2;
    else if (N.includes(` ${Q}`)) score = 3;
    else if (s.includes(Q)) score = 4;
    if (score >= 0) hits.push([score, s.length, s, n]);
  }
  hits.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2].localeCompare(b[2]));
  return hits.slice(0, limit).map((h) => [h[2], h[3]]);
}

export function companyName(name: string): string {
  return name.replace(/\s+(limited|ltd\.?)$/i, "").replace(/\b([A-Z])([A-Z]+)\b/g, (m, a, b) => (m.length > 4 ? a + b.toLowerCase() : m));
}
