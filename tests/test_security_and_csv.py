"""Tests for diff_texts XSS-escaping and the stdlib write_csv helper."""
import csv

from scraper import diff_texts
from cdc_common import write_csv


def test_diff_texts_escapes_injected_markup_on_first_seen():
    out = diff_texts("", "<script>alert(1)</script>")
    assert "<script>" not in out
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" == out


def test_diff_texts_escapes_content_but_keeps_diff_tags():
    # disjoint strings -> a single clean 'replace' opcode
    out = diff_texts("AAAA", "<img onerror=x>")
    # injected tag is neutralised...
    assert "<img" not in out
    assert "&lt;img onerror=x&gt;" in out
    # ...while our own diff wrapper tags survive
    assert '<del style="color: #9ca3af;">AAAA</del>' in out
    assert '<b style="color: #ea580c; background: #ffedd5;">' in out


def test_diff_texts_empty_new_returns_empty():
    assert diff_texts("something", "") == ""


def test_diff_texts_equal_segment_is_escaped():
    out = diff_texts("a<b>c", "a<b>c")  # identical -> all 'equal'
    assert out == "a&lt;b&gt;c"


def test_write_csv_filters_columns_and_writes_bom(tmp_path):
    path = tmp_path / "out.csv"
    records = [
        {"name": "登革熱", "url": "http://x/a", "extra": "ignored"},
        {"name": "瘧疾", "url": "http://x/b"},
    ]
    write_csv(str(path), records, columns=["name", "url", "missing"])

    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # utf-8-sig BOM for Excel
    rows = list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()))
    assert [r["name"] for r in rows] == ["登革熱", "瘧疾"]
    assert "extra" not in rows[0]      # extrasaction=ignore
    assert "missing" not in rows[0]    # absent column dropped from header


def test_write_csv_union_of_keys_when_no_columns(tmp_path):
    path = tmp_path / "out.csv"
    records = [{"a": 1}, {"a": 2, "b": 3}]
    write_csv(str(path), records)
    header = path.read_text(encoding="utf-8-sig").splitlines()[0]
    assert header == "a,b"  # first-seen order, union of keys


def test_write_csv_handles_empty(tmp_path):
    path = tmp_path / "out.csv"
    write_csv(str(path), [])
    assert path.read_text(encoding="utf-8-sig").strip() == ""
