"use client";
// Connect Telegram: uploads symbols + weights only (opt-in server copy), then hands over a one-time t.me link.
// The subscriber secret stays in this browser and is the only way to change or delete the server copy here.
import { useState, useSyncExternalStore } from "react";

const DEMO =
  "HAL 6\nEICHERMOT 6\nGRASIM 5\nTATAPOWER 5\nALKEM 5\nKALYANKJIL 5\nCOCHINSHIP 5\nTITAGARH 4\nIDEA 3\n" +
  "RELIANCE 8\nHDFCBANK 8\nBAJFINANCE 6\nINFY 7\nITC 6\nDIVISLAB 5\nTATASTEEL 5\nJUBLFOOD 5\nDIXON 6";
const SECRET_KEY = "finn.telegram.secret";

type Link = { deep_link: string; expires_at: string; uploaded: { symbol: string; weight_pct: number | null }[] };

function parse(text: string) {
  return text
    .split(/[\n,]+/)
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => {
      const [sym, w] = l.split(/[\s:=]+/);
      const weight = w ? Number(w.replace("%", "")) : NaN;
      return { symbol: sym.toUpperCase(), weight_pct: Number.isFinite(weight) && weight > 0 ? weight : null };
    });
}

function readSecret(): string | null {
  try {
    return localStorage.getItem(SECRET_KEY);
  } catch {
    return null;
  }
}

function subscribeStorage(cb: () => void) {
  window.addEventListener("storage", cb);
  return () => window.removeEventListener("storage", cb);
}

export default function Connect() {
  const [text, setText] = useState(DEMO);
  const [link, setLink] = useState<Link | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Stored secret = this browser already connected. Server render assumes not connected.
  const stored = useSyncExternalStore(
    subscribeStorage,
    () => Boolean(readSecret()),
    () => false,
  );
  const [override, setConnected] = useState<boolean | null>(null);
  const connected = override ?? stored;

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      const r = await fetch("/api/telegram/link", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ holdings: parse(text) }),
      });
      const body = await r.json();
      if (!r.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Couldn't create the link");
      try {
        localStorage.setItem(SECRET_KEY, body.secret);
      } catch {
        // private mode: the link still works; disconnect via /stop in Telegram
      }
      setLink(body);
      setConnected(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    const secret = readSecret();
    if (!secret) return;
    setBusy(true);
    const r = await fetch("/api/subscriptions/me", { method: "DELETE", headers: { authorization: `Bearer ${secret}` } });
    setBusy(false);
    if (r.ok || r.status === 404) {
      try {
        localStorage.removeItem(SECRET_KEY);
      } catch {}
      setConnected(false);
      setLink(null);
    } else {
      setError("Couldn't disconnect — try /stop in Telegram.");
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col gap-5 px-4 py-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Telegram alerts</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Results, management changes, unusual price moves and other material filings on your holdings — at most 5
          messages a day, quiet from 10 pm to 7 am unless it&apos;s critical.
        </p>
      </header>

      <section className="rounded-2xl border p-4 text-sm">
        <p className="font-medium">What gets uploaded</p>
        <p className="mt-1 text-muted-foreground">
          Holdings are used only to rank your Brief and are never stored, unless you turn on Telegram alerts.
          Connecting stores <b>symbols and weights only</b> (no quantities), tied to your Telegram chat.
          “Disconnect &amp; delete” or /stop in Telegram removes them.
        </p>
      </section>

      <label className="text-sm font-medium" htmlFor="holdings">
        Holdings (one per line: SYMBOL weight%)
      </label>
      <textarea
        id="holdings"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={8}
        className="rounded-xl border bg-background p-3 font-mono text-sm"
      />

      {!link && (
        <button
          type="button"
          onClick={connect}
          disabled={busy}
          className="rounded-xl bg-primary px-4 py-3 text-sm font-medium text-primary-foreground disabled:opacity-50"
        >
          {busy ? "Preparing…" : "Connect Telegram"}
        </button>
      )}

      {link && (
        <section className="space-y-3 rounded-2xl border p-4 text-sm">
          <p>
            Uploaded {link.uploaded.length} symbols. Open Telegram and press <b>Start</b> — a test alert arrives
            immediately. The link works once, for 15 minutes.
          </p>
          <a
            href={link.deep_link}
            className="block rounded-xl bg-primary px-4 py-3 text-center font-medium text-primary-foreground"
          >
            Open Telegram
          </a>
        </section>
      )}

      {error && <p className="text-sm text-red-700 dark:text-red-300">{error}</p>}

      {connected && (
        <button type="button" onClick={disconnect} disabled={busy} className="text-sm text-muted-foreground underline">
          Disconnect &amp; delete
        </button>
      )}
    </main>
  );
}
