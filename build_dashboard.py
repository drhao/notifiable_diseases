import json
import os
import re

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Taiwan Notifiable Diseases Dashboard</title>
    <!-- Inter font for clean look -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Sans+TC:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            /* Ultra Minimalist Theme */
            --bg-color: #ffffff;
            --text-primary: #111111;
            --text-secondary: #737373; /* Neutral Gray */
            --border-color: #e5e5e5;
            --table-header-color: #888888;
            --row-hover: #fafafa;
            --accent-color: #000000; /* Strict Black accent */
            --tag-bg: #f5f5f5;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            outline: none;
        }

        body {
            font-family: 'Inter', 'Noto Sans TC', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            padding: 3rem 4rem;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            margin-bottom: 3rem;
            display: flex;
            justify-content: space-between;
            align-items: baseline;
        }

        h1 {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-primary);
            letter-spacing: -0.02em;
        }
        
        .header-controls {
            display: flex;
            gap: 1rem;
            align-items: center;
        }

        #searchInput {
            padding: 0.5rem 0;
            border: none;
            border-bottom: 1px solid var(--border-color);
            font-size: 0.9rem;
            width: 240px;
            color: var(--text-primary);
            background: transparent;
            transition: border-color 0.2s;
            font-family: inherit;
        }

        #searchInput:focus {
            border-color: var(--accent-color);
        }
        
        #searchInput::placeholder {
            color: #d4d4d4;
        }

        /* Table */
        .table-container {
            overflow-x: auto;
            border-top: 1px solid var(--text-primary); /* Strong top border */
            padding-top: 1rem;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem; /* Small, minimalist text */
            min-width: 1400px;
        }
        
        th {
            text-align: left;
            font-weight: 500;
            color: var(--table-header-color);
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border-color);
            white-space: nowrap;
        }

        td {
            padding: 1rem 1rem;
            border-bottom: 1px solid var(--border-color);
            vertical-align: top;
            line-height: 1.6;
            color: #333;
        }

        /* Sticky First Column */
        th:first-child, td:first-child {
            position: sticky;
            left: 0;
            background-color: var(--bg-color);
            z-index: 10;
            width: 220px;
            min-width: 220px;
            font-weight: 500;
            color: var(--text-primary);
            border-right: 1px solid transparent; 
        }
        
        /* Add subtle shadow line only when scrolling? Advanced, skip for pure minimal */
        
        tbody tr:hover td {
            background-color: var(--row-hover);
        }
        tbody tr:hover td:first-child {
            background-color: var(--row-hover);
        }

        /* Typography & Content */
        .disease-name {
            display: block;
            margin-bottom: 0.25rem;
            font-size: 0.95rem;
        }

        .category-tag {
            display: inline-block;
            font-size: 0.7rem;
            color: var(--text-secondary);
            background-color: var(--tag-bg);
            padding: 2px 6px;
            border-radius: 4px;
            margin-right: 0.5rem;
        }
        
        .pdf-link {
            font-size: 0.7rem;
            color: #999;
            text-decoration: none;
            margin-top: 4px;
            display: inline-block;
        }
        
        .pdf-link:hover {
            color: var(--text-primary);
            text-decoration: underline;
        }

        .cell-content {
            max-height: 100px;
            overflow: hidden;
            position: relative;
            transition: all 0.2s ease;
        }
        
        .cell-content.expanded {
            max-height: none;
        }

        .toggle-btn {
            background: none;
            border: none;
            font-size: 0.7rem;
            font-weight: 600;
            color: #999;
            cursor: pointer;
            margin-top: 0.5rem;
            padding: 0;
            display: none;
        }
        
        .toggle-btn:hover {
            color: #000;
        }

        @media (max-width: 768px) {
            body { padding: 1.5rem; }
            header { flex-direction: column; gap: 1rem; }
        }

    </style>
