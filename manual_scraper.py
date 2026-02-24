import os
import re
import json
import time
import requests
import urllib.parse
from bs4 import BeautifulSoup
import pdfplumber

def get_manual_links(base_url="https://www.cdc.gov.tw/Category/DiseaseManual/bU9xd21vK0l5S3gwb3VUTldqdVNnQT09"):
    """Fetches the list of all disease manual links from the main page."""
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(base_url, headers=headers)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'html.parser')
    
    links = []
    # Find links pointing to /File/Get/ inside the main list
    for a in soup.select('ul.infectious_disease_ul a[href]'):
        href = a['href']
        text = a.text.strip().replace('工作手冊', '').replace('.pdf', '')
        if '/File/' in href or '/Category/MPage/' in href or '/Category/ListContent/' in href:
            full_url = urllib.parse.urljoin("https://www.cdc.gov.tw", href)
            # Avoid duplicates and check if not empty
            if text and not any(l['url'] == full_url for l in links):
                links.append({'name': text, 'url': full_url})
    
    # Also check pagination if we missed it
    pages = soup.select('div.pagination a')
    # For now, let's assume it's one long list or handle pagination if needed later
    return links

def get_actual_pdf_link(detail_url):
    """Fetches the detail page and extracts the actual .pdf upload link."""
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(detail_url, headers=headers)
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
        
    return sections

def main():
    pdf_dir = "manual_pdfs"
    os.makedirs(pdf_dir, exist_ok=True)
    
    print("Fetching manual list...")
    links = get_manual_links()
    print(f"Found {len(links)} manual links.")
    
    results = []
    
    for i, disease in enumerate(links):
        name = disease['name']
        list_url = disease['url']
        print(f"[{i+1}/{len(links)}] Processing {name}...")
        
        pdf_url = get_actual_pdf_link(list_url)
        if not pdf_url:
            print(f"  Could not find PDF link for {name}")
            continue
            
        pdf_path = os.path.join(pdf_dir, f"{name.replace('/', '_')}.pdf")
        
        # Download if not exists
        if not os.path.exists(pdf_path):
            try:
                r = requests.get(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200:
                    with open(pdf_path, 'wb') as f:
                        f.write(r.content)
                else:
                    print(f"  Failed to download PDF, status {r.status_code}")
                    continue
            except Exception as e:
                print(f"  Download error: {e}")
                continue
        
        # Extract text
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    extract = page.extract_text()
                    if extract:
                        text += extract + "\n"
        except Exception as e:
            print(f"  PDF read error: {e}")
            continue
            
        # Parse
        parsed_sections = parse_manual_text(text)
        
        record = {
            'name': name,
            'url': pdf_url, # Reference direct PDF
            **parsed_sections
        }
        results.append(record)
        
        # Save individual JSON and CSV
        manual_data_dir = "manual_data"
        os.makedirs(manual_data_dir, exist_ok=True)
        safe_name = name.replace('/', '_')
        indiv_json_path = os.path.join(manual_data_dir, f"{safe_name}.json")
        indiv_csv_path = os.path.join(manual_data_dir, f"{safe_name}.csv")
        
        with open(indiv_json_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
            
        try:
            import pandas as pd
            df_indiv = pd.DataFrame([record])
            df_indiv.to_csv(indiv_csv_path, index=False, encoding="utf-8-sig")
        except ImportError:
            pass
            
        time.sleep(0.5)

    # Save index
    index_records = []
    for r in results:
        safe_name = r['name'].replace('/', '_')
        index_records.append({
            'name': r['name'],
            'pdf_url': r['url'],
            'json_path': f"manual_data/{safe_name}.json",
            'csv_path': f"manual_data/{safe_name}.csv"
        })
        
    with open("manuals_index.json", "w", encoding="utf-8") as f:
        json.dump(index_records, f, ensure_ascii=False, indent=2)
        
    try:
        import pandas as pd
        df_index = pd.DataFrame(index_records)
        df_index.to_csv("manuals_index.csv", index=False, encoding="utf-8-sig")
    except ImportError:
        pass

    with open("disease_manuals.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    try:
        import pandas as pd
        df_all = pd.DataFrame(results)
        df_all.to_csv("disease_manuals.csv", index=False, encoding="utf-8-sig")
    except ImportError:
        pass
    
    print(f"Finished parsing {len(results)} manuals.")

if __name__ == "__main__":
    main()

