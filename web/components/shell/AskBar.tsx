"use client";
// Ask bar, scoped to the screen; one endpoint, POST /api/research/{symbol}/ask: an answer from that company's dossier
// facts and its own transcripts/decks, with sources, or "Not found in sources". A company without a dossier whose
// call transcripts were already read is answered from those transcripts alone, and the answer says so.
// - On a company (ctx.symbol) free text goes to that company.
// - On Brief, Portfolio and Research home (ctx.findCompany) free text goes to the company it names ("Infosys" → INFY,
//   matched in code against the NSE list). Naming none offers at most 5 picks (the largest askable holdings) and a
//   search for any company. A company Ask can't answer gets "No research for X yet" and a way into Research.
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
import { companyName, searchSymbols, useSymbols } from "@/lib/symbols";
import { effectiveWeights } from "@/lib/holdings";

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

// Companies with a dossier and those Ask can answer (GET /research/built), fetched once per page load. If it fails,
// picks fall back to the shipped demo dossiers and `askable` is unknown (null): the Ask API then decides.
type Coverage = { built: string[]; askable: string[] | null };
let coverageOnce: Promise<Coverage> | null = null;
function loadCoverage(): Promise<Coverage> {
  coverageOnce ??= api
    .built()
    .then((r) => ({ built: r.symbols, askable: r.askable ?? r.symbols }))
    .catch(() => {
      coverageOnce = null;
      return { built: [...DEMO_TICKERS], askable: null };
    });
  return coverageOnce;
}

const MAX_PICKS = 5;

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

