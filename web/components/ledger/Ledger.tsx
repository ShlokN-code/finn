"use client";
// ⭐ The Promise Ledger: what management said vs what they delivered. Code decides numeric verdicts; the model
// only judges qualitative promises and must cite both calls. Every verdict and number opens its provenance.
import { useMemo, useState } from "react";
import { ChevronRight } from "lucide-react";
import { Sheet } from "@/components/shell/Sheet";
import { FigureValue } from "@/components/cards";
import { CitationBlock, ClaimProvenance, FigureProvenance } from "@/components/cards/Provenance";
import { TONE_BG, TONE_TEXT, VERDICT, VerdictGlyph, type Verdict } from "@/components/ui/signal";
import { SectionFrame } from "@/components/research/sections";
import { istDayYear } from "@/lib/format";
import type { Dossier, MgmtPromise } from "@/lib/types";

type Filter = "scored" | "due" | "not_yet_due" | "cant_score" | "all";
const SCORED: Verdict[] = ["missed", "goalposts_moved", "quietly_dropped", "kept"];
const ORDER: Record<Verdict, number> = { missed: 0, goalposts_moved: 1, quietly_dropped: 2, kept: 3, not_yet_due: 4, cant_score: 5 };

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

function beat(p: MgmtPromise) {
  return p.verdict === "kept" && /\bbeat\b/.test(p.verdict_reason?.text ?? "");
}

