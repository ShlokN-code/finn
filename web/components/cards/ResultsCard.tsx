// Results: current quarter, QoQ, YoY per line; ✓ Cross-checked / pending / "Couldn't verify — open filing".
import { ArrowUpRight } from "lucide-react";
import type { Card, ResultsDetail } from "@/lib/types";
import { FigureValue } from "./FigureValue";
import { VerificationBadge } from "./primitives";
import { Sparkline } from "./Sparkline";

export function ResultsBody({ card, d }: { card: Card; d: ResultsDetail }) {
  if (d.verification === "mismatch") {
    const url = d.filing_url ?? card.sources[0]?.url;
    return (
      <div className="rounded-xl bg-neg-bg p-3">
        <VerificationBadge state="mismatch" note={d.verification_note} />
        <p className="t-small mt-1 text-ink-2">
          These numbers didn&apos;t match an independent source, so FINN won&apos;t show them.
          {d.verification_note ? ` ${d.verification_note}` : ""}
        </p>
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="t-small mt-2 inline-flex h-9 items-center gap-1 rounded-full border border-rule bg-surface px-3 font-medium"
          >
            Open the results filing <ArrowUpRight className="size-3.5" />
          </a>
        )}
      </div>
    );
  }
  return (
    <div>
      <div className="t-small mb-1 flex items-center justify-between gap-2 text-ink-3">
        <span className="capitalize">
          {d.quarter.label} · {d.basis}
          {d.source_path !== "xbrl" && " · from PDF"}
        </span>
        <VerificationBadge state={d.verification} note={d.verification_note} />
      </div>
      <table className="w-full text-[14px] leading-[20px]">
        <thead>
          <tr className="t-small text-left text-ink-3">
            <th className="py-1 font-normal" />
            <th className="py-1 text-right font-normal">{d.quarter.label}</th>
            <th className="py-1 text-right font-normal">QoQ</th>
            <th className="py-1 text-right font-normal">YoY</th>
          </tr>
        </thead>
        <tbody>
          {d.lines.map((ln) => (
            <tr key={ln.metric} className="border-t border-rule">
              <td className="py-2 pr-2 text-ink-2">{ln.metric}</td>
              <td className="py-2 text-right font-medium">
                <FigureValue f={ln.current} />
              </td>
              <td className="py-2 pl-2 text-right">
                <FigureValue f={ln.qoq} signed />
              </td>
              <td className="py-2 pl-2 text-right">
                <FigureValue f={ln.yoy} signed />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {d.margin_series && (
        <div className="t-small mt-3 flex items-center gap-3 text-ink-3">
          <Sparkline values={d.margin_series.points.map((p) => p.value)} className="text-ink" />
          <span>
            {d.margin_series.metric}, last {d.margin_series.points.length} quarters (screener)
          </span>
        </div>
      )}
      {d.ebitda_note && <p className="t-small mt-2 text-ink-3">{d.ebitda_note}</p>}
      {d.verification_note && d.verification !== "cross_checked" && (
        <p className="t-small mt-1 text-ink-3">{d.verification_note}</p>
      )}
    </div>
  );
}
