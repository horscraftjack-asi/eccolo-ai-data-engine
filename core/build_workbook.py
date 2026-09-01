#!/usr/bin/env python3
"""
build_workbook.py — deterministic CSV -> scored .xlsx for Ziggurat's monthly data crunch.

Client-agnostic. Reads a [client]-analytics-config.md (schema 1.0) for everything client-specific:
identity, active platforms, CTA/trigger detection rules, metrics-to-score, exclusions, sparsity
rule, special-content split. The PROCEDURE (rank-order scoring, tab build, styling) is fixed and
identical for every client.

This is the deterministic half of the analytics-engine skill. The written insight tabs
(Footnotes & Insights, Summary & Strategy) are left as labelled shells for the model to fill.

Supported platforms:
  Meta:    facebook, instagram, stories
  YouTube: youtube  (auto-split into youtube_shorts ≤60s and youtube_longform >60s)
           Or upload pre-split: youtube_shorts, youtube_longform separately.

Usage:
  python build_workbook.py --config chefsteps-analytics-config.md \
      --ig instagram.csv --fb facebook.csv --stories stories.csv \
      --out /mnt/user-data/outputs/ [--month "May 2026"] [--validate-only]

  python build_workbook.py --config chrisyoung-analytics-config.md \
      --yt youtube_table_data.csv \
      --out /mnt/user-data/outputs/
"""

from __future__ import annotations
import argparse
import os
import re
import sys
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field

try:
    import pandas as pd
except ImportError:
    sys.exit("pandas required: pip install pandas --break-system-packages")


# Semver-ish tool version stamped into the §1.3 provenance block (contract §1.3). Bump when the
# emitted artifact shape changes. Mirrors TOOL_VERSION in the sibling sentiment repo (run.py).
TOOL_VERSION = "1.0.0"


class MissingColumns(Exception):
    """Raised when an expected Meta export column is absent — fail loud, never mis-score."""
    def __init__(self, detail: dict):
        self.detail = detail
        super().__init__(f"Missing columns: {detail}")


def build_provenance(client_slug: str, source_ids: list | None = None,
                     run_id: str | None = None) -> dict:
    """The System Integration Contract §1.3 provenance block, identical in shape across all three
    tools. `source_ids` stays [] here until Phase 2 derives a source_id per scored post."""
    return {
        "run_id": run_id or f"analytics-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool": "analytics",
        "tool_version": TOOL_VERSION,
        "client_slug": client_slug or None,
        "source_ids": source_ids or [],
    }


# ----------------------------------------------------------------------------------------------
# Styling spec — encoded from the ChefSteps skill Step 12. This is the contract the workbook build
# must honour so every client's report is structurally identical. brand_accent_hex is overlaid
# per-client from the config (the one styling value that varies).
# ----------------------------------------------------------------------------------------------
STYLE = {
    "font": "Arial",
    "rank1_fill": "1AAD4A", "rank1_text": "FFFFFF",
    "top_fill": "D6F0D6", "bottom_fill": "FFD6D6", "bottom_text": "8B0000",
    "alt_row": "FAF9F7", "white": "FFFFFF",
    "score_bg": "FFF3F0", "total_score_bg": "FFE8E4",
    "footnote_label_bg": "EFE9E4", "caption_bg": "F0F4F8",
    "trigger_text": "2A4A44", "trigger_bg": "D6F0D6", "trigger_blank_bg": "FAFAFA",
    "header_text": "FFFFFF",
    "header_bgs": ["2C2C2C", "2A4A44", "8B2020", "3D4B55", "2C4A8C", "5C3D2E"],
    "stories_divider": "5B3A7A",
    "border": "D0D0D0",
    "widths": {  # column-type -> width, from Step 12
        "num": 4, "title": 46, "format": 14, "cta": 13, "date": 14,
        "raw": 11, "score": 9, "total_score": 12, "rank": 11,
        "note": 42, "permalink": 30, "caption": 3,
    },
    "top_n": 5, "bottom_n": 5,            # feed tabs
    "stories_top_n": 10, "stories_bottom_n": 10,
}

PLATFORM_FINGERPRINTS = {  # column unique to each platform, for auto-mapping an unlabelled CSV
    "facebook":  {"Reactions", "Total clicks", "Link clicks"},
    "instagram": {"Likes", "Saves", "Follows"},
    "stories":   {"Profile visits", "Navigation"},
    # YouTube fingerprint matched AFTER normalize_youtube() renames columns
    "youtube":   {"Watch time (hours)", "Impressions CTR", "Subscribers"},
}

