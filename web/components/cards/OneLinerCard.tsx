// One-liner (M&A, fund raise, litigation, rating, pledging, capex, orders, insider trades): one line + key number.
import type { OneLinerDetail } from "@/lib/types";
import { ClaimText } from "./ClaimLink";
import { FigureValue } from "./FigureValue";

export function oneLinerDirection(d: OneLinerDetail, category: string): string | null {
  if (!d.direction) return null;
  if (category === "credit_rating")
    return { up: "▲ Upgrade", down: "▼ Downgrade", new: "New rating", unchanged: "Reaffirmed" }[d.direction];
  if (category === "pledging")
    return { up: "▲ Pledge increased", down: "▼ Pledge reduced", new: "New pledge", unchanged: "Unchanged" }[d.direction];
  return { up: "▲ Up", down: "▼ Down", new: "New", unchanged: "Unchanged" }[d.direction];
}

export function OneLinerBody({ d, category }: { d: OneLinerDetail; category: string }) {
  const dir = oneLinerDirection(d, category);
  return (
    <div className="t-small space-y-1.5">
      <p className="text-ink-2">
        <ClaimText claim={d.line} />
      </p>
      {d.key_figure && (
        <p>
          <span className="text-ink-2">{d.key_figure.label}: </span>
          <FigureValue f={d.key_figure} className="font-medium" />
        </p>
      )}
      {dir && <p className={`font-medium ${category === "credit_rating" && d.direction === "down" ? "text-neg" : ""}`}>{dir}</p>}
      {d.facts.rating_new && (
        <p className="text-ink-2">
          {d.facts.rating_previous ? `${d.facts.rating_previous} → ` : ""}
          {d.facts.rating_new}
        </p>
      )}
    </div>
  );
}
