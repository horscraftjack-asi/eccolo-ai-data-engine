---
type: analytics-config
schema_version: 1.0
client: James Hoffmann
maintained_by: NaaShika / Ziggurat
update_cadence: Quarterly, or after course launches or significant strategy changes
updated: 2026-06-29
---

# James Hoffmann Analytics Config

*Strategic intelligence + detection rules for the monthly analytics engine. Conforms to
client-config-TEMPLATE schema 1.0. Read in full before writing any insight.*

---

## 1. Identity

```yaml
client_name: Hoffmann
client_slug: jameshoffmann
brand_accent_hex: #2C2C2C
output_filename: Hoffmann_[MonthYear]_Performance.xlsx
platforms_active: [instagram, facebook]
```

*Note: brand_accent_hex is a working estimate (Hoffmann's aesthetic is clean/minimal). Confirm with NaaShika.*

---

## 2. Brand & audience

**Who the client is:** James Hoffmann is the world's leading coffee educator — author of *The World
Atlas of Coffee*, World Barista Champion, and co-founder of Square Mile Coffee Roasters. His YouTube
channel is the primary vehicle for deep-dive coffee education, built on an honest, curious, and
enthusiastic voice that takes the topic seriously while not taking himself too seriously. His
authority comes from deep knowledge, careful word choice, and a visible commitment to truth over
trend.

**Brand voice:** Honest, curious, and enthusiastic — expert without arrogance, passionate without
performance. He takes himself lightly but coffee seriously. Writing feels like conversation with a
very knowledgeable friend who wants to share genuine discovery, not demonstrate status.

**The audience:** Coffee enthusiasts ranging from engaged home brewers to working baristas. They
value accurate, specific information over aspirational lifestyle content. They respond to content
that reveals *why* something works, tests received wisdom, or explores an unexpected corner of
coffee knowledge. They are sceptical of hype and reward intellectual honesty.

**What they sell:** Online courses (e.g. *How to Make Great Espresso*), hosted at his website.
YouTube channel drives awareness and trust. Patreon provides a direct support and community layer
for his most engaged audience (~ongoing). Books available through retail.

---

## 3. Strategy & funnel

**What social is for:** Social is the attention and trust layer that feeds YouTube, which in turn
drives course and Patreon consideration. The funnel is:

**Attention (social) → YouTube video → Course/Patreon consideration → Purchase/subscription**

Social content should demonstrate James's specific analytical voice and the quality of his
educational approach — enough to make the audience want more. The job is trust-building and
curiosity-triggering, not direct conversion.

**The conversion mechanic:** Link in bio is the primary CTA — directing audiences to YouTube,
courses, or Patreon as appropriate to the content context. There is no comment-trigger / auto-DM
mechanic in use. Posts with no CTA are pure awareness plays, appropriate for brand building but
not funnel-driving.

---

## 4. Platform roles

### Instagram
- **Primary function:** Brand awareness, audience deepening, curiosity-triggering. Drive the
  most engaged followers toward YouTube and, from there, toward courses and Patreon.
- **What good looks like:** Saves above 200 = content the audience wants to return to (deep
  educational value) · Shares above 75 = broad appeal beyond existing followers · Comments above
  30 = genuine intellectual engagement · Follows gained on educational content = funnel building.
- **Format expectations:** Reels drive discovery (views, reach, follows) · Carousels work for
  multi-step explanations, comparisons, and technique content · Static images can anchor a single
  striking fact or finding.
- **What to flag as underperformance:** Educational content with low saves (content not sticky
  enough, or hook unclear) · No-CTA posts as a sustained pattern (missed traffic to YouTube or
  courses) · Any content that reads as generic lifestyle coffee content rather than James-
  specific insight.

### Facebook
- **Primary function:** Reach and awareness. Not a primary conversion channel. Facebook is a
  supplementary surface; hold to Facebook norms, not Instagram benchmarks.
- **What good looks like:** Views above 8,000 = strong for this platform and audience size ·
  Reactions above 60 = meaningful engagement · Link clicks above 15 = active traffic driving.
- **Format expectations:** Video/Reel consistently outperforms photo content · Photo posts have
  a secondary visibility role but should not be expected to match video on engagement or reach.
- **What to flag:** Sustained low link clicks (audience not being directed actively) ·
  Photo/Carousel significantly underperforming video across all metrics (format shift signal).

---

## 5. Detection rules

### 5a. CTA detection

**Instagram:**
| Column | Logic |
|---|---|
| Trigger Word | Extract the first ALL-CAPS word (2+ letters) following "Comment"/"comment" in the description. Show the word literally. Blank if none. *Note: Hoffmann does not currently use the comment-trigger mechanic — this column will typically be blank.* |
| Link in Bio | ✓ if description contains "link in bio", "linktree", or "link in our bio" (case-insensitive). Else blank. |
| No CTA | ✓ if both Trigger Word and Link in Bio are blank. Else blank. |

**Facebook:**
| Column | Logic |
|---|---|
| Link in Comments | ✓ if the word "comment" appears anywhere in Title or Description (case-insensitive). Else blank. |

### 5b. Special content types

```yaml
special_content: []
```

*No special content types in use. Standard feed scoring applies to all posts.*

---

## 6. Metrics to score

**Instagram (score these):** Views, Reach, Likes, Comments, Shares, Saves, Follows.

**Facebook (score these):** Views, Reach, Reactions, Comments, Shares, Total clicks, Link clicks.
- *Exclude:* `Reactions, comments and shares` — a lump sum of metrics already scored above.

---

## 7. Benchmarks

None yet — this month establishes the baseline.

*Update this section after the first monthly crunch with actual averages from the data.*

---

## 8. Metric strategic tiers

- **Tier 1 — highest strategic value:** Saves (IG — strongest intent signal for a knowledge-
  dense educational creator; this audience saves to return to) · Link clicks (FB — best proxy
  for course/YouTube/Patreon traffic) · Shares (both — organic reach into new audiences who
  trust the person sharing).
- **Tier 2 — important context:** Views (reach/top-of-funnel) · Reach (unique accounts) ·
  Likes/Reactions (passive engagement) · Follows (IG — new audience entering the funnel).
- **Tier 3 — supporting:** Comments (IG — engagement depth; the coffee audience engages in
  detail when content earns it) · Total clicks (FB) · Profile visits (IG — curiosity signal).

---

## 9. Insight patterns

**What Worked — always look for:**
- Did content that tests conventional wisdom or reveals a surprising finding outperform
  straightforward educational posts? This is Hoffmann's signature move — track it.
- Did posts demonstrating a method (vs. just describing one) drive higher saves and shares?
- Did any content with explicit course or Patreon CTA drive measurably more link clicks than
  generic link-in-bio posts?
- Did Reels/video dominate discovery metrics vs. static content?

**What Didn't Work — always look for:**
- Generic coffee lifestyle content (aesthetics, ambient shots) — if engagement is weak, flag
  as off-brand for this creator.
- No-CTA posts — always note as a missed course/YouTube/Patreon traffic opportunity.
- Posts that make a claim without showing the reasoning or test — flag as underperforming the
  brand voice (and likely underperforming in engagement).
- Duplicate posts or publishing errors — flag immediately.

**What We Do About It — standing recommendations to reassess each month:**
1. Is the link-in-bio CTA directing to the right destination for the content context? (Course
   launch → course page; YouTube video → YouTube; general → channel/Patreon.)
2. Is the content mix maintaining James's specific intellectual voice, or drifting toward
   generic coffee content? Flag drift.
3. Is Facebook video volume being maintained? Photo-heavy months will underperform structurally.
4. Are course launch periods reflected in CTA strategy — i.e., are posts actively directing to
   course pages when a launch is live?

---

## 10. Strategic phase

**Current phase — Ongoing course and Patreon ecosystem (2026):** James's primary revenue
vehicles are online courses and Patreon. Social feeds YouTube, which builds the trust and
audience size that makes course launches and Patreon growth possible. There is no single
imminent launch — this is a steady-state phase of audience deepening and course pipeline building.

**What this means for monthly insights:**
- Flag whether content is building the kind of trust and intellectual credibility that makes
  course launches viable.
- Track whether Follows are trending upward — audience growth is the long-term compound asset.
- Note whether any course is currently live or launching, and whether CTA strategy reflects that.
- Flag content that reads as generic coffee content rather than distinctly Hoffmann — the voice
  differentiation is the primary strategic asset.

**Upcoming phases (for context):**
- Course launches (timing TBC per NaaShika): when a new course is live, social should pivot
  to more explicit course CTAs and link-in-bio should point directly to the course page.
- Any Patreon membership pushes should be reflected in CTA usage and link-in-bio destination.

---

## 11. Glossary

- **Square Mile Coffee Roasters:** Coffee roastery co-founded by James Hoffmann. Relevant context
  for his authority and commercial background.
- **World Atlas of Coffee:** James's book — the most widely read English-language coffee reference.
  A credential anchor.
- **World Barista Champion:** James won the World Barista Championship in 2007. Credential anchor.
- **Patreon:** James's direct-support platform. Monthly subscribers get exclusive content and
  community access. A key revenue layer alongside courses.
- **No CTA post:** An Instagram post with neither a trigger word nor a link-in-bio prompt.
  Awareness only — does not move traffic to courses or Patreon.
- **NaaShika:** Ziggurat SMA lead for Hoffmann.

---

## Related Files
- [[analytics-engine-SKILL]]
- [[client-config-TEMPLATE]]
- [[clients]]
- [[Hoffmann TOV Guide]]

---
*Config schema 1.0 — runs against analytics-engine-SKILL v2.0.*
