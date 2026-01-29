"""
pdf_fetcher.py - Functions for fetching disease links and PDF content from Taiwan CDC website.
"""
import requests
from bs4 import BeautifulSoup
import io
import pypdf
from urllib.parse import urljoin

BASE_URL = "https://www.cdc.gov.tw"
TARGET_URL = "https://www.cdc.gov.tw/Category/DiseaseDefine/ZW54U0FpVVhpVGR3UkViWm8rQkNwUT09"


def fetch_disease_links():
    """Fetch all disease links from the main CDC page."""
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
    
    links = soup.find_all('a', href=True)
    for link in links:
        href = link.get('href')
        text = link.get_text(strip=True)
        
        if 'File/Get' in href:
            full_url = urljoin(BASE_URL, href)
            
            if full_url in seen_urls:
                continue
            
            if not text:
                continue
                
            seen_urls.add(full_url)
            diseases.append({
                'name': text,
                'url': full_url
            })
            
    return diseases


def get_pdf_content(viewer_url):
    """Download PDF from viewer page and extract text content."""
    try:
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
                return None
        else:
            pdf_href = pdf_link_tag.get('href')
            
        full_pdf_url = urljoin(BASE_URL, pdf_href)
        
        # 3. Download PDF
        pdf_res = requests.get(full_pdf_url, timeout=15)
        pdf_res.raise_for_status()
        
        # 4. Extract Text
        with io.BytesIO(pdf_res.content) as f:
            reader = pypdf.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        
        return text.strip()
        
    except Exception as e:
        print(f"  Error processing {viewer_url}: {e}")
        return None
