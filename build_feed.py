"""
build_feed.py - Generate an RSS 2.0 feed of recently updated diseases.

Reads the structured data produced by the scrapers (diseases.json and
disease_manuals.json), collects every entry that carries a last_pdf_update
date, and emits feed.xml sorted newest-first. The feed is published alongside
the dashboards on GitHub Pages so people can subscribe to updates instead of
checking the site daily.

Pure feed construction lives in build_feed() so it can be unit-tested; main()
only does file IO.
"""
import os
import json
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

# The published site root; override with SITE_URL if the Pages URL differs.
SITE_URL = os.environ.get("SITE_URL", "https://drhao.github.io/notifiable_diseases")

MAX_ITEMS = 60


def _parse_date(value):
    """Parse a 'YYYY-MM-DD' (or longer) string into an aware datetime, or None."""
    if not value:
        return None
    try:
        dt = datetime.strptime(value[:10], "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _collect(data, kind, page):
    """Turn a list of disease/manual records into normalised feed items."""
    items = []
    for d in data or []:
        dt = _parse_date(d.get("last_pdf_update"))
        if not dt:
            continue
        name = d.get("name", "").strip()
        if not name:
            continue
        link = d.get("actual_pdf_url") or d.get("url") or f"{SITE_URL}/{page}"
        items.append({
            "title": f"{name}（{kind}）",
            "link": link,
            "date": dt,
            "guid": f"{link}#{dt.strftime('%Y%m%d')}",
            "kind": kind,
        })
    return items


def build_feed(case_data, manual_data, site_url=SITE_URL, now=None):
    """Build the RSS 2.0 XML string from the two datasets."""
    items = _collect(case_data, "病例定義", "index.html") + \
        _collect(manual_data, "防治工作手冊", "manuals.html")
    items.sort(key=lambda x: x["date"], reverse=True)
    items = items[:MAX_ITEMS]

    last_build = format_datetime(now or datetime.now(timezone.utc))

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        '  <channel>',
        '    <title>台灣法定傳染病定義與手冊更新</title>',
        f'    <link>{escape(site_url)}</link>',
        '    <description>Taiwan CDC 法定傳染病病例定義與防治工作手冊的最新異動</description>',
        '    <language>zh-TW</language>',
        f'    <lastBuildDate>{last_build}</lastBuildDate>',
    ]
    for it in items:
        parts += [
            '    <item>',
            f'      <title>{escape(it["title"])}</title>',
            f'      <link>{escape(it["link"])}</link>',
            f'      <guid isPermaLink="false">{escape(it["guid"])}</guid>',
            f'      <pubDate>{format_datetime(it["date"])}</pubDate>',
            f'      <category>{escape(it["kind"])}</category>',
            '    </item>',
        ]
    parts += ['  </channel>', '</rss>', '']
    return "\n".join(parts)


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def main():
    case_data = _load("diseases.json")
    manual_data = _load("disease_manuals.json")
    xml = build_feed(case_data, manual_data)
    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(xml)
    n = xml.count("<item>")
    print(f"Generated feed.xml with {n} items.")


if __name__ == "__main__":
    main()