export function LedgerSection({ d, focus }: { d: Dossier; focus?: string | null }) {
  const L = d.ledger;
  const cred = L.credibility;
  const [filter, setFilter] = useState<Filter>("scored");
  const [open, setOpen] = useState<MgmtPromise | null>(null);
  const [credOpen, setCredOpen] = useState(false);
  const c = L.counts;
  const scoredN = c.kept + c.missed + c.goalposts_moved + c.quietly_dropped;
  const dueNext = useMemo(
    () => L.promises.filter((p) => p.verdict === "not_yet_due" && L.next_test && p.period?.label === L.next_test.label),
    [L],
  );
  const list = useMemo(() => {
    let ps = L.promises;
    if (filter === "scored") ps = ps.filter((p) => SCORED.includes(p.verdict));
    else if (filter === "due") ps = dueNext;
    else if (filter === "not_yet_due") ps = ps.filter((p) => p.verdict === "not_yet_due");
    else if (filter === "cant_score") ps = ps.filter((p) => p.verdict === "cant_score");
    if (focus) {
      const f = focus.toLowerCase();
      const hit = ps.filter((p) => `${p.metric} ${p.metric_key}`.toLowerCase().includes(f));
      if (hit.length) ps = hit;
    }
    return [...ps].sort((a, b) => ORDER[a.verdict] - ORDER[b.verdict] || (b.period?.end ?? "").localeCompare(a.period?.end ?? ""));
  }, [L, filter, dueNext, focus]);

  const filters: [Filter, string, number][] = [
    ["scored", "Scored", scoredN],
    ...(L.next_test_label && dueNext.length ? ([["due", `Due ${L.next_test_label.replace(/ results$/, "")}`, dueNext.length]] as [Filter, string, number][]) : []),
    ["not_yet_due", "Not yet due", c.not_yet_due],
    ["cant_score", "Can't score", c.cant_score],
    ["all", "All", L.promises.length],
  ];

  const segs: [Verdict, number][] = [
    ["kept", c.kept],
    ["missed", c.missed],
    ["goalposts_moved", c.goalposts_moved],
    ["quietly_dropped", c.quietly_dropped],
  ];

  return (
    <SectionFrame id="ledger" title="Promise Ledger" meta={L.meta}>
      <div className="px-4">
        {cred && cred.n > 0 ? (
          <div className="flex items-end gap-3">
            <p className="t-display min-w-0 flex-1">
              {cred.kept} of {cred.n} kept
            </p>
            {cred.shown && cred.score_pct !== null && (
              <button type="button" onClick={() => setCredOpen(true)} className="hit shrink-0 text-right">
                <span className="t-figure-lg block">
                  {cred.score_pct.toFixed(1)}%
                  {cred.trend && (
                    <span className={`ml-1 text-[20px] ${cred.trend === "up" ? "text-pos" : cred.trend === "down" ? "text-neg" : "text-ink-3"}`}>
                      {cred.trend === "up" ? "↗" : cred.trend === "down" ? "↘" : "→"}
                    </span>
                  )}
                </span>
                <span className="t-small text-ink-3 underline decoration-dotted underline-offset-4">credibility</span>
              </button>
            )}
          </div>
        ) : (
          <p className="t-title">No scored promises yet</p>
        )}
        <p className="t-small mt-1.5 text-ink-2">
          {c.not_yet_due} not yet due
          {L.next_test_label && <> · next test: {L.next_test_label}</>}
          {L.next_test_on && <span className="text-ink-3"> (by {istDayYear(L.next_test_on)})</span>}
        </p>
        {cred && !cred.shown && cred.n > 0 && (
          <p className="t-small mt-0.5 text-ink-3">A % score needs {cred.min_n} or more scored promises.</p>
        )}
        {scoredN > 0 && (
          <div className="mt-3">
            <div className="flex h-2 overflow-hidden rounded-full bg-surface-2" aria-hidden>
              {segs.map(([v, n]) =>
                n > 0 ? <span key={v} className={`${TONE_BG[VERDICT[v].tone]} border-r border-paper last:border-0`} style={{ width: `${(n / scoredN) * 100}%` }} /> : null,
              )}
            </div>
            <p className="t-small mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5">
              {segs.map(([v, n]) => (
                <span key={v} className="inline-flex items-center gap-1">
                  <VerdictGlyph verdict={v} />
                  <span className={n ? "" : "text-ink-3"}>
                    {VERDICT[v].label.toLowerCase()} {n}
                  </span>
                </span>
              ))}
              {c.raised > 0 && (
                <span className="inline-flex items-center gap-1 text-ink-2">
                  <span className="font-semibold text-pos">↗</span> raised {c.raised}
                </span>
              )}
            </p>
          </div>
        )}
        <p className="t-small mt-2 text-ink-3">
          {L.calls_read} calls{L.decks_read ? ` · ${L.decks_read} deck${L.decks_read === 1 ? "" : "s"}` : ""} read
          {cred ? ` · ${cred.numeric_n} decided in code · ${cred.qualitative_n} judged by model` : ""}
        </p>
      </div>
      <div className="no-scrollbar mt-3 flex gap-2 overflow-x-auto px-4 pb-1" role="tablist" aria-label="Filter promises">
        {filters.map(([k, label, n]) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={filter === k}
            onClick={() => setFilter(k)}
            className={`hit h-8 shrink-0 rounded-full border px-3 text-[13px] ${filter === k ? "border-ink bg-ink font-medium text-paper" : "border-rule text-ink-2"}`}
          >
            {label} <span className={filter === k ? "opacity-70" : "text-ink-3"}>{n}</span>
          </button>
        ))}
      </div>
      {focus && <p className="t-small px-4 pt-2 text-ink-3">Showing promises about “{focus}”.</p>}
      <ul className="mt-3 divide-y divide-rule border-y border-rule bg-surface">
        {list.map((p) => (
          <PromiseRow key={p.id} p={p} onOpen={() => setOpen(p)} />
        ))}
        {list.length === 0 && <li className="t-small px-4 py-4 text-ink-2">Nothing in this group.</li>}
      </ul>
      <PromiseSheet p={open} onClose={() => setOpen(null)} />
      <Sheet open={credOpen} onClose={() => setCredOpen(false)} eyebrow="Credibility" title={cred ? `${cred.score_pct?.toFixed(1)}% of scored promises kept` : ""}>
        {cred && (
          <div className="t-small space-y-3 text-ink-2">
            <p className="rounded-xl bg-surface-2 p-3 font-mono text-[12px] leading-[18px] text-ink">{cred.formula}</p>
            <p>
              {cred.kept} kept of {cred.n} scored · {cred.numeric_n} decided in code, {cred.qualitative_n} judged by the model. Shown only with
              {" "}{cred.min_n} or more scored promises.
            </p>
            {cred.recent && cred.earlier && (
              <p>
                Trend: last 4 calls {cred.recent.kept} of {cred.recent.n} kept vs earlier {cred.earlier.kept} of {cred.earlier.n}. Shown when both
                halves have 3+ promises and differ by 15 points or more.
              </p>
            )}
          </div>
        )}
      </Sheet>
    </SectionFrame>
  );
}

