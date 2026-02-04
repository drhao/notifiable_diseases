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
    
    # Convert common half-width punctuation to full-width
    # , -> ，, : -> ：, ; -> ；, ! -> ！, ? -> ？, ( -> （, ) -> ）
    punct_map = str.maketrans({
        ',': '，',
        ':': '：',
        ';': '；',
        '!': '！',
        '?': '？',
        '(': '（',
        ')': '）'
    })
    text = text.translate(punct_map)

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
        "病例分類", # Alias for 疾病分類
        "檢體採檢送驗事項"
    ]

    # Normalize Unicode to handle CJK compatibility characters
    content = normalize_text(content)
    
    lines = content.split('\n')
    current_section = None
    buffer = []

    # Regex to match: numeral (一、 or 壹、 or 1.) + optional prefix (e.g. "AFP ") + Header Name + end or colon
    # The header should be at end of line or followed by colon/whitespace only
    # matches: "一、 臨床條件", "一、 AFP 臨床條件", NOT "臨床條件一、(二)..."
    header_pattern = re.compile(
        r'^\s*([一二三四五六壹貳參肆伍陸0-9])\s*[、.]\s*'  # Require numeral
        r'(?:\S+\s+)?'  # Optional prefix like "AFP "
        r'(' + '|'.join(headers_map) + r')'  # Header name
        r'\s*[:：]?\s*$'  # End of line (optionally with colon)
    )

    for line in lines:
        stripped_line = line.strip()
        match = header_pattern.match(stripped_line)
        
        if match:
             header_name = match.group(2)  # Group 2 is the header name (group 1 is the numeral)
             
             # Handle aliases
             if header_name == "病例分類":
                 header_name = "疾病分類"

             # Check if this strictly matches one of our known headers
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
        
    # Parse Case Definitions automatically
    # Note: parse_case_definitions is defined later in the file, but available at runtime
    case_defs = parse_case_definitions(sections.get("疾病分類", ""))
    sections.update(case_defs)
        
    return sections


def extract_english_name(content):
    """
    Extracts English name from the first few lines of content.
    Typically found inside parentheses: (English Name) or （English Name）
    """
    # Look at the first 300 characters or 6 lines (to avoid picking up sub-types in clinical conditions)
    head_lines = content.split("\n")[:6]
    head = "\n".join(head_lines)
    
    # Strategy 1: Pattern to find content inside parens
    # Matches ( English Name ) or （ English Name ）, possibly multi-line
    pattern = re.compile(r'[（\(]([\s\S]*?)[）\)]')
    
    matches = pattern.findall(head)
    for m in matches:
        # Filter out short things like (一) or (1)
        cleaned = m.strip().replace("\n", " ")
        cleaned = re.sub(r'\s+', ' ', cleaned) # collapse spaces
        
        # Must be longer than 2 chars
        if len(cleaned) <= 2:
            continue
            
        # Must NOT contain Chinese characters
        # Range of common CJK characters: 4E00-9FFF
        if re.search(r'[\u4e00-\u9fff]', cleaned):
            continue
            
        # Must contain at least one English letter
        if not re.search(r'[a-zA-Z]', cleaned):
            continue

        return cleaned.replace('，', ',').replace('：', ':')

    # Strategy 2: If no parenthesized name found, look for a line that is mostly English
    # usually on line 2 or 3
    for line in head_lines[:6]:
        line = line.strip()
        if not line: 
            continue
        
        # Skip if it looks like "一、" or "附件"
        if re.match(r'^[一二三四五六0-9]', line) or "附件" in line:
            continue
            
        # Check if line is purely English/Punctuation (allow some symbols)
        # Remove common punctuation allowed in names: - , space, and full-width comma
        check = re.sub(r'[A-Za-z\s\-,，]', '', line)
        if len(check) == 0 and len(line) > 3:
             return line.replace('，', ',').replace('：', ':')

    return ""

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
            
def parse_case_definitions(classification_text):
    """
    Parses '疾病分類' text to extract structured case definitions.
    Returns a dict with 'suspected_case', 'probable_case', 'confirmed_case'.
    """
    if not classification_text:
        return {}

    definitions = {
        'suspected_case': '',
        'probable_case': '',
        'confirmed_case': ''
    }
    
    # Normalize for easier matching
    text = normalize_text(classification_text)
    
    # We want to split by keywords but keep the content.
    # Keywords: 可能病例, 極可能病例, 確定病例
    # Usually preceded by (一), (二) etc.
    
    # Strategy: Find all indices of these keywords
    # Map keyword -> "suspected_case", etc.
    key_map = {
        "極可能病例": "probable_case", # Must check "極可能" before "可能" to avoid partial match if we regex naively
        "可能病例": "suspected_case",
        "確定病例": "confirmed_case"
    }
    
    # We can iterate through the lines and see if a line STARTS with one of these (ignoring numbering)
    lines = text.split('\n')
    current_key = None
    buffer = []
    
    # Pattern: ^\s*(\(.*\)|[0-9]+\.|[一二三四]+\、)?\s*(keyword)\s*[:：]?
    # Matches: "(一) 可能病例:", "1. 確定病例", "確定病例："
    pattern = re.compile(r'^\s*(?:[\(（][一二三四0-9]+[\)）]|[0-9]+\.|[一二三四]\、)?\s*(極可能病例|可能病例|確定病例)\s*[:：]?')
    
    for line in lines:
        line = line.strip()
        match = pattern.match(line)
        if match:
            # We found a new header
            found_keyword = match.group(1)
            
            # Save previous buffer
            if current_key:
                definitions[current_key] = "\n".join(buffer).strip()
            
            # Start new section
            current_key = key_map.get(found_keyword)
            # Add the rest of the line (after the header) to buffer?
            # e.g. "(一) 可能病例: some text..." -> "some text..."
            # Or keep the whole line? User probably wants the content.
            # Usually the header line implies the title, we can strip it or keep it.
            # If we want structured data PROBABLY we strip the header title "可能病例".
            
            # Let's remove the header part from the line
            # match.end() gives end of match
            content_part = line[match.end():].strip()
            buffer = [content_part] if content_part else []
            
        elif current_key:
            buffer.append(line)
            
    # Save last buffer
    if current_key:
        definitions[current_key] = "\n".join(buffer).strip()
        
    return definitions

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
        normalized_text = normalize_text(text)
        parsed = parse_disease_content(normalized_text) # parse_disease_content already normalizes, but it's safe to do it again or pass stripped
        english_name = extract_english_name(normalized_text) # Extract English name from CLEAN text
        
        # Parse Case Definitions from '疾病分類'
        case_defs = parse_case_definitions(parsed.get("疾病分類", ""))
        parsed.update(case_defs)
        
        # Check if parsing found anything
        filled_sections = sum(1 for v in parsed.values() if v)
        print(f"Parsed {disease_name}: found {filled_sections}/9 sections, English: {english_name}")
        
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
            record['english_name'] = english_name
            updated_data.append(record)
        else:
            # Create new record stub (no url available)
            new_record = {'name': disease_name, 'content': normalize_text(text.strip())}
            new_record.update(parsed)
            new_record['english_name'] = english_name
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
