"use client";
// The provenance drawer: every number and claim opens its document, page and verbatim quote (PRODUCT §8, rule 3).
import { ArrowUpRight } from "lucide-react";
import type { Citation, Claim, Figure } from "@/lib/types";
import { figureText, ist, sourceHref, sourceLabel } from "@/lib/format";

const STATUS: Record<string, { text: string; cls: string }> = {
  verified: { text: "Verified in source", cls: "text-pos" },
  unverified: { text: "Unverified", cls: "text-warn" },
  not_found: { text: "Not found in sources", cls: "text-warn" },
};

export function CitationBlock({ c, label }: { c: Citation; label?: string }) {
  return (
    <div className="border-t border-rule py-3 first:border-t-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          {label && <p className="t-micro text-ink-3">{label}</p>}
          <p className="t-small font-medium">{c.title ?? sourceLabel(c)}</p>
          <p className="t-small text-ink-3">
            {[sourceLabel(c), c.published_at ? ist(c.published_at, false) : null].filter(Boolean).join(" · ")}
          </p>
        </div>
        <a
          href={sourceHref(c)}
          target="_blank"
          rel="noopener noreferrer"
          className="t-small inline-flex h-9 shrink-0 items-center gap-1 rounded-full border border-rule px-3 font-medium"
        >
          {c.page ? `Open p.${c.page}` : "Open"} <ArrowUpRight className="size-3.5" />
        </a>
      </div>
      {c.quote && (
        <blockquote className="mt-2 border-l-2 border-ink-3/40 pl-3 font-serif text-[16px] leading-[23px] text-ink">
          “{c.quote}”
        </blockquote>
      )}
      {c.locator && !c.quote && <p className="mt-1 break-all font-mono text-[11px] text-ink-3">{c.locator}</p>}
    </div>
  );
}

export function FigureProvenance({ f }: { f: Figure }) {
  const st = STATUS[f.status] ?? STATUS.unverified;
  return (
    <div>
      <p className="t-small text-ink-2">
        {[f.period?.label, f.basis].filter(Boolean).join(" · ")}
        {(f.period || f.basis) && " · "}
        <span className={st.cls}>{st.text}</span>
      </p>
      <p className="t-figure-lg mt-1">{figureText(f)}</p>
      {f.raw && (
        <p className="t-small mt-1 text-ink-3">
          As printed: {f.raw} {f.raw_unit && !f.raw.toLowerCase().includes(f.raw_unit) ? f.raw_unit : ""}
        </p>
      )}
      {f.check_note && <p className="t-small mt-2 text-ink-2">{f.check_note}</p>}
      {f.formula && (
        <div className="mt-4 rounded-xl bg-surface-2 p-3">
          <p className="t-micro text-ink-3">Computed in code</p>
          <p className="mt-1 font-mono text-[12px] leading-[18px]">{f.formula}</p>
          {f.inputs.length > 0 && (
            <ul className="mt-2 space-y-1">
              {f.inputs.map((i, n) => (
                <li key={n} className="t-small flex justify-between gap-3">
                  <span className="text-ink-2">
                    {i.label}
                    {i.period ? ` · ${i.period.label}` : ""}
                  </span>
                  <span className="t-figure text-[13px]">{figureText(i)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {f.citation && (
        <div className="mt-3">
          <CitationBlock c={f.citation} label="Source" />
        </div>
      )}
      {!f.citation && f.inputs.some((i) => i.citation) && (
        <div className="mt-3">
          <p className="t-micro text-ink-3">Input sources</p>
          {dedupe(f.inputs.map((i) => i.citation).filter((c): c is Citation => !!c)).map((c, i) => (
            <CitationBlock key={i} c={c} />
          ))}
        </div>
      )}
    </div>
  );
}

export function ClaimProvenance({ claim }: { claim: Claim }) {
  const st = STATUS[claim.status] ?? STATUS.unverified;
  return (
    <div>
      <p className="font-serif text-[18px] leading-[25px]">{claim.text}</p>
      <p className={`t-small mt-1 ${st.cls}`}>{st.text}</p>
      <div className="mt-3">
        {dedupe(claim.citations).map((c, i) => (
          <CitationBlock key={i} c={c} />
        ))}
      </div>
    </div>
  );
}

function dedupe(cs: Citation[]): Citation[] {
  const seen = new Set<string>();
  return cs.filter((c) => {
    const k = `${c.url}#${c.page ?? ""}#${c.locator ?? ""}#${c.quote ?? ""}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}
