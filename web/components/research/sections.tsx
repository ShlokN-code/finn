"use client";
// Dossier sections. Each renders its own status (SectionMeta): ready / partial / building / unavailable.
// "Coming soon" sections (red flags, exchange data: building + not_built_yet) show a quiet line, never an error.
import type { ReactNode } from "react";
import { ArrowUpRight, Eye, EyeOff } from "lucide-react";
import { ClaimText, FigureValue } from "@/components/cards";
import { Sparkline } from "@/components/cards/Sparkline";
import { figureText, istDay, istTime } from "@/lib/format";
import { FALLBACK, read, useStored, write } from "@/lib/store";
import type { Dossier, Figure, SectionMeta, Series } from "@/lib/types";

const REASON: Record<string, string> = {
  not_built_yet: "Coming soon.",
  no_screener_page: "screener.in has no page for this company, so FINN can't build this section.",
  no_transcripts: "No earnings-call transcripts were found for this company, so there's nothing to score.",
  few_transcripts: "Too few call transcripts to compare across calls.",
  scanned_documents: "The documents are scanned images FINN can't read yet.",
  no_annual_report: "No annual report was found.",
  not_meaningful_for_lenders: "Not meaningful for lenders.",
  llm_unavailable: "The model was unavailable; FINN retries on the next build.",
  nse_pending: "Fetching exchange data… (about 1–2 minutes)",
  nse_unavailable: "Available after tonight's refresh.",
  not_found_in_sources: "Not found in sources.",
  source_unreachable: "The source couldn't be reached; FINN retries tonight.",
};

export function metaLine(meta: SectionMeta): string | null {
  if (meta.reason === "llm_quota")
    return `Waiting for the model quota — resumes ${meta.resume_after ? `after ${istTime(meta.resume_after)} IST` : "after 13:30 IST"}.`;
  if (meta.status === "building" && meta.reason === "not_built_yet") return "Coming soon.";
  return meta.note ?? (meta.reason ? (REASON[meta.reason] ?? null) : null);
}

export function SectionFrame({
  id,
  title,
  meta,
  children,
  aside,
}: {
  id: string;
  title: string;
  meta: SectionMeta;
  children?: ReactNode;
  aside?: ReactNode;
}) {
  const line = metaLine(meta);
  const showBody = meta.status === "ready" || meta.status === "partial" || (meta.status === "building" && meta.reason === "llm_quota");
  const quiet = meta.status === "building" && meta.reason === "not_built_yet";
  return (
    <section id={id} className="scroll-mt-14 border-t border-rule pb-6 pt-5">
      <div className="flex items-baseline gap-3 px-4">
        <h2 className="t-micro min-w-0 flex-1 text-ink-3">{title}</h2>
        {aside}
      </div>
      {line && (
        <p className={`t-small mt-1.5 px-4 ${quiet ? "text-ink-3" : meta.reason === "llm_quota" ? "text-warn" : "text-ink-2"}`}>{line}</p>
      )}
      {showBody && children}
      {meta.as_of && showBody && (
        <p className="t-small mt-3 px-4 text-ink-3">
          As of {istDay(meta.as_of)}
          {meta.written_by ? ` · written by ${meta.written_by} from cited facts only` : ""}
        </p>
      )}
    </section>
  );
}

function FigureGrid({ figures }: { figures: Figure[] }) {
  if (!figures.length) return null;
  return (
    <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 px-4">
      {figures.map((f, i) => (
        <div key={i} className="min-w-0">
          <dt className="t-small truncate text-ink-3">
            {f.label}
            {f.period?.label && f.period.kind !== "instant" ? ` · ${f.period.label}` : ""}
          </dt>
          <dd className="t-figure mt-0.5">
            <FigureValue f={f} />
          </dd>
        </div>
      ))}
    </dl>
  );
}

function SeriesRows({ series }: { series: Series[] }) {
  return (
    <ul className="mt-3 divide-y divide-rule border-y border-rule bg-surface">
      {series.map((s) => {
        const pts = s.points.filter((p) => p.value !== null);
        const first = pts[0];
        const last = pts.at(-1);
        return (
          <li key={s.metric} className="grid grid-cols-[1fr_auto_auto] items-center gap-3 px-4 py-2.5">
            <span className="min-w-0">
              <span className="block truncate text-[14px]">{s.metric}</span>
              <span className="t-small block text-ink-3">
                {first?.period?.label}–{last?.period?.label}
                {first && last && first !== last ? ` · from ${figureText(first)}` : ""}
              </span>
            </span>
            <Sparkline values={s.points.map((p) => p.value)} width={72} height={22} className="text-ink-2" />
            <span className="t-figure w-[92px] text-right text-[14px]">{last ? <FigureValue f={last} /> : "—"}</span>
          </li>
        );
      })}
    </ul>
  );
}

