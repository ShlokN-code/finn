// Price/volume alert: the move, volume, z-score, and the explanation chain (filing → deal → sector → none).
import { sourceHref } from "@/lib/format";
import type { PriceVolumeDetail } from "@/lib/types";
import { FigureValue } from "./FigureValue";

export function PriceVolumeBody({ d }: { d: PriceVolumeDetail }) {
  return (
    <div className="t-small space-y-2">
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        <span>
          <span className="text-ink-2">Move </span>
          <FigureValue f={d.move_pct} signed className="font-medium" />
        </span>
        {d.relative_move_pct && (
          <span>
            <span className="text-ink-2">vs sector </span>
            <FigureValue f={d.relative_move_pct} signed />
          </span>
        )}
        {d.sector_move_pct && (
          <span className="text-ink-2">
            {d.sector_index} <FigureValue f={d.sector_move_pct} signed />
          </span>
        )}
        {d.volume_ratio && (
          <span>
            <span className="text-ink-2">Volume </span>
            <FigureValue f={d.volume_ratio} />
            <span className="text-ink-2"> of 20-day avg</span>
          </span>
        )}
        {d.z_score !== null && <span className="text-ink-3">{Math.abs(d.z_score).toFixed(1)}σ for this stock</span>}
      </div>
      {d.day_label && <p className="font-medium">{d.day_label}</p>}
      <div>
        <p className="t-micro text-ink-3">Likely explanation</p>
        <ol className="mt-1 space-y-1">
          {d.explanations.map((e, i) => (
            <li key={i} className={e.kind === "none" ? "font-medium text-warn" : ""}>
              {e.citation ? (
                <a
                  href={sourceHref(e.citation)}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(ev) => ev.stopPropagation()}
                  className="underline decoration-ink-3/50 underline-offset-4"
                >
                  {e.text.replace(/^⚠️\s*/, "")}
                </a>
              ) : (
                e.text.replace(/^⚠️\s*/, "")
              )}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
