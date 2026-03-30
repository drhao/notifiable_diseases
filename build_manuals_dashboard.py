import json
import os
from datetime import datetime

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>傳染病防治工作手冊 | Taiwan Disease Manuals</title>
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

        /* Nav Buttons */
        .nav-btn {
            background: #fff;
            border: 1px solid var(--border-color);
            padding: 0.4rem 0.8rem;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.2s;
            color: var(--text-secondary);
            text-decoration: none;
            display: inline-block;
        }
        
        .nav-btn:hover {
            border-color: #000;
            color: #000;
        }

        .nav-btn.primary {
            background: #000;
            color: #fff;
            border-color: #000;
        }
        .nav-btn.primary:hover {
            background: #333;
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
            min-width: 2200px;
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
            white-space: pre-wrap; 
            max-height: 180px;
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
            width: 180px;
            min-width: 180px;
            border-right: 1px solid var(--border-color);
        }
        thead th:first-child {
            z-index: 30;
            background: #f9f9f9;
        }

        @media (max-width: 768px) {
            body { padding: 1rem; }
            .header-top { flex-direction: column; align-items: flex-start; gap: 0.5rem; }
            #searchInput { width: 100%; }
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
        
        .pdf-link {
            font-size: 0.8rem;
            color: #2563eb;
            text-decoration: none;
            display: inline-block;
            margin-top: 8px;
            font-weight: 500;
        }
        .pdf-link:hover { text-decoration: underline; color: #1d4ed8; }

        .pdf-link:hover { text-decoration: underline; color: #1d4ed8; }

        .badge-update {
            display: inline-block;
            background: #fef08a;
            color: #854d0e;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-left: 6px;
            vertical-align: middle;
            border: 1px solid #fde047;
        }
        
        #recentUpdatesBanner {
            background: #fffbeb;
            border: 1px solid #fde68a;
            border-left: 4px solid #f59e0b;
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 6px;
            display: none;
        }

        /* Modal */
        .modal-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); z-index: 1000;
            display: none; justify-content: center; align-items: center;
        }
        .modal {
            background: #fff; padding: 2rem; border-radius: 12px;
            max-width: 600px; width: 90%; max-height: 90vh; overflow-y: auto;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }
        .modal h2 { margin-bottom: 1rem; color: var(--text-primary); }
        .modal p, .modal ul { margin-bottom: 1rem; color: #444; line-height: 1.6; }
        .modal ul { list-style: disc; padding-left: 1.5rem; }
        .close-modal {
            float: right; cursor: pointer; font-size: 1.8rem; line-height: 0.8; color: #888;
        }
        .close-modal:hover { color: #000; }
    </style>
</head>
<body>

    <header>
        <div class="header-top">
            <div>
                <h1>傳染病防治工作手冊 | Taiwan Disease Manuals</h1>
                <div style="font-size:0.8rem; color:#666; font-weight:400; margin-top:4px">最後更新： <!-- LAST_UPDATED --></div>
            </div>
            <div style="display:flex; gap:1rem; align-items:center; flex-wrap:wrap;">
                <a href="index.html" class="nav-btn primary">← 回到病例定義 (Case Definitions)</a>
                <button onclick="openModal()" class="nav-btn">關於 / About</button>
                <input type="text" id="searchInput" placeholder="Search diseases...">
            </div>
        </div>
    </header>

    <div id="recentUpdatesBanner"></div>
    
    <div class="table-container" id="tableContainer">
        <table id="mainTable">
            <thead>
                <tr>
                    <th>Disease Name<br><span style="opacity:0.6; font-weight:400">疾病名稱</span></th>
                    <th>Disease Description<br><span style="opacity:0.6; font-weight:400">疾病概述</span></th>
                    <th>Infectious Agent<br><span style="opacity:0.6; font-weight:400">致病原</span></th>
                    <th>Epidemiology<br><span style="opacity:0.6; font-weight:400">流行病學</span></th>
                    <th>Reservoir<br><span style="opacity:0.6; font-weight:400">傳染窩</span></th>
                    <th>Mode of Transmission<br><span style="opacity:0.6; font-weight:400">傳染方式</span></th>
                    <th>Incubation Period<br><span style="opacity:0.6; font-weight:400">潛伏期</span></th>
                    <th>Period of Communicability<br><span style="opacity:0.6; font-weight:400">可傳染期</span></th>
                    <th>Susceptibility & Resistance<br><span style="opacity:0.6; font-weight:400">感受性及抵抗力</span></th>
                    <th>Case Definition<br><span style="opacity:0.6; font-weight:400">病例定義</span></th>
                    <th>Specimen Collection<br><span style="opacity:0.6; font-weight:400">檢體採檢送驗事項</span></th>
                    <th>Prevention & Control<br><span style="opacity:0.6; font-weight:400">防疫措施</span></th>
                </tr>
            </thead>
            <tbody id="tableBody">
                <!-- Rows -->
            </tbody>
        </table>
    </div>

    <!-- About Modal -->
    <div id="aboutModal" class="modal-overlay">
        <div class="modal">
            <span class="close-modal" onclick="closeModal()">&times;</span>
            <h2>關於本儀表板 (About)</h2>
            <p>
                「傳染病防治工作手冊」儀表板彙整了台灣 CDC 針對各項法定傳染病所發布的工作手冊內容，方便快速查閱。
            </p>
            <h3>主要功能：</h3>
            <ul>
                 <li><b>快速搜尋 (Search)：</b> 支援病名及內容關鍵字即時篩選。</li>
                 <li><b>詳細內容 (Details)：</b> 點擊「Show More」可展開完整的流行病學、防疫措施等長篇規範。</li>
                 <li><b>原始文件 (PDF)：</b> 點擊疾病名稱下方的連結可直接下載 CDC 原始 PDF 檔案。</li>
                 <li><b>自動追蹤更新 (Auto-Update)：</b> 系統自動監控官網發布之最新 PDF，於 30 日內有異動時以 <span class="badge-update" style="margin:0 4px; pointer-events:none;">✨ 剛更新</span> 提示。</li>
                 <li><b>文字差異高亮 (Text Diff)：</b> 自動比對新舊版文件，改動部分將以<del>刪除線</del>與<b style="color:#ea580c; background:#ffedd5;">高亮粗體</b>呈現。</li>
            </ul>
             <br>
             <p style="font-size:0.9rem; color:#888; border-top:1px solid #eee; padding-top:1rem">
                資料來源：台灣衛生福利部疾病管制署 (Taiwan CDC)。<br>
                本專案為資訊整合工具，非官方網站，內容僅供參考，實際規範請以 CDC 公告為準。<br>
                系統最後更新時間： <!-- LAST_UPDATED -->
             </p>
        </div>
    </div>

    <script>
        const DATA = __DATA_PLACEHOLDER__;
        const tbody = document.getElementById('tableBody');
        const searchInput = document.getElementById('searchInput');

        const COLS = [
            "疾病概述", "致病原", "流行病學", "傳染窩", "傳染方式", 
            "潛伏期", "可傳染期", "感受性及抵抗力", "病例定義", "檢體採檢送驗事項", "防疫措施"
        ];
        
        const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

        function render(filter = '') {
            tbody.innerHTML = '';
            
            // Calculate Recent Updates
            const now = Date.now();
            const recentUpdates = [];
            const recentUpdateSet = new Set();
            
            DATA.forEach(d => {
                if (d.last_pdf_update) {
                    const updateTime = new Date(d.last_pdf_update).getTime();
                    if (now - updateTime <= THIRTY_DAYS_MS) {
                        recentUpdates.push(d.name);
                        recentUpdateSet.add(d.name);
                    }
                }
            });
            
            const banner = document.getElementById('recentUpdatesBanner');
            if (recentUpdates.length > 0) {
                const namesHtml = recentUpdates.map(name => `<a href="javascript:searchInput.value='${name}';render('${name}')" style="color:#b45309; text-decoration:underline; margin-right:8px; font-weight:500">${name}</a>`).join('');
                banner.innerHTML = `<span style="font-weight:600; color:#92400e;">✨ 剛更新 (最近30天內):</span> ${namesHtml}`;
                banner.style.display = 'block';
            } else {
                banner.style.display = 'none';
            }
            
            const f = filter.toLowerCase();
            let filtered = DATA.filter(d => {
                if (d.name.toLowerCase().includes(f)) return true;
                // Also search inside content
                for (let col of COLS) {
                    if (d[col] && d[col].toLowerCase().includes(f)) return true;
                }
                return false;
            });
            
            // Sort alphabetically by name
            filtered.sort((a, b) => a.name.localeCompare(b.name, 'zh-TW'));

            filtered.forEach(d => {
                const tr = document.createElement('tr');
                const isUpdated = recentUpdateSet.has(d.name);
                const updatedBadgeHtml = isUpdated ? `<span class="badge-update">✨ 剛更新</span>` : '';
                
                let html = `<td>
                    <div style="font-weight:600; font-size:1.05rem; margin-bottom:4px;">${d.name}${updatedBadgeHtml}</div>
                    <a href="${d.url}" target="_blank" class="pdf-link">下載 PDF 手冊 📥</a>
                </td>`;
                
                COLS.forEach(key => {
                    const text = (isUpdated && d[key + "_diff"]) ? d[key + "_diff"] : (d[key] || "");
                    html += `<td>
                        <div class="cell-content">${text}</div>
                        ${text.length > 100 ? '<button class="toggle-btn" onclick="toggle(this)" style="display:none">Show More</button>' : ''}
                    </td>`;
                });
                
                tr.innerHTML = html;
                tbody.appendChild(tr);
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

        // Modal Functions
        window.openModal = function() {
            document.getElementById('aboutModal').style.display = 'flex';
        }
        window.closeModal = function() {
            document.getElementById('aboutModal').style.display = 'none';
        }
        window.onclick = function(event) {
            const modal = document.getElementById('aboutModal');
            if (event.target == modal) {
                modal.style.display = "none";
            }
        }

        searchInput.addEventListener('input', e => render(e.target.value));

        render();
    </script>
</body>
</html>
"""

def main():
    try:
        with open("disease_manuals.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("disease_manuals.json not found")
        return

    json_str = json.dumps(data, ensure_ascii=False).replace("</script>", "<\\/script>")
    
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Try to grab the exact update timestamp from disease manuals JSON modification if metadata doesn't exist
    if os.path.exists("metadata.json"):
        try:
            with open("metadata.json", "r", encoding="utf-8") as f:
                meta = json.load(f)
                last_updated = meta.get("last_updated", last_updated)
        except Exception:
            pass
    elif os.path.exists("disease_manuals.json"):
        ts = os.path.getmtime("disease_manuals.json")
        last_updated = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

    html_content = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", json_str)
    html_content = html_content.replace("<!-- LAST_UPDATED -->", last_updated)
    
    with open("manuals.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Successfully generated manuals.html with {len(data)} manuals.")

if __name__ == "__main__":
    main()
