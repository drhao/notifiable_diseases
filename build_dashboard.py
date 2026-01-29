import json
import os

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Taiwan Notifiable Diseases Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Noto+Sans+TC:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --card-border: rgba(148, 163, 184, 0.1);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.3);
            --modal-overlay: rgba(15, 23, 42, 0.85);
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
            background-image: 
                radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(139, 92, 246, 0.15) 0px, transparent 50%);
            background-attachment: fixed;
            color: var(--text-primary);
            min-height: 100vh;
            padding: 2rem;
        }

        /* Header */
        header {
            max-width: 1200px;
            margin: 0 auto 3rem auto;
            text-align: center;
        }

        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            background: linear-gradient(to right, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
        }

        .search-container {
            position: relative;
            max-width: 600px;
            margin: 0 auto;
        }

        #searchInput {
            width: 100%;
            padding: 1rem 1.5rem;
            border-radius: 99px;
            border: 1px solid var(--card-border);
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            color: var(--text-primary);
            font-size: 1.1rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }

        #searchInput:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 4px var(--accent-glow);
        }

        /* Grid */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
            max-width: 1200px;
            margin: 0 auto;
        }

        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
            transition: all 0.3s ease;
            cursor: pointer;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            height: 100%;
        }

        .card:hover {
            transform: translateY(-5px);
            border-color: rgba(56, 189, 248, 0.5);
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
        }

        .card-title {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: var(--text-primary);
        }

        .card-category {
            font-size: 0.875rem;
            color: var(--text-secondary);
            background: rgba(255, 255, 255, 0.05);
            padding: 0.25rem 0.75rem;
            border-radius: 99px;
            display: inline-block;
            margin-bottom: 1rem;
        }

        .card-preview {
            font-size: 0.9rem;
            color: var(--text-secondary);
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
            line-height: 1.5;
        }

        .read-more {
            margin-top: 1rem;
            font-size: 0.9rem;
            color: var(--accent);
            font-weight: 500;
            display: flex;
            align-items: center;
        }

        .read-more::after {
            content: '→';
            margin-left: 0.5rem;
            transition: transform 0.2s;
        }

        .card:hover .read-more::after {
            transform: translateX(4px);
        }

        /* Modal */
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: var(--modal-overlay);
            display: flex;
            justify-content: center;
            align-items: center;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
            backdrop-filter: blur(5px);
            z-index: 1000;
            padding: 2rem;
        }

        .modal.active {
            opacity: 1;
            pointer-events: all;
        }

        .modal-content {
            background: #1e293b;
            border: 1px solid var(--card-border);
            border-radius: 20px;
            width: 100%;
            max-width: 900px;
            max-height: 85vh;
            overflow-y: auto;
            position: relative;
            transform: scale(0.95);
            transition: transform 0.3s ease;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            padding: 3rem;
        }

        .modal.active .modal-content {
            transform: scale(1);
        }

        .close-btn {
            position: absolute;
            top: 1.5rem;
            right: 1.5rem;
            background: rgba(255, 255, 255, 0.1);
            border: none;
            color: var(--text-primary);
            width: 32px;
            height: 32px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 1.2rem;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
        }

        .close-btn:hover {
            background: rgba(255, 255, 255, 0.25);
        }

        .modal-title {
            font-size: 2rem;
            margin-bottom: 2rem;
            color: var(--text-primary);
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 1rem;
        }

        /* Detail Sections */
        .detail-section {
            margin-bottom: 2rem;
        }

        .detail-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--accent);
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
        }
        
        .detail-title::before {
            content: '';
            width: 6px;
            height: 6px;
            background: var(--accent);
            border-radius: 50%;
            margin-right: 0.75rem;
        }

        .detail-text {
            color: var(--text-secondary);
            line-height: 1.7;
            white-space: pre-wrap;
            background: rgba(0, 0, 0, 0.2);
            padding: 1rem;
            border-radius: 8px;
            font-size: 1rem;
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(148, 163, 184, 0.3);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(148, 163, 184, 0.5);
        }
        
        @media (max-width: 768px) {
            h1 { font-size: 1.8rem; }
            .modal-content { padding: 1.5rem; }
        }
    </style>
