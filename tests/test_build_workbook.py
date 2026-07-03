"""Unit tests for the deterministic engine seams in core/build_workbook.py.

Covers config parsing, platform fingerprinting, fail-loud column validation, rank-order
scoring (including the deterministic tie-break), and the cross-platform leaderboard.
None of these touch Claude — they are pure, deterministic, and the heart of the engine.
"""
import os

import pandas as pd
import pytest

from core import build_workbook as bw

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
CONFIG = os.path.join(FIXTURES, "testclient-analytics-config.md")


# --- parse_config ---------------------------------------------------------------------------
def test_parse_config_identity_and_metrics():
    cfg = bw.parse_config(CONFIG)
    assert cfg.client_name == "Test Client"
    assert cfg.client_slug == "testclient"
    assert cfg.brand_accent_hex == "2A4A44"
    assert cfg.output_filename == "TestClient_[MonthYear]_Performance.xlsx"
    assert cfg.platforms_active == ["instagram", "facebook", "youtube"]
    # §6 metric lines parsed per platform
    assert cfg.metrics["instagram"] == ["Likes", "Saves", "Reach"]
    assert cfg.metrics["facebook"] == ["Reactions", "Total clicks"]
    assert cfg.metrics["youtube_shorts"] == ["Views", "Watch time (hours)", "Subscribers"]
    assert cfg.metrics["youtube_longform"] == ["Views", "Watch time (hours)", "Subscribers"]


def test_parse_config_slug_falls_back_to_name(tmp_path):
    """No explicit client_slug -> derived from client_name (lowercased, spaces removed)."""
    p = tmp_path / "noslug-analytics-config.md"
    p.write_text("## 1. Identity\n\n```yaml\nclient_name: Two Words\n```\n", encoding="utf-8")
    cfg = bw.parse_config(str(p))
    assert cfg.client_slug == "twowords"


# --- detect_platform ------------------------------------------------------------------------
def test_detect_platform_by_fingerprint():
    ig = pd.read_csv(os.path.join(FIXTURES, "instagram.csv"))
    fb = pd.read_csv(os.path.join(FIXTURES, "facebook.csv"))
    assert bw.detect_platform(ig) == "instagram"
    assert bw.detect_platform(fb) == "facebook"


def test_detect_platform_unknown_returns_none():
    df = pd.DataFrame({"Foo": [1], "Bar": [2]})
    assert bw.detect_platform(df) is None


# --- validate_columns (fail-loud path) ------------------------------------------------------
def test_validate_columns_ok_when_complete():
    cfg = bw.parse_config(CONFIG)
    ig = pd.read_csv(os.path.join(FIXTURES, "instagram.csv"))
    assert bw.validate_columns(ig, "instagram", cfg) == []


def test_validate_columns_reports_missing():
    cfg = bw.parse_config(CONFIG)
    ig = pd.read_csv(os.path.join(FIXTURES, "instagram.csv")).drop(columns=["Permalink", "Saves"])
    missing = bw.validate_columns(ig, "instagram", cfg)
    assert "Permalink" in missing        # structural column
    assert "Saves" in missing            # a scored metric
    assert missing == sorted(missing)    # returned sorted


def test_run_build_raises_missingcolumns(tmp_path):
    """The fail-loud contract: a missing expected column aborts the build, never mis-scores."""
    cfg = bw.parse_config(CONFIG)
    ig = pd.read_csv(os.path.join(FIXTURES, "instagram.csv")).drop(columns=["Permalink"])
    bad = tmp_path / "ig_bad.csv"
    ig.to_csv(bad, index=False)
    with pytest.raises(bw.MissingColumns) as exc:
        bw.run_build(config_path=CONFIG, csv_paths={"instagram": str(bad)}, out_dir=str(tmp_path))
    assert "instagram" in exc.value.detail
    assert "Permalink" in exc.value.detail["instagram"]


