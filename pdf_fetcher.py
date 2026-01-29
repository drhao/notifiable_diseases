"""
pdf_fetcher.py - Functions for fetching disease links and PDF content from Taiwan CDC website.
Saves PDFs locally and extracts disease category from page structure.
"""
import requests
from bs4 import BeautifulSoup
import os
import re
import pdfplumber
from urllib.parse import urljoin

BASE_URL = "https://www.cdc.gov.tw"
TARGET_URL = "https://www.cdc.gov.tw/Category/DiseaseDefine/ZW54U0FpVVhpVGR3UkViWm8rQkNwUT09"
PDF_DIR = "pdfs"


def fetch_disease_links():
    """
    Fetch all disease links from the main CDC page.
    Extracts disease category from page structure.
    Returns list of dicts: {name, url, source_category}
    """
    print(f"Fetching {TARGET_URL}...")
    try:
        response = requests.get(TARGET_URL, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching main page: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    diseases = []
    seen_urls = set()
    
    # Find the main content area with category headers
    # The structure has headers like "第一類法定傳染病" followed by disease links
    
    # Categories pattern
    category_pattern = re.compile(r'第([一二三四五])類法定傳染病|其他傳染病')
    
    current_category = "其他"
    
    # Process all text nodes and links in order
    content_area = soup.find('div', class_='disease-wrapper') or soup.find('div', id='Content') or soup.body
    
    if not content_area:
        content_area = soup.body
    
    # Iterate through elements in order
    for element in content_area.find_all(['h4', 'a', 'li']):
        text = element.get_text(strip=True)
        
        # Check if this is a category header
        cat_match = category_pattern.search(text)
        if cat_match:
            if cat_match.group(1):
                cn_map = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5'}
                current_category = f"第{cat_match.group(1)}類"
            else:
                current_category = "其他"
            continue
        
        # Check if this is a disease link
        if element.name == 'a':
            href = element.get('href', '')
            if 'File/Get' in href:
                full_url = urljoin(BASE_URL, href)
                
                if full_url in seen_urls:
                    continue
                
                if not text:
                    continue
                    
                seen_urls.add(full_url)
                diseases.append({
                    'name': text,
                    'url': full_url,
                    'source_category': current_category
                })
            
    return diseases


def get_pdf_content(viewer_url, disease_name):
    """
    Download PDF from viewer page, save locally, and extract text content.
    Uses pdfplumber for text extraction.
    Returns tuple: (text_content, local_pdf_path) or (None, None) on failure.
    """
    try:
        # Ensure PDF directory exists
        os.makedirs(PDF_DIR, exist_ok=True)
        
        # 1. Get viewer page
        res = requests.get(viewer_url, timeout=10)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # 2. Find PDF link
        pdf_link_tag = soup.select_one('a.viewer-button')
        if not pdf_link_tag:
            embed_tag = soup.select_one('embed')
            if embed_tag:
                pdf_href = embed_tag.get('src')
                if '#' in pdf_href:
                    pdf_href = pdf_href.split('#')[0]
            else:
                print(f"  No PDF link found in {viewer_url}")
                return None, None
        else:
            pdf_href = pdf_link_tag.get('href')
            
        full_pdf_url = urljoin(BASE_URL, pdf_href)
        
        # 3. Download PDF
        pdf_res = requests.get(full_pdf_url, timeout=15)
        pdf_res.raise_for_status()
        
        # 4. Save PDF locally
        # Sanitize filename
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', disease_name)
        pdf_path = os.path.join(PDF_DIR, f"{safe_name}.pdf")
        
        with open(pdf_path, 'wb') as f:
            f.write(pdf_res.content)
        
        # 5. Extract Text using pdfplumber
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        return text.strip(), pdf_path
        
    except Exception as e:
        print(f"  Error processing {viewer_url}: {e}")
        return None, None
