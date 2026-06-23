# 台灣法定傳染病定義儀表板 (Taiwan Notifiable Diseases Dashboard)

這是一個自動化工具專案，用於從台灣衛生福利部疾病管制署 (Taiwan CDC) 網站抓取「法定傳染病病例定義」與「防治工作手冊」，自動比對最新更新，並生成靜態 HTML 儀表板。

**最後更新日期:** 2026-06-23 12:30

## 專案功能

* **雙儀表板設計**: 包含「病例定義 (Case Definitions)」及「防治工作手冊 (Disease Manuals)」雙獨立介面。
* **自動追蹤與文字差異化 (Text Diff)**: 每日自動比對最新 PDF 與歷史版本。針對 30 天內有異動的疾病，自動於網頁上標示「✨ 剛更新」，並對內文的刪除與新增段落進行 <del>刪除線</del> 與 **加亮粗體** 標註。
* **CI/CD 自動化**: 透過 GitHub Actions 每日下午依排程自動執行爬蟲與資料編譯，確保網頁與資料庫隨時與 CDC 官方同步。
* **PDF 解析與本地備份**: 將文件結構化解析提取欄位（臨床條件、流行病學等），並自動下載原始檔案存放於本地 `pdfs/` 及 `manual_pdfs/` 目錄。

## 專案結構

* `scraper.py` / `build_dashboard.py`: 負責「病例定義」的爬蟲與靜態頁面生成 (`index.html`)。
* `manual_scraper.py` / `build_manuals_dashboard.py`: 負責「防治工作手冊」的爬蟲與靜態頁面生成 (`manuals.html`)。
* `cdc_common.py`: 共用的下載核心 —— 統一的 `requests.Session`（含 User-Agent 與自動 retry/backoff）以及 PDF 下載 → sha256 雜湊比對 → `pdfplumber` 文字擷取流程。
* `pdf_fetcher.py` / `data_parser.py`: 病例定義頁面的連結抓取與正則表示式解析腳本。
* `diseases.json` / `disease_manuals.json`: 本專案儲存所有已結構化及含有差異註記 (diff) 的原始 JSON 資料。
* `.github/workflows/daily-scraper.yml`: GitHub Actions 自動執行腳本。

> **部署說明**：生成的 `index.html` / `manuals.html` 屬於建置產物，已不再納入 git 版控（避免每日約 1.7 MB 的歷史膨脹），改由 workflow 直接發布到 GitHub Pages。
>
> ⚠️ **一次性設定**：請至 repo 的 **Settings → Pages → Build and deployment → Source** 選擇 **「GitHub Actions」**。在切換之前，Pages 部署步驟會失敗（但爬蟲與資料更新仍會正常執行）。

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

## 測試

解析邏輯（`data_parser.py`、`manual_scraper.parse_manual_text`）皆為純文字處理，已用 `pytest` 撰寫回歸測試，無需網路或 PDF 即可執行：

```bash
pip install -r requirements-dev.txt
pytest
```

測試涵蓋 PDF 擷取常見的怪異情形（重複字元、半形標點、編號標題、病例分類關鍵字等），CI 也會在每次 push / PR 自動執行（見 `.github/workflows/tests.yml`）。

## 技術說明

* **PDF 處理**: 使用 `pdfplumber` 進行文字提取。
* **版本控管快取**: 以擷取出的真實下載連結與 JSON 檔案相互比對，在尚未更新期間避免重複下載大量 PDF 以節省資源。
* **前後端分離 (SSG)**: Python 做為資料整理，產生含有所有內容的單一 HTML 檔案，內嵌 CSS/JS 與搜尋機制，完全不需要後端伺服器 (Serverless) 即可部屬於 Github Pages 上。
* **更新訂閱**: 每次執行會產生 `feed.xml`（RSS 2.0）並隨 Pages 一併發布，可用 RSS 閱讀器訂閱最新異動。

## 開放資料 API

每次更新會把結構化資料以**靜態 JSON** 發布到 GitHub Pages 的 `api/v1/`（純靜態檔、由 CDN 服務，可程式化取用）：

| 端點 | 內容 |
|---|---|
| `api/v1/summary.json` | 精簡清單（名稱／英文名／分類／更新日期）— **建議優先使用** |
| `api/v1/diseases.json` | 完整病例定義 |
| `api/v1/manuals.json` | 完整防治工作手冊 |
| `api/v1/meta.json` | 筆數、產生時間、授權與資料來源 |

請善用 HTTP 快取（CDN 已提供 `ETag`，重複抓取以 `If-None-Match` 取得 `304` 可大幅節省流量）。

## 授權

本專案程式碼以 [MIT License](LICENSE) 釋出。原始疾病資料來自衛生福利部疾病管制署（Taiwan CDC）公開資訊，其著作權與使用條款依該署規定。

---
*Created by Antigravity*