def test_youtube_missing_metric_degrades_gracefully(tmp_path):
    """YouTube exports vary column-to-column: a missing SCORED metric is skipped + warned,
    not fatal. Meta keeps failing loud (test above) — this leniency is YouTube-only."""
    cfg = bw.parse_config(CONFIG)
    # A "default" YouTube export lacking Watch time (a scored metric for this config)
    yt = pd.read_csv(os.path.join(FIXTURES, "youtube.csv")).drop(columns=["Watch time (hours)"])
    src = tmp_path / "yt_default.csv"
    yt.to_csv(src, index=False)
    result = bw.run_build(config_path=CONFIG, csv_paths={"youtube": str(src)}, out_dir=str(tmp_path))

    assert result["status"] == "built"                      # did NOT fail loud
    val = result["validation"]["youtube_longform"]
    assert val["missing_metrics"] == ["Watch time (hours)"]  # correctly identified as skippable
    assert val["missing_structural"] == []                   # not a wrong-file situation
    assert any("Watch time (hours)" in n and "skipped" in n.lower()
               for n in result["notes"])                     # surfaced prominently


def test_youtube_missing_structural_column_still_fails(tmp_path):
    """Wrong-file detection is preserved: a missing STRUCTURAL YouTube column still aborts."""
    cfg = bw.parse_config(CONFIG)
    yt = pd.read_csv(os.path.join(FIXTURES, "youtube.csv")).drop(columns=["Video title"])
    src = tmp_path / "yt_wrongfile.csv"
    yt.to_csv(src, index=False)
    with pytest.raises(bw.MissingColumns) as exc:
        bw.run_build(config_path=CONFIG, csv_paths={"youtube": str(src)}, out_dir=str(tmp_path))
    assert "Video title" in exc.value.detail.get("youtube_longform", [])


# --- score_posts (deterministic order + tie-break) ------------------------------------------
def test_score_posts_higher_metric_scores_higher():
    df = pd.DataFrame({
        "id": ["low", "mid", "high"],
        "Likes": [10, 20, 30],
        "Publish time": ["2026-05-01", "2026-05-02", "2026-05-03"],
    })
    out = bw.score_posts(df, ["Likes"], sparsity=0.15)
    # rank 1 = lowest raw value, so higher Likes -> higher Score -> better Overall Rank (1 = best)
    assert list(out["id"]) == ["high", "mid", "low"]
    assert list(out["Overall Rank"]) == [1, 2, 3]
    assert out.loc[out["id"] == "high", "Total Score"].iloc[0] == 3


def test_score_posts_tie_break_is_older_first():
    """Two posts with identical Total Score must be ordered older-publish-date first
    (deterministic, reproducible run-to-run)."""
    df = pd.DataFrame({
        "id": ["tie_newer", "tie_older", "winner"],
        "Likes": [10, 10, 30],
        "Publish time": ["2026-05-03", "2026-05-01", "2026-05-02"],
    })
    out = bw.score_posts(df, ["Likes"], sparsity=0.15)
    # winner (Likes 30) ranks first; the two tied rows share Overall Rank, older date first
    assert list(out["id"]) == ["winner", "tie_older", "tie_newer"]
    tied = out[out["id"].isin(["tie_older", "tie_newer"])]
    assert tied["Overall Rank"].nunique() == 1  # genuinely tied on rank


def test_score_posts_drops_sparse_metric():
    """A metric non-zero in <sparsity of rows is excluded from scoring."""
    df = pd.DataFrame({
        "id": ["a", "b", "c", "d", "e"],
        "Likes": [5, 10, 15, 20, 25],
        "Saves": [0, 0, 0, 0, 1],  # only 1/5 = 20% nonzero
    })
    out = bw.score_posts(df, ["Likes", "Saves"], sparsity=0.5)  # 20% < 50% -> Saves dropped
    assert "Score: Likes" in out.columns
    assert "Score: Saves" not in out.columns


# --- top_posts (cross-platform leaderboard) -------------------------------------------------
def test_top_posts_ranks_across_platforms_and_limits():
    ig = pd.DataFrame({
        "Description": ["ig-hot", "ig-cold"],
        "Total Score": [90, 10],
        "Post type": ["Reel", "Image"],
        "Views": [5000, 100],
        "Permalink": ["ig1", "ig2"],
    })
    yt = pd.DataFrame({
        "Video title": ["yt-mid"],
        "Total Score": [50],
        "Views": [3000],
        "Permalink": ["yt1"],
    })
    board = bw.top_posts({"instagram": ig, "youtube_shorts": yt}, limit=2)
    assert [row["score"] for row in board] == [90, 50]  # sorted desc, limited to 2
    assert board[0]["title"] == "ig-hot"
    assert board[0]["tag"] == "IG REEL"
    assert board[1]["tag"] == "YT SHORT"
