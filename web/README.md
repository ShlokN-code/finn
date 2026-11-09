# web

FINN's mobile-first PWA (Next.js 16, App Router). See the root README for setup.

- `app/page.tsx` — skeleton page: shows one row read from Supabase via the API.
- `app/api/hello/route.ts` — server-side proxy to `${API_BASE_URL}/health/db` (no CORS, API URL stays server-side).
- `lib/types.ts` — generated from the backend's Pydantic models (`npm run gen:schema && npm run gen:types`). Do not edit.

Env: `API_BASE_URL` (server-only).