export function SnapshotSection({ d }: { d: Dossier }) {
  const s = d.snapshot;
  return (
    <SectionFrame id="snapshot" title="Snapshot" meta={s.meta}>
      <div className="space-y-2 px-4 pt-1">
        {s.lines.map((c, i) => (
          <p key={i} className="font-serif text-[17px] leading-[25px]">
            <ClaimText claim={c} />
          </p>
        ))}
      </div>
      <FigureGrid figures={s.headline} />
      {s.segments.length > 0 && (
        <>
          <p className="t-micro mt-4 px-4 text-ink-3">Segments</p>
          <FigureGrid figures={s.segments} />
        </>
      )}
    </SectionFrame>
  );
}

export function TrajectorySection({ d }: { d: Dossier }) {
  const t = d.trajectory;
  return (
    <SectionFrame id="trajectory" title="Trajectory" meta={t.meta}>
      {t.note && (
        <p className="px-4 pt-1 font-serif text-[17px] leading-[25px]">
          <ClaimText claim={t.note} />
        </p>
      )}
      <SeriesRows series={t.series} />
      <FigureGrid figures={t.growth} />
    </SectionFrame>
  );
}

export function SeriesSectionView({ id, title, section }: { id: string; title: string; section: Dossier["cash_quality"] }) {
  return (
    <SectionFrame id={id} title={title} meta={section.meta}>
      <FigureGrid figures={section.latest} />
      <SeriesRows series={section.series} />
    </SectionFrame>
  );
}

export function AnalystsSectionView({ d }: { d: Dossier }) {
  const a = d.analysts;
  return (
    <SectionFrame id="analysts" title="What analysts keep asking" meta={a.meta}>
      <ul className="mt-2 divide-y divide-rule border-y border-rule bg-surface">
        {a.points.map((p, i) => (
          <li key={i} className="px-4 py-3">
            <p className="flex items-baseline gap-2">
              <span className="text-[15px] font-medium">{p.theme}</span>
              <span className="t-small text-ink-3">asked in {p.n_calls} calls</span>
            </p>
            <p className="t-small mt-1 text-ink-2">
              <ClaimText claim={p.claim} />
            </p>
          </li>
        ))}
      </ul>
    </SectionFrame>
  );
}

export function RedFlagsSectionView({ d }: { d: Dossier }) {
  const r = d.red_flags;
  return (
    <SectionFrame id="red-flags" title="Red flags" meta={r.meta}>
      <ul className="mt-2 space-y-2 px-4">
        {r.items.map((f, i) => (
          <li key={i} className="t-small">
            <span className={f.severity === "high" ? "font-medium text-neg" : "font-medium text-warn"}>{f.kind.replace(/_/g, " ")} · </span>
            <ClaimText claim={f.claim} />
          </li>
        ))}
        {r.checked.map((c, i) => (
          <li key={`c${i}`} className="t-small text-ink-2">
            ✓ {c}
          </li>
        ))}
      </ul>
    </SectionFrame>
  );
}

function BullBearCol({ title, items }: { title: string; items: Dossier["bull_bear"]["bull"] }) {
  return (
    <div>
      <p className="t-micro text-ink-3">{title}</p>
      <ul className="mt-1.5 space-y-2">
        {items.map((c, i) => (
          <li key={i} className="t-small">
            <ClaimText claim={c} />
          </li>
        ))}
        {items.length === 0 && <li className="t-small text-ink-3">Not found in sources.</li>}
      </ul>
    </div>
  )
}

export function BullBearSectionView({ d }: { d: Dossier }) {
  const b = d.bull_bear;
  return (
    <SectionFrame id="bull-bear" title="Bull vs bear" meta={b.meta}>
      <div className="mt-2 space-y-5 px-4">
        <BullBearCol title="Bull" items={b.bull} />
        <BullBearCol title="Bear" items={b.bear} />
      </div>
    </SectionFrame>
  );
}

