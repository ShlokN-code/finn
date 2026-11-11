"use client";
// The provenance drawer: every number and claim opens its document, page and verbatim quote (PRODUCT §8, rule 3).
// Open always lands on something a person can read (results PDF page, iXBRL view, filing PDF); a machine-readable
// original (raw XBRL) is offered only as a small secondary link (DECISIONS: readable Open links).
import type { ReactNode } from "react";
import { ArrowUpRight } from "lucide-react";
import type { Citation, Claim, Figure } from "@/lib/types";
import { figureText, ist, openLabel, sourceHref, sourceLabel } from "@/lib/format";

const STATUS: Record<string, { text: string; cls: string }> = {
  verified: { text: "Verified in source", cls: "text-pos" },
  unverified: { text: "Unverified", cls: "text-warn" },
  not_found: { text: "Not found in sources", cls: "text-warn" },
};

function OpenButton({ c }: { c: Citation }) {
  return (
    <a
      href={sourceHref(c)}
      target="_blank"
      rel="noopener noreferrer"
      className="t-small inline-flex h-9 shrink-0 items-center gap-1 whitespace-nowrap rounded-full border border-rule px-3 font-medium"
    >
      {openLabel(c)} <ArrowUpRight className="size-3.5" />
    </a>
  );
}

function RawLink({ c }: { c: Citation }) {
  if (!c.raw_url || c.raw_url === c.url) return null;
  return (
    <a href={c.raw_url} target="_blank" rel="noopener noreferrer" className="t-small mt-1 inline-block text-ink-3 underline underline-offset-4">
      Raw XBRL (machine-readable)
    </a>
  );
}

export function CitationBlock({ c, label, children }: { c: Citation; label?: string; children?: ReactNode }) {
  const meta = [sourceLabel(c), c.published_at ? ist(c.published_at, false) : null].filter(Boolean).join(" · ");
  return (
    <div className="border-t border-rule py-3 first:border-t-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          {label && <p className="t-micro text-ink-3">{label}</p>}
          <p className="t-small font-medium">{c.title ?? sourceLabel(c)}</p>
          <p className="t-small text-ink-3">{meta}</p>
        </div>
        <OpenButton c={c} />
      </div>
      {c.quote && (
        <blockquote className="mt-2 border-l-2 border-ink-3/40 pl-3 font-serif text-[16px] leading-[23px] text-ink">
          “{c.quote}”
        </blockquote>
      )}
      {c.page && (c.doc_kind === "results_pdf" || c.doc_kind === "pdf") && (
        <p className="t-small mt-1 text-ink-3">Page {c.page} as your PDF viewer counts it; the document may print its own page numbers.</p>
      )}
      {children}
      {c.locator && !c.quote && !children && <p className="mt-1 break-all font-mono text-[11px] text-ink-3">{c.locator}</p>}
      <RawLink c={c} />
    </div>
  );
}

type Supplied = { label: string; period: string | null; value: string; locator: string | null };
type Doc = { c: Citation; items: Supplied[] };

/** Every sourced figure behind `f` (itself and its inputs, recursively), grouped by the document it came from. */
function sourceDocs(f: Figure): Doc[] {
  const docs = new Map<string, Doc>();
  const visit = (x: Figure) => {
    if (x.citation) {
      const key = `${sourceHref(x.citation)}|${x.citation.quote ?? ""}`;
      let d = docs.get(key);
      if (!d) docs.set(key, (d = { c: x.citation, items: [] }));
      const item = { label: x.label, period: x.period?.label ?? null, value: figureText(x), locator: x.citation.locator };
      if (!d.items.some((i) => i.label === item.label && i.period === item.period)) d.items.push(item);
    }
    x.inputs.forEach(visit);
  };
  visit(f);
  return [...docs.values()];
}

function checkUrl(f: Figure): string | null {
  if (f.citation?.check_url) return f.citation.check_url;
  for (const i of f.inputs) {
    const u = checkUrl(i);
    if (u) return u;
  }
  return null;
}

export function FigureProvenance({ f }: { f: Figure }) {
  const st = STATUS[f.status] ?? STATUS.unverified;
  const docs = sourceDocs(f);
  const check = checkUrl(f);
  return (
    <div>
      <p className="t-small text-ink-2">
        {[f.period?.label, f.basis].filter(Boolean).join(" · ")}
        {(f.period || f.basis) && " · "}
        <span className={st.cls}>{st.text}</span>
      </p>
      <p className="t-figure-lg mt-1 whitespace-nowrap">{figureText(f)}</p>
      {f.raw && f.citation?.source_type !== "xbrl" && (
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
                <li key={n} className="t-small flex items-baseline justify-between gap-3">
                  <span className="min-w-0 text-ink-2">
                    {i.label}
                    {i.period ? ` · ${i.period.label}` : ""}
                  </span>
                  <span className="t-figure shrink-0 whitespace-nowrap text-[13px]">{figureText(i)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {docs.length > 0 && (
        <div className="mt-3">
          <p className="t-micro text-ink-3">{docs.length === 1 ? "Source" : `Sources · ${docs.length} documents`}</p>
          {docs.map((d, i) => (
            <CitationBlock key={i} c={d.c}>
              {(d.items.length > 1 || f.inputs.length > 0) && (
                <ul className="mt-2 space-y-1">
                  {d.items.map((it, n) => (
                    <li key={n} className="t-small flex items-baseline justify-between gap-3">
                      <span className="min-w-0 text-ink-2">
                        {it.label}
                        {it.period ? ` · ${it.period}` : ""}
                        {it.locator && <span className="block break-all font-mono text-[11px] text-ink-3">{it.locator}</span>}
                      </span>
                      <span className="t-figure shrink-0 whitespace-nowrap text-[13px]">{it.value}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CitationBlock>
          ))}
        </div>
      )}
      {check && (
        <a href={check} target="_blank" rel="noopener noreferrer" className="t-small mt-3 inline-flex items-center gap-1 text-ink-2 underline underline-offset-4">
          Cross-check: screener.in quarterly table <ArrowUpRight className="size-3.5" />
        </a>
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
    const k = `${sourceHref(c)}#${c.locator ?? ""}#${c.quote ?? ""}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}
