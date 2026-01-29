"""
data_parser.py - Functions for parsing extracted PDF text into structured data.
"""
import re


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
