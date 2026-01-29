"""
data_parser.py - Functions for parsing extracted PDF text into structured data.
Can be run independently to test parsing on local PDFs.
"""
import re
import os
import json
import unicodedata
import pdfplumber

def deduplicate_chars(text, n=4):
    """
    Remove repeated character sequences caused by PDF extraction issues.
    e.g., '臨臨臨臨床床床床' -> '臨床' when n=4
    """
    if not text:
        return text
    result = []
    i = 0
    while i < len(text):
        char = text[i]
        # Check if next n-1 chars are the same
        if i + n <= len(text) and all(text[i+j] == char for j in range(n)):
            result.append(char)
            i += n  # Skip the repeated chars
        else:
            result.append(char)
            i += 1
    return ''.join(result)

def normalize_text(text):
    """Normalize Unicode text to handle CJK compatibility characters."""
    # NFKC normalization converts compatibility characters to their standard forms
    text = unicodedata.normalize('NFKC', text)
    # Handle quadruple-repeated chars from some PDF extractions
    text = deduplicate_chars(text, 4)
    return text

def parse_disease_content(content):
    """
    Parses the raw content string into specific sections.
    Returns a dictionary with 6 keys for disease definitions.
    """
    sections = {
        "臨床條件": "",
        "檢驗條件": "",
        "流行病學條件": "",
        "通報定義": "",
        "疾病分類": "",
        "檢體採檢送驗事項": ""
    }
    
    # Map header keywords to keys in the sections dict
    # Using a list to ensure priority if needed, but here keys are distinct
    headers_map = [
        "臨床條件",
        "檢驗條件",
        "流行病學條件",
        "通報定義",
        "疾病分類",
        "檢體採檢送驗事項"
    ]

    # Normalize Unicode to handle CJK compatibility characters
    content = normalize_text(content)
    
    lines = content.split('\n')
    current_section = None
    buffer = []

    # Regex to match: Optional numeral (一、 or 壹、 or 1.) + optional prefix (e.g. "AFP ") + Header Name
    # matches: "一、臨床條件", "一、 AFP 臨床條件", "壹、臨床條件", " 1. 臨床條件" etc.
    header_pattern = re.compile(r'^\s*(?:[一二三四五六壹貳參肆伍陸0-9]\s*[、.]?\s*)?(?:\S+\s+)?(' + '|'.join(headers_map) + r')')

    for line in lines:
        stripped_line = line.strip()
        match = header_pattern.match(stripped_line)
        
        if match:
             header_name = match.group(1)
             
             # Check if this strictly matches one of our known headers
             # (Regex group 1 is the header name from the list)
             if header_name in sections:
                 # Save previous section
                 if current_section and current_section in sections:
                     sections[current_section] = "\n".join(buffer).strip()
                 
                 current_section = header_name
                 buffer = []
                 continue

        if current_section:
            buffer.append(line) # Keep original whitespace/indentation in buffer? user asked for simple
            
    if current_section and current_section in sections:
        sections[current_section] = "\n".join(buffer).strip()
        
    return sections


def main():
    """
    Independent execution: Read local PDFs and test the parser.
    Updates diseases.json if it exists.
    """
    pdf_dir = "pdfs"
    json_path = "diseases.json"
    
    if not os.path.exists(pdf_dir):
        print(f"Directory {pdf_dir} not found.")
        return

    print(f"Testing parser on files in {pdf_dir}/...")
    
    processed_count = 0
    updated_data = []
    
    # Load existing JSON to preserve other fields (url, source_category) if we want to save back
    existing_map = {}
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            for d in existing_data:
                existing_map[d['name']] = d
    
    files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]
    
    for filename in sorted(files):
        disease_name = filename.replace(".pdf", "").replace("_", "/")
        pdf_path = os.path.join(pdf_dir, filename)
        
        # Extract text via pdfplumber
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    extract = page.extract_text()
                    if extract:
                        text += extract + "\n"
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue
            
        # Parse
        parsed = parse_disease_content(text)
        
        # Check if parsing found anything
        filled_sections = sum(1 for v in parsed.values() if v)
        print(f"Parsed {disease_name}: found {filled_sections}/6 sections")
        
        # Update existing record - try to find by name (handle _ vs / differences)
        record = None
        for name, r in existing_map.items():
            # Match by normalizing both names
            if name.replace("/", "_") == disease_name.replace("/", "_"):
                record = r
                break
        
        if record:
            # Only update the parsed fields, keep existing url, source_category, etc.
            for k, v in parsed.items():
                record[k] = v
            record['content'] = normalize_text(text.strip())
            updated_data.append(record)
        else:
            # Create new record stub (no url available)
            new_record = {'name': disease_name, 'content': normalize_text(text.strip())}
            new_record.update(parsed)
            updated_data.append(new_record)
            print(f"  Warning: No existing record found for {disease_name}")
            
        processed_count += 1

    # Save back to JSON?? 
    # The user said "exec parser directly so I don't have to re-download".
    # This implies we should update the data source.
    if updated_data:
        # Sort by name or preserve order? Let's preserve order from existing if possible
        # Currently updated_data is sorted by filename.
        
        # Let's write to diseases.json
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, ensure_ascii=False, indent=2)
        print(f"\nUpdated {json_path} with parsed data from {processed_count} PDFs.")
        
        # Also update CSV
        try:
            import pandas as pd
            df = pd.DataFrame(updated_data)
            cols = ["name", "url", "source_category", "pdf_path", "臨床條件", "檢驗條件", "流行病學條件", "通報定義", "疾病分類", "檢體採檢送驗事項"]
            # Filter cols
            final_cols = [c for c in cols if c in df.columns]
            df[final_cols].to_csv("diseases.csv", index=False, encoding="utf-8-sig")
            print("Updated diseases.csv")
        except ImportError:
            pass

if __name__ == "__main__":
    main()
