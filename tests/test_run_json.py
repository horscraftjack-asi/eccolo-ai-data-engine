"""Contract §5 run.json side-output tests.

run_build() emits <workbook-stem>.run.json beside the .xlsx. These validate it field-by-field
against §5: the provenance block (§1.3), the platforms list, and per-post source_id / total_score
/ rank / cta_detected — cross-checked against the scored tables the workbook itself was built from.
"""
import json
import os

import pytest

from core import build_workbook as bw

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
CONFIG = os.path.join(FIXTURES, "testclient-analytics-config.md")
ALL_CSVS = {
    "facebook": os.path.join(FIXTURES, "facebook.csv"),
    "instagram": os.path.join(FIXTURES, "instagram.csv"),
    "youtube": os.path.join(FIXTURES, "youtube.csv"),
}
PROV_KEYS = {"run_id", "generated_at", "tool", "tool_version", "client_slug", "source_ids"}
CTA_ENUM = {"TriggerWord", "LinkInBio", "LinkInComments", "None"}
PLATFORM_PREFIX = {"yt:": ("youtube_shorts", "youtube_longform"),
                   "ig:": ("instagram",), "fb:": ("facebook",), "st:": ("stories",)}


@pytest.fixture
def no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture
def run_json(no_api_key, tmp_path):
    result = bw.run_build(config_path=CONFIG, csv_paths=ALL_CSVS, out_dir=str(tmp_path))
    with open(result["run_json"], encoding="utf-8") as f:
        return json.load(f)


def test_run_json_top_level_shape(run_json):
    assert set(run_json) == {"provenance", "platforms", "posts"}
    assert isinstance(run_json["platforms"], list)
    assert run_json["platforms"] == sorted(run_json["platforms"])
    assert run_json["posts"]


def test_run_json_provenance_is_contract_section13(run_json):
    prov = run_json["provenance"]
    assert set(prov) == PROV_KEYS
    assert prov["tool"] == "analytics"
    assert prov["tool_version"] == "1.0.0"
    assert prov["client_slug"] == "testclient"


def test_run_json_source_ids_distinct_nonempty_sorted(run_json):
    prov_ids = run_json["provenance"]["source_ids"]
    post_ids = {p["source_id"] for p in run_json["posts"] if p["source_id"]}
    assert prov_ids == sorted(post_ids)
    assert len(prov_ids) == len(set(prov_ids))  # distinct


def test_each_post_has_valid_section5_fields(run_json):
    for p in run_json["posts"]:
        assert set(p) == {"source_id", "total_score", "rank", "cta_detected"}
        assert isinstance(p["total_score"], int)
        assert isinstance(p["rank"], int)
        assert p["cta_detected"] in CTA_ENUM
        if p["source_id"]:
            prefix = p["source_id"].split(":", 1)[0] + ":"
            assert prefix in PLATFORM_PREFIX


def test_run_json_matches_the_scored_tables(no_api_key, tmp_path, monkeypatch):
    """rank/total_score/source_id for every post must match the exact scored table row the
    workbook was built from — the run.json is a faithful projection, not a re-computation."""
    captured = {}
    orig = bw.build_workbook

    def spy(tables, *args, **kwargs):
        captured.update({k: v.copy() for k, v in tables.items()})
        return orig(tables, *args, **kwargs)

    monkeypatch.setattr(bw, "build_workbook", spy)
    result = bw.run_build(config_path=CONFIG, csv_paths=ALL_CSVS, out_dir=str(tmp_path))
    with open(result["run_json"], encoding="utf-8") as f:
        by_sid = {p["source_id"]: p for p in json.load(f)["posts"]}

    cfg = bw.parse_config(CONFIG)
    for key, df in captured.items():
        platform = bw._platform_of_table(key, cfg)
        for _, row in df.iterrows():
            sid = bw.derive_source_id(platform, row)
            assert sid in by_sid, f"{sid} ({key}) missing from run.json"
            assert by_sid[sid]["total_score"] == int(row["Total Score"])
            assert by_sid[sid]["rank"] == int(row["Overall Rank"])
            # source_id prefix must match the row's actual platform
            expected_prefix = next(pre for pre, plats in PLATFORM_PREFIX.items()
                                   if platform in plats)
            assert sid.startswith(expected_prefix)


def test_cta_detection_maps_to_enum(run_json):
    """The synthetic IG/FB fixtures exercise each CTA branch at least once."""
    ctas = {p["cta_detected"] for p in run_json["posts"]}
    assert {"TriggerWord", "LinkInBio", "LinkInComments"} <= ctas


# --- source_id derivation unit tests --------------------------------------------------------
def test_derive_source_id_youtube_from_video_id():
    assert bw.derive_source_id("youtube_shorts", {"Video ID": "abc12345678"}) == "yt:abc12345678"


def test_derive_source_id_meta_from_permalink():
    assert bw.derive_source_id("instagram", {"Permalink": "https://instagram.com/p/CxYz/"}) == "ig:CxYz"
    assert bw.derive_source_id("facebook", {"Permalink": "https://facebook.com/p/f9"}) == "fb:f9"


def test_derive_source_id_prefers_explicit_post_id_column():
    assert bw.derive_source_id("instagram",
                               {"Post ID": "17999", "Permalink": "https://instagram.com/p/x"}) == "ig:17999"


def test_derive_source_id_blank_when_underivable():
    assert bw.derive_source_id("instagram", {"Permalink": ""}) == ""
    assert bw.derive_source_id("youtube_shorts", {"Permalink": "not-a-youtube-url"}) == ""


def test_build_run_json_counts_missing_source_ids():
    import pandas as pd
    df = pd.DataFrame({
        "Permalink": ["https://instagram.com/p/ok", ""],
        "Total Score": [5, 3], "Overall Rank": [1, 2],
        "Trigger Word": ["", ""], "Link in Bio": [False, False],
    })
    cfg = bw.parse_config(CONFIG)
    rj, n_missing = bw.build_run_json({"instagram": df}, cfg, bw.build_provenance("testclient"))
    assert n_missing == 1
    assert rj["provenance"]["source_ids"] == ["ig:ok"]
