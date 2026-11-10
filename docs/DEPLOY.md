# Deploy: Supabase → Render → Vercel

Skeleton path: phone → Vercel (`web/`) → `/api/hello` route → Render (`backend/api`) `/health/db` → Supabase Postgres `public.hello`.
All three on free plans. **If any dashboard asks for a payment method or a paid plan, stop — don't add one.**
Do the steps in this order (each needs a value from the previous one).

---

## 1. Supabase (database) — ~5 min

1. Go to **supabase.com** → **Start your project** → **Continue with GitHub** → authorise.
2. If asked, create an organisation: any name, plan **Free**.
3. **New project**:
   - Name: `finn`
   - Database password: click **Generate a password**, then **copy it into your password manager** (needed in step 7).
   - Region: **South Asia (Mumbai)**
   - Leave the rest as default → **Create new project**. Wait ~2 min until the dashboard stops showing "Setting up project".
4. Left sidebar → **SQL Editor** → **+ New query**.
5. Paste the whole contents of [`backend/db/migrations/0001_hello.sql`](../backend/db/migrations/0001_hello.sql) → **Run** (or Cmd+Enter). Expected: "Success. No rows returned".
6. Check: left sidebar → **Table Editor** → `hello` → one row ("Namaste from Supabase…").
7. Top bar → **Connect** → in the dialog choose **Connection String**, Type **URI**, Method **Session pooler** (not "Direct connection" — that is IPv6-only and Render can't reach it). Copy the string. It looks like
   `postgresql://postgres.<project-ref>:[YOUR-PASSWORD]@aws-1-ap-south-1.pooler.supabase.com:5432/postgres`
   Replace `[YOUR-PASSWORD]` (including the brackets) with the password from step 3. This full string is **`DATABASE_URL`** — treat it as a secret; don't paste it in chat or commit it.

## 2. Render (API) — ~8 min

1. Go to **render.com** → **Get Started** → **GitHub** → authorise.
2. Dashboard → **+ New** → **Web Service**.
3. Source: **Git Provider → GitHub** → **Configure account** → install the Render app for **Only select repositories → `ShlokN-code/finn`** → back in Render select `finn` → **Connect**.
4. Fill in:
   | Field | Value |
   |---|---|
   | Name | `finn-api` (your URL becomes `https://finn-api.onrender.com`; if taken, Render adds a suffix — use whatever it shows) |
   | Language | `Python 3` |
   | Branch | `main` |
   | Region | **Singapore** (closest to Supabase Mumbai) |
   | Root Directory | `backend` |
   | Build Command | `pip install ".[api]"` |
   | Start Command | `uvicorn api.main:app --host 0.0.0.0 --port $PORT` |
   | Instance Type | **Free** |
5. **Environment Variables** → **Add Environment Variable** twice:
   - `DATABASE_URL` = the Session-pooler string from Supabase step 7
   - `PYTHON_VERSION` = `3.12.7`
6. **Advanced** → **Health Check Path** = `/health`. Leave Auto-Deploy **On Commit**.
7. **Deploy Web Service**. Wait for "Your service is live 🎉" (~3–5 min first time).
8. Check in a browser: `https://<your-render-url>/health/db` → JSON with `"status": "ok"` and the row. If you see `"error": "OperationalError"`, the password in `DATABASE_URL` is wrong or the Direct (not pooler) string was used.

## 3. Vercel (web) — ~5 min

1. Go to **vercel.com** → **Sign Up** → **Hobby** → **Continue with GitHub** → authorise.
2. **Add New…** → **Project** → under "Import Git Repository" → **Install** / **Adjust GitHub App Permissions** → **Only select repositories → `ShlokN-code/finn`** → back in Vercel click **Import** next to `finn`.
3. Configure Project:
   - Framework Preset: **Next.js** (auto-detected)
   - **Root Directory → Edit → select `web` → Continue** ← important
   - Build and Output Settings: leave defaults
   - **Environment Variables**: Key `API_BASE_URL`, Value `https://<your-render-url>` (no trailing slash) → **Add**
4. **Deploy**. Wait ~1–2 min → **Continue to Dashboard** → **Visit**. URL looks like `https://finn-<something>.vercel.app`.
5. Optional (faster): Project → **Settings → Functions → Function Region → Mumbai, India (bom1)** → Save → Deployments → ⋯ → **Redeploy**.
6. Open the URL on your phone. Expected: "FINN · Connected · Namaste from Supabase…". The first load after idle may say "Waking the API…" for up to ~50 s.

## 4. GitHub (keep-alive) — ~1 min

> Backup only since 10 Nov 2026 — the primary keepalive is cron-job.org (§6).

1. github.com/ShlokN-code/finn → **Settings** → **Secrets and variables** → **Actions** → **Variables** tab → **New repository variable**: Name `API_BASE_URL`, Value `https://<your-render-url>` → **Add variable**.
2. **Actions** tab → **keepalive** → **Run workflow** → **Run workflow**. It should go green in ~1 min. From then on it runs every 10 minutes.

## Tell Claude

Send back the **Render URL** and the **Vercel URL** (not the database string). Claude verifies the chain with curl and records the URLs in the README.

## 4. Telegram bot (Phase 2) — ~5 min

1. In Telegram, open **@BotFather** → `/newbot` → name `FINN` (any) → username ending in `bot` (e.g. `finn_alerts_bot`). BotFather replies with the **token** — a secret; don't paste it in chat or commit it.
2. Make a webhook secret: `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
3. **Render** → `finn-api` → Environment → add `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME` (without @), `TELEGRAM_WEBHOOK_SECRET`, `WEB_BASE_URL` (the Vercel URL) → Save (redeploys).
4. **GitHub** → repo → Settings → Secrets and variables → Actions: secret `TELEGRAM_BOT_TOKEN`; variable `WEB_BASE_URL`.
5. Local `.env` (repo root): `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `API_PUBLIC_URL=https://<render-url>`. Then `cd backend && ../.venv/bin/python -m jobs.telegram_setup` → prints `bot: @…` and `webhook: https://<render-url>/telegram/webhook`.
6. Send `/start` to the bot → "Connected to the demo portfolio" + a **Test alert**.

## After every push: confirm Render deployed it

Render installs only `.[api]` (see `backend/pyproject.toml`); CI's `api-import` job imports `api.main` with exactly
those extras, so a missing dependency fails CI first. After a push, confirm the new commit is live:

```bash
scripts/check_deploy.sh
```

It polls `GET /version` (commit from Render's `RENDER_GIT_COMMIT`) until it matches local `HEAD`, or fails after
15 minutes — then read the Render deploy log; the previous deploy stays live.

## 6. External scheduler (cron-job.org) — ~20 min

GitHub's cron fires too rarely to rely on (10 Nov 2026: keepalive ran 3 times in ~19 h instead of ~110; ingest ran once
in ~6 h). cron-job.org (free) triggers everything instead; the GitHub cron entries stay as a backup, and a slot that
already ran is skipped (`backend/finn/ingest/schedule.py`), so the two never double the work.

Four jobs: **keepalive** (`/ping`: API + DB), **filings** (every 30 min), **daily** (post-close), **alerts** (07:00).

### 6a. GitHub token (fine-grained, this repo, Actions only)

1. github.com → your avatar (top right) → **Settings** → left sidebar, bottom: **Developer settings**.
2. **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
3. **Token name:** `finn-cron-job-org`. **Description:** `cron-job.org → workflow_dispatch on finn/ingest`.
4. **Resource owner:** `ShlokN-code`.
5. **Expiration:** the longest offered (e.g. 1 year / custom). Put the expiry date in your calendar — when it lapses,
   cron-job.org's dispatch jobs start failing with HTTP 401 and you get the failure email.
6. **Repository access:** **Only select repositories** → pick **ShlokN-code/finn**.
7. **Permissions → Repository permissions:** set **Actions** to **Read and write**. (In the newer layout: **+ Add
   permissions** → tick **Actions** → choose **Read and write**.) **Metadata: Read-only** is added automatically and is
   required. Leave **everything else at "No access"** — no Contents, Secrets, Workflows, Administration, and no
   account permissions.
8. **Generate token** → copy it (starts with `github_pat_`); GitHub shows it once. Paste it only into cron-job.org's
   header fields below — not in chat, not in the repo.

What this token can do if it ever leaks: start, cancel, re-run or delete runs of this repo's workflows, enable/disable
them, and read run logs (secrets are masked). It cannot read secrets, change code, or touch any other repository.
Revoke it on the same page.

### 6b. cron-job.org account

1. cron-job.org → **Sign up** (free) → confirm the email → you land in the **Console**.
2. Top-right menu → **Settings** → set your **time zone** to **Asia/Kolkata** (new jobs default to it).
3. In each job below, **Notifications:** tick *notify on failure* with **after 3 failures** (one Render cold start
   shouldn't email you) and *notify when the job is disabled automatically* (cron-job.org disables jobs that keep
   failing).

Field names below follow cron-job.org's job editor (**Common** tab: title, URL, schedule; **Advanced** tab: time
zone, request method, headers, body, timeout); exact labels may differ slightly.

