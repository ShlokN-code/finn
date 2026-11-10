// One-liner (M&A, fund raise, litigation, rating, pledging, capex, orders, insider trades): one line + key number.
import type { OneLinerDetail } from "@/lib/types";
import { FigureValue } from "./FigureValue";

const DIRECTION: Record<string, string> = { up: "▲ Up", down: "▼ Down", new: "New", unchanged: "Unchanged" };

export function OneLinerBody({ d, category }: { d: OneLinerDetail; category: string }) {
  const dir =
    d.direction && category === "credit_rating"
      ? { up: "▲ Upgrade", down: "▼ Downgrade", new: "New rating", unchanged: "Reaffirmed" }[d.direction]
      : d.direction && category === "pledging"
        ? { up: "▲ Pledge increased", down: "▼ Pledge reduced", new: "New pledge", unchanged: "Unchanged" }[d.direction]
        : d.direction
          ? DIRECTION[d.direction]
          : null;
  return (
    <div className="space-y-1 text-sm">
      {d.key_figure && (
        <p>
          {d.key_figure.label}: <FigureValue f={d.key_figure} className="font-semibold" />
        </p>
      )}
      {dir && <p className="text-xs font-medium">{dir}</p>}
      {d.facts.rating_new && (
        <p className="text-xs text-muted-foreground">
          {d.facts.rating_previous ? `${d.facts.rating_previous} → ` : ""}
          {d.facts.rating_new}
        </p>
      )}
    </div>
  );
}
