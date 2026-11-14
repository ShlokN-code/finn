"use client";
// Ask bar, scoped to the screen; one endpoint, POST /api/research/{symbol}/ask: an answer from that company's dossier
// facts and its own transcripts/decks, with sources, or "Not found in sources".
// - On a company (ctx.symbol) free text goes to that company.
// - On Brief and Portfolio (ctx.findCompany) free text goes to the company it names ("Infosys" → INFY, matched in
//   code against the NSE list); naming none offers the user's holdings that have research as picks; a named company
//   without research gets "No research for X yet" and a way into Research.
// - Hidden on Rules. Elsewhere Ask explains that it works inside a company.
// The suggestion chips still jump to the part of the screen that answers them (no model call).
import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { MessageSquareText, Loader2, ChevronRight } from "lucide-react";
import { Sheet } from "./Sheet";
import { useAskContext } from "./ui-store";
import { api, FetchError } from "@/lib/client";
import type { AskAnswer } from "@/lib/types";
import { ClaimProvenance } from "@/components/cards/Provenance";
import { FigureValue } from "@/components/cards/FigureValue";
import { istClock, istDay } from "@/lib/format";
import { buildIndex, findCompany } from "@/lib/askMatch";
import { DEMO_TICKERS } from "@/lib/demo";
import { FALLBACK, useStored, type LocalHolding } from "@/lib/store";
import { companyName, useSymbols } from "@/lib/symbols";

type State =
  | { kind: "idle" }
  | { kind: "loading"; sym: string; q: string }
  | { kind: "done"; sym: string; a: AskAnswer }
  | { kind: "error"; sym: string; q: string; msg: string };

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

// Symbols with a dossier, fetched once per page load (GET /research/built); the shipped demo dossiers if it fails.
let builtOnce: Promise<string[]> | null = null;
function loadBuilt(): Promise<string[]> {
  builtOnce ??= api
    .built()
    .then((r) => r.symbols)
    .catch(() => {
      builtOnce = null;
      return [...DEMO_TICKERS];
    });
  return builtOnce;
}

export function AskBar() {
  const ctx = useAskContext();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [st, setSt] = useState<State>({ kind: "idle" });
  const ctrl = useRef<AbortController | null>(null);
  const symbol = ctx.symbol;
  const scope = symbol ?? (ctx.findCompany ? "*" : "");

  // A new screen scope starts a fresh conversation (reset during render, React's pattern for prop changes).
  const [forScope, setForScope] = useState(scope);
  if (forScope !== scope) {
    setForScope(scope);
    setSt({ kind: "idle" });
    setQ("");
  }
  useEffect(() => () => ctrl.current?.abort(), [scope]);

  const ask = async (sym: string, question: string) => {
    if (question.trim().length < 3) return;
    ctrl.current?.abort();
    const c = new AbortController();
    ctrl.current = c;
    setSt({ kind: "loading", sym, q: question.trim() });
    try {
      const a = await api.ask(sym, question.trim(), c.signal);
      if (!c.signal.aborted) setSt({ kind: "done", sym, a });
    } catch (e) {
      if (c.signal.aborted) return;
      const msg =
        e instanceof FetchError && e.waking
          ? "FINN's server is waking up (up to a minute on the free tier). Try again shortly."
          : e instanceof FetchError
            ? e.message
            : "Couldn't reach FINN.";
      setSt({ kind: "error", sym, q: question.trim(), msg });
    }
  };

  if (ctx.hidden) return null;
  const close = () => setOpen(false);

  return (
    <>
      <div className="px-3 pb-2 pt-2" data-ask-bar>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="flex h-11 w-full items-center gap-2 rounded-full border border-rule bg-surface px-4 text-left text-[15px] text-ink-3"
        >
          <MessageSquareText className="size-[18px] shrink-0" strokeWidth={1.5} />
          <span className="truncate">{ctx.placeholder}</span>
        </button>
      </div>
      <Sheet open={open} onClose={close} eyebrow="Ask" title={ctx.placeholder.replace(/…$/, "")}>
        <div className="space-y-2">
          {symbol ? (
            <>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void ask(symbol, q);
                }}
              >
                <label className="t-micro text-ink-3" htmlFor="ask-q">
                  Your question about {symbol}
                </label>
                <QuestionField q={q} setQ={setQ} busy={st.kind === "loading"} placeholder="e.g. What did management say about margins?" />
                <p className="t-small mt-1.5 text-ink-3">
                  Answers only from {symbol}&apos;s filings, transcripts and decks, with sources. No news, no outside
                  knowledge.
                </p>
              </form>
              <Result st={st} onRetry={(s, qq) => void ask(s, qq)} />
            </>
          ) : ctx.findCompany ? (
            <FindCompanyAsk q={q} setQ={setQ} st={st} ask={ask} onLeave={close} />
          ) : null}

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
            !symbol &&
            !ctx.findCompany && (
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

function QuestionField({ q, setQ, busy, placeholder }: { q: string; setQ: (v: string) => void; busy: boolean; placeholder: string }) {
  return (
    <div className="mt-1 flex gap-2">
      <input
        id="ask-q"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        maxLength={300}
        enterKeyHint="send"
        placeholder={placeholder}
        className="h-11 min-w-0 flex-1 rounded-xl border border-rule bg-paper px-3 text-[16px] outline-none focus:border-ink-3"
      />
      <button
        type="submit"
        disabled={q.trim().length < 3 || busy}
        className="h-11 shrink-0 rounded-xl bg-ink px-4 text-[15px] font-medium text-paper disabled:opacity-40"
      >
        Ask
      </button>
    </div>
  );
}

/** Brief / Portfolio: ask about the company the question names, or one of the user's holdings with research. */
function FindCompanyAsk({
  q,
  setQ,
  st,
  ask,
  onLeave,
}: {
  q: string;
  setQ: (v: string) => void;
  st: State;
  ask: (sym: string, q: string) => Promise<void>;
  onLeave: () => void;
}) {
  const list = useSymbols();
  const holdings = useStored<LocalHolding[]>("holdings", FALLBACK.holdings);
  const [built, setBuilt] = useState<string[] | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [needPick, setNeedPick] = useState(false);
  useEffect(() => {
    let live = true;
    void loadBuilt().then((b) => live && setBuilt(b));
    return () => {
      live = false;
    };
  }, []);

  const index = useMemo(() => (list ? buildIndex(list) : null), [list]);
  const held = useMemo(() => holdings.map((h) => h.symbol), [holdings]);
  const mine = useMemo(() => [...held, ...(built ?? DEMO_TICKERS)], [held, built]);
  const named = useMemo(() => (index ? findCompany(q, index, mine) : null), [q, index, mine]);
  const picks = useMemo(() => (built ? held.filter((s) => built.includes(s)) : []), [held, built]);
  const nameOf = (s: string) => {
    const n = index?.names.get(s);
    return n ? companyName(n) : s;
  };
  const target = named?.symbol ?? picked;

  return (
    <>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (target) void ask(target, q);
          else setNeedPick(true);
        }}
      >
        <label className="t-micro text-ink-3" htmlFor="ask-q">
          Your question about a company
        </label>
        <QuestionField q={q} setQ={setQ} busy={st.kind === "loading"} placeholder="e.g. What did Infosys say about margins?" />
        <p className="t-small mt-1.5 text-ink-3" data-ask-target={named?.symbol ?? ""}>
          {named
            ? `About ${nameOf(named.symbol)} (${named.symbol}). `
            : picked
              ? `About ${nameOf(picked)} (${picked}). `
              : "Name a company (e.g. Infosys or INFY), or pick one below. "}
          Answers only from its filings, transcripts and decks, with sources.
        </p>
      </form>

      {!named && (
        <div className="pt-1" data-ask-picks>
          <p className={`t-small ${needPick && !picked ? "font-medium text-ink" : "text-ink-2"}`}>
            {needPick && !picked ? "Which company? Ask about:" : "Ask about:"}
          </p>
          {built === null ? (
            <p className="t-small mt-1 text-ink-3">Loading your companies with research…</p>
          ) : picks.length ? (
            <div className="mt-1.5 flex flex-wrap gap-2">
              {picks.map((s) => (
                <button
                  key={s}
                  type="button"
                  aria-pressed={picked === s}
                  onClick={() => {
                    setPicked(s);
                    setNeedPick(false);
                    if (q.trim().length >= 3) void ask(s, q);
                  }}
                  className={`h-9 rounded-full border px-3 text-[14px] font-medium ${picked === s ? "border-ink bg-ink text-paper" : "border-rule"}`}
                >
                  {s}
                </button>
              ))}
            </div>
          ) : (
            <p className="t-small mt-1 text-ink-3">
              None of your holdings has research yet. Name a company, or open one from{" "}
              <Link href="/research" onClick={onLeave} className="underline underline-offset-4">
                Research
              </Link>
              .
            </p>
          )}
        </div>
      )}

      <Result st={st} onRetry={(s, qq) => void ask(s, qq)} nameOf={nameOf} onLeave={onLeave} />
    </>
  );
}

