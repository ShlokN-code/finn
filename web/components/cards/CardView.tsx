// Switches on card_type and renders the right body inside the shared shell. Reused by /e/[id] and the Brief.
import type { Card } from "@/lib/types";
import { CardShell } from "./CardShell";
import { InlineChip } from "./InlineChip";
import { ManagementBody } from "./ManagementChangeCard";
import { OneLinerBody } from "./OneLinerCard";
import { PriceVolumeBody } from "./PriceVolumeAlertCard";
import { ResultsBody } from "./ResultsCard";

export function CardView({ card }: { card: Card }) {
  const d = card.detail;
  if (card.card_type === "inline_chip" && d?.kind === "chip") {
    return <InlineChip symbol={card.symbol} d={d} />;
  }
  let body = null;
  if (d?.kind === "results") body = <ResultsBody card={card} d={d} />;
  else if (d?.kind === "management_change") body = <ManagementBody d={d} />;
  else if (d?.kind === "price_volume") body = <PriceVolumeBody d={d} />;
  else if (d?.kind === "one_liner") body = <OneLinerBody d={d} category={card.category} />;
  else if (card.card_type === "results")
    body = <p className="text-xs text-muted-foreground">Numbers are being extracted and cross-checked — open the filing meanwhile.</p>;
  return <CardShell card={card}>{body}</CardShell>;
}
