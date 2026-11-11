// The demo portfolio's Brief, cached at Vercel's edge (DECISIONS: Phase 4 first paint).
// Evaluators start with the demo portfolio and no rules, so this *is* their Brief. The edge serves the last good
// copy instantly (stale-while-revalidate) while Render wakes; only successful answers are cached.
import { apiFetch } from "@/lib/api";

export const maxDuration = 60;

const WINDOWS = new Set(["24h", "3d", "7d"]);
const DEMO_WEIGHTS: Record<string, number> = {
  HAL: 6, EICHERMOT: 6, GRASIM: 5, TATAPOWER: 5, ALKEM: 5, KALYANKJIL: 5, COCHINSHIP: 5, TITAGARH: 4, IDEA: 3,
  RELIANCE: 8, HDFCBANK: 8, BAJFINANCE: 6, INFY: 7, ITC: 6, DIVISLAB: 5, TATASTEEL: 5, JUBLFOOD: 5, DIXON: 6,
};

export async function GET(req: Request) {
  const window = new URL(req.url).searchParams.get("window") ?? "7d";
  if (!WINDOWS.has(window)) return Response.json({ detail: "window must be 24h, 3d or 7d" }, { status: 400 });
  try {
    const r = await apiFetch("/brief", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        holdings: Object.entries(DEMO_WEIGHTS).map(([symbol, weight_pct]) => ({ symbol, weight_pct })),
        window,
      }),
    });
    const text = await r.text();
    return new Response(text, {
      status: r.status,
      headers: {
        "content-type": "application/json",
        "cache-control": "public, max-age=0, must-revalidate",
        ...(r.ok ? { "vercel-cdn-cache-control": "max-age=300, stale-while-revalidate=86400" } : {}),
      },
    });
  } catch (e) {
    const timedOut = e instanceof Error && e.name === "TimeoutError";
    return Response.json(
      { detail: timedOut ? "API timed out — it may still be waking up" : "API unreachable" },
      { status: 502, headers: { "cache-control": "no-store" } },
    );
  }
}
