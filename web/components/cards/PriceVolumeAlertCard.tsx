// Price/volume alert: the move, volume, z-score, and the explanation chain (filing → deal → sector → none).
import type { PriceVolumeDetail } from "@/lib/types";
import { FigureValue } from "./FigureValue";

export function PriceVolumeBody({ d }: { d: PriceVolumeDetail }) {
  return (
    <div className="space-y-2 text-sm">
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        <span>
          Move <FigureValue f={d.move_pct} signed className="font-semibold" />
        </span>
        {d.sector_move_pct && (
          <span className="text-muted-foreground">
            {d.sector_index} <FigureValue f={d.sector_move_pct} signed />
          </span>
        )}
        {d.volume_ratio && (
          <span>
            Volume <FigureValue f={d.volume_ratio} /> 20-day avg
          </span>
        )}
        {d.z_score !== null && <span className="text-muted-foreground">{Math.abs(d.z_score).toFixed(1)}σ day</span>}
      </div>
      {d.day_label && <p className="text-xs font-medium">{d.day_label}</p>}
      <ul className="space-y-1 text-xs">
        {d.explanations.map((e, i) => (
          <li key={i} className={e.kind === "none" ? "font-medium text-amber-700 dark:text-amber-300" : ""}>
            {e.citation ? (
              <a href={e.citation.url} target="_blank" rel="noopener noreferrer" className="underline-offset-2 hover:underline">
                {e.text}
              </a>
            ) : (
              e.text
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
