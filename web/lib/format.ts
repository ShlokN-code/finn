// Display formatting (Indian conventions). Display only — never feed these strings back into arithmetic.
import type { Figure } from "@/lib/types";

const inr0 = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const inr1 = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const inr2 = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const minus = (s: string) => s.replace("-", "−");

export function moneyCr(v: number): string {
  return `₹${minus(Math.abs(v) >= 100 ? inr0.format(v) : inr1.format(v))} Cr`;
}

export function signed(v: number, digits = 1, suffix = "%"): string {
  const r = Number(v.toFixed(digits));
  const sign = r > 0 ? "+" : r < 0 ? "−" : "±";
  return `${sign}${Math.abs(r).toFixed(digits)}${suffix}`;
}

export function figureText(f: Figure | null | undefined, opts: { signed?: boolean } = {}): string {
  if (!f || f.value === null) return "n/m";
  const v = f.value;
  switch (f.unit) {
    case "INR_CR":
      return moneyCr(v);
    case "PCT":
      return opts.signed ? signed(v) : `${minus(inr1.format(v))}%`;
    case "BPS":
      return signed(v, 0, " bps");
    case "X":
      return `${inr1.format(v)}×`;
    case "INR":
    case "INR_PER_SHARE":
      return `₹${inr2.format(v)}`;
    case "YEARS":
      return `${inr1.format(v)} yrs`;
    default:
      return minus(inr1.format(v));
  }
}

export function ist(iso: string, withTime = true): string {
  return (
    new Date(iso).toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
      day: "numeric",
      month: "short",
      ...(withTime ? { hour: "2-digit", minute: "2-digit", hour12: false } : { year: "numeric" }),
    }) + (withTime ? " IST" : "")
  );
}

export const CATEGORY_LABEL: Record<string, string> = {
  results: "Results",
  mna: "M&A",
  management_change: "Management change",
  litigation: "Litigation",
  credit_rating: "Credit rating",
  pledging: "Pledging",
  capex: "Capex",
  press_release: "Press release",
  insider_trading: "Insider trade",
  fund_raise: "Fund raise",
  dividend: "Dividend",
  bonus_split: "Bonus / split",
  earnings_call: "Earnings call",
  agm_egm: "AGM / EGM",
  postal_ballot: "Postal ballot",
  price_volume: "Price / volume",
};
