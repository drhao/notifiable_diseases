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
            max-height: 200px;
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

        /* Ensure scrolling lands correctly below header */
        .category-header-row {
            scroll-margin-top: 180px;
        }

        .category-header-row td {
            background: #f1f1f1;
            font-weight: 700;
            color: #000;
            padding: 0.75rem 1rem;
            font-size: 1rem;
            border-top: 2px solid #e5e5e5;
        }

        /* Nav Buttons */
        .nav-btn {
            background: #fff;
            border: 1px solid #e5e5e5;
            padding: 0.5rem 1rem;
            border-radius: 6px; /* slightly more square for better touch */
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.2s;
            color: #333;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        
        .nav-btn:hover {
            border-color: #000;
            color: #000;
            background: #fafafa;
            transform: translateY(-1px);
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
            font-size: 0.7rem;
            padding: 2px 6px;
            background: var(--tag-bg);
            border-radius: 4px;
            color: var(--text-secondary);
            margin-left: 8px;
            border: 1px solid var(--border-color);
            vertical-align: middle;
        }
        
        .pdf-link {
            font-size: 0.75rem;
            color: #000;
            text-decoration: none;
            opacity: 0.5;
            display: block;
            margin-top: 6px;
        }
        .pdf-link:hover { opacity: 1; text-decoration: underline; }

    </style>
</head>
<body>

    <header>
        <div class="header-top">
            <h1>TW Notifiable Diseases</h1>
            <div style="display:flex; gap:1rem; align-items:center">
                <select id="sortSelect" style="padding:0.5rem; border-radius:6px; border:1px solid #e5e5e5; font-size:0.9rem">
                    <option value="category">Sort by Category</option>
                    <option value="name">Sort by English Name</option>
                </select>
                <input type="text" id="searchInput" placeholder="Search diseases...">
            </div>
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
        const sortSelect = document.getElementById('sortSelect');
        
        // Initial Sort State
        let currentSort = 'category'; 

        const COLS = ["臨床條件", "檢驗條件", "流行病學條件", "通報定義", "疾病分類", "檢體採檢送驗事項"];

        // Group categories for navigation
        // Key map for sorting/labels
        const CAT_ORDER = [1, 5, 2, 3, 4, 99];
        const CAT_LABELS = {
            1: "Cat 1 第一類",
            2: "Cat 2 第二類",
            3: "Cat 3 第三類",
            4: "Cat 4 第四類",
            5: "Cat 5 第五類",
            99: "Other 其他"
        };

        function render(filter = '') {
            tbody.innerHTML = '';
            catNav.innerHTML = '';
            
            const f = filter.toLowerCase();
            let filtered = DATA.filter(d => 
                d.name.toLowerCase().includes(f) || 
                (d.english_name && d.english_name.toLowerCase().includes(f)) ||
                (d.content && d.content.toLowerCase().includes(f))
            );
            
            // Apply Sorting
            if (currentSort === 'name') {
                // Sort by English Name -> Chinese Name
                filtered.sort((a, b) => {
                    const enA = (a.english_name || a.name).toLowerCase();
                    const enB = (b.english_name || b.name).toLowerCase();
                    return enA.localeCompare(enB);
                });
                
                // Hide Category Nav when sorting by name
                catNav.style.display = 'none';
                
            } else {
                // Sort by Category Sort Key (which is already done in Python, but we can ensure it here)
                // Actually DATA comes sorted by category key from Python.
                // We just need to ensure we process them in order for grouping separators.
                
                 catNav.style.display = 'flex';
            }

            let lastCat = null;
            const catsFound = new Set();
            
            filtered.forEach((d, index) => {
                const currentCat = d.sort_key || 99;
                catsFound.add(currentCat);
                
                // Add Category Header Row if we are in Category Sort Mode
                if (currentSort === 'category' && currentCat !== lastCat) {
                    lastCat = currentCat;
                    
                    // Row for anchor
                    const headerRow = document.createElement('tr');
                    headerRow.className = 'category-header-row';
                    headerRow.id = `cat-${currentCat}`;
                    headerRow.innerHTML = `<td colspan="7">${CAT_LABELS[currentCat] || "Other"}</td>`;
                    tbody.appendChild(headerRow);
                }

                const tr = document.createElement('tr');
                
                // Name Col with tag inline + English Name
                let html = `<td>
                    <div><span style="font-weight:600">${d.name}</span>${d.category_tag ? `<span class="tag">${d.category_tag}</span>` : ''}</div>
                    ${d.english_name ? `<div style="font-size:0.8rem; color:#555; margin-top:2px">${d.english_name}</div>` : ''}
                    <a href="${d.url}" target="_blank" class="pdf-link">View PDF</a>
                </td>`;
                
                COLS.forEach(key => {
                    // For 檢體採檢送驗事項, show PDF link instead of content
                    if (key === "檢體採檢送驗事項") {
                        html += `<td>
                            <a href="${d.url}" target="_blank" class="pdf-link" style="opacity:1">詳見 PDF</a>
                        </td>`;
                    } else {
                        const text = d[key] || "";
                        html += `<td>
                            <div class="cell-content">${text}</div>
                            ${text ? '<button class="toggle-btn" onclick="toggle(this)" style="display:none">Show More</button>' : ''}
                        </td>`;
                    }
                });
                
                tr.innerHTML = html;
                tbody.appendChild(tr);
            });
            
            // Generate Nav Buttons
            CAT_ORDER.forEach(c => {
                if (catsFound.has(c)) {
                    const btn = document.createElement('button');
                    btn.className = 'nav-btn';
                    btn.textContent = CAT_LABELS[c];
                    btn.onclick = () => {
                        const el = document.getElementById(`cat-${c}`);
                        if(el) {
                            el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }
                    };
                    catNav.appendChild(btn);
                }
            });
            
            // Helper to check overflow
            setTimeout(() => {
                document.querySelectorAll('.cell-content').forEach(div => {
                    if (div.scrollHeight > div.clientHeight) {
                         const btn = div.nextElementSibling;
                         if (btn && btn.classList.contains('toggle-btn')) {
                             btn.style.display = 'inline-block';
                         }
                    }
                });
            }, 0);
        }

        window.toggle = function(btn) {
            const div = btn.previousElementSibling;
            div.classList.toggle('expanded');
            btn.textContent = div.classList.contains('expanded') ? 'Show Less' : 'Show More';
        }

        searchInput.addEventListener('input', e => render(e.target.value));
        sortSelect.addEventListener('change', (e) => {
            currentSort = e.target.value;
            render(searchInput.value);
        });

        render();
    </script>
</body>
</html>
"""

def parse_source_category(source_cat):
    """Convert source_category string to sort key."""
    if not source_cat:
        return 99
    cn_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5}
    match = re.search(r'第([一二三四五0-9]+)類', source_cat)
    if match:
        val_str = match.group(1)
        val = cn_map.get(val_str)
        if val:
            return val
        if val_str.isdigit():
            return int(val_str)
    return 99

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
    except FileNotFoundError:
        print("diseases.json not found")
        return

    for d in data:
        # Use source_category from scraper if available, fallback to parsing 疾病分類
        source_cat = d.get('source_category', '')
        if source_cat:
            d['sort_key'] = parse_source_category(source_cat)
            d['category_tag'] = source_cat
        else:
            # Fallback to parsing from content
            sort_key, tag = parse_category_sort_key(d.get("疾病分類", ""))
            d['sort_key'] = sort_key
            d['category_tag'] = tag

    # Sort order: 1, 5, 2, 3, 4, others (99)
    custom_order = {1: 0, 5: 1, 2: 2, 3: 3, 4: 4, 99: 5}
    data.sort(key=lambda x: (custom_order.get(x['sort_key'], 5), x['name']))
    json_str = json.dumps(data, ensure_ascii=False).replace("</script>", "<\\/script>")
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", json_str))
    
    print(f"Generated index.html with {len(data)} diseases.")

if __name__ == "__main__":
    main()
