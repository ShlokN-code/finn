"use client";
// A number with provenance: tap → sheet with document, page, quote, formula and inputs (PRODUCT §8 rule).
import { useState } from "react";
import type { Figure } from "@/lib/types";
import { figureText } from "@/lib/format";
import { Sheet } from "@/components/shell/Sheet";
import { FigureProvenance } from "./Provenance";

export function FigureValue({
  f,
  signed = false,
  printed = false,
  className = "",
}: {
  f: Figure | null | undefined;
  signed?: boolean;
  /** Show the value exactly as the source printed it (ledger: "119.3 million", "7.54 %"). */
  printed?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  if (!f) return <span className="text-ink-3">—</span>;
  const unverified = f.status !== "verified";
  const text = printed && f.raw ? f.raw.replace(/\s+%/, "%") : figureText(f, { signed });
  return (
    <>
      <button
        type="button"
        data-figure
        onClick={(e) => {
          e.stopPropagation();
          setOpen(true);
        }}
        className={`hit whitespace-nowrap tabular-nums underline decoration-dotted decoration-1 underline-offset-[5px] ${
          unverified ? "decoration-warn" : "decoration-ink-3/70"
        } ${className}`}
        aria-label={`${f.label}: ${text}${unverified ? " (unverified)" : ""} — show source`}
      >
        {text}
      </button>
      <Sheet open={open} onClose={() => setOpen(false)} eyebrow="Source" title={f.label}>
        <FigureProvenance f={f} />
      </Sheet>
    </>
  );
}
