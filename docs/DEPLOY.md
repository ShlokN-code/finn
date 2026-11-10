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
