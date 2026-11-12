"use client";
// Prices, status dots, calendar and scoreboard for the phone's holdings (POST /api/portfolio: symbols + weights
// only). Keeps the last good answer for the same holdings on the phone, so a sleeping server never blanks it.
import { useEffect, useState } from "react";
import { api, FetchError } from "@/lib/client";
import { effectiveWeights } from "@/lib/holdings";
import { read, write, type LocalHolding } from "@/lib/store";
import type { PortfolioRequest, PortfolioResponse } from "@/lib/types";

type Saved = { sig: string; at: number; resp: PortfolioResponse };
export type PortfolioState = { data: PortfolioResponse | null; at: number | null; loading: boolean; error: FetchError | null; cached: boolean };

export function usePortfolio(holdings: LocalHolding[], enabled: boolean, nonce = 0): PortfolioState {
  const sig = holdings.map((h) => h.symbol).sort().join(",");
  const [st, setSt] = useState<PortfolioState>({ data: null, at: null, loading: true, error: null, cached: false });
  useEffect(() => {
    if (!enabled) return;
    const saved = read<Saved | null>("portfolio", null);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- show the phone's last copy at once
    if (saved && saved.sig === sig) setSt({ data: saved.resp, at: saved.at, loading: true, error: null, cached: true });
    const ctrl = new AbortController();
    const req: PortfolioRequest = {
      holdings: effectiveWeights(holdings).map((h) => ({ symbol: h.symbol, weight_pct: h.weight_pct })) as PortfolioRequest["holdings"],
    };
    api
      .portfolio(req, ctrl.signal)
      .then((resp) => {
        const at = Date.now();
        write("portfolio", { sig, at, resp } satisfies Saved);
        setSt({ data: resp, at, loading: false, error: null, cached: false });
      })
      .catch((e) => {
        if (ctrl.signal.aborted) return;
        setSt((s) => ({ ...s, loading: false, error: e instanceof FetchError ? e : new FetchError(0, "Couldn't reach FINN") }));
      });
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sig, enabled, nonce]);
  return st;
}
