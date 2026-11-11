// Paste/CSV import (PRODUCT §7): "SYMBOL 6%" is a weight, "SYMBOL 120" a share quantity. Stored in the browser.
// Until prices are wired (Friday's /portfolio), quantity-only holdings share the weight the others leave, equally.
import type { LocalHolding } from "@/lib/store";

export type ParseResult = { holdings: LocalHolding[]; unknown: string[]; errors: string[] };

export function parseHoldings(text: string, known: Set<string> | null): ParseResult {
  const out = new Map<string, LocalHolding>();
  const unknown: string[] = [];
  const errors: string[] = [];
  const now = ""; // stamped on save (no clock reads during prerender)
  for (const raw of text.split(/\r?\n|;/)) {
    const line = raw.trim();
    if (!line || /^symbol\b/i.test(line)) continue; // blank or CSV header
    const parts = line.split(/[\s,:=\t]+/).filter(Boolean);
    const sym = parts[0]?.toUpperCase().replace(/^NSE:/, "");
    if (!sym || !/^[A-Z0-9&_-]{1,20}$/.test(sym)) {
      errors.push(line);
      continue;
    }
    if (known && !known.has(sym)) unknown.push(sym);
    const v = parts[1];
    let weight: number | null = null;
    let qty: number | null = null;
    if (v) {
      const n = Number(v.replace(/[%,]/g, ""));
      if (!Number.isFinite(n) || n <= 0) {
        errors.push(line);
        continue;
      }
      if (v.includes("%") || (parts[2] ?? "").startsWith("%")) weight = n;
      else qty = n;
    }
    out.set(sym, { symbol: sym, weight_pct: weight, quantity: qty, added_at: now });
  }
  return { holdings: [...out.values()], unknown, errors };
}

/** Weights to send with /brief. Given weights are kept; holdings without one share what's left equally. */
export function effectiveWeights(h: LocalHolding[]): LocalHolding[] {
  const given = h.filter((x) => x.weight_pct !== null);
  const missing = h.length - given.length;
  if (missing === 0 || given.length === 0) return h;
  const left = Math.max(0, 100 - given.reduce((a, x) => a + (x.weight_pct ?? 0), 0));
  const each = left > 0 ? left / missing : null;
  return h.map((x) => (x.weight_pct !== null ? x : { ...x, weight_pct: each === null ? null : Math.round(each * 100) / 100 }));
}
