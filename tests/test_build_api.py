"""Tests for the static JSON API builder."""
from datetime import datetime, timezone

from build_api import build_api_payloads, _clean


def test_clean_strips_diff_and_local_fields():
    rec = {
        "name": "登革熱", "url": "http://x", "臨床條件": "...",
        "臨床條件_diff": "<b>x</b>", "pdf_path": "pdfs/登革熱.pdf",
        "pdf_hash": "abc",
    }
    out = _clean(rec)
    assert "臨床條件_diff" not in out
    assert "pdf_path" not in out
    assert out["pdf_hash"] == "abc"   # kept: useful for change detection
    assert out["臨床條件"] == "..."


def test_build_api_payloads_structure_and_counts():
    cases = [{"name": "A", "source_category": "第1類", "last_pdf_update": "2026-06-01",
              "english_name": "A-en", "pdf_path": "x", "臨床條件": "c"}]
    manuals = [{"name": "B", "last_pdf_update": "2026-06-02", "疾病概述": "o"}]
    now = datetime(2026, 6, 5, tzinfo=timezone.utc)

    p = build_api_payloads(cases, manuals, now=now)
    assert set(p) == {"diseases.json", "manuals.json", "summary.json", "meta.json"}

    # full files are cleaned
    assert "pdf_path" not in p["diseases.json"][0]
    assert p["diseases.json"][0]["臨床條件"] == "c"

    # meta counts + timestamp
    assert p["meta.json"]["counts"] == {"case_definitions": 1, "manuals": 1}
    assert p["meta.json"]["generated"] == "2026-06-05T00:00:00Z"

    # summary is compact
    row = p["summary.json"]["case_definitions"][0]
    assert row == {"name": "A", "english_name": "A-en",
                   "category": "第1類", "last_pdf_update": "2026-06-01"}
    assert "臨床條件" not in row


def test_build_api_payloads_handles_empty():
    p = build_api_payloads([], [], now=datetime(2026, 6, 5, tzinfo=timezone.utc))
    assert p["diseases.json"] == []
    assert p["meta.json"]["counts"] == {"case_definitions": 0, "manuals": 0}


def test_summary_category_falls_back_to_category_key():
    cases = [{"name": "A", "category": "第2類", "last_pdf_update": "2026-06-01"}]
    p = build_api_payloads(cases, [], now=datetime(2026, 6, 5, tzinfo=timezone.utc))
    assert p["summary.json"]["case_definitions"][0]["category"] == "第2類"
