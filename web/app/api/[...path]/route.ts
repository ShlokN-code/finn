// Proxies an allow-listed set of API routes so the browser never needs the API URL or CORS.
// Holdings sent to /brief pass straight through and are not logged here.
import { apiBase } from "@/lib/api";

export const maxDuration = 60;

const ALLOWED: [string, RegExp][] = [
  ["POST", /^brief$/],
  ["GET", /^events\/[^/]+\/card$/],
  ["POST", /^telegram\/link$/],
  ["GET", /^subscriptions\/me$/],
  ["PUT", /^subscriptions\/me$/],
  ["DELETE", /^subscriptions\/me$/],
  // Research (Phase 3): builds run in the background on the API, so every call here returns quickly.
  ["GET", /^research\/symbols$/],
  ["GET", /^research\/jobs\/\d+$/],
  ["GET", /^research\/[A-Za-z0-9&_-]{1,20}$/],
  ["POST", /^research\/[A-Za-z0-9&_-]{1,20}\/build$/],
  ["POST", /^research\/[A-Za-z0-9&_-]{1,20}\/ask$/],
];

async function proxy(req: Request, ctx: RouteContext<"/api/[...path]">) {
  const { path } = await ctx.params;
  const joined = path.map(encodeURIComponent).join("/");
  if (!ALLOWED.some(([m, re]) => m === req.method && re.test(path.join("/")))) {
    return Response.json({ detail: "not found" }, { status: 404 });
  }
  const base = apiBase();
  if (!base) return Response.json({ detail: "API_BASE_URL not set on Vercel" }, { status: 503 });
  const headers: Record<string, string> = { "content-type": "application/json" };
  const auth = req.headers.get("authorization");
  if (auth) headers.authorization = auth;
  try {
    const r = await fetch(`${base}/${joined}`, {
      method: req.method,
      headers,
      body: req.method === "GET" || req.method === "DELETE" ? undefined : await req.text(),
      cache: "no-store",
      signal: AbortSignal.timeout(55_000),
    });
    return new Response(await r.text(), {
      status: r.status,
      headers: { "content-type": r.headers.get("content-type") ?? "application/json" },
    });
  } catch (e) {
    const timedOut = e instanceof Error && e.name === "TimeoutError";
    return Response.json(
      { detail: timedOut ? "API timed out — it may still be waking up" : "API unreachable" },
      { status: 502 },
    );
  }
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as DELETE };
