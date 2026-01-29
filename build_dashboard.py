import json
import os
import re

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Taiwan Notifiable Diseases Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Sans+TC:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #ffffff;
            --text-primary: #111111;
            --text-secondary: #737373;
            --border-color: #e5e5e5;
            --table-header-color: #525252;
            --row-hover: #fafafa;
            --accent-color: #000000;
            --tag-bg: #f5f5f5;
            --nav-bg: rgba(255, 255, 255, 0.9);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; outline: none; }

        body {
            font-family: 'Inter', 'Noto Sans TC', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            padding: 2rem;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* Sticky Header with Nav */
        header {
            position: sticky;
            top: 0;
            z-index: 100;
            background: var(--nav-bg);
            backdrop-filter: blur(8px);
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 1rem;
        }

        .header-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding-top: 1rem;
        }

        h1 { font-size: 1.25rem; font-weight: 600; }

        #searchInput {
            padding: 0.5rem 1rem;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            font-size: 0.9rem;
            width: 240px;
        }

        /* Category Nav */
        .category-nav {
            display: flex;
            gap: 0.5rem;
            overflow-x: auto;
            padding-bottom: 0.5rem;
        }
        
        .nav-btn {
            background: #fff;
            border: 1px solid var(--border-color);
            padding: 0.4rem 0.8rem;
            border-radius: 99px;
            font-size: 0.8rem;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.2s;
            color: var(--text-secondary);
        }
        
        .nav-btn:hover {
            border-color: #000;
            color: #000;
        }
        
        .nav-btn.active {
            background: #000;
            color: #fff;
            border-color: #000;
        }

        /* Table */
        .table-container {
            flex: 1;
            overflow: auto;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: #fff;
        }

        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            min-width: 1600px;
        }
        
        thead {
            position: sticky;
            top: 0;
            z-index: 20;
            background: #f9f9f9;
        }
        
        th {
            text-align: left;
            font-weight: 600;
            color: var(--table-header-color);
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border-color);
            background: #f9f9f9;
            font-size: 0.85rem;
            white-space: nowrap;
        }

        td {
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            vertical-align: top;
            font-size: 0.9rem;
            color: #333;
            line-height: 1.6;
        }

        /* Essential for Line Breaks */
        .cell-content {
            white-space: pre-wrap; /* Preserves extract newlines */
            max-height: 120px;
            overflow: hidden;
            position: relative;
        }
        
        .cell-content.expanded {
            max-height: none;
        }

        /* Sticky First Column */
        th:first-child, td:first-child {
            position: sticky;
            left: 0;
            background: #fff;
            z-index: 10;
            width: 220px;
            min-width: 220px;
            border-right: 1px solid var(--border-color);
        }
        thead th:first-child {
            z-index: 30;
            background: #f9f9f9;
        }

        /* Category Header Row in Table */
        .category-header-row td {
            background: #f1f1f1;
            font-weight: 700;
            color: #000;
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
        }

        .toggle-btn {
            background: none;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 0.8rem;
            margin-top: 0.5rem;
            padding: 0;
            text-decoration: underline;
            display: none;
        }
        
        .tag {
            display: inline-block;
            font-size: 0.75rem;
            padding: 2px 6px;
            background: var(--tag-bg);
            border-radius: 4px;
            color: var(--text-secondary);
            margin-top: 4px;
            border: 1px solid var(--border-color);
        }
        
        .pdf-link {
            font-size: 0.75rem;
            color: #000;
            text-decoration: none;
            opacity: 0.5;
            display: block;
            margin-top: 4px;
        }
        .pdf-link:hover { opacity: 1; text-decoration: underline; }

    </style>
