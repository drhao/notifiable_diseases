"""
Edge-case regression tests for the PDF text parsers (D3).

These pin down behaviour on the messy inputs real CDC PDFs produce — repeated
glyphs, numeric vs Chinese-numeral headings, multi-line English names, inline
case-definition content, and page-footer noise — and back the coverage
guardrail in check_coverage.py.
"""
from data_parser import (
    deduplicate_chars,
    normalize_text,
    parse_disease_content,
    extract_english_name,
    parse_case_definitions,
)
from manual_scraper import parse_manual_text


# --- deduplicate_chars: run-length threshold (n=4) ------------------------

def test_dedup_triple_is_preserved():
    # only runs of >= 4 collapse; a legitimate triple stays untouched
    assert deduplicate_chars("看看看") == "看看看"


def test_dedup_double_word_preserved():
    assert deduplicate_chars("謝謝大家") == "謝謝大家"


def test_dedup_exact_quadruple_to_one():
    assert deduplicate_chars("區區區區") == "區"


def test_dedup_run_of_five_collapses_to_two():
    # 5 = one group of 4 (-> 1) + 1 leftover char
    assert deduplicate_chars("AAAAA") == "AA"


def test_dedup_mixed_quadruples_form_phrase():
    assert deduplicate_chars("臨臨臨臨床床床床條條條條件件件件") == "臨床條件"


# --- normalize_text -------------------------------------------------------

def test_normalize_fullwidth_latin_to_ascii():
    # NFKC folds fullwidth letters/digits, helping English-name extraction
    assert normalize_text("ＣＯＶＩＤ－１９") == "COVID-19"


def test_normalize_halfwidth_paren_becomes_fullwidth():
    assert normalize_text("(test)") == "（test）"


# --- parse_disease_content ------------------------------------------------

def test_parse_disease_content_numeric_numbering():
    content = "1. 臨床條件\nfever\n2. 檢驗條件\npcr"
    out = parse_disease_content(content)
    assert out["臨床條件"] == "fever"
    assert out["檢驗條件"] == "pcr"


def test_parse_disease_content_header_colon_suffix():
    assert parse_disease_content("一、臨床條件：\nfoo")["臨床條件"] == "foo"


def test_parse_disease_content_multiline_section_preserved():
    out = parse_disease_content("一、臨床條件\nline1\nline2\nline3")
    assert out["臨床條件"] == "line1\nline2\nline3"


def test_parse_disease_content_unknown_heading_stays_as_content():
    out = parse_disease_content("一、臨床條件\nfever\n二、其他項目\nstuff")
    assert "fever" in out["臨床條件"] and "stuff" in out["臨床條件"]
    assert out["檢驗條件"] == ""  # 其他項目 is not a known header


# --- extract_english_name -------------------------------------------------

def test_extract_english_name_multiline_parenthetical_collapsed():
    content = "嚴重特殊傳染性肺炎\n（Severe Fever with\nThrombocytopenia）\n一、臨床條件"
    assert extract_english_name(content) == "Severe Fever with Thrombocytopenia"


def test_extract_english_name_with_digits_and_hyphen():
    assert extract_english_name("疾病名\n（COVID-19）") == "COVID-19"


# --- parse_case_definitions -----------------------------------------------

def test_case_def_inline_content_after_header():
    text = "（一）可能病例：臨床表現A\n（二）確定病例：實驗室B"
    out = parse_case_definitions(text)
    assert out["suspected_case"] == "臨床表現A"
    assert out["confirmed_case"] == "實驗室B"


def test_case_def_out_of_order():
    out = parse_case_definitions("確定病例\nC\n可能病例\nS")
    assert out["confirmed_case"] == "C"
    assert out["suspected_case"] == "S"


def test_case_def_only_confirmed():
    out = parse_case_definitions("確定病例\nonly this")
    assert out["confirmed_case"] == "only this"
    assert out["suspected_case"] == ""
    assert out["probable_case"] == ""


# --- parse_manual_text ----------------------------------------------------

def test_manual_skips_year_revision_footer():
    out = parse_manual_text("一、疾病概述\nfoo\n2023年修訂\n二、致病原\nbar")
    assert out["疾病概述"] == "foo"
    assert out["致病原"] == "bar"


def test_manual_skips_workbook_footer():
    out = parse_manual_text("一、疾病概述\nfoo\n登革熱工作手冊 － 5\n二、致病原\nbar")
    assert out["疾病概述"] == "foo"
    assert "工作手冊" not in out["疾病概述"]


def test_manual_chinese_numeral_eleven_header():
    assert parse_manual_text("十一、防疫措施\nclean up")["防疫措施"] == "clean up"


def test_manual_bare_header_without_numeral_is_not_a_section():
    out = parse_manual_text("一、疾病概述\nfoo\n致病原\nstill concept")
    assert out["致病原"] == ""              # never started (no numeral prefix)
    assert "致病原" in out["疾病概述"]       # folded into the open section instead
