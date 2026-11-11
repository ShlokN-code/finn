// Switches on card_type and renders the right body inside the shared shell. Reused by /e/[id] and the Brief.
import type { ComponentProps } from "react";
import type { Card } from "@/lib/types";
import { CardShell } from "./CardShell";
import { InlineChip } from "./InlineChip";
import { ManagementBody } from "./ManagementChangeCard";
import { OneLinerBody } from "./OneLinerCard";
import { PriceVolumeBody } from "./PriceVolumeAlertCard";
import { ResultsBody } from "./ResultsCard";
import { WhatToWatchBody } from "./WhatToWatchCard";

export function CardBody({ card }: { card: Card }) {
  const d = card.detail;
  if (d?.kind === "results") return <ResultsBody card={card} d={d} />;
  if (d?.kind === "management_change") return <ManagementBody d={d} />;
  if (d?.kind === "price_volume") return <PriceVolumeBody d={d} />;
  if (d?.kind === "one_liner") return <OneLinerBody d={d} category={card.category} />;
  if (card.card_type === "what_to_watch") return <WhatToWatchBody card={card} />;
  if (card.card_type === "results")
    return <p className="t-small text-ink-2">Numbers are being extracted and cross-checked — open the filing meanwhile.</p>;
  return null;
}

export function CardView({ card, ...shell }: { card: Card } & Omit<ComponentProps<typeof CardShell>, "card" | "children">) {
  const d = card.detail;
  if (card.card_type === "inline_chip" && d?.kind === "chip") {
    return (
      <div className="bg-surface px-4 py-3">
        <InlineChip symbol={card.symbol} d={d} />
      </div>
    );
  }
  return (
    <CardShell card={card} {...shell}>
      <CardBody card={card} />
    </CardShell>
  );
}