### 6c. Job 1 — keepalive

**Console → Cronjobs → Create cronjob**

| Field | Value |
|---|---|
| Title | `FINN keepalive` |
| URL | `https://finn-api-4ejm.onrender.com/ping` |
| Enable job | on |
| Execution schedule | **Every 10 minutes** |
| Advanced → Request method | `GET` (or `HEAD`) |
| Advanced → Timeout | the maximum offered (a cold Render start takes ~50 s; the ping still wakes it) |

`/ping` wakes Render *and* runs `SELECT 1` on Supabase, so one ping covers both free tiers. It replies with the
2-byte plain text `ok` (`Content-Length: 2`, never compressed); a database problem returns HTTP 503 `db down`.
**Test run** at the bottom → expect HTTP 200 and `ok`. **Save**.

Don't use `/health/db` here: Render's Cloudflare edge Brotli-compresses and chunk-streams that JSON for clients that
accept `br`, which cron-job.org rejects as "output too large" (and `HEAD` on it returns 405).

### 6d. Jobs 2–4 — ingest dispatches

All three call the same GitHub endpoint; only the title, schedule and body differ. **Create cronjob** for each:

| Field | Value (same for all three) |
|---|---|
| URL | `https://api.github.com/repos/ShlokN-code/finn/actions/workflows/ingest.yml/dispatches` |
| Advanced → Request method | `POST` |
| Advanced → Headers (add 5) | `Authorization` = `Bearer github_pat_…` (your token) · `Accept` = `application/vnd.github+json` · `X-GitHub-Api-Version` = `2022-11-28` · `Content-Type` = `application/json` · `User-Agent` = `finn-scheduler` |
| Advanced → Time zone | `Asia/Kolkata` |
| Enable job | on |

