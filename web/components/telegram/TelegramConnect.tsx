"use client";
// Connect Telegram: uploads symbols + weights only (opt-in server copy), then hands over a one-time t.me link.
// The subscriber secret stays in this browser and is the only way to change or delete the server copy here.
import { useState, useSyncExternalStore } from "react";
import { ArrowUpRight, Send } from "lucide-react";
import { effectiveWeights } from "@/lib/holdings";
import { FALLBACK, useStored, type LocalHolding } from "@/lib/store";
import { localAlertSettings } from "@/components/rules/AlertRules";

const SECRET_KEY = "finn.telegram.secret";
type Link = { deep_link: string; expires_at: string; uploaded: { symbol: string; weight_pct: number | null }[] };

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

export function TelegramConnect() {
  const holdings = useStored<LocalHolding[]>("holdings", FALLBACK.holdings);
  const [link, setLink] = useState<Link | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const stored = useSyncExternalStore(subscribeStorage, () => Boolean(readSecret()), () => false);
  const [override, setConnected] = useState<boolean | null>(null);
  const connected = override ?? stored;

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      const r = await fetch("/api/telegram/link", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          holdings: effectiveWeights(holdings).map((h) => ({ symbol: h.symbol, weight_pct: h.weight_pct })),
          settings: localAlertSettings(), // the rules edited on this phone become the alerts' rules
        }),
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Couldn't create the link — try again in a minute");
      try {
        localStorage.setItem(SECRET_KEY, body.secret);
      } catch {}
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
    const r = await fetch("/api/subscriptions/me", { method: "DELETE", headers: { authorization: `Bearer ${secret}` } }).catch(() => null);
    setBusy(false);
    if (r && (r.ok || r.status === 404)) {
      try {
        localStorage.removeItem(SECRET_KEY);
      } catch {}
      setConnected(false);
      setLink(null);
    } else {
      setError("Couldn't disconnect — send /stop to the bot in Telegram.");
    }
  }

  return (
    <div className="space-y-3">
      <p className="t-body text-ink-2">
        Results, management changes, unusual price moves and other material filings on your holdings — by default at
        most 5 messages a day, quiet from 10 pm to 7 am except M&amp;A, a CEO/MD exit or a rating downgrade (change these
        under Alert rules).
      </p>
      <div className="rounded-xl bg-surface-2 p-3">
        <p className="t-micro text-ink-3">What gets uploaded</p>
        <p className="t-small mt-1 text-ink-2">
          Holdings are used only to rank your Brief and are never stored, unless you turn on Telegram alerts.
          Connecting stores <b className="font-semibold text-ink">symbols and weights only</b> (no quantities), tied to your
          Telegram chat. “Disconnect &amp; delete” or /stop in Telegram removes them.
        </p>
        <p className="t-small mt-2 text-ink-3">
          Will upload: {holdings.length} symbols ({holdings.slice(0, 4).map((h) => h.symbol).join(", ")}
          {holdings.length > 4 ? "…" : ""}).
        </p>
      </div>
      {!link && (
        <button
          type="button"
          onClick={connect}
          disabled={busy}
          className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-ink text-[15px] font-medium text-paper disabled:opacity-50"
        >
          <Send className="size-4" strokeWidth={1.75} />
          {busy ? "Preparing…" : connected ? "Re-send link (update holdings)" : "Connect Telegram"}
        </button>
      )}
      {link && (
        <div className="space-y-2 rounded-xl border border-rule p-3">
          <p className="t-small">
            Uploaded {link.uploaded.length} symbols. Open Telegram and press <b>Start</b> — a test alert arrives at once.
            The link works once, for 15 minutes.
          </p>
          <a
            href={link.deep_link}
            className="inline-flex h-12 w-full items-center justify-center gap-1.5 rounded-xl bg-ink text-[15px] font-medium text-paper"
          >
            Open Telegram <ArrowUpRight className="size-4" />
          </a>
        </div>
      )}
      {error && <p className="t-small text-neg">{error}</p>}
      {connected && (
        <button type="button" onClick={disconnect} disabled={busy} className="t-small h-11 font-medium text-ink-2 underline underline-offset-4">
          Disconnect &amp; delete
        </button>
      )}
    </div>
  );
}
