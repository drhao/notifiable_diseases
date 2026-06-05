import os
import re
import json
import time
import logging
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime

from scraper import diff_texts
from data_parser import clean_section_text
from cdc_common import BASE_URL, fetch, download_pdf, write_csv, setup_logging

logger = logging.getLogger(__name__)

MANUAL_LIST_URL = "https://www.cdc.gov.tw/Category/DiseaseManual/bU9xd21vK0l5S3gwb3VUTldqdVNnQT09"


def parse_manual_listing(html):
    """
    Parse one manual listing page's HTML.
    Returns (manual_links, pagination_urls):
      - manual_links: list of {'name', 'url'} disease entries on this page
      - pagination_urls: absolute URLs of other listing pages linked from here
    Kept pure (no network) so it can be unit-tested offline.
    """
    soup = BeautifulSoup(html, 'html.parser')

    links = []
    for a in soup.select('ul.infectious_disease_ul a[href]'):
        href = a['href']
        text = a.text.strip().replace('工作手冊', '').replace('.pdf', '')
        if '/File/' in href or '/Category/MPage/' in href or '/Category/ListContent/' in href:
            full_url = urllib.parse.urljoin(BASE_URL, href)
            if text:
                links.append({'name': text, 'url': full_url})

    pagination_urls = []
    for a in soup.select('.pagination a[href], nav.pagination a[href], ul.pagination a[href]'):
        href = a.get('href', '').strip()
        if href and href not in ('#',):
            pagination_urls.append(urllib.parse.urljoin(BASE_URL, href))

    return links, pagination_urls


def get_manual_links(base_url=MANUAL_LIST_URL, max_pages=30):
    """
    Fetch all disease manual links, following pagination if present.

    Crawls the listing starting at base_url, discovering further pages from the
    pagination bar (bounded by max_pages). De-duplicates by URL. If the site has
    no pagination this simply returns the single page's links, matching the
    previous behaviour.
    """
    to_visit = [base_url]
    visited = set()
    seen_urls = set()
    results = []

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            r = fetch(url)
            r.encoding = 'utf-8'
        except Exception as e:
            logger.warning("Error fetching listing page %s: %s", url, e)
            continue

        links, pages = parse_manual_listing(r.text)
        for link in links:
            if link['url'] not in seen_urls:
                seen_urls.add(link['url'])
                results.append(link)

        for page_url in pages:
            if page_url not in visited and page_url not in to_visit:
                to_visit.append(page_url)

    return results

def get_actual_pdf_link(detail_url):
    """Fetches the detail page and extracts the actual .pdf upload link."""
    r = fetch(detail_url)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    for a in soup.select('a[href]'):
        if '.pdf' in a['href'].lower() or '/File/Get/' in a['href']:
            # Prevent circular reference if it points back to itself
            full_url = urllib.parse.urljoin("https://www.cdc.gov.tw", a['href'])
            if full_url != detail_url:
                return full_url
    # If no further PDF link found, maybe the detail_url itself is a PDF delivery endpoint
    return detail_url

def parse_manual_text(text):
    """Parses text into sections based on typical headers."""
    # List of common headers to look for
    headers_map = [
        "疾病概述", "致病原", "流行病學", "傳染窩", "傳染方式", 
        "潛伏期", "可傳染期", "感受性及抵抗力", "病例定義", "檢體採檢送驗事項", "防疫措施"
    ]
    
    # Regex to match: numeral (一、 or 壹、) + optional title + header
    # e.g., "一、疾病概述（Disease description）"
    header_pattern = re.compile(
        r'^\s*([一二三四五六七八九十壹貳參肆伍陸柒捌玖拾]+)\s*[、.]\s*'
        r'(' + '|'.join(headers_map) + r')'
        r'(?:\s*[（\(][A-Za-z\s\-]+[）\)])?\s*$', re.IGNORECASE
    )
    
    sections = {k: "" for k in headers_map}
    current_section = None
    buffer = []
    
    for line in text.split('\n'):
        # Ignore page footers/headers or pagination markers
        stripped = line.strip()
        if stripped.endswith("年修訂") or "工作手冊" in stripped and "－" in stripped:
            continue
            
        match = header_pattern.match(stripped)
        if match:
            # Save previous
            if current_section and current_section in sections:
                sections[current_section] = "\n".join(buffer).strip()
            
            header_name = match.group(2)
            current_section = header_name
            buffer = []
            continue
            
        if current_section:
            buffer.append(line)
            
    # Save last
    if current_section and current_section in sections:
        sections[current_section] = "\n".join(buffer).strip()

    for key in sections:
        sections[key] = clean_section_text(sections[key])

    return sections

def main():
    setup_logging()
    pdf_dir = "manual_pdfs"
    os.makedirs(pdf_dir, exist_ok=True)
    
    try:
        with open("disease_manuals.json", "r", encoding="utf-8") as f:
            existing_data = {d['name']: d for d in json.load(f)}
    except FileNotFoundError:
        existing_data = {}
    
    now_date_str = datetime.now().strftime("%Y-%m-%d")
    
    logger.info("Fetching manual list...")
    links = get_manual_links()
    logger.info("Found %d manual links.", len(links))
    
    results = []
    
    for i, disease in enumerate(links):
        name = disease['name']
        list_url = disease['url']
        logger.info("[%d/%d] Processing %s...", i + 1, len(links), name)

        pdf_url = get_actual_pdf_link(list_url)
        if not pdf_url:
            logger.warning("Could not find PDF link for %s", name)
            continue
            
        old_record = existing_data.get(name)
        expected_hash = old_record.get('pdf_hash') if old_record else None

        # Download (+ hash + text extraction) via the shared helper.
        try:
            text, pdf_path, current_hash = download_pdf(pdf_url, pdf_dir, name, expected_hash)
        except Exception as e:
            logger.warning("Download/extract error: %s", e)
            continue

        if text is None and current_hash == expected_hash:
            logger.info("  Unchanged (hash matched); skipping extraction.")
            # Update the URL just in case
            old_record['url'] = pdf_url
            if 'last_pdf_update' not in old_record:
                old_record['last_pdf_update'] = now_date_str
            results.append(old_record)
            continue

        logger.info("  Update detected: %s (hash %s)", name, current_hash[:6])

        # Parse
        parsed_sections = parse_manual_text(text)
        
        record = {
            'name': name,
            'url': pdf_url, # Reference direct PDF
            'pdf_hash': current_hash,
            'last_pdf_update': now_date_str,
            **parsed_sections
        }
        
        if old_record:
            for k in ["疾病概述", "致病原", "流行病學", "傳染窩", "傳染方式", "潛伏期", "可傳染期", "感受性及抵抗力", "病例定義", "檢體採檢送驗事項", "防疫措施"]:
                val_old = old_record.get(k, "")
                val_new = parsed_sections.get(k, "")
                if val_old != val_new:
                    record[k + "_diff"] = diff_texts(val_old, val_new)
                    
        results.append(record)

        time.sleep(0.5)

    with open("disease_manuals.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    write_csv("disease_manuals.csv", results)

    logger.info("Finished parsing %d manuals.", len(results))

if __name__ == "__main__":
    main()