| Title | Execution schedule (**Custom**, Asia/Kolkata) | Advanced → Request body |
|---|---|---|
| `FINN filings` | Days of week **Mon–Fri** · Hours **8–22** · Minutes **0, 30** | `{"ref":"main","inputs":{"job":"filings","scheduled":"true"}}` |
| `FINN daily` | Days of week **Mon–Fri** · Hour **16** · Minute **30** | `{"ref":"main","inputs":{"job":"daily","scheduled":"true"}}` |
| `FINN alerts` | **Every day** · Hour **7** · Minute **0** | `{"ref":"main","inputs":{"job":"alerts","scheduled":"true"}}` |

The 08:00 and 22:30 filing slots start and exit at once (the job's own window is 08:30–22:00 IST); listing hours
8–22 is simpler than carving them out.

**Test run** each → expect **HTTP 204** (GitHub accepted the dispatch). Then check
https://github.com/ShlokN-code/finn/actions — a new `ingest` run appears within seconds. A 401 means the token is
wrong or expired; 403 means the Actions permission isn't *Read and write*; 404 means the URL or repository access
is off; 422 means the body is malformed.

### 6e. Check it's working

Tell Claude once the jobs are saved: the `ingest_runs` table records `trigger = scheduler` for these runs, and
GitHub's run list shows them as `workflow_dispatch`. A plain manual **Run workflow** from GitHub's UI still forces a
filings run outside the window and never skips; the scheduler's `"scheduled":"true"` makes a run respect the window
and skip a slot that already ran.
