// "What to watch": a results board meeting is announced — the promises the results will test live in the dossier.
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { Card } from "@/lib/types";

export function WhatToWatchBody({ card }: { card: Card }) {
  return (
    <div className="t-small space-y-2 text-ink-2">
      <p>The board meeting is announced; results aren&apos;t out yet. FINN scores them against management&apos;s own guidance once they land.</p>
      <Link
        href={`/research/${encodeURIComponent(card.symbol)}#ledger`}
        onClick={(e) => e.stopPropagation()}
        className="inline-flex h-9 items-center gap-1 font-medium text-ink"
      >
        Promises these results will test <ChevronRight className="size-4" />
      </Link>
    </div>
  );
}
