// Signal glyphs: colour only where it carries meaning (impact, verdicts, verification, warnings).
// The spec's ✅ ❌ ↘ ↗ 🔇 / 🟢🔴🟡⚪ are drawn as monochrome glyphs in signal colour, not system emoji.
import { VolumeX } from "lucide-react";
import type { Impact, MgmtPromise } from "@/lib/types";

export type Tone = "pos" | "neg" | "warn" | "muted";
export const TONE_TEXT: Record<Tone, string> = { pos: "text-pos", neg: "text-neg", warn: "text-warn", muted: "text-ink-3" };
export const TONE_BG: Record<Tone, string> = { pos: "bg-pos", neg: "bg-neg", warn: "bg-warn", muted: "bg-ink-3" };

export const IMPACT: Record<Impact, { label: string; tone: Tone }> = {
  positive: { label: "Positive", tone: "pos" },
  negative: { label: "Negative", tone: "neg" },
  mixed: { label: "Mixed", tone: "warn" },
  neutral: { label: "Neutral", tone: "muted" },
};

export function Dot({ tone, className = "" }: { tone: Tone; className?: string }) {
  return <span aria-hidden className={`inline-block size-1.5 shrink-0 rounded-full ${TONE_BG[tone]} ${className}`} />;
}

export function ImpactLabel({ impact, title }: { impact: Impact | null; title?: string }) {
  if (!impact) return null;
  const i = IMPACT[impact];
  return (
    <span title={title} className={`t-small inline-flex items-center gap-1.5 whitespace-nowrap ${TONE_TEXT[i.tone]}`}>
      <Dot tone={i.tone} />
      {i.label}
    </span>
  );
}

export type Verdict = MgmtPromise["verdict"];
export const VERDICT: Record<Verdict, { label: string; glyph: string; tone: Tone }> = {
  kept: { label: "Kept", glyph: "✓", tone: "pos" },
  missed: { label: "Missed", glyph: "✕", tone: "neg" },
  goalposts_moved: { label: "Goalposts moved", glyph: "↘", tone: "warn" },
  quietly_dropped: { label: "Quietly dropped", glyph: "", tone: "muted" },
  not_yet_due: { label: "Not yet due", glyph: "○", tone: "muted" },
  cant_score: { label: "Can't score", glyph: "–", tone: "muted" },
};

export function VerdictGlyph({ verdict, className = "" }: { verdict: Verdict; className?: string }) {
  const v = VERDICT[verdict];
  if (verdict === "quietly_dropped")
    return <VolumeX aria-label={v.label} className={`size-[15px] ${TONE_TEXT[v.tone]} ${className}`} strokeWidth={2} />;
  return (
    <span aria-label={v.label} className={`inline-block w-[15px] text-center font-semibold leading-none ${TONE_TEXT[v.tone]} ${className}`}>
      {v.glyph}
    </span>
  );
}
