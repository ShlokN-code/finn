// Proxies GET {API_BASE_URL}/health/db so the browser never needs the API URL or CORS.
// Render's free tier sleeps; a cold start can take ~50s, hence the long timeout.
export const maxDuration = 60;

export async function GET() {
  const base = process.env.API_BASE_URL;
  if (!base) {
    return Response.json({ status: "error", error: "API_BASE_URL not set on Vercel" }, { status: 503 });
  }
  const t0 = Date.now();
  try {
    const r = await fetch(`${base.replace(/\/$/, "")}/health/db`, {
      cache: "no-store",
      signal: AbortSignal.timeout(55_000),
    });
    const body = await r.json();
    return Response.json({ ...body, round_trip_ms: Date.now() - t0 }, { status: r.status });
  } catch (e) {
    const timedOut = e instanceof Error && e.name === "TimeoutError";
    return Response.json(
      { status: "error", error: timedOut ? "API timed out — it may still be waking up" : "API unreachable" },
      { status: 502 },
    );
  }
}
