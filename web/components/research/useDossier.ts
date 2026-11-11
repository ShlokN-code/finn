"use client";
// One dossier: GET it, poll an active build (every 3 s; every 60 s while parked for model quota), refetch when a
// section is published (dossier_version changes). If the API can't be reached, the 4 demo tickers fall back to
// their saved fixtures (labelled). Never starts a build by itself — the user confirms first.
import { useCallback, useEffect, useRef, useState } from "react";
import { api, FetchError } from "@/lib/client";
import { DEMO_TICKERS } from "@/lib/demo";
import type { DossierJob, DossierResponse } from "@/lib/types";
import { mockJobSequence } from "./mockBuild";

export type DossierState = {
  resp: DossierResponse | null;
  status: "loading" | "ready" | "error" | "notfound";
  error: FetchError | null;
  source: "live" | "fixture" | "mock";
  slow: boolean;
  building: boolean;
  buildError: string | null;
};

const ACTIVE = new Set<DossierJob["status"]>(["queued", "running", "waiting_quota"]);
export const isActive = (j: DossierJob | null | undefined) => !!j && ACTIVE.has(j.status);

export function useDossier(symbol: string, mock: boolean) {
  const [s, setS] = useState<DossierState>({ resp: null, status: "loading", error: null, source: "live", slow: false, building: false, buildError: null });
  const version = useRef<number>(-1);
  const [tick, setTick] = useState(0);

  const load = useCallback(async () => {
    const slow = setTimeout(() => setS((p) => ({ ...p, slow: true })), 4000);
    try {
      if (mock) {
        const fx = await api.fixture((DEMO_TICKERS as readonly string[]).includes(symbol) ? symbol : "INFY");
        version.current = 0;
        setS((p) => ({ ...p, resp: { ...fx, symbol, job: null }, status: "ready", source: "mock", slow: false }));
        return;
      }
      const resp = await api.dossier(symbol);
      version.current = resp.dossier_version;
      setS((p) => ({ ...p, resp, status: "ready", error: null, source: "live", slow: false }));
    } catch (e) {
      const err = e instanceof FetchError ? e : new FetchError(0, String(e));
      if (err.status === 404) return setS((p) => ({ ...p, status: "notfound", error: err, slow: false }));
      if ((DEMO_TICKERS as readonly string[]).includes(symbol)) {
        try {
          const fx = await api.fixture(symbol);
          return setS((p) => ({ ...p, resp: fx, status: "ready", source: "fixture", error: err, slow: false }));
        } catch {}
      }
      setS((p) => ({ ...p, status: p.resp ? "ready" : "error", error: err, slow: false }));
    } finally {
      clearTimeout(slow);
    }
  }, [symbol, mock]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetches the dossier (external system)
    load();
  }, [load, tick]);

  // Poll an active job.
  const job = s.resp?.job ?? null;
  const jobActive = isActive(job);
  useEffect(() => {
    if (!jobActive || !job || s.source !== "live") return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const j = await api.job(job.id);
        if (cancelled) return;
        const { dossier_version, ...jobOnly } = j;
        if (dossier_version !== version.current || !isActive(jobOnly)) {
          await load();
        } else {
          setS((p) => (p.resp ? { ...p, resp: { ...p.resp, job: jobOnly } } : p));
        }
        if (isActive(jobOnly)) timer = setTimeout(poll, jobOnly.status === "waiting_quota" ? 60_000 : 3000);
      } catch {
        if (!cancelled) timer = setTimeout(poll, 6000);
      }
    };
    timer = setTimeout(poll, 3000);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobActive, job?.id, s.source]);

  // Dev-only: a scripted job so the progress UI can be checked without spending model quota.
  useEffect(() => {
    if (!mock || s.status !== "ready") return;
    return mockJobSequence(symbol, (j) => setS((p) => (p.resp ? { ...p, resp: { ...p.resp, job: j } } : p)));
  }, [mock, s.status, symbol]);

  const build = useCallback(async () => {
    setS((p) => ({ ...p, building: true, buildError: null }));
    try {
      const resp = await api.build(symbol);
      version.current = resp.dossier_version;
      setS((p) => ({ ...p, resp, building: false, source: "live" }));
    } catch (e) {
      const err = e instanceof FetchError ? e : new FetchError(0, String(e));
      setS((p) => ({
        ...p,
        building: false,
        buildError:
          err.status === 429
            ? "FINN has used today's budget for new dossiers. It resets at midnight IST — the 4 ready companies open instantly meanwhile."
            : err.waking
              ? "FINN's server is waking up — try again in a minute."
              : err.message,
      }));
    }
  }, [symbol]);

  return { ...s, build, reload: () => setTick((t) => t + 1) };
}
