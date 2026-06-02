"""Regression tests for manual_scraper.parse_manual_text."""
from manual_scraper import parse_manual_text


def test_parse_manual_text_basic_sections():
    text = (
        "一、疾病概述\n這是一種急性疾病。\n"
        "二、致病原\n某病毒。\n"
        "三、流行病學\n全球分布。\n"
    )
    r = parse_manual_text(text)
    assert r["疾病概述"] == "這是一種急性疾病。"
    assert r["致病原"] == "某病毒。"
    assert r["流行病學"] == "全球分布。"


def test_parse_manual_text_header_with_english_parenthetical():
    """Headers like '一、疾病概述（Disease description）' should match."""
    text = "一、疾病概述（Disease description）\n內容\n"
    r = parse_manual_text(text)
    assert r["疾病概述"] == "內容"


def test_parse_manual_text_skips_footers():
    text = (
        "一、疾病概述\n第一行\n"
        "112 年修訂\n"
        "第二行\n"
        "二、致病原\n病原內容\n"
    )
    r = parse_manual_text(text)
    # the "年修訂" footer line is dropped, surrounding content is kept
    assert "第一行" in r["疾病概述"]
    assert "第二行" in r["疾病概述"]
    assert "年修訂" not in r["疾病概述"]
    assert r["致病原"] == "病原內容"


def test_parse_manual_text_empty():
    r = parse_manual_text("")
    assert all(v == "" for v in r.values())
