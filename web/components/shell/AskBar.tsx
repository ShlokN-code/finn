"use client";
// Always-visible Ask bar, scoped to the screen. On a company (ctx.symbol) free text goes to
// POST /api/research/{symbol}/ask: an answer from that company's dossier facts and its own transcripts/decks,
// with sources, or "Not found in sources". The 3 suggestions still jump to the section that answers them (no
// model call). Elsewhere Ask explains that it works inside a company.
import { useEffect, useRef, useState } from "react";
import { MessageSquareText, Loader2 } from "lucide-react";
import { Sheet } from "./Sheet";
import { useAskContext } from "./ui-store";
import { api, FetchError } from "@/lib/client";
import type { AskAnswer } from "@/lib/types";
import { ClaimProvenance } from "@/components/cards/Provenance";
import { FigureValue } from "@/components/cards/FigureValue";
import { istClock, istDay } from "@/lib/format";

type State =
  | { kind: "idle" }
  | { kind: "loading"; q: string }
  | { kind: "done"; a: AskAnswer }
  | { kind: "error"; q: string; msg: string };

function unavailableText(a: AskAnswer, symbol: string): string {
  const when = a.resume_after ? `${istDay(a.resume_after)}, ${istClock(a.resume_after)} IST` : "later";
  switch (a.reason) {
    case "no_dossier":
      return `Ask answers from ${symbol}'s research. Tap “Research ${symbol}” on this page first; questions work once it's built.`;
    case "visitor_cap":
      return `You've used today's questions (they keep FINN's free model quota fair for everyone). More after ${when}.`;
    case "quota":
      return `Ask's model quota for today is used up. It resumes after ${when}. The sections on this page are all still readable.`;
    default:
      return "The model couldn't answer just now. Try again in a minute.";
  }
}

export function AskBar() {
  const ctx = useAskContext();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [st, setSt] = useState<State>({ kind: "idle" });
  const ctrl = useRef<AbortController | null>(null);
  const symbol = ctx.symbol;

  // A new company (or none) starts a fresh conversation (reset during render, React's pattern for prop changes).
  const [forSymbol, setForSymbol] = useState(symbol);
  if (forSymbol !== symbol) {
    setForSymbol(symbol);
    setSt({ kind: "idle" });
    setQ("");
  }
  useEffect(() => () => ctrl.current?.abort(), [symbol]);

  const ask = async (question: string) => {
    if (!symbol || question.trim().length < 3) return;
    ctrl.current?.abort();
    const c = new AbortController();
    ctrl.current = c;
    setSt({ kind: "loading", q: question.trim() });
    try {
      const a = await api.ask(symbol, question.trim(), c.signal);
      if (!c.signal.aborted) setSt({ kind: "done", a });
    } catch (e) {
      if (c.signal.aborted) return;
      const msg =
        e instanceof FetchError && e.waking
          ? "FINN's server is waking up (up to a minute on the free tier). Try again shortly."
          : e instanceof FetchError
            ? e.message
            : "Couldn't reach FINN.";
      setSt({ kind: "error", q: question.trim(), msg });
    }
  };

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
          {symbol && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void ask(q);
              }}
            >
              <label className="t-micro text-ink-3" htmlFor="ask-q">
                Your question about {symbol}
              </label>
              <div className="mt-1 flex gap-2">
                <input
                  id="ask-q"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  maxLength={300}
                  enterKeyHint="send"
                  placeholder="e.g. What did management say about margins?"
                  className="h-11 min-w-0 flex-1 rounded-xl border border-rule bg-paper px-3 text-[15px] outline-none focus:border-ink-3"
                />
                <button
                  type="submit"
                  disabled={q.trim().length < 3 || st.kind === "loading"}
                  className="h-11 shrink-0 rounded-xl bg-ink px-4 text-[15px] font-medium text-paper disabled:opacity-40"
                >
                  Ask
                </button>
              </div>
              <p className="t-small mt-1.5 text-ink-3">
                Answers only from {symbol}&apos;s filings, transcripts and decks, with sources. No news, no outside
                knowledge.
              </p>
            </form>
          )}

          {st.kind === "loading" && (
            <div className="flex items-center gap-2 py-3 text-ink-2" role="status">
              <Loader2 className="size-4 animate-spin" />
              <span className="t-small">Reading {symbol}&apos;s transcripts and figures…</span>
            </div>
          )}
          {st.kind === "error" && (
            <div className="rounded-xl border border-rule px-4 py-3" role="alert">
              <p className="t-small text-ink-2">{st.msg}</p>
              <button type="button" className="t-small mt-1 underline" onClick={() => void ask(st.q)}>
                Retry
              </button>
            </div>
          )}
          {st.kind === "done" && symbol && <Answer a={st.a} symbol={symbol} />}

          {ctx.chips.length > 0 ? (
            <div className="pt-3">
              <p className="t-small text-ink-2">Suggested for this screen — each opens the part that answers it.</p>
              <ul className="mt-2 space-y-2">
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
            </div>
          ) : (
            !symbol && (
              <p className="t-small text-ink-2">
                Ask works inside a company: open one from Research (or a card&apos;s ticker) and ask about its
                guidance, margins, debt or what management said.
              </p>
            )
          )}
        </div>
      </Sheet>
    </>
  );
}

function Answer({ a, symbol }: { a: AskAnswer; symbol: string }) {
  const left =
    a.remaining_today != null ? `${a.remaining_today} question${a.remaining_today === 1 ? "" : "s"} left today` : null;
  const foot = [a.cached ? "Saved answer" : null, left].filter(Boolean).join(" · ");
  if (a.status === "unavailable") {
    return (
      <div className="rounded-xl border border-rule px-4 py-3" data-ask-state="unavailable">
        <p className="t-small text-ink-2">{unavailableText(a, symbol)}</p>
      </div>
    );
  }
  if (a.status === "not_found" || !a.answer) {
    return (
      <div className="rounded-xl border border-rule px-4 py-3" data-ask-state="not_found">
        <p className="t-headline">Not found in sources</p>
        <p className="t-small mt-1 text-ink-2">
          {a.reason === "unsupported_number"
            ? "The model's answer used a number that isn't printed in the sources, so FINN withheld it."
            : `${symbol}'s dossier, transcripts and decks don't answer this. FINN doesn't guess.`}
        </p>
        {foot && <p className="t-small mt-2 text-ink-3">{foot}</p>}
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-rule px-4 py-3" data-ask-state="answered">
      <p className="t-headline">{a.answer.text}</p>
      {a.figures.length > 0 && (
        <ul className="mt-2 space-y-1">
          {a.figures.map((f, i) => (
            <li key={i} className="t-small flex justify-between gap-3">
              <span className="text-ink-2">
                {f.label}
                {f.period ? ` · ${f.period.label}` : ""}
              </span>
              <FigureValue f={f} />
            </li>
          ))}
        </ul>
      )}
      <div className="mt-3 border-t border-rule pt-2">
        <p className="t-micro text-ink-3">Sources</p>
        <ClaimProvenance claim={a.answer} />
      </div>
      {foot && <p className="t-small mt-2 text-ink-3">{foot}</p>}
    </div>
  );
}