# --------------------------------------------------------------------------------------------------
# YouTube Studio — column normalisation
# YouTube Studio's "Table data" CSV export (Content > Analytics > Advanced mode > Export)
# uses human-readable column names. This map renames them to engine-friendly keys.
# --------------------------------------------------------------------------------------------------
YT_COLUMN_MAP = {
    "Content":                              "Video ID",
    "Video publish time":                   "Publish time",
    "Impressions click-through rate (%)":   "Impressions CTR",
    # YouTube Studio renamed these two columns at some point ("Impressions" -> "Thumbnail
    # impressions", "Impressions click-through rate (%)" -> "Thumbnail click-through rate (%)").
    # Both naming generations show up across different clients' exports depending on when they
    # last re-selected columns in Advanced mode, so both are normalised to the same canonical
    # name the rest of the engine (fingerprinting, footnotes, config metric matching) expects.
    "Thumbnail impressions":                "Impressions",
    "Thumbnail click-through rate (%)":     "Impressions CTR",
    # These pass through unchanged:
    #   Video title, Duration, Views, Watch time (hours), Subscribers,
    #   Estimated revenue (USD), Likes, Shares, Comments added, New viewers,
    #   Returning viewers, Engaged views, Stayed to watch (%), Average percentage viewed (%)
}

YT_SHORTS_THRESHOLD = 60   # seconds — videos ≤ this are classified as Shorts


def normalize_youtube(df: pd.DataFrame) -> pd.DataFrame:
    """Rename YouTube Studio export columns, strip the aggregate Total row, build Permalink."""
    df = df.rename(columns={k: v for k, v in YT_COLUMN_MAP.items() if k in df.columns})
    # Strip summary row — YouTube Studio inserts a grand-total row with Content/Video ID == "Total"
    id_col = "Video ID" if "Video ID" in df.columns else None
    if id_col:
        df = df[df[id_col].fillna("") != "Total"].copy()
    df = df.dropna(subset=["Video title"] if "Video title" in df.columns else []).copy()
    # Construct clickable permalink from the video ID
    if "Video ID" in df.columns:
        df["Permalink"] = df["Video ID"].apply(
            lambda v: f"https://youtube.com/watch?v={v}" if pd.notna(v) else "")
    return df.reset_index(drop=True)


def filter_youtube_to_month(df: pd.DataFrame, month: str) -> tuple[pd.DataFrame, int]:
    """Keep only videos actually PUBLISHED in the report month.

    YouTube Studio's Table data export lists every video with any activity in the selected
    date range, not just videos published in it — an evergreen Short from a year ago with a
    fresh view spike shows up alongside this month's new uploads. Meta exports don't have this
    problem (the client scopes those to the report period before export), so left unfiltered,
    YouTube results skew toward old high-lifetime-total videos instead of reflecting this
    month's actual output. Returns (filtered_df, n_excluded).
    """
    if "Publish time" not in df.columns or not len(df):
        return df, 0
    target = pd.Period(pd.to_datetime(month, errors="coerce"), freq="M") if month else None
    if target is None or pd.isna(target):
        return df, 0
    pub = pd.to_datetime(df["Publish time"], errors="coerce")
    mask = pub.dt.to_period("M") == target
    filtered = df[mask].copy().reset_index(drop=True)
    return filtered, len(df) - len(filtered)


