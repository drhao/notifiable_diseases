"""
scraper.py - Main script to fetch and parse Taiwan CDC notifiable disease definitions.
"""
import json
import time
import difflib

from pdf_fetcher import fetch_disease_links, get_actual_pdf_url, download_and_extract_pdf
from data_parser import parse_disease_content

def diff_texts(old_text, new_text):
    if not old_text:
        return new_text
    if not new_text:
        return ""
        
    matcher = difflib.SequenceMatcher(None, old_text, new_text)
    result = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            result.append(new_text[j1:j2])
        elif tag == 'insert' or tag == 'replace':
            if tag == 'replace':
                result.append(f'<del style="color: #9ca3af;">{old_text[i1:i2]}</del>')
            result.append(f'<b style="color: #ea580c; background: #ffedd5;">{new_text[j1:j2]}</b>')
        elif tag == 'delete':
            result.append(f'<del style="color: #9ca3af;">{old_text[i1:i2]}</del>')
    return "".join(result)


def main():
    try:
        with open("diseases.json", "r", encoding="utf-8") as f:
            existing_data = {d['name']: d for d in json.load(f)}
    except FileNotFoundError:
        existing_data = {}

    links = fetch_disease_links()
    print(f"Found {len(links)} unique disease links.")
    
    results = []
    status_records = []
    updated_diseases = []
    
    from datetime import datetime
    now_date_str = datetime.now().strftime("%Y-%m-%d")
    
    for i, disease in enumerate(links):
        print(f"[{i+1}/{len(links)}] Processing {disease['name']} ({disease.get('source_category', 'N/A')})...")
        
        record = {'name': disease['name'], 'category': disease.get('source_category', 'N/A'), 'status': 'Fail', 'issues': [], 'updated_now': False}
        
        actual_pdf_url = get_actual_pdf_url(disease['url'])
        
        if not actual_pdf_url:
            print(f"  Failed to get PDF URL for {disease['name']}")
            record['issues'].append("No PDF Link")
            status_records.append(record)
            continue
            
        disease['actual_pdf_url'] = actual_pdf_url
        
        # Check cache
        old_disease = existing_data.get(disease['name'])
        if old_disease and old_disease.get('actual_pdf_url') == actual_pdf_url and old_disease.get('content'):
            print(f"  Unchanged! Skipping download.")
            old_disease['source_category'] = disease.get('source_category', old_disease.get('source_category'))
            # Preserve last update date if exists
            if 'last_pdf_update' not in old_disease:
                old_disease['last_pdf_update'] = now_date_str # Initialize for older records
            results.append(old_disease)
            record['status'] = 'Success'
            status_records.append(record)
            continue
            
        # If we reach here, it's either new or updated
        if old_disease:
            disease['last_pdf_update'] = now_date_str
            updated_diseases.append(disease['name'])
            record['updated_now'] = True
            print(f"  Update detected: {disease['name']}")
        else:
            disease['last_pdf_update'] = now_date_str
        
        content, pdf_path = download_and_extract_pdf(actual_pdf_url, disease['name'])
        
        if content:
            disease['content'] = content
            disease['pdf_path'] = pdf_path
            structured_fields = parse_disease_content(content)
            disease.update(structured_fields)
            
            # Compute diffs if updated
            if record.get('updated_now') and old_disease:
                for k in ["臨床條件", "檢驗條件", "流行病學條件", "通報定義", "疾病分類", "檢體採檢送驗事項", "suspected_case", "probable_case", "confirmed_case"]:
                    val_old = old_disease.get(k, "")
                    val_new = disease.get(k, "")
                    if val_old != val_new:
                        disease[k + "_diff"] = diff_texts(val_old, val_new)
            
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

    # Generate Status Report
    generate_report(status_records, len(links), now_str, updated_diseases)

    print("Done.")


def generate_report(records, total_links, timestamp, updated_diseases=None):
    """Generates status_report.md"""
    if updated_diseases is None:
        updated_diseases = []
        
    success_count = sum(1 for r in records if r['status'] == 'Success')
    fail_count = total_links - success_count
    
    lines = []
    lines.append(f"# Scraper Status Report")
    lines.append(f"**Execution Time:** {timestamp}")
    lines.append(f"")
    
    lines.append(f"## 📢 Latest PDF Updates")
    if updated_diseases:
        lines.append(f"The following disease definitions were updated in this run:  ")
        for ud in updated_diseases:
            lines.append(f"- **{ud}**")
    else:
        lines.append(f"*No updates detected in this run.*")
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
        
        if r.get('updated_now'):
            status_icon += " 💡 Updated"
            
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
