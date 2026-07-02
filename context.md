# context.md — eccolo-ai-data-engine

> Ground truth for architectural review and handoff. Written 2026-07-02 by direct code read, not
> from memory of past sessions. Honest about rough edges; uncertainties flagged rather than guessed.

## What this repo is

The **Analytics Engine** — the measurement third of the Eccolo creator data flywheel. Takes monthly
platform CSV exports (Facebook, Instagram, Stories from Meta; YouTube Studio "Table data"), scores
every post by rank-order scoring against a per-client config, and produces a formatted Excel
performance workbook plus Claude-written insight sections. Internal tool for Ziggurat talent/social
managers. Flask app, one Railway service, Jinja-served UI (no separate frontend build).

In the Eccolo pipeline (edit performance → source video → comment scrape → sentiment → insight),
this repo is stage 1: it surfaces which edits performed best, and its result screen offers the hop
into stage 2/3 (the scraper) when the top post is a YouTube video.

## Architecture

- **`app.py`** — Flask. Routes: `GET /` (Jinja UI), `GET /api/clients` (JSON client list for an
  external frontend), `POST /run` (multipart CSVs + client slug → `.xlsx` download, with build
  metadata smuggled in URL-quoted response headers: `X-Client`, `X-Month`, `X-Counts`, `X-Notes`,
  `X-Insight-Note`, `X-Top-Posts`). CORS via `FRONTEND_ORIGIN` env (unset → `*`).
- **`core/build_workbook.py`** — the engine. Config parsing (hand-rolled regex over Markdown
  headings + fenced yaml, NOT PyYAML), platform fingerprint detection, column validation
  (fail-loud `MissingColumns`), CTA/trigger detection, rank-order scoring (`score_posts`),
  cross-platform `top_posts()` leaderboard, and `run_build()` — the single orchestration function
  shared by CLI (`main()`) and the web app.
- **`core/tabs.py`** — openpyxl tab builders (feed tabs, stories, YouTube, Footnotes, Summary).
  Insight sections render from an `insights` dict when given, else as labelled shells.
- **`core/insights.py`** — the Claude API call. Summarises scored tables into a prompt with the full
  raw client config, calls **`claude-opus-4-8`, adaptive thinking, max_tokens 8000, streaming**
  (model is **hardcoded**, no env override), parses a JSON object of five insight sections.
  Degrades gracefully: no `ANTHROPIC_API_KEY` / SDK missing / call fails → `None` + a note, and the
  workbook builds with shell sections.
- **`configs/*.md`** — one per client (chefsteps, xyla, chrisyoung, ninjon, stevemould,
  **hoffmann** — note the slug, see below). Dropdown self-populates from this folder. Per the
  System Integration Contract §1.1 this folder is the **canonical client_slug registry**.
- **`templates/index.html`** — the whole UI in one file: Eccolo "Console" dark theme, client
  dropdown, Meta/YouTube source toggle, drag-drop CSVs, fake-but-charming progress steps, result
  screen with cross-platform leaderboard, build notes, insight-status line, and the flywheel hop.
- **Deploy:** Railway, `Procfile` → gunicorn `--timeout 300 --workers 2` (also `gunicorn.conf.py`
  with the same values — two places to keep in sync).

### Data flow of one run

`POST /run` → save uploads to a tempdir → `run_build()`: parse config → read CSVs → fingerprint
sanity-check → validate columns (fail loud) → split IG special content → CTA detection → rank-order
score each platform table → **`generate_insights()` (Claude, synchronous, inside the HTTP
request)** → build workbook → return file + header metadata → template JS renders the result screen
and auto-downloads.

Note: the Claude call happens **inline within the `/run` request**. gunicorn timeout is 300s and
Railway's edge proxy kills requests at ~300s. The sibling repo (`eccolo-ai-scraper-sentiment`) hit
exactly this wall and moved to an async job+poll pattern; this repo has not. Bounded today by the
8000-token output cap (~60–120s typical), but it is the same landmine, unexploded.

## The unification (what "merged last night" actually means)

The two repos were **not merged**. Deliberately. What happened:

- Both UIs were redesigned to the same "Console" dark visual language (previously "Threadline",
  now rebranded Eccolo — no Threadline strings remain in code, only `tl-` CSS animation prefixes).
- Cross-links were added at the UI layer, carried by query params, both optional via env vars:
  - Permanent "Scraper ↗" nav link (`SCRAPER_URL` env; unset → hidden).
  - Contextual hop: result screen's "Scrape top video →" opens `<scraper>/?url=<permalink>` — but
    **only when the top-ranked post is a YouTube post with a permalink**. For Meta-only clients
    (most of the roster) this never appears. Note the hop sends only `?url=`, **not
    `?client_slug=`**, even though the scraper reads both — client continuity is dropped at this
    seam and the user re-types the slug.
  - Reverse hop: this page reads `?client=<slug>` on load and preselects the dropdown if the slug
    matches a bundled config; unknown slug falls back silently.
