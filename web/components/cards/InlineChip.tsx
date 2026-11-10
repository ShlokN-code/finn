// Inline chip for dividends and bonus/splits, e.g. "₹8 dividend · record 21 Nov".
import type { ChipDetail } from "@/lib/types";

export function InlineChip({ symbol, d }: { symbol: string; d: ChipDetail }) {
  const body = (
    <span className="inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs">
      <span className="font-semibold">{symbol}</span> {d.text}
    </span>
  );
  return d.citation ? (
    <a href={d.citation.url} target="_blank" rel="noopener noreferrer">
      {body}
    </a>
  ) : (
    body
  );
}
