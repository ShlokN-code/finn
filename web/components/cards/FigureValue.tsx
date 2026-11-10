"use client";
// A number with provenance: tap → drawer with document, page, quote, formula and inputs (PRODUCT §8 rule).
import { useState } from "react";
import type { Figure } from "@/lib/types";
import { figureText } from "@/lib/format";

export function FigureValue({ f, signed = false, className = "" }: { f: Figure | null | undefined; signed?: boolean; className?: string }) {
  const [open, setOpen] = useState(false);
  if (!f) return <span className="text-muted-foreground">—</span>;
  const unverified = f.status !== "verified";
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={`tabular-nums underline decoration-dotted underline-offset-4 ${unverified ? "decoration-amber-500" : "decoration-foreground/30"} ${className}`}
        aria-label={`${f.label}: ${figureText(f, { signed })} — show source`}
      >
        {figureText(f, { signed })}
      </button>
      {open && <Provenance f={f} onClose={() => setOpen(false)} />}
    </>
  );
}

function Provenance({ f, onClose }: { f: Figure; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end bg-black/40" onClick={onClose} role="dialog" aria-modal>
      <div
        className="max-h-[80vh] w-full overflow-y-auto rounded-t-2xl bg-background p-5 text-sm shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-start justify-between gap-4">
          <div>
            <p className="font-semibold">{f.label}</p>
            <p className="text-xs text-muted-foreground">
              {f.period?.label ?? ""} {f.basis ? `· ${f.basis}` : ""} · {f.status.replace("_", " ")}
            </p>
          </div>
          <button type="button" onClick={onClose} className="text-muted-foreground" aria-label="Close">
            ✕
          </button>
        </div>
        <p className="text-2xl font-semibold tabular-nums">{figureText(f)}</p>
        {f.check_note && <p className="mt-2 text-xs text-muted-foreground">{f.check_note}</p>}
        {f.formula && (
          <div className="mt-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Computed in code</p>
            <p className="mt-1 font-mono text-xs">{f.formula}</p>
            <ul className="mt-2 space-y-1">
              {f.inputs.map((i, n) => (
                <li key={n} className="flex justify-between gap-3 text-xs">
                  <span>{i.label} {i.period ? `(${i.period.label})` : ""}</span>
                  <span className="tabular-nums">{figureText(i)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {f.citation && (
          <div className="mt-4 space-y-1">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Source</p>
            <a href={f.citation.url} target="_blank" rel="noopener noreferrer" className="block break-all text-xs underline">
              {f.citation.title ?? f.citation.url}
            </a>
            {f.citation.page && <p className="text-xs">Page {f.citation.page}</p>}
            {f.citation.locator && <p className="font-mono text-xs text-muted-foreground">{f.citation.locator}</p>}
            {f.citation.quote && <blockquote className="border-l-2 pl-2 text-xs italic">“{f.citation.quote}”</blockquote>}
            {f.raw && (
              <p className="text-xs text-muted-foreground">
                As printed: {f.raw} {f.raw_unit ?? ""}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
