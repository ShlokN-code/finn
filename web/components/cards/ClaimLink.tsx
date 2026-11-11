"use client";
// A sentence with provenance: tap → its citations with page and quote.
import { useState, type ReactNode } from "react";
import type { Claim } from "@/lib/types";
import { Sheet } from "@/components/shell/Sheet";
import { ClaimProvenance } from "./Provenance";

export function ClaimText({ claim, className = "", children }: { claim: Claim; className?: string; children?: ReactNode }) {
  const [open, setOpen] = useState(false);
  const unverified = claim.status !== "verified";
  return (
    <>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen(true);
        }}
        className={`text-left underline decoration-dotted decoration-1 underline-offset-[5px] ${
          unverified ? "decoration-warn" : "decoration-ink-3/50"
        } ${className}`}
      >
        {children ?? claim.text}
      </button>
      <Sheet open={open} onClose={() => setOpen(false)} eyebrow="Source">
        <ClaimProvenance claim={claim} />
      </Sheet>
    </>
  );
}
