"""Tests for build_feed's RSS construction."""
from datetime import datetime, timezone

from build_feed import build_feed, _parse_date


def test_parse_date_handles_good_and_bad():
    assert _parse_date("2026-06-05").year == 2026
    assert _parse_date("2026-06-05 11:31").month == 6
    assert _parse_date("") is None
    assert _parse_date("not-a-date") is None
    assert _parse_date(None) is None


def test_build_feed_orders_newest_first_and_tags_kind():
    case = [
        {"name": "登革熱", "last_pdf_update": "2026-06-01", "actual_pdf_url": "http://x/d"},
        {"name": "瘧疾", "last_pdf_update": "2026-06-05", "actual_pdf_url": "http://x/m"},
    ]
    manual = [{"name": "結核病", "last_pdf_update": "2026-06-03", "url": "http://x/t"}]
    xml = build_feed(case, manual, site_url="http://site",
                     now=datetime(2026, 6, 6, tzinfo=timezone.utc))

    # newest (瘧疾 06-05) appears before 結核病 (06-03) before 登革熱 (06-01)
    assert xml.index("瘧疾") < xml.index("結核病") < xml.index("登革熱")
    assert "病例定義" in xml and "防治工作手冊" in xml
    assert xml.count("<item>") == 3
    assert "<link>http://x/m</link>" in xml


def test_build_feed_skips_entries_without_date():
    case = [
        {"name": "有日期", "last_pdf_update": "2026-06-01", "url": "http://x/a"},
        {"name": "沒日期"},
        {"last_pdf_update": "2026-06-02"},  # no name
    ]
    xml = build_feed(case, [], now=datetime(2026, 6, 6, tzinfo=timezone.utc))
    assert xml.count("<item>") == 1
    assert "有日期" in xml
    assert "沒日期" not in xml


def test_build_feed_escapes_special_chars():
    case = [{"name": "A & B <test>", "last_pdf_update": "2026-06-01",
             "url": "http://x/a?q=1&z=2"}]
    xml = build_feed(case, [], now=datetime(2026, 6, 6, tzinfo=timezone.utc))
    assert "A &amp; B &lt;test&gt;" in xml
    assert "q=1&amp;z=2" in xml
    # raw unescaped ampersand must not appear
    assert "&z=2" not in xml.replace("&amp;", "")


def test_build_feed_empty_is_valid_rss():
    xml = build_feed([], [], now=datetime(2026, 6, 6, tzinfo=timezone.utc))
    assert xml.startswith("<?xml")
    assert "<rss version=\"2.0\">" in xml
    assert "<item>" not in xml
