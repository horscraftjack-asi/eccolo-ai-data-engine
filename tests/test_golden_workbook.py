"""Golden-workbook regression guard.

Phase 2 adds only the run.json side-output — the .xlsx must be unchanged. This snapshots every
sheet's full cell grid and compares against a committed golden (tests/fixtures/golden_workbook.json).
Any future edit that alters scoring, tab layout, or styling output trips this test, which is the
point: it protects the engine internals (contract §5 red line) from silent drift.

To refresh intentionally (only when a workbook change is deliberate): regenerate the golden with
the snapshot logic below and review the diff in the PR.
"""
import json
import os

import pytest
from openpyxl import load_workbook

from core import build_workbook as bw

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
CONFIG = os.path.join(FIXTURES, "testclient-analytics-config.md")
GOLDEN = os.path.join(FIXTURES, "golden_workbook.json")


def _snapshot(path):
    wb = load_workbook(path)
    # default=str parity with how the golden was serialized (dates/None normalised to strings)
    return json.loads(json.dumps(
        {ws.title: [[c.value for c in row] for row in ws.iter_rows()] for ws in wb.worksheets},
        default=str,
    ))


def test_workbook_data_tabs_unchanged(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = bw.run_build(
        config_path=CONFIG,
        csv_paths={
            "facebook": os.path.join(FIXTURES, "facebook.csv"),
            "instagram": os.path.join(FIXTURES, "instagram.csv"),
            "youtube": os.path.join(FIXTURES, "youtube.csv"),
        },
        out_dir=str(tmp_path),
    )
    with open(GOLDEN, encoding="utf-8") as f:
        golden = json.load(f)
    current = _snapshot(result["output"])

    assert list(current) == list(golden), "sheet set/order changed"
    for sheet in golden:
        assert current[sheet] == golden[sheet], f"cell content changed in sheet: {sheet}"
