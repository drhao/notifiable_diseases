"""Tests for manual_scraper's link extraction and pagination crawl."""
import manual_scraper
from manual_scraper import parse_manual_listing, get_manual_links

BASE = "https://www.cdc.gov.tw"


def _page(items, pagination=()):
    """Build a minimal listing-page HTML string."""
    lis = "".join(
        f'<li><a href="{href}">{name}工作手冊</a></li>' for name, href in items
    )
    pages = "".join(f'<a href="{href}">{label}</a>' for label, href in pagination)
    return (
        f'<ul class="infectious_disease_ul">{lis}</ul>'
        f'<div class="pagination">{pages}</div>'
    )


def test_parse_manual_listing_extracts_links_and_pages():
    html = _page(
        items=[("登革熱", "/File/Get/abc"), ("瘧疾", "/Category/MPage/xyz")],
        pagination=[("2", "/Category/DiseaseManual/list?page=2")],
    )
    links, pages = parse_manual_listing(html)
    assert {l["name"] for l in links} == {"登革熱", "瘧疾"}
    assert links[0]["url"] == BASE + "/File/Get/abc"
    assert pages == [BASE + "/Category/DiseaseManual/list?page=2"]


def test_parse_manual_listing_strips_suffix_and_ignores_unrelated():
    html = (
        '<ul class="infectious_disease_ul">'
        '<a href="/File/Get/a">流感.pdf</a>'
        '<a href="/about">關於我們</a>'  # not a /File or /Category link -> ignored
        '</ul>'
    )
    links, pages = parse_manual_listing(html)
    assert links == [{"name": "流感", "url": BASE + "/File/Get/a"}]
    assert pages == []


def test_get_manual_links_follows_pagination_and_dedupes(monkeypatch):
    page1 = _page(
        items=[("A", "/File/Get/a"), ("B", "/File/Get/b")],
        pagination=[("2", "/list?page=2")],
    )
    page2 = _page(
        items=[("B", "/File/Get/b"), ("C", "/File/Get/c")],  # B duplicated
        pagination=[("1", "/list?page=1")],  # back-link must not loop
    )
    pages = {
        manual_scraper.MANUAL_LIST_URL: page1,
        BASE + "/list?page=2": page2,
    }

    class FakeResp:
        def __init__(self, text):
            self.text = text
            self.encoding = None

    def fake_fetch(url, timeout=20):
        return FakeResp(pages[url])

    monkeypatch.setattr(manual_scraper, "fetch", fake_fetch)

    links = get_manual_links()
    names = [l["name"] for l in links]
    assert names == ["A", "B", "C"]  # deduped, page2 visited, no infinite loop


def test_get_manual_links_survives_page_fetch_error(monkeypatch):
    def boom(url, timeout=20):
        raise RuntimeError("network down")

    monkeypatch.setattr(manual_scraper, "fetch", boom)
    # Should not raise; just yields nothing.
    assert get_manual_links() == []
