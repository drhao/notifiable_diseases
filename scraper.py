import requests
from bs4 import BeautifulSoup
import re
import json
import os
import time
import io
import pypdf
from urllib.parse import urljoin

BASE_URL = "https://www.cdc.gov.tw"
TARGET_URL = "https://www.cdc.gov.tw/Category/DiseaseDefine/ZW54U0FpVVhpVGR3UkViWm8rQkNwUT09"

def fetch_disease_links():
    print(f"Fetching {TARGET_URL}...")
    try:
        response = requests.get(TARGET_URL, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching main page: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    diseases = []
    
    # Select all links that look like File/Get
    # We want to try to capture the category if possible, but the structure is a bit loose.
    # We can rely on the fact that we saw headers in the text dump.
    # For now, let's just grab all unique links to ensure coverage.
    
    seen_urls = set()
    
    links = soup.find_all('a', href=True)
    for link in links:
        href = link.get('href')
        text = link.get_text(strip=True)
        
        if 'File/Get' in href:
            full_url = urljoin(BASE_URL, href)
            
            if full_url in seen_urls:
                continue
            
            # Filter out obviously non-disease links if any, though File/Get on this page seems specific.
            # Only keep if text is reasonable length maybe?
            if not text:
                continue
                
            seen_urls.add(full_url)
            diseases.append({
                'name': text,
                'url': full_url
            })
            
    return diseases

def get_pdf_content(viewer_url):
    try:
        # 1. Get viewer page
        res = requests.get(viewer_url, timeout=10)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # 2. Find PDF link
        # wrapper: <a class="nav-link viewer-button" href="...">
        pdf_link_tag = soup.select_one('a.viewer-button')
        if not pdf_link_tag:
            # Try embed if anchor not found
            embed_tag = soup.select_one('embed')
            if embed_tag:
                pdf_href = embed_tag.get('src')
                # remove #toolbar=0 etc
                if '#' in pdf_href:
                    pdf_href = pdf_href.split('#')[0]
            else:
                print(f"  No PDF link found in {viewer_url}")
                return None
        else:
            pdf_href = pdf_link_tag.get('href')
            
        full_pdf_url = urljoin(BASE_URL, pdf_href)
        
        # 3. Download PDF
        # print(f"  Downloading PDF: {full_pdf_url}")
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

def parse_disease_content(content):
    """
    Parses the raw content string into specific sections.
    """
    sections = {
        "臨床條件": "",
        "檢驗條件": "",
        "流行病學條件": "",
        "通報定義": "",
        "疾病分類": "",
        "檢體採檢送驗事項": ""
    }
    
    key_map = {
        "一": "臨床條件",
        "二": "檢驗條件",
        "三": "流行病學條件",
        "四": "通報定義",
        "五": "疾病分類",
        "六": "檢體採檢送驗事項"
    }

    lines = content.split('\n')
    current_section = None
    buffer = []

    header_pattern = re.compile(r'^\s*([一二三四五六])\s*、?\s*(.*)')

    for line in lines:
        line = line.strip()
        match = header_pattern.match(line)
        
        if match:
             numeral = match.group(1)
             
             if numeral in key_map:
                 if current_section and current_section in sections:
                     sections[current_section] = "\n".join(buffer).strip()
                 
                 current_section = key_map[numeral]
                 buffer = []
                 continue

        if current_section:
            buffer.append(line)
            
    if current_section and current_section in sections:
        sections[current_section] = "\n".join(buffer).strip()
        
    return sections

def main():
    links = fetch_disease_links()
    print(f"Found {len(links)} unique disease links.")
    
    results = []
    
    for i, disease in enumerate(links):
        print(f"[{i+1}/{len(links)}] Processing {disease['name']}...")
        content = get_pdf_content(disease['url'])
        
        if content:
            disease['content'] = content
            # Parse structured fields
            structured_fields = parse_disease_content(content)
            disease.update(structured_fields)
            
            results.append(disease)
        else:
            print(f"  Failed to extract content for {disease['name']}")
        
        time.sleep(0.5)
        
        if (i+1) % 10 == 0:
             with open("diseases.json", "w", encoding="utf-8") as f: # Saving partial to main file for safety or partial
                json.dump(results, f, ensure_ascii=False, indent=2)

    with open("diseases.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Save as CSV with structured columns
    try:
        import pandas as pd
        df = pd.DataFrame(results)
        
        # Define desired column order
        cols = ["name", "url", "臨床條件", "檢驗條件", "流行病學條件", "通報定義", "疾病分類", "檢體採檢送驗事項"]
        # Make sure we don't crash if a column is somehow missing (though it shouldn't be with the dict init)
        existing_cols = df.columns.tolist()
        final_cols = [c for c in cols if c in existing_cols]
        
        # Save structured CSV
        df[final_cols].to_csv("diseases.csv", index=False, encoding="utf-8-sig")
        print("Saved diseases.json and diseases.csv")
    except Exception as e:
        print(f"Could not save CSV: {e}")

    print("Done.")

if __name__ == "__main__":
    main()