</head>
<body>

    <header>
        <h1>Notifiable Disease Explorer</h1>
        <div class="search-container">
            <input type="text" id="searchInput" placeholder="Search diseases (e.g., Dengue, Rabies)...">
        </div>
    </header>

    <main class="grid" id="cardGrid">
        <!-- Cards injected by JS -->
    </main>

    <!-- Modal -->
    <div class="modal" id="detailModal">
        <div class="modal-content">
            <button class="close-btn" id="closeModal">&times;</button>
            <h2 class="modal-title" id="modalTitle">Disease Name</h2>
            <div id="modalBody">
                <!-- Content injected by JS -->
            </div>
            <div style="margin-top:2rem; text-align:right;">
                 <a id="modalLink" href="#" target="_blank" style="color:var(--accent); text-decoration:none; font-size:0.9rem;">View Official Page &nearr;</a>
            </div>
        </div>
    </div>

    <script>
        // Data injected by Python build script
        const DATA = __DATA_PLACEHOLDER__;

        const grid = document.getElementById('cardGrid');
        const searchInput = document.getElementById('searchInput');
        const modal = document.getElementById('detailModal');
        const closeModal = document.getElementById('closeModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalBody = document.getElementById('modalBody');
        const modalLink = document.getElementById('modalLink');

        // Fields to display in modal
        const FIELDS = [
            "臨床條件",
            "檢驗條件",
            "流行病學條件",
            "通報定義",
            "疾病分類",
            "檢體採檢送驗事項"
        ];

        function renderCards(filterText = '') {
            grid.innerHTML = '';
            const lowerFilter = filterText.toLowerCase();

            const filteredAndSorted = DATA.filter(d => 
                d.name.toLowerCase().includes(lowerFilter) || 
                (d.content && d.content.toLowerCase().includes(lowerFilter))
            ).sort((a, b) => a.name.localeCompare(b.name, 'zh-TW'));

            filteredAndSorted.forEach(d => {
                const card = document.createElement('div');
                card.className = 'card';
                card.onclick = () => openModal(d);

                // Try to find a snippet
                // If "臨床條件" exists, use that.
                let snippet = d["臨床條件"] || d.content || "No details available.";
                if (snippet.length > 100) snippet = snippet.substring(0, 100) + '...';

                card.innerHTML = `
                    <div>
                        <h3 class="card-title">${d.name}</h3>
                        <span class="card-category">Disease</span>
                        <p class="card-preview">${snippet}</p>
                    </div>
                    <div class="read-more">View Case Definition</div>
                `;
                grid.appendChild(card);
            });
        }

        function openModal(data) {
            modalTitle.textContent = data.name;
            modalBody.innerHTML = '';
            modalLink.href = data.url;

            let hasStructured = false;

            FIELDS.forEach(field => {
                if (data[field] && data[field].trim()) {
                    hasStructured = true;
                    const sec = document.createElement('div');
                    sec.className = 'detail-section';
                    sec.innerHTML = `
                        <div class="detail-title">${field}</div>
                        <div class="detail-text">${data[field]}</div>
                    `;
                    modalBody.appendChild(sec);
                }
            });

            // If no structured data found (maybe processing failed?), show raw content
            if (!hasStructured) {
                const sec = document.createElement('div');
                sec.className = 'detail-section';
                sec.innerHTML = `
                    <div class="detail-title">Full Content</div>
                    <div class="detail-text">${data.content || "No content available."}</div>
                `;
                modalBody.appendChild(sec);
            }

            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }

        function close() {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }

        closeModal.onclick = close;
        modal.onclick = (e) => {
            if (e.target === modal) close();
        };
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') close();
        });

        searchInput.addEventListener('input', (e) => {
            renderCards(e.target.value);
        });

        // Initial render
        renderCards();

    </script>
</body>
</html>
"""

def main():
    print("Building dashboard...")
    try:
        with open("diseases.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: diseases.json not found.")
        return

    # Serialize data to JSON string for JS
    json_str = json.dumps(data, ensure_ascii=False)

    # In a real app we might escape the string to be safe against </script> attacks if data is untrusted.
    # For this internal tool, simple replacement is likely fine, but let's be slightly safer.
    # Replacing </script> with <\/script> 
    json_str = json_str.replace("</script>", "<\\/script>")

    final_html = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", json_str)

    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(final_html)
    
    print(f"Success! Generated dashboard.html with {len(data)} records.")

if __name__ == "__main__":
    main()
