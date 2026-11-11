"use client";
// Brief data, fastest source first (DECISIONS: Phase 4 first paint):
//   1. this phone's last Brief for the same holdings + rules + window (localStorage) — instant;
//   2. first visit on the demo portfolio: the edge-cached demo Brief (Vercel serves it while Render wakes);
//   3. nothing within 1.5 s: the saved showcase day, clearly labelled, with a "Live Brief ready" pill later;
//   4. always: POST /api/brief with holdings + rules + queued swipes; keep the last good copy on failure.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, FetchError } from "@/lib/client";
import { effectiveWeights } from "@/lib/holdings";
import {
  cacheBrief,
  FALLBACK,
  holdingsSignature,
  isDemoPortfolio,
  read,
  settleFeedback,
  useStored,
  type CachedBrief,
  type LocalHolding,
  type Visit,
  type WindowKey,
} from "@/lib/store";
import type { BriefRequest, BriefResponse, FeedbackAction, WeightRule } from "@/lib/types";

export type Source = "cache" | "edge" | "fallback" | "live" | "showcase";

export type BriefState = {
  data: BriefResponse | null;
  source: Source | null;
  refreshing: boolean;
  slow: boolean;
  error: FetchError | null;
  liveReady: boolean;
  fetchedAt: string | null;
};

export function useBrief(opts: {
  window: WindowKey;
  customSince: string | null;
  visit: Visit | null;
  showcase: boolean;
  enabled: boolean;
}) {
  const holdings = useStored<LocalHolding[]>("holdings", FALLBACK.holdings);
  const rules = useStored<WeightRule[]>("rules", FALLBACK.rules);
  const pending = useStored<FeedbackAction[]>("pending", FALLBACK.pending);
  const [nonce, setNonce] = useState(0);
  const [state, setState] = useState<BriefState>({
    data: null,
    source: null,
    refreshing: false,
    slow: false,
    error: null,
    liveReady: false,
    fetchedAt: null,
  });
  const liveRef = useRef<BriefResponse | null>(null);

  const since =
    opts.window === "since" ? (opts.visit?.previous ?? null) : opts.window === "custom" ? opts.customSince : null;
  const reqWindow: BriefRequest["window"] =
    opts.window === "since" || opts.window === "custom" ? (since ? "since" : "7d") : opts.window;
  const sig = useMemo(() => holdingsSignature(holdings, rules), [holdings, rules]);
  const cacheKey = `brief.${opts.window}`;
  const pendingKey = pending.map((p) => p.at).join(",");

  useEffect(() => {
    if (!opts.enabled) return;
    let cancelled = false;
    const ctrl = new AbortController();
    const timers: ReturnType<typeof setTimeout>[] = [];
    liveRef.current = null;

    if (opts.showcase) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- marks the request in flight
      setState((s) => ({ ...s, refreshing: true, error: null, liveReady: false }));
      api
        .showcase()
        .then((resp) => !cancelled && setState({ data: resp, source: "showcase", refreshing: false, slow: false, error: null, liveReady: false, fetchedAt: null }))
        .catch((e) => !cancelled && setState((s) => ({ ...s, refreshing: false, error: e as FetchError })));
      return () => {
        cancelled = true;
      };
    }

    const cached = read<CachedBrief | null>(cacheKey, null);
    const usable = cached && cached.sig === sig ? cached : null;
    // Paint the cached Brief from localStorage at once, flagged as refreshing (DECISIONS: first paint).
    setState((s) => ({
      data: usable?.resp ?? (s.source === "showcase" ? null : s.data),
      source: usable ? "cache" : s.source === "showcase" ? null : s.source,
      refreshing: true,
      slow: false,
      error: null,
      liveReady: false,
      fetchedAt: usable?.at ?? s.fetchedAt,
    }));

    if (!usable && isDemoPortfolio(holdings) && rules.length === 0 && pending.length === 0 && reqWindow !== "since") {
      const w = reqWindow;
      api
        .demoBrief(w, ctrl.signal)
        .then((resp) => {
          if (cancelled || liveRef.current) return;
          setState((s) => ({ ...s, data: resp, source: "edge", liveReady: false }));
        })
        .catch(() => {});
    }
    if (!usable) {
      timers.push(
        setTimeout(() => {
          if (cancelled || liveRef.current) return;
          setState((s) => {
            if (s.data) return s;
            api
              .showcase()
              .then((resp) => {
                if (cancelled || liveRef.current) return;
                setState((s2) => (s2.data ? s2 : { ...s2, data: resp, source: "fallback" }));
              })
              .catch(() => {});
            return s;
          });
        }, 1500),
      );
    }
    timers.push(setTimeout(() => !cancelled && setState((s) => ({ ...s, slow: s.refreshing })), 4000));

    const sent = pending;
    const req: BriefRequest = {
      // Symbols + weights only: quantities never leave the phone.
      holdings: effectiveWeights(holdings).map((h) => ({ symbol: h.symbol, weight_pct: h.weight_pct })) as BriefRequest["holdings"],
      window: reqWindow,
      since: reqWindow === "since" ? since : null,
      rules,
      feedback: sent,
    };
    api
      .brief(req, ctrl.signal)
      .then((resp) => {
        if (cancelled) return;
        liveRef.current = resp;
        const at = new Date().toISOString();
        cacheBrief(cacheKey, { resp, at, sig: holdingsSignature(holdings, resp.rules) });
        if (sent.length) settleFeedback(resp.rules, sent.map((p) => p.at).sort().at(-1) ?? null);
        setState((s) =>
          s.source === "fallback"
            ? { ...s, refreshing: false, slow: false, liveReady: true, error: null }
            : { data: resp, source: "live", refreshing: false, slow: false, error: null, liveReady: false, fetchedAt: at },
        );
      })
      .catch((e) => {
        if (cancelled || (e instanceof DOMException && e.name === "AbortError")) return;
        setState((s) => ({ ...s, refreshing: false, slow: false, error: e instanceof FetchError ? e : new FetchError(0, String(e)) }));
      });
    return () => {
      cancelled = true;
      ctrl.abort();
      timers.forEach(clearTimeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opts.enabled, opts.showcase, cacheKey, sig, reqWindow, since, nonce, pendingKey]);

  const showLive = useCallback(() => {
    if (liveRef.current)
      setState((s) => ({ ...s, data: liveRef.current, source: "live", liveReady: false, fetchedAt: new Date().toISOString() }));
  }, []);
  const refresh = useCallback(() => setNonce((n) => n + 1), []);
  return { ...state, since, reqWindow, refresh, showLive };
}
