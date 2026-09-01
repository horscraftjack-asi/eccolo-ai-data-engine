---
type: analytics-config
schema_version: 1.0
client: Thoughty2
maintained_by: Jack / Ziggurat
update_cadence: Quarterly, or immediately after the newsletter/Patreon/CTA direction is confirmed
updated: 2026-09-01
---

# Thoughty2 Analytics Config

*Strategic intelligence + detection rules for the monthly analytics engine. Conforms to
client-config-TEMPLATE schema 1.0. Read in full before writing any insight.*

---

## 1. Identity

```yaml
client_name: Thoughty2
client_slug: thoughty2
brand_accent_hex: #1A1A2E
output_filename: Thoughty2_[MonthYear]_Performance.xlsx
platforms_active: [instagram, facebook, youtube_shorts, youtube_longform]
```

*Note: brand_accent_hex is a placeholder (dark navy, no confirmed brand colour on file) — confirm
or replace. No config existed for this client before this run; no other slug was found elsewhere
in the Eccolo flywheel, so `thoughty2` is the canonical ID going forward. `youtube_shorts` added
after validating the actual Table data export — 22 of the 500 videos this period run ≤60s, so
Shorts is a real (if minor) part of the current mix, not just long-form.*

---

## 2. Brand & audience

**Who the client is:** Thoughty2 is Arran Lomas, a British YouTuber known as "the gatekeeper of
useless facts" — fast-paced, documentary-style long-form videos covering history, science,
unexplained mysteries, and pop-culture curiosities. His real asset is a multi-thousand-video
script and research archive that nobody else in this space has — the back-catalogue is the
moat, not any single video.

**Brand voice:** Curious, energetic, plain-spoken, a little cheeky — built for "did you know"
momentum rather than dry lecture. Confident narration, high information density per minute.

**The audience:** Broad, curiosity-driven viewers who want fascinating facts in digestible form —
the kind of person who wants "something to say down the pub." They binge long-form YouTube and
will engage with short-form as a discovery layer, but currently have no next step offered to them
anywhere in the funnel.

**What they sell:** Effectively nothing active right now — that is the core problem this phase is
solving. Patreon exists but looks dead. A book exists but its link is stale and disconnected from
current promotion. A board game is in development (pre-launch, timing tbc). No newsletter yet
(proposed). Primary income today is YouTube ad revenue; there is no direct-monetisation or
capture layer running on social at all.

---

## 3. Strategy & funnel

