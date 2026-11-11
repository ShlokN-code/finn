"use client";
// Browser → Vercel proxy (/api/*) → Render. Render's free tier can take ~50 s to wake: callers show progress,
// never a blank screen, and keep the last good data (CLAUDE.md rule 7).
import type { BriefRequest, BriefResponse, DossierJob, DossierResponse, DriversSection } from "@/lib/types";

export class FetchError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
  get waking() {
    return this.status === 502 || this.status === 503 || this.status === 504 || this.status === 0;
  }
}

async function call<T>(url: string, init: RequestInit = {}, timeoutMs = 58_000): Promise<T> {
  let r: Response;
  try {
    r = await fetch(url, { cache: "no-store", ...init, signal: init.signal ?? AbortSignal.timeout(timeoutMs) });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new FetchError(0, navigator.onLine === false ? "You're offline" : "Couldn't reach FINN");
  }
  if (!r.ok) {
    let detail = `FINN answered ${r.status}`;
    try {
      const b = await r.json();
      if (typeof b?.detail === "string") detail = b.detail;
    } catch {}
    throw new FetchError(r.status, detail);
  }
  return (await r.json()) as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  brief: (req: BriefRequest, signal?: AbortSignal) => call<BriefResponse>("/api/brief", { ...json(req), signal }),
  demoBrief: (window: "24h" | "3d" | "7d", signal?: AbortSignal) =>
    call<BriefResponse>(`/api/brief/demo?window=${window}`, { cache: "default", signal }),
  showcase: () => call<BriefResponse>("/showcase/brief.json", { cache: "default" }),
  dossier: (sym: string, signal?: AbortSignal) =>
    call<DossierResponse>(`/api/research/${encodeURIComponent(sym)}`, { signal }),
  build: (sym: string) => call<DossierResponse>(`/api/research/${encodeURIComponent(sym)}/build`, { method: "POST" }),
  job: (id: number, signal?: AbortSignal) =>
    call<DossierJob & { dossier_version: number }>(`/api/research/jobs/${id}`, { signal }, 20_000),
  fixture: (sym: string) => call<DossierResponse>(`/fixtures/dossier_${sym}.json`, { cache: "default" }),
  symbols: () => call<{ symbols: [string, string][] }>("/api/research/symbols", {}, 58_000),
  drivers: (symbols: string[]) =>
    call<{ drivers: Record<string, DriversSection | null> }>(
      `/api/research/drivers?symbols=${encodeURIComponent(symbols.join(","))}`,
    ),
  staticSymbols: () => call<{ at: string; symbols: [string, string][] }>("/nse-symbols.json", { cache: "default" }),
};