</head>
<body>

    <header>
        <h1>Notifiable Diseases</h1>
        <div class="header-controls">
            <input type="text" id="searchInput" placeholder="Search...">
        </div>
    </header>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Disease / Category</th>
                    <th>Clinical Conditions <br><span style="font-weight:400; opacity:0.6">臨床條件</span></th>
                    <th>Lab Criteria <br><span style="font-weight:400; opacity:0.6">檢驗條件</span></th>
                    <th>Epidemiology <br><span style="font-weight:400; opacity:0.6">流行病學</span></th>
                    <th>Reporting <br><span style="font-weight:400; opacity:0.6">通報定義</span></th>
                    <th>Classification <br><span style="font-weight:400; opacity:0.6">疾病分類</span></th>
                    <th>Specimen <br><span style="font-weight:400; opacity:0.6">檢體採檢</span></th>
                </tr>
            </thead>
            <tbody id="tableBody">
                <!-- Rows -->
            </tbody>
        </table>
    </div>

    <script>
        const DATA = __DATA_PLACEHOLDER__;
        const tbody = document.getElementById('tableBody');
        const searchInput = document.getElementById('searchInput');

        const COLS = [
            "臨床條件",
            "檢驗條件",
            "流行病學條件",
            "通報定義",
            "疾病分類",
            "檢體採檢送驗事項"
        ];

        function render(filter = '') {
            tbody.innerHTML = '';
            const f = filter.toLowerCase();
            
            // Filter
            const filtered = DATA.filter(d => 
                d.name.toLowerCase().includes(f) || 
                (d.content && d.content.toLowerCase().includes(f))
            );

            filtered.forEach(d => {
                const tr = document.createElement('tr');
                
                // Name Col
                let html = `<td>
                    <span class="disease-name">${d.name}</span>
                    <div>
                        ${d.category_tag ? `<span class="category-tag">${d.category_tag}</span>` : ''}
                    </div>
                    <a href="${d.url}" target="_blank" class="pdf-link">Source PDF</a>
                </td>`;
                
                // Content Cols
                COLS.forEach(key => {
                    const text = d[key] || "";
                    const isLong = text.length > 100;
                    
                    html += `<td>
                        <div class="cell-content">
                            ${text}
                        </div>
                        ${isLong ? '<button class="toggle-btn" onclick="toggle(this)">+</button>' : ''}
                    </td>`;
                });
                
                tr.innerHTML = html;
                tbody.appendChild(tr);
            });
            
            // Show buttons if needed (simple check via JS after render or inline logic)
            // The template logic above adds the button if string length > 100.
            // We need to ensure the button is display:block if present.
            document.querySelectorAll('.toggle-btn').forEach(btn => btn.style.display = 'block');
        }

        window.toggle = function(btn) {
            const div = btn.previousElementSibling;
            div.classList.toggle('expanded');
            btn.textContent = div.classList.contains('expanded') ? '–' : '+';
        }

        searchInput.addEventListener('input', e => render(e.target.value));

        render();
    </script>
</body>
</html>
"""

def parse_category_sort_key(classification):
    """
    Returns an integer for sorting classification.
    1 -> Cat 1
    ...
    5 -> Cat 5
    99 -> Other
    """
    if not classification:
        return 99, ""
        
    # Map Chinese numerals
    cn_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5}
    
    # Regex for "第X類"
    match = re.search(r'第([一二三四五0-9]+)類', classification)
    if match:
        val_str = match.group(1)
        val = cn_map.get(val_str)
        if not val and val_str.isdigit():
            val = int(val_str)
        
        if val:
            return val, f"第{val_str}類"
            
    return 99, ""

def main():
    print("Building minimalist dashboard...")
    try:
        with open("diseases.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: diseases.json not found.")
        return

    # Pre-process for sorting and tagging
    for d in data:
        sort_key, tag = parse_category_sort_key(d.get("疾病分類", ""))
        d['sort_key'] = sort_key
        d['category_tag'] = tag

    # Sort data by category list then name
    data.sort(key=lambda x: (x['sort_key'], x['name']))

    json_str = json.dumps(data, ensure_ascii=False)
    json_str = json_str.replace("</script>", "<\\/script>")

    final_html = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", json_str)

    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(final_html)
    
    print(f"Success! Generated dashboard.html with {len(data)} records, sorted by category.")

if __name__ == "__main__":
    main()