function PromiseRow({ p, onOpen }: { p: MgmtPromise; onOpen: () => void }) {
  const v = VERDICT[p.verdict];
  const first = p.statements[0];
  const scored = p.scored_target ?? p.statements[p.statements.length - 1];
  const revised = p.revision !== "none" && p.statements.length > 1 && first.raw_target && scored.raw_target && first.raw_target !== scored.raw_target;
  const evidence = p.delivered?.citation ?? (p.statements.length > 1 ? p.statements[p.statements.length - 1].quote : null);
  return (
    <li>
      <div
        role="button"
        tabIndex={0}
        onClick={onOpen}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onOpen()}
        className="flex cursor-pointer gap-3 px-4 py-3.5"
      >
        <span className="pt-[3px]">
          <VerdictGlyph verdict={p.verdict} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-baseline gap-2">
            <span className={`t-micro min-w-0 flex-1 ${TONE_TEXT[v.tone]}`}>
              {v.label}
              {beat(p) ? " · beat" : ""}
              {p.revision === "raised" && <span className="text-pos"> · ↗ raised</span>}
              {p.verdict_by === "model" && <span className="text-ink-3"> · judged by model</span>}
            </span>
            <span className="t-small shrink-0 text-ink-3">{p.period?.label ?? "No date"}</span>
          </span>
          <span className="mt-1 block text-[15px] leading-[21px]">
            <span className="font-medium">{cap(p.metric)}</span>
            {p.kind !== "qualitative" && scored.raw_target && (
              <>
                {" "}
                {revised && (
                  <>
                    <s className="text-ink-3 decoration-ink-3">{first.raw_target}</s> <span className="text-ink-3">→</span>{" "}
                  </>
                )}
                <span className="t-figure text-[15px]">{scored.raw_target}</span>
              </>
            )}
          </span>
          {p.kind === "qualitative" && <span className="t-small mt-0.5 block text-ink-2">“{scored.quote.quote ?? p.statement}”</span>}
          {p.delivered && (
            <span className="t-small mt-1 block">
              <span className="text-ink-3">Delivered </span>
              <FigureValue f={p.delivered} printed className="font-medium" />
            </span>
          )}
          {p.dropped_note && <span className="t-small mt-1 block text-ink-2">{p.dropped_note}</span>}
          {!p.delivered && !p.dropped_note && p.verdict_reason && (p.verdict === "cant_score" || p.verdict === "not_yet_due") && (
            <span className="t-small mt-1 block text-ink-3">{p.verdict_reason.text}</span>
          )}
          <span className="t-small mt-1 flex items-center gap-1 text-ink-3">
            <span className="truncate">
              {first.call_label}
              {first.quote.page ? ` p.${first.quote.page}` : ""}
              {evidence && evidence !== first.quote ? ` → ${evidence.title?.replace(/ (call )?transcript$/i, " call").replace(/ investor presentation$/i, " deck") ?? "source"}${evidence.page ? ` p.${evidence.page}` : ""}` : ""}
            </span>
            <ChevronRight className="size-3.5 shrink-0" />
          </span>
        </span>
      </div>
    </li>
  );
}

function PromiseSheet({ p, onClose }: { p: MgmtPromise | null; onClose: () => void }) {
  const v = p ? VERDICT[p.verdict] : null;
  return (
    <Sheet
      open={!!p}
      onClose={onClose}
      eyebrow={p ? `${p.period?.label ?? "No date"} · ${p.basis.scope === "segment" && p.basis.segment ? p.basis.segment : p.basis.scope}` : ""}
      title={p ? cap(p.metric) : ""}
    >
      {p && v && (
        <div>
          <p className={`flex items-center gap-2 text-[15px] font-semibold ${TONE_TEXT[v.tone]}`}>
            <VerdictGlyph verdict={p.verdict} /> {v.label}
            {beat(p) ? " · beat" : ""}
          </p>
          <p className="t-small mt-0.5 text-ink-3">
            {p.verdict_by === "code"
              ? p.verdict === "goalposts_moved"
                ? "Decided in code: a later call revised the target unfavourably — that is the verdict even if the new target is met."
                : p.verdict === "quietly_dropped"
                  ? "Decided in code: no delivered figure, and later calls don't mention it."
                  : p.verdict === "not_yet_due" || p.verdict === "cant_score"
                    ? "Status set in code; it doesn't count toward credibility."
                    : "Decided in code from the target and the delivered figure."
              : `Judged by ${p.verdict_model ?? "the model"} — it must quote a later call, which is checked.`}
          </p>
          {p.verdict_reason && (
            <div className="mt-3">
              <ClaimProvenance claim={p.verdict_reason} />
            </div>
          )}
          <p className="t-micro mt-4 text-ink-3">What management said · {p.statements.length === 1 ? "1 call" : `${p.statements.length} calls`}</p>
          <ol className="mt-1">
            {p.statements.map((s, i) => (
              <li key={i} className="border-t border-rule pt-1 first:border-0">
                <p className="t-small mt-2">
                  <span className="font-medium">{s.call_label}</span>
                  <span className="text-ink-3"> · {istDayYear(s.made_on)}</span>
                  {s.raw_target && (
                    <span>
                      {" "}
                      · target <span className="t-figure text-[13px]">{s.raw_target}</span>
                      {s.period_text ? <span className="text-ink-3"> ({s.period_text})</span> : null}
                    </span>
                  )}
                  {p.scored_target && s.doc_id === p.scored_target.doc_id && s.made_on === p.scored_target.made_on && p.statements.length > 1 && <span className="text-ink-3"> · scored</span>}
                </p>
                <CitationBlock c={s.quote} />
                {s.speaker && <p className="t-small -mt-1 pb-2 text-ink-3">— {s.speaker}</p>}
              </li>
            ))}
          </ol>
          {p.delivered && (
            <>
              <p className="t-micro mt-4 text-ink-3">
                What was delivered · {p.delivered_source === "screener" ? "screener table" : p.delivered_source === "xbrl" ? "exchange XBRL" : "management-reported"}
              </p>
              <div className="mt-2">
                <FigureProvenance f={p.delivered} />
              </div>
            </>
          )}
          {p.dropped_note && <p className="t-small mt-4 text-ink-2">{p.dropped_note}</p>}
        </div>
      )}
    </Sheet>
  );
}