function Result({
  st,
  onRetry,
  nameOf,
  onLeave,
}: {
  st: State;
  onRetry: (sym: string, q: string) => void;
  nameOf?: (s: string) => string;
  onLeave?: () => void;
}) {
  if (st.kind === "loading")
    return (
      <div className="flex items-center gap-2 py-3 text-ink-2" role="status">
        <Loader2 className="size-4 animate-spin" />
        <span className="t-small">Reading {st.sym}&apos;s transcripts and figures…</span>
      </div>
    );
  if (st.kind === "error")
    return (
      <div className="rounded-xl border border-rule px-4 py-3" role="alert">
        <p className="t-small text-ink-2">{st.msg}</p>
        <button type="button" className="t-small mt-1 underline" onClick={() => onRetry(st.sym, st.q)}>
          Retry
        </button>
      </div>
    );
  if (st.kind !== "done") return null;
  // Outside the company's page (Brief, Portfolio): say plainly when there's no research, and link into it.
  if (nameOf && st.a.status === "unavailable" && st.a.reason === "no_dossier")
    return (
      <div className="rounded-xl border border-rule px-4 py-3" data-ask-state="no_research">
        <p className="t-headline">No research for {nameOf(st.sym)} yet</p>
        <p className="t-small mt-1 text-ink-2">
          FINN builds it from {nameOf(st.sym)}&apos;s filings, call transcripts and decks in 2–4 minutes; then you can ask
          here.
        </p>
        <Link
          href={`/research/${encodeURIComponent(st.sym)}`}
          onClick={onLeave}
          className="mt-3 inline-flex h-10 items-center rounded-full bg-ink px-4 text-[14px] font-medium text-paper"
        >
          Open {st.sym} in Research
        </Link>
      </div>
    );
  return (
    <>
      <Answer a={st.a} symbol={st.sym} />
      {nameOf && (
        <Link
          href={`/research/${encodeURIComponent(st.sym)}`}
          onClick={onLeave}
          className="t-small inline-flex min-h-10 items-center gap-1 font-medium underline underline-offset-4"
        >
          Open {st.sym} research
          <ChevronRight className="size-4" />
        </Link>
      )}
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
        <ClaimProvenance claim={a.answer} sourcesOnly />
      </div>
      {foot && <p className="t-small mt-2 text-ink-3">{foot}</p>}
    </div>
  );
}