</head>
<body>

    <header>
        <div class="header-top">
            <h1>TW Notifiable Diseases</h1>
            <input type="text" id="searchInput" placeholder="Search...">
        </div>
        <div class="category-nav" id="catNav">
            <!-- Buttons injected by JS -->
        </div>
    </header>

    <div class="table-container" id="tableContainer">
        <table id="mainTable">
            <thead>
                <tr>
                    <th>Disease</th>
                    <th>Clinical Conditions <br><span style="opacity:0.6; font-weight:400">臨床條件</span></th>
                    <th>Lab Criteria <br><span style="opacity:0.6; font-weight:400">檢驗條件</span></th>
                    <th>Epidemiology <br><span style="opacity:0.6; font-weight:400">流行病學</span></th>
                    <th>Reporting <br><span style="opacity:0.6; font-weight:400">通報定義</span></th>
                    <th>Classification <br><span style="opacity:0.6; font-weight:400">疾病分類</span></th>
                    <th>Specimen <br><span style="opacity:0.6; font-weight:400">檢體採檢</span></th>
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
        const catNav = document.getElementById('catNav');
        const searchInput = document.getElementById('searchInput');
        const tableContainer = document.getElementById('tableContainer');

        const COLS = ["臨床條件", "檢驗條件", "流行病學條件", "通報定義", "疾病分類", "檢體採檢送驗事項"];

        // Group categories for navigation
        // Key map for sorting/labels
        const CAT_ORDER = [1, 2, 3, 4, 5, 99];
        const CAT_LABELS = {
            1: "第一類 Category 1",
            2: "第二類 Category 2",
            3: "第三類 Category 3",
            4: "第四類 Category 4",
            5: "第五類 Category 5",
            99: "Other 其他"
        };

        function render(filter = '') {
            tbody.innerHTML = '';
            catNav.innerHTML = '';
            
            const f = filter.toLowerCase();
            const filtered = DATA.filter(d => 
                d.name.toLowerCase().includes(f) || 
                (d.content && d.content.toLowerCase().includes(f))
            );

            // If filtering, we just show list. If not, we show categories headers.
            const isFiltered = filter.length > 0;
            
            let lastCat = null;
            const catsFound = new Set();
            
            filtered.forEach((d, index) => {
                const currentCat = d.sort_key || 99;
                
                // Add Section Header if category changes (only if not filtering heavily, though user might want it)
                // Let's always add it for structure if sorted.
                if (currentCat !== lastCat) {
                    lastCat = currentCat;
                    catsFound.add(currentCat);
                    
                    // Row for anchor
                    const headerRow = document.createElement('tr');
                    headerRow.className = 'category-header-row';
                    headerRow.id = `cat-${currentCat}`;
                    headerRow.innerHTML = `<td colspan="7">${CAT_LABELS[currentCat] || "Other"}</td>`;
                    tbody.appendChild(headerRow);
                }

                const tr = document.createElement('tr');
                
                // Name Col
                let html = `<td>
                    <div style="font-weight:600">${d.name}</div>
                    ${d.category_tag ? `<span class="tag">${d.category_tag}</span>` : ''}
                    <a href="${d.url}" target="_blank" class="pdf-link">PDF Source</a>
                </td>`;
                
                COLS.forEach(key => {
                    const text = d[key] || "";
                    const isLong = text.length > 150;
                    html += `<td>
                        <div class="cell-content ${isLong ? 'long' : ''}">${text}</div>
                        ${isLong ? '<button class="toggle-btn" onclick="toggle(this)">Show More</button>' : ''}
                    </td>`;
                });
                
                tr.innerHTML = html;
                tbody.appendChild(tr);
            });
            
            // Generate Nav Buttons based on what's visible
            CAT_ORDER.forEach(c => {
                if (catsFound.has(c)) {
                    const btn = document.createElement('button');
                    btn.className = 'nav-btn';
                    btn.textContent = CAT_LABELS[c].split(' ')[0]; // Just Chinese part for short btn
                    btn.title = CAT_LABELS[c];
                    btn.onclick = () => {
                        const el = document.getElementById(`cat-${c}`);
                        if(el) {
                            // Scroll container to element
                            // el.scrollIntoView({ behavior: 'smooth', block: 'start' }); 
                            // Sticky header might block it, so we need offset.
                            
                            // Simple offset calculation
                            const headerOffset = 180; // approx header height
                            const elementPosition = el.getBoundingClientRect().top;
                            const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
                            
                           // Since we are scrolling the BODY mostly or table container?
                           // We set body/main scroll.
                           // Actually the table is in a container.
                           // Wait, if we use browser native scrollIntoView on body...
                           
                           // Using scrollIntoView on the row usually puts it at top of view.
                           // But we have sticky header covering it.
                           // Let's use simple logic:
                           
                           const y = el.getBoundingClientRect().top + window.pageYOffset - 140;
                           window.scrollTo({top: y, behavior: 'smooth'});
                        }
                    };
                    catNav.appendChild(btn);
                }
            });
            
             document.querySelectorAll('.toggle-btn').forEach(btn => btn.style.display = 'inline-block');
        }

        window.toggle = function(btn) {
            const div = btn.previousElementSibling;
            div.classList.toggle('expanded');
            btn.textContent = div.classList.contains('expanded') ? 'Show Less' : 'Show More';
        }

        searchInput.addEventListener('input', e => render(e.target.value));

        render();
    </script>
</body>
</html>
"""

def parse_category_sort_key(classification):
    if not classification: return 99, ""
    match = re.search(r'第([一二三四五0-9]+)類', classification)
    if match:
        val_str = match.group(1)
        cn_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5}
        val = cn_map.get(val_str)
        if not val and val_str.isdigit(): val = int(val_str)
        if val: return val, f"第{val_str}類"
    return 99, ""

def main():
    try:
        with open("diseases.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError: return

    for d in data:
        sort_key, tag = parse_category_sort_key(d.get("疾病分類", ""))
        d['sort_key'] = sort_key
        d['category_tag'] = tag

    data.sort(key=lambda x: (x['sort_key'], x['name']))
    json_str = json.dumps(data, ensure_ascii=False).replace("</script>", "<\\/script>")
    
    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", json_str))

if __name__ == "__main__":
    main()
