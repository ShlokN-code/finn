"use client";
// Always-visible Ask bar, scoped to the screen. Until /ask is wired (Friday), the 3 suggestions jump to the
// section or card that answers them; free text says so honestly. lib/ask.ts is the one place to change.
import { useState } from "react";
import { MessageSquareText } from "lucide-react";
import { Sheet } from "./Sheet";
import { useAskContext } from "./ui-store";

export function AskBar() {
  const ctx = useAskContext();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  return (
    <>
      <div className="px-3 pb-2 pt-2">
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="flex h-11 w-full items-center gap-2 rounded-full border border-rule bg-surface px-4 text-left text-[15px] text-ink-3"
        >
          <MessageSquareText className="size-[18px] shrink-0" strokeWidth={1.5} />
          <span className="truncate">{ctx.placeholder}</span>
        </button>
      </div>
      <Sheet open={open} onClose={() => setOpen(false)} eyebrow="Ask" title={ctx.placeholder.replace(/…$/, "")}>
        <div className="space-y-2">
          {ctx.chips.length > 0 ? (
            <>
              <p className="t-small text-ink-2">Suggested for this screen — each opens the part that answers it.</p>
              <ul className="space-y-2">
                {ctx.chips.map((c) => (
                  <li key={c.label}>
                    <button
                      type="button"
                      onClick={() => {
                        setOpen(false);
                        c.run();
                      }}
                      className="w-full rounded-xl border border-rule px-4 py-3 text-left text-[15px] hover:bg-surface-2"
                    >
                      {c.label}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="t-small text-ink-2">Open a card or a company to get suggestions here.</p>
          )}
          <form
            className="pt-3"
            onSubmit={(e) => {
              e.preventDefault();
            }}
          >
            <label className="t-micro text-ink-3" htmlFor="ask-q">
              Your question
            </label>
            <input
              id="ask-q"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="e.g. What did management say about margins?"
              className="mt-1 h-11 w-full rounded-xl border border-rule bg-paper px-3 text-[15px] outline-none focus:border-ink-3"
            />
            {q.trim().length > 2 && (
              <p className="t-small mt-2 text-ink-2">
                Free-text answers, cited from filings and transcripts, arrive with the next release. Until then the
                suggestions above jump straight to the answer.
              </p>
            )}
          </form>
        </div>
      </Sheet>
    </>
  );
}
