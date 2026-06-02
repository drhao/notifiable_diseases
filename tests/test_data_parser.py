"""Regression tests for data_parser's pure-text parsing functions.

These cover the quirky bits of CDC PDF extraction (repeated glyphs, half-width
punctuation, numbered headers, case-definition keywords) so that a change to
the regexes or normalisation is caught instead of silently mangling data.
"""
import os

import pytest

from data_parser import (
    deduplicate_chars,
    normalize_text,
    parse_disease_content,
    parse_case_definitions,
    extract_english_name,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


# --- deduplicate_chars -----------------------------------------------------

def test_deduplicate_chars_collapses_quadruples():
    assert deduplicate_chars("臨臨臨臨床床床床", 4) == "臨床"


def test_deduplicate_chars_leaves_normal_text():
    assert deduplicate_chars("臨床條件", 4) == "臨床條件"


def test_deduplicate_chars_empty():
    assert deduplicate_chars("", 4) == ""
    assert deduplicate_chars(None, 4) is None


# --- normalize_text --------------------------------------------------------

def test_normalize_text_halfwidth_punct_to_fullwidth():
    # Only punctuation is widened; ASCII letters are left as-is.
    assert normalize_text("a,b:c;d!e?f(g)") == "a，b：c；d！e？f（g）"


def test_normalize_text_dedups_after_normalising():
    assert normalize_text("臨臨臨臨床床床床") == "臨床"


# --- parse_disease_content -------------------------------------------------

def test_parse_disease_content_extracts_all_sections():
    text = (
        "一、 臨床條件\n發燒\n"
        "二、 檢驗條件\nPCR 陽性\n"
        "三、 流行病學條件\n曾赴流行區\n"
        "四、 通報定義\n符合臨床條件即通報\n"
        "五、 疾病分類\n（一）確定病例：符合檢驗條件\n"
        "六、 檢體採檢送驗事項\n七日內送驗\n"
    )
    r = parse_disease_content(text)
    assert r["臨床條件"] == "發燒"
    assert r["檢驗條件"] == "PCR 陽性"
    assert r["流行病學條件"] == "曾赴流行區"
    assert r["通報定義"] == "符合臨床條件即通報"
    assert r["檢體採檢送驗事項"] == "七日內送驗"
    # 疾病分類 also gets exploded into case definitions
    assert r["confirmed_case"] == "符合檢驗條件"


def test_parse_disease_content_alias_bingli_fenlei():
    """'病例分類' should be treated as an alias of '疾病分類'."""
    text = "一、 病例分類\n（一）確定病例：X\n"
    r = parse_disease_content(text)
    assert r["疾病分類"].startswith("（一）確定病例")


def test_parse_disease_content_header_with_english_prefix():
    """Headers like '一、 AFP 臨床條件' should still be recognised."""
    text = "一、 AFP 臨床條件\n肢體無力\n二、 檢驗條件\n病毒分離\n"
    r = parse_disease_content(text)
    assert r["臨床條件"] == "肢體無力"
    assert r["檢驗條件"] == "病毒分離"


def test_parse_disease_content_ignores_inline_header_mentions():
    """A header word not at the start of a numbered line must not split."""
    text = "一、 臨床條件\n本病的臨床條件包含多項，檢驗條件另述。\n"
    r = parse_disease_content(text)
    assert "檢驗條件另述" in r["臨床條件"]
    assert r["檢驗條件"] == ""


def test_parse_disease_content_empty():
    r = parse_disease_content("")
    assert all(r[k] == "" for k in
               ("臨床條件", "檢驗條件", "流行病學條件", "通報定義",
                "疾病分類", "檢體採檢送驗事項"))


# --- parse_case_definitions ------------------------------------------------

def test_parse_case_definitions_three_classes():
    text = (
        "（一）可能病例：符合臨床條件\n"
        "（二）極可能病例：加上快篩陽性\n"
        "（三）確定病例：符合檢驗條件\n"
    )
    r = parse_case_definitions(text)
    assert r["suspected_case"] == "符合臨床條件"
    assert r["probable_case"] == "加上快篩陽性"
    assert r["confirmed_case"] == "符合檢驗條件"


def test_parse_case_definitions_jike_not_confused_with_ke():
    """'極可能病例' must map to probable, not be eaten by '可能病例'."""
    text = "極可能病例：A\n可能病例：B\n"
    r = parse_case_definitions(text)
    assert r["probable_case"] == "A"
    assert r["suspected_case"] == "B"


def test_parse_case_definitions_numbered_variants():
    text = "1. 可能病例：甲\n2. 確定病例：乙\n"
    r = parse_case_definitions(text)
    assert r["suspected_case"] == "甲"
    assert r["confirmed_case"] == "乙"


def test_parse_case_definitions_empty():
    assert parse_case_definitions("") == {}


# --- extract_english_name --------------------------------------------------

def test_extract_english_name_parenthesised():
    assert extract_english_name("登革熱\n（Dengue fever）\n一、 臨床條件") == "Dengue fever"


def test_extract_english_name_rejects_chinese_and_short():
    # (一) is too short / Chinese; should fall through and find nothing here
    assert extract_english_name("狂犬病\n（一）說明\n") == ""


def test_extract_english_name_line_fallback():
    # A purely alphabetic English line on its own is picked up as a fallback.
    assert extract_english_name("嚴重急性呼吸道症候群\nSARS\n一、 臨床條件") == "SARS"


def test_extract_english_name_line_fallback_misses_digits():
    """Known limitation: the line fallback does not handle names with digits
    (e.g. COVID-19); only the parenthesised strategy would catch those."""
    assert extract_english_name("嚴重特殊傳染性肺炎\nCOVID-19\n一、 臨床條件") == ""
    assert extract_english_name("嚴重特殊傳染性肺炎\n（COVID-19）\n一、 臨床條件") == "COVID-19"


# --- fixture-driven regression ---------------------------------------------

def test_parse_real_world_fixture():
    with open(os.path.join(FIXTURES, "dengue_definition.txt"), encoding="utf-8") as f:
        text = f.read()
    r = parse_disease_content(text)
    # Every defined section should be populated from the fixture
    for key in ("臨床條件", "檢驗條件", "流行病學條件", "通報定義",
                "疾病分類", "檢體採檢送驗事項"):
        assert r[key], f"section {key} unexpectedly empty"
    assert "頭痛" in r["臨床條件"]
    assert r["suspected_case"].startswith("符合臨床條件")
    assert "NS1" in r["probable_case"]
    assert "檢驗條件" in r["confirmed_case"]
    assert extract_english_name(text) == "Dengue fever"
