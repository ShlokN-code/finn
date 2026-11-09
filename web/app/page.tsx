"use client";

import { useEffect, useState } from "react";

type Hello =
  | { status: "ok"; row: { id: number; message: string; created_at: string }; db_ms: number; round_trip_ms: number }
  | { status: "error"; error: string };

const ist = (iso: string) =>
  new Date(iso).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", dateStyle: "medium", timeStyle: "short" }) +
  " IST";

async function getHello(): Promise<Hello> {
  try {
    const r = await fetch("/api/hello", { cache: "no-store" });
    return (await r.json()) as Hello;
  } catch {
    return { status: "error", error: "Network error" };
  }
}

export default function Home() {
  const [data, setData] = useState<Hello | null>(null);
  const [loading, setLoading] = useState(true);
  const [slow, setSlow] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const slowTimer = setTimeout(() => setSlow(true), 4000);
    getHello().then((d) => {
      if (cancelled) return;
      clearTimeout(slowTimer);
      setData(d);
      setLoading(false);
    });
    return () => {
      cancelled = true;
      clearTimeout(slowTimer);
    };
  }, [attempt]);

  const retry = () => {
    setLoading(true);
    setSlow(false);
    setAttempt((n) => n + 1);
  };

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col gap-6 px-4 py-10">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">FINN</h1>
        <p className="text-sm opacity-70">Skeleton check: web → API → database</p>
      </header>

      <section className="rounded-2xl border border-black/10 p-5 dark:border-white/15" aria-live="polite">
        {loading && (
          <p className="text-sm">
            {slow ? "Waking the API (free tier sleeps when idle — up to ~50s)…" : "Loading…"}
          </p>
        )}
        {!loading && data?.status === "ok" && (
          <div className="flex flex-col gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-emerald-600">Connected</p>
            <p className="text-lg">{data.row.message}</p>
            <p className="text-xs opacity-60">
              Row #{data.row.id} · created {ist(data.row.created_at)} · DB {data.db_ms} ms · round trip{" "}
              {data.round_trip_ms} ms
            </p>
          </div>
        )}
        {!loading && data?.status === "error" && (
          <div className="flex flex-col gap-3">
            <p className="text-xs font-medium uppercase tracking-wide text-red-600">Not connected</p>
            <p className="text-sm">{data.error}</p>
            <button onClick={retry} className="self-start rounded-full bg-foreground px-4 py-2 text-sm text-background">
              Retry
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