- `GET /api/clients` + CORS config were added as an **additive** API surface for a possible future
  unified frontend — currently nothing consumes it (the scraper repo's frontend links here, it
  doesn't fetch from here).

So: shared design language + link-level integration. "Separate repos, separate deploys,
deliberately not merged (a bug in one shouldn't take the other down)" is documented intent in both
READMEs — do not "fix" it by merging.

## Contract conformance (System Integration Contract)

The contract file itself is **not in this repo** (it lives in Jack's AI OS vault:
`The Second Layer/projects/eccolo-ai/data-tools/SYSTEM_INTEGRATION_CONTRACT.md`). Per its §7
checklist, Analytics must: add `source_id` prefixes, emit a `.run.json` side-output (§5), and
confirm the slug registry. **None of that is implemented**: no provenance block, no `source_id`,
no `.run.json` anywhere in this repo. The workbook and the header metadata are the only outputs.

**The slug registry itself is the known spine break:** this repo defines `hoffmann`
(`hoffmann-analytics-config.md`), the sentiment engine and the contract's own §1.1 examples and
naming rule ("James Hoffmann" → multi-word names collapse to one token → `jameshoffmann`) use
`jameshoffmann`. The sentiment repo's `clients/jameshoffmann.md` carries an explicit "flag for
Jack" note about this. Concrete symptom today: a scraper/sentiment → analytics hop with
`?client=jameshoffmann` fails to preselect the dropdown here. Every future by-ID join breaks on
this creator until reconciled.

## Known rough edges / stale docs

- **`app.py` header docstring and README are stale**: both say insight generation is "stubbed at
  the bottom for phase 2" / "currently added afterward via the skill". False since commit
  `b2f49ad` — insights run live inside `run_build()` via `core/insights.py`. The commented-out
  `/insights` stub at the bottom of `app.py` is a leftover of the older plan.
- **Model hardcoded** in `insights.py` (`claude-opus-4-8`); the sibling repo made its model
  env-configurable (`SENTIMENT_MODEL`). No `ANALYTICS_MODEL` equivalent.
- **No tests.** Zero test files in the repo. The "verified against a real ChefSteps May 2026
  deliverable — zero diffs" claim (project docs) predates the YouTube support and the Claude
  insights; the YT tabs and insight sections have never been verified against a reference
  deliverable, only eyeballed.
- Insight JSON truncation isn't detected: `max_tokens=8000`, no `stop_reason` check — a truncated
  response fails `json.loads` and degrades to shells with a generic failure note. Graceful, but
  the note doesn't say "truncated".
- gunicorn config duplicated (Procfile flags + gunicorn.conf.py).
- Excludes (`cfg.excludes`) are parsed as hardcoded defaults, not from config prose — a documented
  "well-known ones encoded" shortcut.
- Page `<title>` still says "Ziggurat Analytics Engine" (branding drift vs Eccolo; breadcrumbs
  already say `eccolo`).

## Deliberate tradeoffs (do NOT "fix" these)

- **Two repos, two deploys, link-level integration** — ratified; convergence is a later cycle.
- **`core/build_workbook.py` is claimed shared verbatim with the analytics-engine skill** ("one
  source of truth, scoring logic never forks"). *Uncertainty:* the skill's copy lives outside this
  repo and byte-identity was not verified in this review — treat any edit to `core/` as needing a
  matching skill-side sync.
- **Metadata via response headers** on `/run` — chosen because the primary response must be the
  file download; values URL-quoted for Latin-1 safety. Odd-looking, intentional.
- **Fail-loud `MissingColumns`** rather than best-effort scoring — never mis-score silently.
- **Deterministic tie-breaking** in scoring (older-post-first on tied Total Score) — reproducibility.
- **Empty special-content tabs are still emitted** with a note — the team expects the tab to exist.
- **CORS `*` fallback when `FRONTEND_ORIGIN` unset** — documented as fine for dev, to be locked
  down "before this is load-bearing in production".
- The fake progress steps in the UI are cosmetic theatre over a single synchronous request —
  known, accepted.

## Uncertainties (flagged, not guessed)

- Live Railway state (env vars set? `SCRAPER_URL`? `ANTHROPIC_API_KEY`? which domain?) is not
  visible from the repo. The scraper's own PROJECT_CONTEXT.md is the authoritative deploy record.
- Whether anything external already consumes `/api/clients` (believed: nothing yet).
- Whether the skill copy of the engine has drifted from `core/` (see above).
