// Inline chip for dividends and bonus/splits, e.g. "₹8 dividend · record 21 Nov".
import type { ChipDetail } from "@/lib/types";

export function InlineChip({ symbol, d }: { symbol: string; d: ChipDetail }) {
  const body = (
    <span className="t-small inline-flex items-center gap-1.5">
      <span className="font-semibold">{symbol}</span>
      <span className="text-ink-2">{d.text}</span>
    </span>
  );
  return d.citation ? (
    <a href={d.citation.url} target="_blank" rel="noopener noreferrer" className="underline decoration-ink-3/40 underline-offset-4">
      {body}
    </a>
  ) : (
    body
  );
}
