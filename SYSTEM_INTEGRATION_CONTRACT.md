<!-- VENDORED COPY — canonical source: ~/Jack's AI OS/The Second Layer/projects/eccolo-ai/data-tools/SYSTEM_INTEGRATION_CONTRACT.md (byte-identical duplicate under Ziggurat/efforts/data-tools/). Do not edit here; edit the canonical copy and re-vendor. -->

# Ziggurat Creator Flywheel — System Integration Contract

> **Purpose:** The single reference all three data tools build against so they stay independently shippable *now* while becoming assemblable into one platform *later*. If a tool touches its inputs or outputs, it conforms to this doc. Disagreements between a tool and this doc are resolved in favour of this doc — or this doc is updated deliberately, never drifted from silently.
>
> **Scope this cycle:** standalone + system-aware, plus *one-directional handoffs* (scraper → sentiment). The feedback loop and platform convergence are next cycle, but every seam here is designed so that cycle is assembly, not rework.
>
> _Last updated: 2026-06-29 · Maintainer: Jack_

---

## 0. The three tools and how they relate

```
  ┌──────────────┐   comments CSV    ┌──────────────────┐
  │  Scraper     │ ────────────────▶ │  Sentiment       │
  │  (YouTube)   │                   │  (insight engine)│
  └──────────────┘                   └──────────────────┘
        │                                     │
        │ structured side-output              │ structured side-output
        ▼                                     ▼
  ╌╌╌╌╌╌╌╌╌╌╌╌╌╌ shared spine: client_slug · source_id · run metadata ╌╌╌╌╌╌╌╌╌╌╌╌

  ┌──────────────────┐
  │  Analytics       │  (Meta CSVs in → scored workbook out)
  │  engine          │  measurement half — not yet in the live handoff path
  └──────────────────┘
```

- **Scraper** produces raw audience signal.
- **Sentiment** turns signal into direction (what to build / deepen).
- **Analytics** measures whether what shipped performed.

This cycle wires **scraper → sentiment** only. Analytics stays standalone but becomes system-aware (emits the shared spine) so it can join the loop next cycle.

---

## 1. The shared spine (mandatory in every tool)

Three identifiers plus run metadata. Every tool stamps these onto everything it emits. This is the whole of "system-aware" — get these right and integration is joinable later by ID.

### 1.1 `client_slug`
The canonical creator/client identifier. **Already defined by the analytics engine config schema — adopt it verbatim, do not invent a parallel scheme.**

- lowercase, no spaces, no hyphens between words
- examples: `chefsteps`, `xyla`, `chrisyoung`, `jameshoffmann`, `ninjon`, `tomscott`, `stevemould`, `bobbyduke`, `thoughty2`, `chateaudiaries`, `primalspace`
- the canonical registry of slugs is the set of config files in `ziggurat-analytics-engine/configs/`. If a slug isn't there yet, the analytics config is the source of truth that defines it.

> **Naming rule (from the analytics cowork context):** "Chris Young" → `chrisyoung`, "Bobby Duke" → `bobbyduke`. Multi-word names collapse to one lowercase token.

### 1.2 `source_id`
A platform-prefixed identifier for the *piece of content* a signal attaches to. This is what lets a comment, a sentiment finding, and a performance row all point at the same thing.

**Format:** `<platform>:<native_id>`

| Platform | Prefix | Native ID | Example |
|---|---|---|---|
| YouTube | `yt:` | 11-char video ID | `yt:dQw4w9WgXcQ` |
| Instagram | `ig:` | Meta post ID | `ig:17912345678901234` |
| Facebook | `fb:` | Meta post ID | `fb:1234567890_9876543210` |
| Stories | `st:` | Meta story/media ID | `st:17998765432101234` |

**Reserved for next cycle (do not use yet, but the namespace is claimed so the feedback loop has somewhere to plug in):**

| Domain | Prefix | Meaning |
|---|---|---|
| Email/nurture | `kit:` | a Kit sequence or email (Ninjon, ChefSteps) |
| Owned-audience event | `acct:` | account signup / conversion event on a `.com` |
| Product | `prod:` | a product/SKU (Deck of Many Colors, Combustion, Studio Pass) |

Rules:
- Always keep the **raw native ID** as a separate field too (`video_id`, `post_id`) — the prefixed `source_id` is additive, never a replacement. Standalone use never depends on the prefix.
- A single artifact may carry **multiple** `source_id`s (e.g. a sentiment report built from three videos).

### 1.3 Run metadata
Every emitted artifact carries:

```json
{
  "run_id": "string — unique per run (uuid or tool-prefixed timestamp, e.g. scrape-20260629T1432Z)",
  "generated_at": "ISO-8601 UTC, e.g. 2026-06-29T14:32:00Z",
  "tool": "scraper | sentiment | analytics",
  "tool_version": "semver-ish string, e.g. 1.2.0",
  "client_slug": "chrisyoung",
  "source_ids": ["yt:dQw4w9WgXcQ"]
}
```

This block is the same shape in all three tools. Call it the **`provenance`** block everywhere.

---

## 2. The output convention (mandatory)

**Every tool emits two things: the human artifact it already produces, AND a machine-readable structured side-output carrying the provenance block.**

| Tool | Human artifact (unchanged) | New structured side-output |
|---|---|---|
| Scraper | threaded JSON download | *(already structured — just add `provenance`)* |
| Sentiment | Markdown report | `*.summary.json` (themes/questions/pain points + provenance) |
| Analytics | scored `.xlsx` workbook | `*.run.json` (per-post scores by `source_id` + provenance) |

The human artifact is what people read and is never compromised for the machine one. The structured side-output is what the future platform reads without re-parsing prose or spreadsheets.

