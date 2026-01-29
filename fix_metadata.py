
import json
import os
from pdf_fetcher import fetch_disease_links

def fix_metadata():
    # 1. Fetch current live data (reliable single source of truth for Category/URL)
    print("Fetching fresh links...")
    links = fetch_disease_links()
    link_map = {item['name']: item for item in links}
    
    # 2. Load existing json
    with open('diseases.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 3. Patch data
    patched_count = 0
    for d in data:
        name = d['name']
        
        # Try exact match
        source = link_map.get(name)
        
        # Try fuzzy match (slash vs underscore)
        if not source:
            name_slash = name.replace("_", "/")
            source = link_map.get(name_slash)
            
        if source:
            # Check if missing info
            if not d.get('source_category') or d.get('source_category') == 'MISSING':
                 d['source_category'] = source['source_category']
                 d['url'] = source['url']
                 print(f"Patched {name}: Category={source['source_category']}, URL={source['url']}")
                 patched_count += 1
            elif not d.get('url') or d.get('url') == 'MISSING':
                 d['url'] = source['url']
                 print(f"Patched {name}: URL={source['url']}")
                 patched_count += 1
        else:
            print(f"Warning: {name} not found in official CDC list.")

    # 4. Save
    with open('diseases.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Fix complete. Patched {patched_count} records.")

    # 5. Also update CSV
    try:
        import pandas as pd
        df = pd.DataFrame(data)
        cols = ["name", "url", "source_category", "pdf_path", "臨床條件", "檢驗條件", "流行病學條件", "通報定義", "疾病分類", "檢體採檢送驗事項"]
        final_cols = [c for c in cols if c in df.columns]
        df[final_cols].to_csv("diseases.csv", index=False, encoding="utf-8-sig")
        print("Updated diseases.csv")
    except Exception as e:
        print(f"CSV update failed: {e}")

if __name__ == "__main__":
    fix_metadata()