export function DriversSectionView({ d }: { d: Dossier }) {
  const x = d.drivers;
  const confirmed = useStored<Record<string, string[]>>("drivers", FALLBACK.drivers);
  const mine = confirmed[d.symbol] ?? [];
  const toggle = (id: string) => {
    const cur = read<Record<string, string[]>>("drivers", FALLBACK.drivers);
    const list = cur[d.symbol] ?? [];
    write("drivers", { ...cur, [d.symbol]: list.includes(id) ? list.filter((i) => i !== id) : [...list, id] });
  };
  return (
    <SectionFrame id="drivers" title="What to watch · suggested drivers" meta={x.meta}>
      <p className="t-small px-4 text-ink-2">From the company&apos;s own calls: what management guides on and analysts ask about most. Tap to watch.</p>
      <ul className="mt-2 divide-y divide-rule border-y border-rule bg-surface">
        {x.items.map((dr) => {
          const on = mine.includes(dr.id);
          return (
            <li key={dr.id} className="flex items-start gap-3 px-4 py-3">
              <span className="min-w-0 flex-1">
                <span className="block text-[15px] font-medium">{dr.label}</span>
                <span className="t-small block text-ink-2">{dr.description}</span>
                {dr.source && (
                  <span className="t-small mt-0.5 block text-ink-3">
                    <ClaimText claim={dr.source}>Why suggested</ClaimText>
                  </span>
                )}
              </span>
              <button
                type="button"
                onClick={() => toggle(dr.id)}
                aria-pressed={on}
                className={`inline-flex h-10 shrink-0 items-center gap-1.5 rounded-full border px-3 text-[13px] font-medium ${on ? "border-ink bg-ink text-paper" : "border-rule"}`}
              >
                {on ? <Eye className="size-4" /> : <EyeOff className="size-4 text-ink-3" />}
                {on ? "Watching" : "Watch"}
              </button>
            </li>
          );
        })}
      </ul>
    </SectionFrame>
  );
}

export function ExchangeSectionView({ d }: { d: Dossier }) {
  return (
    <SectionFrame id="exchange" title="Exchange data · latest results, pledging" meta={d.exchange_data.meta}>
      {d.exchange_data.pledging.length > 0 && <FigureGrid figures={d.exchange_data.pledging} />}
    </SectionFrame>
  );
}

const DOC_STATUS: Record<string, string> = {
  read: "read",
  scanned: "scanned — not readable",
  too_large: "too large",
  failed: "couldn't download",
  not_pdf: "not a PDF",
  skipped: "skipped",
};

export function SourcesSection({ d }: { d: Dossier }) {
  return (
    <section id="sources" className="scroll-mt-14 border-t border-rule pb-6 pt-5">
      <h2 className="t-micro px-4 text-ink-3">Sources · {d.sources.length} documents</h2>
      <ul className="mt-2 divide-y divide-rule border-y border-rule bg-surface">
        {d.sources.map((s) => (
          <li key={s.id}>
            <a href={s.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-4 py-2.5">
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[14px]">{s.title}</span>
                <span className="t-small block text-ink-3">
                  {s.pages ? `${s.pages} pages · ` : ""}
                  {DOC_STATUS[s.status] ?? s.status}
                </span>
              </span>
              <ArrowUpRight className="size-4 shrink-0 text-ink-3" />
            </a>
          </li>
        ))}
        {d.screener_url && (
          <li>
            <a href={d.screener_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-4 py-2.5">
              <span className="min-w-0 flex-1">
                <span className="block text-[14px]">screener.in standardised tables</span>
                <span className="t-small block text-ink-3">{d.basis ?? ""} financials · ratios · cash flows</span>
              </span>
              <ArrowUpRight className="size-4 shrink-0 text-ink-3" />
            </a>
          </li>
        )}
      </ul>
      <p className="t-small px-4 pt-3 text-ink-3">
        Quotes checked against the source text: {d.quality.quotes_checked.toLocaleString("en-IN")} · moved to the right page:{" "}
        {d.quality.quotes_reanchored} · dropped: {d.quality.quotes_dropped}. Model claims without support dropped: {d.quality.claims_dropped}.
        {d.cost.calls > 0 && ` Built with ${d.cost.calls} model calls (≈ $${d.cost.est_usd.toFixed(2)} at list price).`}
      </p>
    </section>
  );
}
