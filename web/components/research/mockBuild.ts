// Dev-only scripted build (?mock=build): exercises BuildProgress without calling the API or spending quota.
import type { DossierJob, JobStep } from "@/lib/types";

const STEPS: [string, string][] = [
  ["discover", "Finding documents"],
  ["documents", "Reading documents"],
  ["extract", "Extracting guidance"],
  ["compute", "Computing figures"],
  ["ledger", "Scoring promises"],
  ["judge", "Judging qualitative promises"],
  ["reduce", "Writing the summary"],
  ["publish", "Publishing"],
];

export function mockJobSequence(symbol: string, emit: (j: DossierJob) => void): () => void {
  const now = () => new Date().toISOString();
  const resume = new Date(Date.now() + 3 * 3600 * 1000).toISOString();
  const frames: { status: DossierJob["status"]; upto: number; waiting?: boolean; msg: string; read: number; g: number; q?: number }[] = [
    { status: "queued", upto: -1, msg: "Queued", read: 0, g: 0, q: 1 },
    { status: "running", upto: 0, msg: "Found 8 transcripts, 1 annual report, 3 decks", read: 0, g: 0 },
    { status: "running", upto: 1, msg: "Reading 2 of 8 transcripts", read: 2, g: 6 },
    { status: "running", upto: 2, msg: "Reading 6 of 8 transcripts · 21 guidance statements found", read: 6, g: 21 },
    { status: "running", upto: 4, msg: "Scoring promises against delivered figures", read: 8, g: 29 },
    { status: "waiting_quota", upto: 4, waiting: true, msg: "Waiting for model quota", read: 8, g: 29 },
  ];
  let i = 0;
  const step = () => {
    const f = frames[i];
    const steps: JobStep[] = STEPS.map(([key, label], k) => ({
      key,
      label,
      detail: null,
      status: k <= f.upto ? "done" : k === f.upto + 1 ? (f.waiting ? "waiting" : f.status === "running" ? "running" : "pending") : "pending",
    }));
    emit({
      id: 999,
      symbol,
      status: f.status,
      stage: STEPS[Math.max(0, f.upto + 1)]?.[0] ?? null,
      message: f.msg,
      counters: { transcripts_read: f.read, transcripts_total: 8, guidance_found: f.g, quotes_dropped: 0 },
      steps,
      queue_position: f.q ?? null,
      reason: "requested",
      queued_at: now(),
      started_at: f.status === "queued" ? null : now(),
      updated_at: now(),
      finished_at: null,
      resume_after: f.waiting ? resume : null,
      error: null,
    });
    i = Math.min(i + 1, frames.length - 1);
  };
  step();
  const t = setInterval(step, 1800);
  return () => clearInterval(t);
}