**What social is for:** Today, social is pure top-of-funnel reach with no capture — every video
ends and nothing catches anyone. The proposed fix (pending Arran's sign-off): make the archive
itself the connective tissue.

**Attention (YouTube / FB / IG) → Capture (cleaned Linktree + auto-DM trigger word) → Newsletter
(archive-repackaged nurture layer) → Patreon reactivation / board game pre-launch audience / book
revival**

**The conversion mechanic:** None live yet. Linktree currently has no clear CTA and includes a
dead book-promo link. The proposal on the table: auto-DM trigger words on comments (a literal,
specific keyword — not a generic phrase like "I'd love this," which converts far worse) paired
with a cleaned-up Linktree pointing to a single clear next step. Exact trigger word and Linktree
destination are undecided until Arran confirms direction. **Section 5a below reflects this
honestly — there is nothing to detect in this month's data because nothing has shipped yet.**

---

## 4. Platform roles

### YouTube (long-form)
- **Primary function:** The core asset and primary revenue driver (ad revenue). Also the natural
  home for whatever CTA/description-link strategy gets adopted once the funnel is wired up.
- **What good looks like:** None yet — this month establishes the baseline. Track Views, Watch
  time, Subscribers gained, Estimated revenue, Average view duration, Impressions CTR as the
  core health signals.
- **Format expectations:** Long-form only (videos run well beyond Shorts length in this export) —
  no Shorts data currently in scope.
- **What to flag as underperformance:** Any video with high Impressions but low CTR (thumbnail/
  title not converting curiosity into a click) · low Average view duration relative to total
  length (hook or pacing issue) · no description-level CTA on any video, consistent with the
  wider "zero capture" problem.

### YouTube (Shorts)
- **Primary function:** Minor discovery/reach surface — the large majority of output is long-form,
  Shorts are a small slice of this period's mix (22 of ~500 videos). Same "no capture" problem
  applies here as everywhere else.
- **What good looks like:** None yet — this month establishes the baseline.
- **Format expectations:** ≤60s cuts, same subject matter as the long-form archive.
- **What to flag as underperformance:** Same plumbing gap as long-form — no description CTA;
  also worth flagging if Shorts volume is too low to read reliably month to month.

### Facebook
- **Primary function:** Reach/awareness surface — a discovery layer for the archive, not currently
  a conversion channel of any kind.
- **What good looks like:** None yet — this month establishes the baseline.
- **Format expectations:** Content in this export is native video/Reel only — no static image
  posts currently in the mix.
- **What to flag as underperformance:** Total absence of any link-in-comments or CTA language
  (confirmed in this month's copy — zero CTA mentions found) · reach without a next step for the
  audience, which is the exact plumbing gap Arran needs to hear about.

### Instagram
- **Primary function:** Reach/awareness surface, same role as Facebook — pure top-of-funnel today.
- **What good looks like:** None yet — this month establishes the baseline.
- **Format expectations:** IG Reels only in this export.
- **What to flag as underperformance:** Same as Facebook — no CTA, no link-in-bio language, no
  capture mechanism detected anywhere in this month's copy.

---

## 5. Detection rules

### 5a. CTA detection

**No live conversion mechanic exists yet.** A scan of this month's Facebook and Instagram copy
found zero CTA language of any kind (no "link in bio," no "comment [word]," no Patreon/book
mentions) — this is the literal data evidence behind the "zero capture" framing for today's call.
The table below is a placeholder to activate the moment Arran confirms the trigger word and
Linktree destination; until then, expect every column to come back blank.

**Facebook & Instagram (once live):**
| Column | Logic |
|---|---|
| Trigger Word | Extract the literal ALL-CAPS keyword following "Comment"/"comment" in the description, once the auto-DM system is live. Blank until then. |
| Link in Bio/Linktree | ✓ if description contains "link in bio", "linktree", or similar (case-insensitive). Currently always blank. |
| No CTA | ✓ if both above are blank — expect this to be ✓ on effectively every post until the mechanic ships. |

### 5b. Special content types

```yaml
special_content: []
```

*None currently. If the board game pre-launch produces a distinct recurring content type (teaser
clips, reveal content), add a detection rule here once that phase starts.*

---

## 6. Metrics to score

**YouTube Long-form (score these):** Views, Watch time (hours), Subscribers, Estimated revenue (GBP), Impressions, Impressions CTR.
- *Exclude:* `Average view duration` — exported as HH:MM:SS text, not a rankable number. Read it
  qualitatively per-video (as a % of total Duration) rather than scoring it.

**YouTube Shorts (score these):** Views, Returning viewers, New viewers, Engaged views, Impressions, Impressions CTR, Stayed to watch (%), Subscribers, Likes, Shares, Comments added, Watch time (hours), Average percentage viewed (%).
- *Updated 2026-09-01 per Jack's steer — full 13-metric set matching the columns in his actual
  YouTube Studio Shorts export, superseding the earlier exclusion of Watch time/revenue (that
  assumed low Shorts volume; Jack confirmed these should be scored). Column names match his
  export literally: `Thumbnail impressions`/`Thumbnail click-through rate (%)` (YouTube's newer
  naming for these two) are normalised to `Impressions`/`Impressions CTR` by the engine.*
- *Exclude:* `Average view duration` (HH:MM:SS text) — not a rankable numeric column, same as
  long-form. `Average percentage viewed (%)` is the numeric completion-rate metric used instead.
- *Exclude:* `Estimated revenue (GBP)` — shown as a passthrough column, not scored (still
  negligible/unreliable at Shorts volume).

**Facebook (score these):** Views, Reach, Reactions, Comments, Shares, Total clicks, Other clicks.
- *Exclude:* `Reactions, comments and shares` — a lump sum of metrics already scored above.
- *Exclude:* `Negative feedback from users: Hide all/Hide` — too sparse this month to rank
  meaningfully; track qualitatively instead.

**Instagram (score these):** Views, Reach, Likes, Shares, Comments, Saves, Follows.

---

## 7. Benchmarks

None yet — this month establishes the baseline.

---

## 8. Metric strategic tiers

- **Tier 1 — highest strategic value:** Estimated revenue and Subscribers (YouTube — direct
  business outcome) · Saves (IG — bookmark-worthy content, the clearest pre-funnel intent signal
  available before any CTA exists) · Impressions CTR (YouTube — thumbnail/title effectiveness).
- **Tier 2 — important context:** Views and Watch time (YouTube — attention depth) · Reach and
  Views (FB/IG — top-of-funnel scale) · Shares (all platforms — organic spread).
- **Tier 3 — supporting:** Likes/Reactions (passive signal) · Comments (engagement depth, and the
  channel that the future auto-DM trigger will run through) · Total/Other clicks (FB).

---

## 9. Insight patterns

**What Worked — always look for:**
- Which YouTube titles/thumbnails produced the strongest Impressions CTR — this is the pattern
  worth handing back to Arran as evidence for what "curiosity hook" language works best.
- Which FB/IG clips generated disproportionate Reach or Shares relative to the account average —
  candidates for the kind of content the newsletter should be built from first.
- Any format (historical mystery, science, pop-culture) consistently outperforming others across
  platforms — this shapes what the archive-based newsletter should lead with.

**What Didn't Work — always look for:**
- Confirm, every month, that there is still no CTA/link-in-bio/comment-trigger language in the
  copy — this is the standing problem until the funnel work ships.
- High-reach posts with low downstream signal (saves/shares) — reach without stickiness.
- Any video with high Impressions but weak CTR — thumbnail/title not doing its job.

**What We Do About It — standing recommendations to reassess each month:**
1. Has the auto-DM trigger word / Linktree cleanup shipped yet? Flag every month until it has,
   then start populating Section 5a for real.
2. Is the newsletter live? Once it is, this becomes the primary lens for reading FB/IG performance
   — content should be evaluated partly on how well it seeds newsletter material.
3. Has Patreon activity moved at all (even directionally) since the reactivation conversation?
4. Is the board game pre-launch audience-building underway, and is any content flagged for it?

---

## 10. Strategic phase

**Current phase — Plumbing fix, pre-funnel (through today's steer call, July 2026):** The content
engine works — volume and quality are not the issue. The problem is that nothing captures the
audience anywhere: no CTA, a dead Patreon, a stale book link, and a Linktree with no clear next
step. The pitch on the table is to make the archive itself — via a short, curation-only
newsletter — the connective tissue between YouTube/FB/IG attention and Patreon reactivation, the
upcoming board game, and the book. Quick wins (Linktree cleanup, auto-DM trigger words) are
designed to ship immediately, independent of whether the bigger newsletter strategy is agreed.

**What this means for monthly insights:**
- Treat this month's numbers as the "before" baseline — the entire point of today's call is that
  none of this data reflects a working funnel yet.
- Flag the zero-CTA finding explicitly; it is the evidence base for the pitch, not just a data
  footnote.
- Once quick wins ship, next month's report should specifically track whether Trigger Word/Link
  in Bio activity appears at all.
- Do not benchmark against other clients' CTA/conversion metrics — there is nothing comparable
  yet for Thoughty2.

**Upcoming phases (for context):**
- **Quick wins live (timing tbc, pending sign-off):** Linktree cleanup + auto-DM trigger word.
  Section 5a should be activated the moment these ship.
- **Newsletter launch (timing tbc):** Archive-repackaged newsletter as nurture layer feeding
  Patreon, board game, and book.
- **Board game pre-launch (timing tbc):** May introduce a special content type (see 5b).

---

## 11. Glossary

- **Arran Lomas:** Thoughty2's real name — the creator behind the channel.
- **Francesco:** In the room alongside Arran for the archive-monetisation call; not a proxy —
  address Arran directly.
- **Joel / Siana:** Arran's management. Per standing agreement, no further Linktree/social changes
  ship until Arran (with Joel/Siana) confirms priorities and active channels.
- **The archive:** Arran's multi-thousand-video script/fact research back-catalogue — the core
  asset behind the proposed newsletter strategy.
- **The newsletter (proposed):** A short, email-native format repackaging existing archive
  material (e.g. "5 things to talk about at the pub this weekend"). Curation, not new production.
  Not yet live.
- **Quick wins:** Linktree cleanup (clear CTA, kill the dead book-promo link) and auto-DM trigger
  words on comments — both shippable immediately, independent of the wider newsletter strategy.
- **Zero capture:** The standing diagnosis for this account — high volume, high-quality content
  with no mechanism anywhere converting a viewer into anything (email, Patreon, community).

---

## Related Files
- [[analytics-engine-SKILL]]
- [[client-config-TEMPLATE]]

---
*Config schema 1.0 — runs against analytics-engine-SKILL v2.0.*
