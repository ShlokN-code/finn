// Display formatting (Indian conventions). Display only — never feed these strings back into arithmetic.
import type { Card, Citation, Figure } from "@/lib/types";

const inr0 = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const inr1 = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const inr2 = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const upTo2 = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });
const pct = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 1, maximumFractionDigits: 2 });

const minus = (s: string) => s.replace("-", "−");

export function moneyCr(v: number): string {
  return `₹${minus(Math.abs(v) >= 100 ? inr0.format(v) : inr1.format(v))} Cr`;
}

/** Signed change with ▲/▼ (moves stay ink; the glyph carries direction). */
export function signed(v: number, digits = 1, suffix = "%"): string {
  const r = Number(v.toFixed(digits));
  const glyph = r > 0 ? "▲" : r < 0 ? "▼" : "±";
  return `${glyph}${Math.abs(r).toFixed(digits)}${suffix}`;
}

export function count(v: number): string {
  const a = Math.abs(v);
  if (a >= 1e7) return `${minus(upTo2.format(v / 1e7))} Cr`;
  if (a >= 1e5) return `${minus(upTo2.format(v / 1e5))} lakh`;
  return minus(inr0.format(v));
}

export function figureText(f: Figure | null | undefined, opts: { signed?: boolean } = {}): string {
  if (!f || f.value === null) return "n/m";
  const v = f.value;
  switch (f.unit) {
    case "INR_CR":
      return opts.signed ? `${v >= 0 ? "▲" : "▼"}${moneyCr(Math.abs(v))}` : moneyCr(v);
    case "PCT":
      return opts.signed ? signed(v) : `${minus(pct.format(v))}%`;
    case "BPS":
      return signed(v, 0, " bps");
    case "X":
      return `${inr2.format(v)}×`;
    case "INR":
    case "INR_PER_SHARE":
      return `₹${inr2.format(v)}`;
    case "YEARS":
      return `${inr1.format(v)} yrs`;
    case "DAYS":
      return `${inr0.format(v)} days`;
    case "COUNT":
    case "SHARES":
      return count(v);
    default:
      return minus(inr1.format(v));
  }
}

const IST = "Asia/Kolkata";
const fmt = (o: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat("en-IN", { timeZone: IST, ...o });
const fTime = fmt({ hour: "2-digit", minute: "2-digit", hour12: false });
const fDay = fmt({ day: "numeric", month: "short" });
const fDayYear = fmt({ day: "numeric", month: "short", year: "numeric" });
const fDate = fmt({ year: "numeric", month: "2-digit", day: "2-digit" });
const fClock = fmt({ hour: "numeric", minute: "2-digit", hour12: true });

export const istTime = (iso: string) => fTime.format(new Date(iso));
export const istClock = (iso: string) => fClock.format(new Date(iso)).replace(" ", " ").toLowerCase();
export const istDay = (iso: string) => fDay.format(new Date(iso));
export const istDayYear = (iso: string) => fDayYear.format(new Date(iso));
export const istDateKey = (iso: string | number | Date) => fDate.format(new Date(iso));
export const isTodayIST = (iso: string) => istDateKey(iso) === istDateKey(Date.now());

/** "16:38" today, "30 Oct 16:38" otherwise. */
export function istWhen(iso: string): string {
  return isTodayIST(iso) ? istTime(iso) : `${istDay(iso)} ${istTime(iso)}`;
}

export function ist(iso: string, withTime = true): string {
  return withTime ? `${istDay(iso)} ${istTime(iso)} IST` : istDayYear(iso);
}

export function readTime(seconds: number): string {
  if (seconds <= 0) return "nothing to read";
  if (seconds < 120) return `~${Math.max(10, Math.round(seconds / 10) * 10)} sec`;
  return `~${Math.round(seconds / 60)} min`;
}

export const CATEGORY_LABEL: Record<string, string> = {
  results: "Results",
  mna: "M&A",
  management_change: "Management",
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
  price_volume: "Price move",
  investor_meetings: "Investor meeting",
  routine: "Routine",
  unclassified: "Unclassified",
};

export const CATEGORY_PLURAL: Record<string, string> = {
  results: "results",
  mna: "M&A filings",
  management_change: "management changes",
  litigation: "litigation filings",
  credit_rating: "rating actions",
  pledging: "pledge filings",
  capex: "capex filings",
  press_release: "press releases",
  insider_trading: "insider trades",
  fund_raise: "fund raises",
  dividend: "dividends",
  bonus_split: "bonus/split filings",
  price_volume: "price moves",
};

/** Lead with meaning: code-written results lines and named appointees beat generic exchange subjects. */
export function displayHeadline(card: Card): { headline: string; sub: string | null } {
  const d = card.detail;
  if (card.card_type === "results" && d?.kind === "results" && d.verification !== "mismatch") {
    return { headline: card.so_what, sub: null };
  }
  if (d?.kind === "management_change" && d.people.length > 0) {
    const p = d.people[0];
    const change = { appointed: "appointed", resigned: "resigns", re_designated: "re-designated", retired: "retires", other: "" }[p.change];
    const more = d.people.length > 1 ? ` (+${d.people.length - 1} more)` : "";
    return { headline: `${p.name}, ${p.role}${change ? ` — ${change}` : ""}${more}`, sub: null };
  }
  const title = card.headline.replace(/^[^:]{2,40}:\s+/, "");
  const cleaned = title.charAt(0).toUpperCase() + title.slice(1);
  if (card.card_type === "what_to_watch") return { headline: cleaned, sub: card.so_what };
  if (card.so_what && card.so_what !== cleaned) return { headline: cleaned, sub: card.so_what };
  return { headline: cleaned, sub: null };
}

const PDF_TYPES = new Set(["exchange_filing", "concall_transcript", "investor_presentation", "annual_report"]);
export function sourceHref(c: Citation): string {
  return c.page && PDF_TYPES.has(c.source_type) ? `${c.url}#page=${c.page}` : c.url;
}

export function sourceLabel(c: Citation): string {
  const page = c.page ? ` p.${c.page}` : "";
  switch (c.source_type) {
    case "exchange_filing":
      return `${c.exchange ?? "NSE"} filing${page}`;
    case "xbrl":
      return "NSE XBRL";
    case "screener_table":
      return "screener.in";
    case "concall_transcript":
      return `${c.title?.replace(/ transcript$/i, "") ?? "Call transcript"}${page}`;
    case "investor_presentation":
      return `${c.title?.replace(/ investor presentation$/i, " deck") ?? "Investor deck"}${page}`;
    case "annual_report":
      return `${c.title ?? "Annual report"}${page}`;
    case "price_feed":
      return "Price feed";
    case "web_profile":
      return "web · unverified";
    default:
      return c.title ?? "Source";
  }
}