/** Brief, Portfolio, Research home: ask about the company the question names, or pick one. */
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
  const [cov, setCov] = useState<Coverage | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [needPick, setNeedPick] = useState(false);
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [find, setFind] = useState("");
  useEffect(() => {
    let live = true;
    void loadCoverage().then((c) => live && setCov(c));
    return () => {
      live = false;
    };
  }, []);

  const index = useMemo(() => (list ? buildIndex(list) : null), [list]);
  const askable = cov?.askable ?? null;
  const ranked = useMemo(
    () =>
      [...effectiveWeights(holdings)]
        .sort((a, b) => (b.weight_pct ?? 0) - (a.weight_pct ?? 0) || a.symbol.localeCompare(b.symbol))
        .map((h) => h.symbol),
    [holdings],
  );
  const mine = useMemo(() => [...ranked, ...(askable ?? DEMO_TICKERS)], [ranked, askable]);
  const named = useMemo(() => (index ? findCompany(q, index, mine) : null), [q, index, mine]);
  const pickable = cov ? (askable ?? cov.built) : null;
  const picks = useMemo(() => (pickable ? ranked.filter((s) => pickable.includes(s)).slice(0, MAX_PICKS) : []), [ranked, pickable]);
  const hits = useMemo(() => (list && find.trim() ? searchSymbols(list, find, 5) : []), [list, find]);
  const nameOf = (s: string) => {
    const n = index?.names.get(s);
    return n ? companyName(n) : s;
  };
  const canAsk = (s: string) => !askable || askable.includes(s); // unknown coverage → let the API decide
  const target = named?.symbol ?? picked;
  // "No research for X yet" is derived, not stored at tap time: a company picked (or asked about) before coverage
  // loaded still gets it the moment coverage says Ask can't answer it.
  const none = target && !canAsk(target) && (target === picked || target === submitted) ? target : null;

  const go = (sym: string, question: string) => {
    setSubmitted(sym);
    if (canAsk(sym) && question.trim().length >= 3) void ask(sym, question);
  };
  // Selecting always shows something: a company Ask can't answer gets "No research for X yet"; one it can is asked
  // at once when there's a question, else it becomes the pressed chip and the question field takes focus (called
  // inside the tap, so a phone keeps its keyboard up for the question).
  const choose = (sym: string) => {
    setPicked(sym);
    setNeedPick(false);
    setFind("");
    go(sym, q);
    if (canAsk(sym) && q.trim().length < 3) document.getElementById("ask-q")?.focus();
  };
  const chips = picked && !picks.includes(picked) && canAsk(picked) ? [picked, ...picks] : picks;
  // An earlier answer about another company is cleared from view once a different company is chosen.
  const showResult = !target || st.kind === "idle" || st.sym === target;

  return (
    <>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (target) go(target, q);
          else setNeedPick(true);
        }}
      >
        <label className="t-micro text-ink-3" htmlFor="ask-q">
          Your question about a company
        </label>
        <QuestionField
          q={q}
          setQ={setQ}
          busy={st.kind === "loading"}
          placeholder={target ? `Your question about ${nameOf(target)}` : "e.g. What did Infosys say about margins?"}
        />
        <p className="t-small mt-1.5 text-ink-3" data-ask-target={target ?? ""}>
          {target
            ? `About ${nameOf(target)} (${target}). `
            : "Name a company (e.g. Infosys or INFY), or pick one below. "}
          Answers only from its filings, transcripts and decks, with sources.
        </p>
      </form>

      {!named && (
        <div className="pt-1" data-ask-picks>
          <p className={`t-small ${needPick && !picked ? "font-medium text-ink" : "text-ink-2"}`}>
            {needPick && !picked ? "Which company? Ask about:" : "Ask about:"}
          </p>
          {cov === null ? (
            <p className="t-small mt-1 text-ink-3">Loading your companies…</p>
          ) : chips.length ? (
            <div className="mt-1.5 flex flex-wrap gap-2">
              {chips.map((s) => (
                <button
                  key={s}
                  type="button"
                  aria-pressed={picked === s}
                  onClick={() => choose(s)}
                  className={`h-9 rounded-full border px-3 text-[14px] font-medium ${picked === s ? "border-ink bg-ink text-paper" : "border-rule"}`}
                >
                  {s}
                </button>
              ))}
            </div>
          ) : (
            <p className="t-small mt-1 text-ink-3">None of your holdings can be asked about yet. Search for any company below.</p>
          )}
          <label className="t-micro mt-3 block text-ink-3" htmlFor="ask-company">
            Search any company
          </label>
          <input
            id="ask-company"
            value={find}
            onChange={(e) => setFind(e.target.value)}
            placeholder={list ? "Name or NSE symbol" : "Loading the NSE list…"}
            autoCapitalize="characters"
            autoCorrect="off"
            spellCheck={false}
            enterKeyHint="search"
            role="combobox"
            aria-expanded={hits.length > 0}
            aria-controls="ask-company-results"
            className="mt-1 h-11 w-full rounded-xl border border-rule bg-paper px-3 text-[16px] outline-none focus:border-ink-3"
          />
          {hits.length > 0 && (
            <ul id="ask-company-results" role="listbox" className="mt-1 divide-y divide-rule rounded-xl border border-rule">
              {hits.map(([s, n]) => (
                <li key={s} role="option" aria-selected={picked === s}>
                  <button
                    type="button"
                    // Keep focus in the search field while the tap lands: a blur would drop the phone keyboard and
                    // shift the sheet under the finger. The click (not pointerdown) selects, so scrolling past an
                    // option doesn't pick it.
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => choose(s)}
                    className="flex min-h-11 w-full items-center gap-2 px-3 py-2 text-left"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block text-[15px] font-semibold">{s}</span>
                      <span className="t-small block truncate text-ink-2">{companyName(n)}</span>
                    </span>
                    {askable && !askable.includes(s) && <span className="t-small shrink-0 text-ink-3">no research yet</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {picked && !named && !none && q.trim().length < 3 && st.kind !== "loading" && (
        <p className="t-small rounded-xl border border-rule px-4 py-3 font-medium" data-ask-selected={picked}>
          {nameOf(picked)} ({picked}) selected. Type your question above, then tap Ask.
        </p>
      )}
      {none ? (
        <NoResearch sym={none} name={nameOf(none)} onLeave={onLeave} />
      ) : (
        showResult && <Result st={st} onRetry={(s, qq) => void ask(s, qq)} nameOf={nameOf} onLeave={onLeave} />
      )}
    </>
  );
}

function NoResearch({ sym, name, onLeave }: { sym: string; name: string; onLeave?: () => void }) {
  return (
    <div className="rounded-xl border border-rule px-4 py-3" data-ask-state="no_research">
      <p className="t-headline">No research for {name} yet</p>
      <p className="t-small mt-1 text-ink-2">
        FINN builds it from {name}&apos;s filings, call transcripts and decks in 2–4 minutes; then you can ask here.
      </p>
      <Link
        href={`/research/${encodeURIComponent(sym)}`}
        onClick={onLeave}
        className="mt-3 inline-flex h-10 items-center rounded-full bg-ink px-4 text-[14px] font-medium text-paper"
      >
        Open {sym} in Research
      </Link>
    </div>
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
  // Outside the company's page: say plainly when there's no research, and link into it.
  if (nameOf && st.a.status === "unavailable" && st.a.reason === "no_dossier")
    return <NoResearch sym={st.sym} name={nameOf(st.sym)} onLeave={onLeave} />;
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
      <div className="rounded-xl border border-rule px-4 py-3" data-ask-state="not_found" data-ask-basis={a.basis ?? "dossier"}>
        <p className="t-headline">Not found in sources</p>
        <p className="t-small mt-1 text-ink-2">
          {a.reason === "unsupported_number"
            ? "The model's answer used a number that isn't printed in the sources, so FINN withheld it."
            : `${symbol}'s dossier, transcripts and decks don't answer this. FINN doesn't guess.`}
        </p>
        <TranscriptsOnly a={a} symbol={symbol} />
        {foot && <p className="t-small mt-2 text-ink-3">{foot}</p>}
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-rule px-4 py-3" data-ask-state="answered" data-ask-basis={a.basis ?? "dossier"}>
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
      <TranscriptsOnly a={a} symbol={symbol} />
      {foot && <p className="t-small mt-2 text-ink-3">{foot}</p>}
    </div>
  );
}

function TranscriptsOnly({ a, symbol }: { a: AskAnswer; symbol: string }) {
  if (a.basis !== "transcripts") return null;
  return (
    <p className="t-small mt-2 text-ink-3" data-ask-basis-note>
      From {symbol}&apos;s call transcripts only: FINN hasn&apos;t built its full research yet.
    </p>
  );
}
