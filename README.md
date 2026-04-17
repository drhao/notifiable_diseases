# 台灣法定傳染病定義儀表板 (Taiwan Notifiable Diseases Dashboard)

這是一個自動化工具專案，用於從台灣衛生福利部疾病管制署 (Taiwan CDC) 網站抓取「法定傳染病病例定義」與「防治工作手冊」，自動比對最新更新，並生成靜態 HTML 儀表板。

<<<<<<< HEAD
**最後更新日期:** 2026-04-17 10:50
=======
**最後更新日期:** 2026-04-17 10:50
>>>>>>> afd7788413d60e59fd03d941dee1bea0718a88a3

## 專案功能

* **雙儀表板設計**: 包含「病例定義 (Case Definitions)」及「防治工作手冊 (Disease Manuals)」雙獨立介面。
* **自動追蹤與文字差異化 (Text Diff)**: 每日自動比對最新 PDF 與歷史版本。針對 30 天內有異動的疾病，自動於網頁上標示「✨ 剛更新」，並對內文的刪除與新增段落進行 <del>刪除線</del> 與 **加亮粗體** 標註。
* **CI/CD 自動化**: 透過 GitHub Actions 每日下午依排程自動執行爬蟲與資料編譯，確保網頁與資料庫隨時與 CDC 官方同步。
* **PDF 解析與本地備份**: 將文件結構化解析提取欄位（臨床條件、流行病學等），並自動下載原始檔案存放於本地 `pdfs/` 及 `manual_pdfs/` 目錄。

## 專案結構

* `scraper.py` / `build_dashboard.py`: 負責「病例定義」的爬蟲與靜態頁面生成 (`index.html`)。
* `manual_scraper.py` / `build_manuals_dashboard.py`: 負責「防治工作手冊」的爬蟲與靜態頁面生成 (`manuals.html`)。
* `pdf_fetcher.py` / `data_parser.py`: PDF 網路抓取與正則表示式解析的核心公用腳本。
* `diseases.json` / `disease_manuals.json`: 本專案儲存所有已結構化及含有差異註記 (diff) 的原始 JSON 資料。
* `.github/workflows/daily-scraper.yml`: GitHub Actions 自動執行腳本。

## 如何使用

1. **安裝依賴套件**:

    ```bash
    pip install -r requirements.txt
    ```

    *(主要依賴: `requests`, `beautifulsoup4`, `pdfplumber`, `pandas`)*

2. **手動執行病例定義爬蟲**:

    ```bash
    python scraper.py
    python build_dashboard.py
    ```

3. **手動執行防治工作手冊爬蟲**:

    ```bash
    python manual_scraper.py
    python build_manuals_dashboard.py
    ```

    這會自動抓取尚未更新的部分並匯出 HTML。執行完畢後只需用瀏覽器打開 `index.html` 或是 `manuals.html` 即可。

## 技術說明

* **PDF 處理**: 使用 `pdfplumber` 進行文字提取。
* **版本控管快取**: 以擷取出的真實下載連結與 JSON 檔案相互比對，在尚未更新期間避免重複下載大量 PDF 以節省資源。
* **前後端分離 (SSG)**: Python 做為資料整理，產生含有所有內容的單一 HTML 檔案，內嵌 CSS/JS 與搜尋機制，完全不需要後端伺服器 (Serverless) 即可部屬於 Github Pages 上。

---
*Created by Antigravity*
