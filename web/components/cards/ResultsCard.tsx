// Results: current quarter, QoQ, YoY per line; ✓ Cross-checked / pending / "Couldn't verify — open filing".
import type { Card, ResultsDetail } from "@/lib/types";
import { FigureValue } from "./FigureValue";
import { VerificationBadge } from "./primitives";
import { Sparkline } from "./Sparkline";

export function ResultsBody({ card, d }: { card: Card; d: ResultsDetail }) {
  if (d.verification === "mismatch") {
    const url = d.filing_url ?? card.sources[0]?.url;
    return (
      <div className="rounded-xl border border-red-200 p-3 text-sm dark:border-red-900">
        <VerificationBadge state="mismatch" note={d.verification_note} />
        <p className="mt-1 text-xs text-muted-foreground">
          The numbers didn&apos;t match an independent source, so FINN won&apos;t show them.
        </p>
        {url && (
          <a href={url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-sm font-medium underline">
            Open the results filing →
          </a>
        )}
      </div>
    );
  }
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-xs text-muted-foreground">
        <span className="capitalize">
          {d.quarter.label} · {d.basis}
          {d.source_path !== "xbrl" && " · from PDF"}
        </span>
        <VerificationBadge state={d.verification} note={d.verification_note} />
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-muted-foreground">
            <th className="font-normal" />
            <th className="text-right font-normal">{d.quarter.label}</th>
            <th className="text-right font-normal">QoQ</th>
            <th className="text-right font-normal">YoY</th>
          </tr>
        </thead>
        <tbody>
          {d.lines.map((ln) => (
            <tr key={ln.metric} className="border-t">
              <td className="py-1.5">{ln.metric}</td>
              <td className="py-1.5 text-right">
                <FigureValue f={ln.current} />
              </td>
              <td className="py-1.5 text-right">
                <FigureValue f={ln.qoq} signed />
              </td>
              <td className="py-1.5 text-right">
                <FigureValue f={ln.yoy} signed />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {d.margin_series && (
        <div className="mt-3 flex items-center gap-3 text-xs text-muted-foreground">
          <Sparkline values={d.margin_series.points.map((p) => p.value ?? 0)} />
          <span>EBITDA margin, last {d.margin_series.points.length} quarters (screener)</span>
        </div>
      )}
      {d.ebitda_note && <p className="mt-2 text-[11px] text-muted-foreground">{d.ebitda_note}</p>}
    </div>
  );
}
