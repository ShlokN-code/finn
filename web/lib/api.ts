// Server-side access to the FINN API on Render. The browser never sees API_BASE_URL (DECISIONS: web proxy).
// Render's free tier sleeps; a cold start can take ~50 s, hence the long timeout.

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export function apiBase(): string | null {
  const base = process.env.API_BASE_URL;
  return base ? base.replace(/\/$/, "") : null;
}

export async function apiFetch(path: string, init: RequestInit = {}, timeoutMs = 55_000): Promise<Response> {
  const base = apiBase();
  if (!base) throw new ApiError(503, "API_BASE_URL not set on Vercel");
  return fetch(`${base}${path}`, { cache: "no-store", ...init, signal: AbortSignal.timeout(timeoutMs) });
}
