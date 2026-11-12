"use client";
// Build progress for a dossier job: steps, live message, counters, queue position — and, when the strong models'
// daily quota is used up, a plain explanation plus a pointer to the sections that are already readable.
import { Check, Clock, Loader2, X } from "lucide-react";
import type { DossierJob } from "@/lib/types";
import { istDay, istTime, isTodayIST } from "@/lib/format";

const when = (iso: string) => `${isTodayIST(iso) ? "" : istDay(iso) + " "}${istTime(iso)} IST`;

export function BuildProgress({ job, readyCount }: { job: DossierJob; readyCount: number }) {
  const waiting = job.status === "waiting_quota" || job.steps.some((s) => s.status === "waiting");
  const c = job.counters;
  return (
    <section className="mx-4 mt-3 rounded-xl border border-rule bg-surface p-4" aria-live="polite" data-build-progress={job.status}>
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="t-micro text-ink-3">
            {job.status === "queued" ? "Queued" : waiting ? "Paused for model quota" : "Building dossier"}
          </p>
          <p className="t-headline mt-1">
            {job.status === "queued"
              ? job.queue_position && job.queue_position > 1
                ? `${job.queue_position - 1} ahead of you`
                : "Starting in a moment"
              : job.message}
          </p>
          {c.transcripts_total > 0 && (
            <p className="t-small mt-0.5 text-ink-2">
              {c.transcripts_read} of {c.transcripts_total} transcripts read · {c.guidance_found} guidance statements found
            </p>
          )}
        </div>
      </div>
      {waiting && (
        <div className="t-small mt-3 rounded-lg bg-warn-bg p-3 text-ink">
          <p className="font-medium text-warn">FINN&apos;s AI quota for today is used up.</p>
          <p className="mt-1 text-ink-2">
            The steps that need the stronger model — judging qualitative promises and writing the summary — resume
            {job.resume_after ? ` after ${when(job.resume_after)}` : " after 13:30 IST"}, automatically. Numbers, the
            numeric Promise Ledger and every other section {readyCount > 0 ? `are ready below (${readyCount}).` : "appear below as they finish."}
          </p>
        </div>
      )}
      <ol className="mt-3 space-y-1.5">
        {job.steps.map((s) => (
          <li key={s.key} className="t-small flex items-center gap-2.5">
            <StepIcon status={s.status} />
            <span className={s.status === "pending" || s.status === "skipped" ? "text-ink-3" : ""}>{s.label}</span>
            {s.detail && <span className="truncate text-ink-3">· {s.detail}</span>}
            {s.status === "skipped" && <span className="text-ink-3">· skipped</span>}
          </li>
        ))}
      </ol>
      {job.status === "failed" && job.error && <p className="t-small mt-3 text-neg">{job.error}</p>}
    </section>
  );
}

function StepIcon({ status }: { status: DossierJob["steps"][number]["status"] }) {
  const cls = "size-4 shrink-0";
  if (status === "done") return <Check className={`${cls} text-pos`} strokeWidth={2.25} />;
  if (status === "running") return <Loader2 className={`${cls} animate-spin text-ink`} strokeWidth={2} />;
  if (status === "waiting") return <Clock className={`${cls} text-warn`} strokeWidth={2} />;
  if (status === "failed") return <X className={`${cls} text-neg`} strokeWidth={2.25} />;
  return <span className={`${cls} grid place-items-center`}><span className="size-1.5 rounded-full bg-rule" /></span>;
}
