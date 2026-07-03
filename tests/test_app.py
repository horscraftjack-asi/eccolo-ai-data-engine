"""Web-layer tests via Flask's test client.

Covers the Phase 2 delivery seam: POST /run stashes the §5 run.json, and
GET /api/run/<run_id>.json serves back exactly the content run_build wrote to disk.
"""
import json
import os
from urllib.parse import unquote

import pytest

import app as flask_app
from core import build_workbook as bw

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
CONFIG = os.path.join(FIXTURES, "testclient-analytics-config.md")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    flask_app.app.config["TESTING"] = True
    return flask_app.app.test_client()


def _run_multipart():
    # Upload the fixture config so the run uses it regardless of the bundled client list.
    return {
        "config": (open(CONFIG, "rb"), "testclient-analytics-config.md"),
        "ig": (open(os.path.join(FIXTURES, "instagram.csv"), "rb"), "instagram.csv"),
        "fb": (open(os.path.join(FIXTURES, "facebook.csv"), "rb"), "facebook.csv"),
        "yt": (open(os.path.join(FIXTURES, "youtube.csv"), "rb"), "youtube.csv"),
        "client": "testclient",
    }


def test_run_then_download_run_json_parity(client, tmp_path):
    r = client.post("/run", data=_run_multipart(), content_type="multipart/form-data")
    assert r.status_code == 200
    assert ".xlsx" in r.headers["Content-Disposition"]

    # X-Provenance carries the run_id the result screen uses to build the download URL
    provenance = json.loads(unquote(r.headers["X-Provenance"]))
    assert provenance["tool"] == "analytics"
    run_id = provenance["run_id"]

    served = client.get(f"/api/run/{run_id}.json")
    assert served.status_code == 200
    assert served.mimetype == "application/json"
    body = served.get_json()

    # The served run.json is a valid §5 doc whose provenance matches what /run reported
    assert set(body) == {"provenance", "platforms", "posts"}
    assert body["provenance"] == provenance
    assert body["posts"]

    # Parity with disk: an independent build produces the same platforms/posts (run_id/timestamp
    # aside), proving the served content mirrors the on-disk run.json rather than diverging.
    direct = bw.run_build(config_path=CONFIG, csv_paths={
        "facebook": os.path.join(FIXTURES, "facebook.csv"),
        "instagram": os.path.join(FIXTURES, "instagram.csv"),
        "youtube": os.path.join(FIXTURES, "youtube.csv"),
    }, out_dir=str(tmp_path))
    with open(direct["run_json"], encoding="utf-8") as f:
        on_disk = json.load(f)
    assert body["platforms"] == on_disk["platforms"]
    assert body["posts"] == on_disk["posts"]


def test_unknown_run_id_is_404(client):
    r = client.get("/api/run/analytics-does-not-exist.json")
    assert r.status_code == 404
    assert "error" in r.get_json()