def split_youtube_by_duration(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a combined YouTube export into Shorts (≤60 s) and long-form (>60 s).

    Returns (shorts_df, longform_df). Either may be empty if no videos fall in that bucket.
    If Duration column is absent, everything lands in longform with a note.
    """
    if "Duration" not in df.columns:
        return pd.DataFrame(columns=df.columns), df.copy()
    dur = pd.to_numeric(df["Duration"], errors="coerce").fillna(0)
    mask = dur <= YT_SHORTS_THRESHOLD
    return df[mask].copy().reset_index(drop=True), df[~mask].copy().reset_index(drop=True)


# ----------------------------------------------------------------------------------------------
# Config parsing
# ----------------------------------------------------------------------------------------------
@dataclass
class Config:
    raw: str
    client_name: str = ""
    client_slug: str = ""
    brand_accent_hex: str = "2A4A44"
    output_filename: str = ""
    platforms_active: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)        # platform -> [metric cols to score]
    excludes: dict = field(default_factory=dict)       # platform -> [cols to never score]
    sparsity_threshold: float = 0.15
    ig_trigger_anchor: str = "Comment"                 # word the trigger follows
    ig_link_in_bio_phrases: list = field(default_factory=lambda: ["link in bio", "linktree", "link in our bio"])
    fb_link_in_comments_token: str = "comment"
    special_content: list = field(default_factory=list)  # list of dicts: name, platform, phrases, handling


def _yaml_block(text: str, after_heading: str) -> str:
    """Pull the first ```yaml ... ``` fence appearing under a given heading.

    Tolerant of section-number prefixes between the hashes and the keyword, e.g.
    `### 5b. Special content types` or `## 1. Identity` — the engine reads configs by
    heading keyword, and the template numbers its sections, so the matcher must skip a
    leading `<num><letter>.` token before the keyword it's looking for.
    """
    h = re.search(rf"^#+\s*(?:[\w]+\.\s*)?{re.escape(after_heading)}.*?$", text, re.M | re.I)
    if not h:
        return ""  # heading genuinely absent — return empty, never silently grab a different fence
    m = re.search(r"```ya?ml\s*(.*?)```", text[h.end():], re.S)
    return m.group(1) if m else ""


def _scalar(yaml_text: str, key: str, default: str = "") -> str:
    m = re.search(rf"^{re.escape(key)}\s*:\s*(.+?)\s*$", yaml_text, re.M)
    if not m:
        return default
    return m.group(1).strip().strip("#").strip().strip("'\"")
    # note: strip("#") handles hex values written bare like `#FC684E` in the config


def _hex(yaml_text: str, key: str, default: str) -> str:
    m = re.search(rf"^{re.escape(key)}\s*:\s*#?([0-9A-Fa-f]{{6}})", yaml_text, re.M)
    return m.group(1).upper() if m else default


def _list_inline(yaml_text: str, key: str) -> list:
    m = re.search(rf"^{re.escape(key)}\s*:\s*\[(.*?)\]", yaml_text, re.M)
    if not m:
        return []
    return [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()]


def parse_config(path: str) -> Config:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    cfg = Config(raw=text)

    ident = _yaml_block(text, "Identity")
    cfg.client_name = _scalar(ident, "client_name") or "Client"
    cfg.client_slug = _scalar(ident, "client_slug") or cfg.client_name.lower().replace(" ", "")
    cfg.brand_accent_hex = _hex(ident, "brand_accent_hex", "2A4A44")
    cfg.output_filename = _scalar(ident, "output_filename") or f"{cfg.client_name}_[MonthYear]_Performance.xlsx"
    cfg.platforms_active = _list_inline(ident, "platforms_active")

    # Metrics to score: parsed from §6 prose lines "**Platform (score these):** a, b, c".
    for plat, label in [
        ("instagram",        "Instagram"),
        ("facebook",         "Facebook"),
        ("stories",          "Stories"),
        ("youtube_shorts",   "YouTube Shorts"),
        ("youtube_longform", "YouTube Long-form"),
    ]:
        m = re.search(rf"\*\*{re.escape(label)}\s*\(score these\):\*\*\s*(.+)", text)
        if m:
            cfg.metrics[plat] = [x.strip().strip("`.") for x in re.split(r"[,.]", m.group(1)) if x.strip()]
    # Exclusions are noted in prose; the well-known ones are encoded as defaults the build applies.
    cfg.excludes = {
        "facebook": ["Reactions, comments and shares"],
        "stories": ["Navigation"],
    }

    # Special content (§5b yaml). Parse name/platform/phrases per entry.
    sc_block = _yaml_block(text, "Special content")
    if sc_block and "None" not in sc_block:
        for entry in re.split(r"-\s*name:", sc_block)[1:]:
            name = re.match(r"\s*(.+)", entry).group(1).strip().strip("'\"")
            plat = (re.search(r"platform:\s*(\w+)", entry) or [None, "instagram"])[1]
            phrases = re.findall(r'"([^"]+)"', entry)
            cfg.special_content.append({"name": name, "platform": plat, "phrases": phrases})
    return cfg


# ----------------------------------------------------------------------------------------------
# Platform detection + column validation
# ----------------------------------------------------------------------------------------------
def detect_platform(df: pd.DataFrame) -> str | None:
    cols = set(df.columns)
    for plat, fp in PLATFORM_FINGERPRINTS.items():
        if fp & cols == fp:
            return plat
    return None


YOUTUBE_PLATFORMS = ("youtube_shorts", "youtube_longform")


def structural_columns(platform: str) -> set:
    """Columns whose absence means the WRONG FILE was uploaded (not a missing metric).

    These always fail the build loud — degrading gracefully over them would silently
    process a file that isn't what it claims to be.
    """
    if platform in YOUTUBE_PLATFORMS:
        # YouTube exports have no Description or Post type — just title, publish time, duration
        return {"Video title", "Publish time", "Duration"}
    needed = {"Description", "Permalink", "Publish time"}
    if platform != "stories":
        needed |= {"Post type"}
    return needed


def split_missing(df: pd.DataFrame, platform: str, cfg: Config) -> tuple[list, list]:
    """Return (missing_structural, missing_metrics) for a platform's dataframe.

    Structural = wrong-file columns (always fatal). Metrics = scored columns declared in
    the config; on YouTube these degrade gracefully (skip + warn) rather than failing.
    """
    have = set(df.columns)
    missing_structural = sorted(structural_columns(platform) - have)
    missing_metrics = sorted(set(cfg.metrics.get(platform, [])) - have)
    return missing_structural, missing_metrics


def validate_columns(df: pd.DataFrame, platform: str, cfg: Config) -> list:
    """Return the sorted union of expected-but-missing columns; empty list = OK."""
    missing_structural, missing_metrics = split_missing(df, platform, cfg)
    return sorted(set(missing_structural) | set(missing_metrics))


# ----------------------------------------------------------------------------------------------
# CTA / trigger detection — read literally from config rules (the one part executed, not interpreted)
# ----------------------------------------------------------------------------------------------
def ig_trigger_word(desc: str, anchor: str = "Comment") -> str:
    if not isinstance(desc, str):
        return ""
    m = re.search(rf"{anchor}\s+([A-Z]{{2,}})", desc, re.I)
    if not m:
        return ""
    # first ALL-CAPS word (2+ letters) following the anchor
    m2 = re.search(rf"{anchor}\s+\b([A-Z]{{2,}})\b", desc)
    return m2.group(1) if m2 else ""


def ig_link_in_bio(desc: str, phrases: list) -> bool:
    d = (desc or "").lower()
    return any(p in d for p in phrases)


def fb_link_in_comments(title: str, desc: str, token: str) -> bool:
    blob = f"{title or ''} {desc or ''}".lower()
    return token in blob


def is_special(desc: str, phrases: list) -> bool:
    d = desc or ""
    return any(p in d for p in phrases)


# ----------------------------------------------------------------------------------------------
# Cross-platform leaderboard — used by the web UI's result screen. Built from the SAME scored
# tables the workbook tabs use, so "top performer" always matches what's in the .xlsx.
# ----------------------------------------------------------------------------------------------
def _platform_tag(platform: str, post_type) -> str:
    pt = str(post_type or "").strip()
    if platform == "instagram":
        return f"IG {pt.split()[-1].upper()}" if pt else "IG POST"
    if platform == "facebook":
        return f"FB {pt.upper()}" if pt else "FB POST"
    if platform == "stories":
        return "STORY"
    if platform == "youtube_shorts":
        return "YT SHORT"
    if platform == "youtube_longform":
        return "YT LONG"
    return platform.upper()


def top_posts(tables: dict, limit: int = 4) -> list:
    """Combine every scored table into one cross-platform leaderboard by Total Score."""
    rows = []
    for plat in ("facebook", "instagram", "stories", "youtube_shorts", "youtube_longform"):
        df = tables.get(plat)
        if df is None or not len(df):
            continue
        for _, r in df.iterrows():
            title = r.get("Video title") or r.get("Title") or r.get("Description") or ""
            views = pd.to_numeric(r.get("Views"), errors="coerce")
            rows.append({
                "platform": plat,
                "tag": _platform_tag(plat, r.get("Post type")),
                "title": str(title).strip()[:140],
                "score": int(r.get("Total Score", 0)),
                "views": None if pd.isna(views) else float(views),
                "permalink": r.get("Permalink") or "",
            })
    rows.sort(key=lambda x: x["score"], reverse=True)
    return rows[:limit]


# ----------------------------------------------------------------------------------------------
# Rank-order scoring — standard competition ranking, ties share rank, sum across metrics
# ----------------------------------------------------------------------------------------------
def score_posts(df: pd.DataFrame, metrics: list, sparsity: float) -> pd.DataFrame:
    df = df.copy()
    scored_metrics = []
    for met in metrics:
        if met not in df.columns:
            continue
        col = pd.to_numeric(df[met], errors="coerce").fillna(0)
        # sparsity rule: drop a metric where <threshold of rows are non-zero
        if (col != 0).mean() < sparsity:
            continue
        # rank 1 = lowest raw value, N = highest (so higher metric -> higher score)
        df[f"Score: {met}"] = col.rank(method="min").astype(int)
        scored_metrics.append(met)
    score_cols = [f"Score: {m}" for m in scored_metrics]
    df["Total Score"] = df[score_cols].sum(axis=1).astype(int)
    df["Overall Rank"] = df["Total Score"].rank(method="min", ascending=False).astype(int)
    # Sort by rank, breaking Total-Score ties by older-date-first so the order is deterministic
    # and reproducible run to run (otherwise tied posts fall in arbitrary input order).
    if "Publish time" in df.columns:
        df["_pub"] = pd.to_datetime(df["Publish time"], errors="coerce")
        df = df.sort_values(["Overall Rank", "_pub"], ascending=[True, True]).drop(columns="_pub").reset_index(drop=True)
    else:
        df = df.sort_values("Overall Rank").reset_index(drop=True)
    return df


# ----------------------------------------------------------------------------------------------
# Contract §5 structured side-output (.run.json) — an ADDITIONAL emission alongside the workbook.
# Reads only the already-scored tables; never mutates them (§5 red line: engine internals are
# verified against a real ChefSteps deliverable — do not edit). source_id is derived per §1.2.
# ----------------------------------------------------------------------------------------------
STANDARD_PLATFORMS = ("facebook", "instagram", "stories", "youtube_shorts", "youtube_longform")
_META_PREFIX = {"instagram": "ig", "facebook": "fb", "stories": "st"}
# Meta exports vary; try a dedicated post-ID column first (real exports may carry one), then fall
# back to the Permalink. None of the bundled fixtures carry an ID column — Permalink is the norm.
_POST_ID_COLS = ("Post ID", "Post Id", "post_id", "Media ID", "Media Id", "Publish Id", "Content ID")
_YT_PERMALINK_RE = re.compile(r"[?&]v=([A-Za-z0-9_-]{11})")


def _val(v) -> str:
    """Coerce a cell to a clean string, treating NaN/None as empty."""
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    return str(v).strip()


def _native_id_from_permalink(url: str) -> str:
    """Last non-empty path segment of a permalink, e.g. instagram.com/p/ABC/ -> 'ABC'."""
    base = _val(url).split("?")[0].rstrip("/")
    if not base:
        return ""
    return base.rsplit("/", 1)[-1].strip()


def derive_source_id(platform: str, row) -> str:
    """Contract §1.2 `<platform>:<native_id>`. Returns '' when nothing is derivable (the caller
    counts these rather than failing the build). The raw ID columns stay untouched — the prefixed
    source_id is additive, never a replacement."""
    if platform in ("youtube_shorts", "youtube_longform"):
        vid = _val(row.get("Video ID"))
        if vid:
            return f"yt:{vid}"
        m = _YT_PERMALINK_RE.search(_val(row.get("Permalink")))
        return f"yt:{m.group(1)}" if m else ""
    prefix = _META_PREFIX.get(platform, "")
    if not prefix:
        return ""
    for col in _POST_ID_COLS:
        v = _val(row.get(col))
        if v:
            return f"{prefix}:{v}"
    token = _native_id_from_permalink(row.get("Permalink"))
    return f"{prefix}:{token}" if token else ""


def cta_detected(platform: str, row) -> str:
    """Map the already-computed CTA columns to the §5 enum
    (TriggerWord | LinkInBio | LinkInComments | None). One value per post."""
    if platform == "instagram":
        if _val(row.get("Trigger Word")):
            return "TriggerWord"
        if bool(row.get("Link in Bio")):
            return "LinkInBio"
        return "None"
    if platform == "facebook":
        if bool(row.get("Link in Comments")):
            return "LinkInComments"
        return "None"
    return "None"


def _platform_of_table(key: str, cfg: Config) -> str | None:
    """A scored table is either a standard platform or a special-content table (an IG sub-view)."""
    if key in STANDARD_PLATFORMS:
        return key
    for sc in cfg.special_content:
        if sc["name"] == key:
            return sc["platform"]
    return None


def build_run_json(tables: dict, cfg: Config, provenance: dict) -> tuple[dict, int]:
    """Assemble the contract §5 side-output from the scored tables. Returns (run_json, n_missing)
    where n_missing counts posts whose source_id could not be derived. `provenance` is embedded
    with its `source_ids` populated to the distinct non-empty source_ids across all scored tables."""
    posts = []
    platforms = []
    n_missing = 0
    for key, df in tables.items():
        if df is None or not len(df):
            continue
        platform = _platform_of_table(key, cfg)
        if platform is None:
            continue
        if platform not in platforms:
            platforms.append(platform)
        for _, row in df.iterrows():
            sid = derive_source_id(platform, row)
            if not sid:
                n_missing += 1
            posts.append({
                "source_id": sid,
                "total_score": int(row.get("Total Score", 0)),
                "rank": int(row.get("Overall Rank", 0)),
                "cta_detected": cta_detected(platform, row),
            })
    distinct = sorted({p["source_id"] for p in posts if p["source_id"]})
    provenance = {**provenance, "source_ids": distinct}
    return {"provenance": provenance, "platforms": sorted(platforms), "posts": posts}, n_missing


# ----------------------------------------------------------------------------------------------
# Workbook build — assembles all tabs in the standard order using core/tabs.py builders.
# ----------------------------------------------------------------------------------------------
def build_workbook(tables: dict, cfg: Config, month: str, out_dir: str, notes: list,
                   breakdown_frames: dict | None = None, insights: dict | None = None) -> str:
    """
    tables:           scored frames keyed "facebook" / "instagram" / "stories" / "<special name>"
    breakdown_frames: full IG/FB frames (pre-special-split) for the Footnotes breakdown tables
    insights:         optional pre-written insight content; if absent, insight sections are shells
    Builds the .xlsx in the uniform Ziggurat format. Returns the output path.
    """
    from openpyxl import Workbook
    try:
        from . import tabs
    except ImportError:
        import tabs  # direct-script invocation (CLI) where there's no parent package

    breakdown_frames = breakdown_frames or {}
    fname = cfg.output_filename.replace("[MonthYear]", month.replace(" ", ""))
    out_path = os.path.join(out_dir, fname)
    wb = Workbook()
    wb.remove(wb.active)

    # Standard tab order: Facebook, Instagram, [special: Trial Reels], Stories, Footnotes, Summary.
    if "facebook" in tables:
        tabs.build_feed_tab(wb, tables["facebook"], cfg, month, kind="facebook")
    if "instagram" in tables:
        tabs.build_feed_tab(wb, tables["instagram"], cfg, month, kind="instagram")

    # Special-content tabs (e.g. Trial Reels). If a configured type produced zero posts this
    # month, still emit the tab with the low-count note — the team expects the tab to exist.
    for sc in cfg.special_content:
        name = sc["name"]
        if name in tables and len(tables[name]):
            tabs.build_feed_tab(wb, tables[name], cfg, month, kind=sc["platform"],
                                title=f"{name} — {month}",
                                top_note=f"{name} are scored independently and excluded from the main Instagram performance data.")
        else:
            note = (f"0 {name} detected in {month}. No posts contained the trial-format copy markers."
                    if name.lower().startswith("trial")
                    else f"0 {name} detected in {month}.")
            tabs.build_empty_special_tab(wb, name, month, note)

    if "stories" in tables:
        tabs.build_stories_tab(wb, tables["stories"], cfg, month)

    # YouTube tabs — Shorts before Long-form so the team's focus content is first
    if "youtube_shorts" in tables:
        tabs.build_youtube_tab(wb, tables["youtube_shorts"], cfg, month, kind="youtube_shorts")
    if "youtube_longform" in tables:
        tabs.build_youtube_tab(wb, tables["youtube_longform"], cfg, month, kind="youtube_longform")

    extra = []
    n_special = sum(len(tables.get(sc["name"], [])) for sc in cfg.special_content)
    extra.append(f"{n_special} {cfg.special_content[0]['name'] if cfg.special_content else 'special'} detected this month."
                 if cfg.special_content else "")
    extra.append("Stories CSV present." if "stories" in tables else "No Stories CSV this month.")

    tabs.build_footnotes(wb, cfg, month,
                         ig_df=breakdown_frames.get("instagram"),
                         fb_df=breakdown_frames.get("facebook"),
                         st_df=tables.get("stories"),
                         yt_shorts_df=tables.get("youtube_shorts"),
                         yt_longform_df=tables.get("youtube_longform"),
                         insights=insights)
    tabs.build_summary(wb, cfg, month,
                       ig_df=breakdown_frames.get("instagram"),
                       fb_df=breakdown_frames.get("facebook"),
                       st_df=tables.get("stories"),
                       yt_shorts_df=tables.get("youtube_shorts"),
                       yt_longform_df=tables.get("youtube_longform"),
                       insights=insights,
                       extra_note="Note: " + " ".join(x for x in extra if x))

    os.makedirs(out_dir, exist_ok=True)
    wb.save(out_path)
    return out_path


# ----------------------------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------------------------
def infer_month(dfs: list) -> str:
    """Infer the report month from the most recent publish date across all provided dataframes.
    Handles both Meta ISO timestamps and YouTube's 'Jun 13, 2026' format via pandas' flexible parser.
    """
    for df in dfs:
        col = next((c for c in ("Publish time",) if c in df.columns), None)
        if col:
            t = pd.to_datetime(df[col], errors="coerce").dropna()
            if len(t):
                return t.max().strftime("%B %Y")
    return "Unknown Month"


def run_build(config_path: str, csv_paths: dict, month: str | None = None,
              out_dir: str = ".", validate_only: bool = False) -> dict:
    """Shared orchestration used by BOTH the CLI and the web app — one source of truth.

    config_path: path to a [client]-analytics-config.md
    csv_paths:   {
                   "facebook": path, "instagram": path, "stories": path,  # Meta
                   "youtube": path,           # combined YT export — auto-split by Duration
                   "youtube_shorts": path,    # pre-split Shorts export (optional)
                   "youtube_longform": path,  # pre-split long-form export (optional)
                 }
                 Include only what you have. Meta and YouTube can be mixed freely.
    Returns a report dict. Raises MissingColumns if any expected column is absent.
    """
    cfg = parse_config(config_path)
    report = {"client": cfg.client_name, "platforms_active": cfg.platforms_active,
              "validation": {}, "notes": [],
              # Contract §1.3 spine — stamped once per run. source_ids populated in Phase 2.
              "provenance": build_provenance(cfg.client_slug, source_ids=[])}

    # --- Meta platforms ---
    dfs = {}
    for plat in ("facebook", "instagram", "stories"):
        path = csv_paths.get(plat)
        if not path:
            if plat in cfg.platforms_active:
                report["notes"].append(f"{plat}: in platforms_active but no CSV provided — tab skipped.")
            continue
        df = pd.read_csv(path)
        detected = detect_platform(df)
        if detected and detected != plat:
            report["notes"].append(f"WARNING: {plat} CSV looks like {detected} data (column fingerprint).")
        if plat not in cfg.platforms_active:
            report["notes"].append(f"WARNING: {plat} CSV provided but {plat} not in platforms_active.")
        missing_structural, missing_metrics = split_missing(df, plat, cfg)
        report["validation"][plat] = {
            "missing_columns": sorted(set(missing_structural) | set(missing_metrics)),
            "missing_structural": missing_structural,
            "missing_metrics": missing_metrics,
            "rows": len(df),
        }
        dfs[plat] = df

    # --- YouTube platform ---
    # Accept a combined export (auto-split by Duration) OR pre-split separate files.
    yt_shorts_df: pd.DataFrame | None = None
    yt_longform_df: pd.DataFrame | None = None

    yt_combined_path = csv_paths.get("youtube")
    yt_shorts_path   = csv_paths.get("youtube_shorts")
    yt_longform_path = csv_paths.get("youtube_longform")

    if yt_combined_path:
        raw = normalize_youtube(pd.read_csv(yt_combined_path))
        shorts, longform = split_youtube_by_duration(raw)
        if len(shorts):
            yt_shorts_df = shorts
            report["notes"].append(f"YouTube auto-split: {len(shorts)} Shorts (≤{YT_SHORTS_THRESHOLD}s).")
        if len(longform):
            yt_longform_df = longform
            report["notes"].append(f"YouTube auto-split: {len(longform)} long-form (>{YT_SHORTS_THRESHOLD}s).")
    else:
        if yt_shorts_path:
            yt_shorts_df = normalize_youtube(pd.read_csv(yt_shorts_path))
        if yt_longform_path:
            yt_longform_df = normalize_youtube(pd.read_csv(yt_longform_path))

    for plat, yt_df in (("youtube_shorts", yt_shorts_df), ("youtube_longform", yt_longform_df)):
        if yt_df is None or len(yt_df) == 0:
            continue
        missing_structural, missing_metrics = split_missing(yt_df, plat, cfg)
        report["validation"][plat] = {
            "missing_columns": sorted(set(missing_structural) | set(missing_metrics)),
            "missing_structural": missing_structural,
            "missing_metrics": missing_metrics,
            "rows": len(yt_df),
        }
        dfs[plat] = yt_df

    # --- Fail loud on missing columns ---
    # Meta platforms fail on ANY missing expected column — stable exports mean a gap almost
    # always signals a header rename we must not silently mis-score around.
    # YouTube exports legitimately vary column-to-column: a missing STRUCTURAL column still
    # fails (wrong file), but missing SCORED METRICS degrade gracefully — we score what's
    # present and surface a prominent note listing what was skipped.
    fatal = {}
    for plat, v in report["validation"].items():
        if plat in YOUTUBE_PLATFORMS:
            if v["missing_structural"]:
                fatal[plat] = v["missing_structural"]
            elif v["missing_metrics"]:
                label = "YouTube Shorts" if plat == "youtube_shorts" else "YouTube Long-form"
                report["notes"].append(
                    f"{label}: export was missing {len(v['missing_metrics'])} scored metric(s) — "
                    f"{', '.join(v['missing_metrics'])}. Scored the columns that were present and "
                    "skipped these. To include them, re-export via YouTube Studio → Advanced mode "
                    "with those columns visible.")
        elif v["missing_columns"]:
            fatal[plat] = v["missing_columns"]
    if fatal:
        raise MissingColumns(fatal)
    if validate_only:
        report["status"] = "validated"
        return report

    month = month or infer_month(list(dfs.values()))
    tables = {}

    # --- Score Meta ---
    if "instagram" in dfs:
        ig = dfs["instagram"]
        for sc in [s for s in cfg.special_content if s["platform"] == "instagram"]:
            mask = ig["Description"].apply(lambda d: is_special(d, sc["phrases"]))
            special_df = ig[mask]
            ig = ig[~mask]
            report["notes"].append(f"{len(special_df)} {sc['name']} excluded from main IG scoring.")
            if len(special_df):
                tables[sc["name"]] = score_posts(special_df, cfg.metrics.get("instagram", []), cfg.sparsity_threshold)
        ig = ig.copy()
        ig["Trigger Word"] = ig["Description"].apply(lambda d: ig_trigger_word(d, cfg.ig_trigger_anchor))
        ig["Link in Bio"] = ig["Description"].apply(lambda d: ig_link_in_bio(d, cfg.ig_link_in_bio_phrases))
        ig["No CTA"] = (ig["Trigger Word"] == "") & (~ig["Link in Bio"])
        tables["instagram"] = score_posts(ig, cfg.metrics.get("instagram", []), cfg.sparsity_threshold)

    if "facebook" in dfs:
        fb = dfs["facebook"].copy()
        fb["Link in Comments"] = fb.apply(
            lambda r: fb_link_in_comments(r.get("Title", ""), r.get("Description", ""), cfg.fb_link_in_comments_token),
            axis=1)
        tables["facebook"] = score_posts(fb, cfg.metrics.get("facebook", []), cfg.sparsity_threshold)

    if "stories" in dfs:
        tables["stories"] = score_posts(dfs["stories"].copy(), cfg.metrics.get("stories", []), cfg.sparsity_threshold)

    # --- Score YouTube ---
    for plat in ("youtube_shorts", "youtube_longform"):
        if plat in dfs:
            yt, n_excluded = filter_youtube_to_month(dfs[plat].copy(), month)
            if n_excluded:
                label = "YouTube Shorts" if plat == "youtube_shorts" else "YouTube Long-form"
                report["notes"].append(
                    f"{label}: excluded {n_excluded} video(s) published outside {month} "
                    "(evergreen videos with activity this month but published earlier/later) "
                    "to keep scoring scoped to this month's output, matching Meta.")
            tables[plat] = score_posts(yt, cfg.metrics.get(plat, []), cfg.sparsity_threshold)

    breakdown_frames = {"instagram": tables.get("instagram"), "facebook": tables.get("facebook")}

    try:
        try:
            from .insights import generate_insights
        except ImportError:
            from insights import generate_insights
        insights, insight_note = generate_insights(cfg, tables, month)
    except Exception as exc:
        insights, insight_note = None, f"Claude insights failed at import: {type(exc).__name__}: {exc}"
    report["notes"].append(insight_note)

    out_path = build_workbook(tables, cfg, month, out_dir, report["notes"],
                              breakdown_frames=breakdown_frames, insights=insights)

    # Contract §5 side-output: <workbook-stem>.run.json beside the .xlsx. Purely additive —
    # the workbook above is untouched. Populates provenance.source_ids as a side effect.
    run_json, n_missing = build_run_json(tables, cfg, report["provenance"])
    report["provenance"]["source_ids"] = run_json["provenance"]["source_ids"]
    if n_missing:
        report["notes"].append(
            f"{n_missing} post(s) had no derivable source_id (blank in run.json) — "
            "no post-ID column and no parseable permalink.")
    run_json_path = os.path.splitext(out_path)[0] + ".run.json"
    with open(run_json_path, "w", encoding="utf-8") as f:
        json.dump(run_json, f, indent=2)

    report.update({"status": "built", "month": month, "output": out_path,
                   "run_json": run_json_path,
                   "top_posts": top_posts(tables),
                   "counts": {k: len(v) for k, v in tables.items()}})
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--fb")
    ap.add_argument("--ig")
    ap.add_argument("--stories")
    ap.add_argument("--yt",          help="Combined YouTube Table data.csv (auto-split by Duration)")
    ap.add_argument("--yt-shorts",   help="Pre-split YouTube Shorts export")
    ap.add_argument("--yt-longform", help="Pre-split YouTube Long-form export")
    ap.add_argument("--month")
    ap.add_argument("--out", default="/mnt/user-data/outputs/")
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()

    csv_paths = {
        "facebook": args.fb, "instagram": args.ig, "stories": args.stories,
        "youtube": args.yt, "youtube_shorts": args.yt_shorts, "youtube_longform": args.yt_longform,
    }
    try:
        report = run_build(config_path=args.config, csv_paths=csv_paths,
                           month=args.month, out_dir=args.out, validate_only=args.validate_only)
    except MissingColumns as e:
        print(json.dumps({"status": "missing_columns", "detail": e.detail,
                          "hint": "Meta may have renamed an export header. Fix mapping or re-export."}, indent=2))
        sys.exit(2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
