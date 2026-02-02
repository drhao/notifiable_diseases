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
    status_records = []
    
    for i, disease in enumerate(links):
        print(f"[{i+1}/{len(links)}] Processing {disease['name']} ({disease.get('source_category', 'N/A')})...")
        
        record = {'name': disease['name'], 'category': disease.get('source_category', 'N/A'), 'status': 'Fail', 'issues': []}
        
        content, pdf_path = get_pdf_content(disease['url'], disease['name'])
        
        if content:
            disease['content'] = content
            disease['pdf_path'] = pdf_path
            structured_fields = parse_disease_content(content)
            disease.update(structured_fields)
            results.append(disease)
            
            record['status'] = 'Success'
            for k in ["臨床條件", "檢驗條件", "流行病學條件", "通報定義", "疾病分類"]:
                val = disease.get(k)
                if not val or not val.strip():
                     record['issues'].append(f"Missing {k}")
        else:
            print(f"  Failed to extract content for {disease['name']}")
            record['issues'].append("Download/Extract Failed")
        
        status_records.append(record)
        
        time.sleep(0.5)
        
        if (i+1) % 10 == 0:
             with open("diseases.json", "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

    with open("diseases.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    try:
        import pandas as pd
        df = pd.DataFrame(results)
        
        cols = ["name", "url", "source_category", "pdf_path", "臨床條件", "檢驗條件", "流行病學條件", "通報定義", "疾病分類", "檢體採檢送驗事項"]
        existing_cols = df.columns.tolist()
        final_cols = [c for c in cols if c in existing_cols]
        
        df[final_cols].to_csv("diseases.csv", index=False, encoding="utf-8-sig")
        print("Saved diseases.json and diseases.csv")
    except Exception as e:
        print(f"Could not save CSV: {e}")

    # Save metadata with timestamp
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("metadata.json", "w", encoding="utf-8") as f:
        json.dump({"last_updated": now_str}, f)

    with open("metadata.json", "w", encoding="utf-8") as f:
        json.dump({"last_updated": now_str}, f)

    # Generate Status Report
    generate_report(status_records, len(links), now_str)

    print("Done.")


def generate_report(records, total_links, timestamp):
    """Generates status_report.md"""
    
    success_count = sum(1 for r in records if r['status'] == 'Success')
    fail_count = total_links - success_count
    
    lines = []
    lines.append(f"# Scraper Status Report")
    lines.append(f"**Execution Time:** {timestamp}")
    lines.append(f"")
    
    lines.append(f"## Summary")
    lines.append(f"- **Total Diseases Found:** {total_links}")
    lines.append(f"- **Successfully Fetched & Parsed:** {success_count}")
    lines.append(f"- **Failed:** {fail_count}")
    lines.append(f"")
    
    lines.append(f"## Detailed Status")
    lines.append(f"| Disease | Status | Category | Issues |")
    lines.append(f"| --- | --- | --- | --- |")
    
    for r in records:
        status_icon = "✅" if r['status'] == 'Success' else "❌"
        issues_str = ", ".join(r['issues']) if r['issues'] else "-"
        
        # Make issues red if critical
        if r['status'] == 'Fail':
            issues_str = f"**{issues_str}**"
        elif r['issues']:
             # Missing sections in success case
             status_icon = "⚠️"
             issues_str = f"Missing: {issues_str}"
             
        name = r['name'].replace("|", " ")
        cat = r['category'].replace("|", " ")
        
        lines.append(f"| {name} | {status_icon} {r['status']} | {cat} | {issues_str} |")
        
    report_content = "\n".join(lines)
    
    with open("status_report.md", "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"Generated status_report.md with {len(records)} records.")


if __name__ == "__main__":
    main()
