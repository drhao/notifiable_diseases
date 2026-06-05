"""Tests for the coverage guardrail and the JSON-embedding hardening."""
import json

from check_coverage import case_ok, manual_ok, dataset_stats, evaluate
from dashboard_common import embed_json


# --- check_coverage -------------------------------------------------------

def test_case_ok_accepts_core_or_structured_fields():
    assert case_ok({"通報定義": "x"})
    assert case_ok({"confirmed_case": "x"})
    assert not case_ok({"通報定義": "", "name": "只有名字"})
    assert not case_ok({})


def test_manual_ok_needs_min_sections():
    assert manual_ok({"疾病概述": "a", "致病原": "b", "流行病學": "c"})
    assert not manual_ok({"疾病概述": "a", "致病原": "b"})  # only 2 < MANUAL_MIN


def test_dataset_stats_rate():
    recs = [{"通報定義": "x"}, {"通報定義": "y"}, {}]
    s = dataset_stats(recs, case_ok)
    assert s == {"total": 3, "ok": 2, "rate": 2 / 3}


def test_evaluate_healthy_returns_no_problems():
    s = {"total": 70, "ok": 69, "rate": 69 / 70}
    assert evaluate("cases", s, prev_count=72) == []


def test_evaluate_flags_low_rate():
    s = {"total": 70, "ok": 10, "rate": 10 / 70}
    problems = evaluate("cases", s, prev_count=70, min_rate=0.6)
    assert any("well-parsed" in p for p in problems)


def test_evaluate_flags_shrinkage():
    s = {"total": 40, "ok": 40, "rate": 1.0}  # rate fine, but count crashed
    problems = evaluate("cases", s, prev_count=73, max_shrink=0.30)
    assert any("fell" in p for p in problems)


def test_evaluate_flags_empty_dataset():
    problems = evaluate("cases", {"total": 0, "ok": 0, "rate": 1.0})
    assert any("empty" in p for p in problems)


def test_evaluate_skips_shrink_without_baseline():
    s = {"total": 1, "ok": 1, "rate": 1.0}
    assert evaluate("cases", s, prev_count=None) == []


# --- embed_json (XSS-safe inlining) --------------------------------------

def test_embed_json_escapes_script_breakout():
    out = embed_json({"x": "</script><script>alert(1)</script>"})
    assert "<" not in out and ">" not in out
    assert "\\u003c" in out and "\\u003e" in out
    assert json.loads(out) == {"x": "</script><script>alert(1)</script>"}


def test_embed_json_escapes_ampersand_and_line_separators():
    payload = {"a": "x & y", "b": "p" + chr(0x2028) + "q" + chr(0x2029) + "r"}
    out = embed_json(payload)
    assert "&" not in out
    assert chr(0x2028) not in out and chr(0x2029) not in out
    assert "\\u0026" in out and "\\u2028" in out and "\\u2029" in out
    assert json.loads(out) == payload
