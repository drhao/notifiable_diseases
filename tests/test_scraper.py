"""Tests for scraper orchestration helpers."""
from scraper import _keep_previous, diff_texts


def test_keep_previous_retains_old_record():
    results = []
    record = {"issues": []}
    old = {"name": "登革熱", "臨床條件": "old text"}
    assert _keep_previous(results, record, old) is True
    assert results == [old]                       # disease preserved in dataset
    assert "kept previous record" in record["issues"]


def test_keep_previous_noop_without_old_record():
    results = []
    record = {"issues": []}
    assert _keep_previous(results, record, None) is False
    assert results == []
    assert record["issues"] == []


def test_diff_texts_new_only_is_escaped():
    # sanity that diff markup + escaping still holds (guards the XSS invariant)
    out = diff_texts("", "<b>x</b>")
    assert out == "&lt;b&gt;x&lt;/b&gt;"
