# Ziggurat Analytics Engine — web UI

Hosted front-end for the monthly social data crunch. Upload Meta CSV exports, pick a client,
download the scored performance workbook. No Claude account needed.

## Run locally
    pip install -r requirements.txt
    python app.py
    # open http://localhost:8080

## Deploy (Railway, via GitHub)
Same flow as the YouTube scraper — a second Railway service pointed at a new repo.

1. **Create a new GitHub repo** (e.g. `eccolo-ai-data-engine`) and add these files, keeping
   the folder structure exactly: `app.py` at the root, with `templates/`, `core/`, and `configs/`
   beside it. The structure matters — Flask looks for `templates/` relative to `app.py`, and the
   app imports the engine from `core/`.
2. **In Railway: New Project → Deploy from GitHub repo**, and pick the repo.
3. **Railway auto-detects and builds.** It sees `requirements.txt` (Python), installs the deps,
   reads the `Procfile`, and starts gunicorn. Nothing to configure for the basic deploy. First
   build takes a couple of minutes.
4. **Open the generated URL** — it serves the upload page directly. Pick a client, drop in the
   month's CSVs, download the workbook.

No separate front-end to deploy: the UI ships inside this app (`templates/index.html`) and is
served automatically at the root URL. No build step, no Dockerfile required — the Procfile route
is all Railway needs.

### Required files (all present in this bundle)
- `app.py` — the Flask app (reads `$PORT` from Railway automatically)
- `Procfile` — `web: gunicorn app:app --bind 0.0.0.0:$PORT`
- `requirements.txt` — Python dependencies
- `templates/index.html` — the upload UI
- `core/build_workbook.py` + `core/__init__.py` — the engine (shared with the skill)
- `configs/*.md` — one config per client; the dropdown self-populates from these

## Adding a client
Drop a `[slug]-analytics-config.md` into `configs/` and redeploy — the dropdown self-populates.
Configs are produced by the `analytics-config-intake` skill.

## API surface (for the unified flywheel frontend)

This app's own page (`templates/index.html`) still works exactly as before — nothing here changes
that. These two routes are the additive surface an external frontend calls to fold analytics into
the same unified UI as the scraper/sentiment tools, without merging repos or deploys:

- **`GET /api/clients`** — `{ "clients": [{ "slug", "name", "platforms_active" }, ...] }`. Same
  source as the page's own dropdown (`available_clients()`), just JSON instead of Jinja.
- **`POST /run`** — unchanged; already the route the page's own JS calls via `fetch()` with
  `FormData`. Returns the built `.xlsx` as a file download, with build metadata (client, month,
  counts, notes) in response headers (`X-Client`, `X-Month`, `X-Counts`, `X-Notes`,
  `X-Insight-Note`) rather than a JSON body, since the primary response has to be the file.

**CORS:** set `FRONTEND_ORIGIN` (comma-separated for multiple) to the unified frontend's URL so it
can call `/api/clients` and `/run` cross-origin. Unset defaults to `*` — fine for local dev; lock it
down before this is load-bearing in production. This app's own same-origin page is unaffected either
way.

## The flywheel cross-link to the Comment Scraper

This app and `eccolo-ai-scraper-sentiment` are **separate repos, separate Railway deploys, separate
URLs** — deliberately not merged. They're tied together at the UI layer with plain links carrying
context via query params, not a shared frontend:

- **Permanent nav:** a "Scraper ↗" link sits in the header at all times (once `SCRAPER_URL` is
  set) — not tied to any run, just a plain jump to `<scraper-url>/`.
- **Contextual hop, Analytics → scraper:** the Result screen's "Scrape top video →" button opens
  `<scraper-url>/?url=<video-url>` for the top-ranked post, in a new tab, prefilling the scraper's
  form — but only when that top post is specifically a YouTube post with a link. Most bundled
  clients only have Instagram/Facebook/Stories active, so this won't show for them.
- **Contextual hop, scraper → Analytics:** built on the scraper side (`VITE_ANALYTICS_URL`) — it
  opens `<this-app-url>/?client=<slug>`. This page reads `?client=` on load and preselects that
  client's dropdown if the slug is recognised; unrecognised or missing slug just falls back to the
  default, never errors.

Neither hop is required — unset either env var and that link/behaviour simply doesn't appear.

## Architecture
`core/build_workbook.py` is the single source of truth — the SAME file the analytics-engine skill
uses. The web app and the skill both call `run_build()`, so scoring logic never forks.

- Deterministic build (scoring, tabs, formatting): done here, free, instant.
- Written insight tabs (Footnotes/Summary): generated live inside the same `/run` by
  `core/insights.py` (Claude API). If `ANTHROPIC_API_KEY` is unset or the call fails, the build
  degrades gracefully to labelled insight shells with a note — no separate step or endpoint.