---

## 3. The scraper → sentiment handoff (the one live link this cycle)

This is the only automated handoff being built now. It has to be exact, because a wrong column shape here means reshaping by hand every time — which defeats the point.

### 3.1 Canonical comments CSV (the interchange format)

The scraper gains a "flatten to CSV" export. The sentiment engine accepts **either** this CSV **or** the scraper's native JSON. The CSV is the contract; these columns, these names, this order:

| Column | Type | Notes |
|---|---|---|
| `client_slug` | string | from the scrape's provenance; may be blank if scraped standalone |
| `source_id` | string | `yt:VIDEO_ID` — same on every row of a single-video scrape |
| `comment_id` | string | native YouTube comment ID |
| `parent_id` | string | empty for top-level; the parent `comment_id` for replies |
| `author` | string | |
| `text` | string | the comment body; newlines escaped, not stripped |
| `likes` | integer | |
| `published_at` | ISO-8601 | |
| `is_reply` | boolean | `true`/`false` — convenience flag derived from `parent_id` |

Rules:
- One row per comment **and** per reply (the thread is flattened; `parent_id` preserves structure).
- The scraper's existing threaded JSON (`comments[].replies[]`, per §7 of the scraper context) maps onto this losslessly: top-level comment → row with empty `parent_id`; each reply → row with `parent_id` = the top-level `comment_id`.
- UTF-8, quoted fields, header row required.

### 3.2 What the sentiment engine guarantees back
- It reads `source_id` and `client_slug` straight from the CSV into its own provenance block — so its report is automatically traceable to the exact video(s) and client without anyone re-typing anything.
- If `client_slug` is blank (standalone scrape), the sentiment run prompts for / accepts one. Standalone never breaks; it just asks.

---

## 4. The sentiment structured side-output

The Markdown report stays exactly as specced in the task briefs (that's the human deliverable). Alongside it, emit `<report-name>.summary.json`:

```json
{
  "provenance": { "...": "the block from §1.3" },
  "purpose": "course-development | content-ideation | ip-development | qa-mining",
  "themes": [
    { "name": "Grind consistency", "prominence": "strong|moderate|weak", "source_ids": ["yt:..."] }
  ],
  "question_clusters": [
    { "name": "What basket for my machine?", "covered_in_source": "fully|partly|not", "course_relevance": "module|section|demo" }
  ],
  "pain_points": [
    { "name": "Flow rate changed unexplained", "prominence": "strong", "course_response": "demonstration" }
  ],
  "gaps": [
    { "name": "Pressurised baskets barely covered", "opportunity": "course-only content" }
  ]
}
```

This is deliberately lightweight — it is *not* the report, it's the report's findings made queryable so the platform can later join a theme against that content's analytics performance. The `purpose` field is what makes sentiment one configurable engine rather than several tools (see §6).

---

## 5. The analytics structured side-output

Engine internals are verified against a real ChefSteps deliverable — **do not edit them**. This is purely an additional emission alongside the workbook: `<output-name>.run.json`:

```json
{
  "provenance": { "...": "the block from §1.3" },
  "platforms": ["instagram", "facebook", "stories"],
  "posts": [
    { "source_id": "ig:179...", "total_score": 42, "rank": 3, "cta_detected": "TriggerWord|LinkInBio|LinkInComments|None" }
  ]
}
```

Keying every scored post by `source_id` is what lets next cycle ask: *"the post that came from the theme sentiment flagged — how did it actually rank?"* That join is the feedback loop. Reserving it now costs one extra file write.

---

## 6. The one open design decision this contract assumes

**Sentiment is ONE configurable engine, not several task-types.** The `purpose` field in §4 carries the difference between Hoffmann's "develop a course," Ninjon's "find the biggest comment bucket," and Chris Young's "what backstories do comments want." This mirrors the pattern the analytics engine already proved (stable core + per-client config), which lowers build risk.

Consequence: the two existing Hoffmann prompt files (`james-hoffmann-course-sentiment-analysis-task.md` and `HOF_Comment_Analysis_Prompt.md`) collapse into **one engine + a Hoffmann/course-development config**, the same way `chefsteps-analytics-config.md` configures the analytics engine. If you reject this and want genuinely separate tools, §4's `purpose` field and the single-engine assumption need revisiting before building.

---

## 7. What each tool must do to conform (checklist)

**Scraper**
- [ ] Add optional `client_slug` input (UI + API)
- [ ] Add `source_id` (`yt:<video_id>`) to output; keep raw `video_id`
- [ ] Add `provenance` block to the JSON
- [ ] Add "flatten to CSV" export matching §3.1 exactly

**Sentiment**
- [ ] Generalise to one engine + `purpose` config (collapse the two Hoffmann files)
- [ ] Accept the §3.1 CSV *or* the scraper's native JSON as input
- [ ] Keep the Markdown report unchanged
- [ ] Emit the `.summary.json` side-output (§4)

**Analytics**
- [ ] No engine-internal changes
- [ ] Add `source_id` prefixes to the post identifiers it already reads
- [ ] Emit the `.run.json` side-output (§5)
- [ ] Confirm `client_slug` registry = the `configs/` folder

---

## 8. What is explicitly NOT in this cycle
- Live sentiment → analytics or analytics → ideation connections (feedback loop)
- The owned-audience/product measurement (`kit:`, `acct:`, `prod:` namespaces are reserved but unused)
- Platform convergence / shared datastore
- YouTube *performance* analytics (YouTube stays "signal only" this cycle unless decided otherwise — see the asymmetry note in the build plan)

These are deferred by choice, not oversight. The spine in §1 is what makes picking them up later cheap.
