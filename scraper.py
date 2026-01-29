"""
scraper.py - Main script to fetch and parse Taiwan CDC notifiable disease definitions.
"""
import json
import time

from pdf_fetcher import fetch_disease_links, get_pdf_content
from data_parser import parse_disease_content


def main():
    links = fetch_disease_links()
    print(f"Found {len(links)} unique disease links.")
    
    results = []
    
    for i, disease in enumerate(links):
        print(f"[{i+1}/{len(links)}] Processing {disease['name']}...")
        content = get_pdf_content(disease['url'])
        
        if content:
            disease['content'] = content
            structured_fields = parse_disease_content(content)
            disease.update(structured_fields)
            results.append(disease)
        else:
            print(f"  Failed to extract content for {disease['name']}")
        
        time.sleep(0.5)
        
        if (i+1) % 10 == 0:
             with open("diseases.json", "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

    with open("diseases.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Save as CSV with structured columns
    try:
        import pandas as pd
        df = pd.DataFrame(results)
        
        cols = ["name", "url", "臨床條件", "檢驗條件", "流行病學條件", "通報定義", "疾病分類", "檢體採檢送驗事項"]
        existing_cols = df.columns.tolist()
        final_cols = [c for c in cols if c in existing_cols]
        
        df[final_cols].to_csv("diseases.csv", index=False, encoding="utf-8-sig")
        print("Saved diseases.json and diseases.csv")
    except Exception as e:
        print(f"Could not save CSV: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
