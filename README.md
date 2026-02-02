# 台灣法定傳染病定義儀表板 (Taiwan Notifiable Diseases Dashboard)

這是一個自動化工具專案，用於從台灣衛生福利部疾病管制署 (Taiwan CDC) 網站抓取法定傳染病的定義文件 (PDF)，並將其解析為結構化資料，最後生成一個現代化、易於閱讀的靜態 HTML 儀表板。

**最後更新日期:** 2026-02-02 09:58

## 專案功能

* **自動化爬蟲**: 自動抓取 CDC 網站上最新的法定傳染病列表與分類。
* **PDF 解析**: 下載並解析定義文件 PDF，提取關鍵章節（臨床條件、檢驗條件、流行病學條件、通報定義、疾病分類）。
* **本地備份**: 將所有 PDF 文件下載並儲存於本地 `pdfs/` 目錄，以便離線存取。
* **互動式儀表板**:
  * **分類導航**: 依照傳染病分類（第一類至第五類、其他）快速篩選。
  * **簡潔介面**: 清晰的表格佈局，包含搜尋功能與「顯示更多」的展開/收合設計。
  * **原始文件連結**: 直接連結至本地或線上 PDF 文件。

## 專案結構

* `scraper.py`: 主程式，負責協調整個流程（抓取連結 -> 下載 PDF -> 解析內容 -> 儲存資料）。
* `pdf_fetcher.py`:負責從 CDC 網站抓取疾病列表連結，以及下載 PDF 檔案。
* `data_parser.py`: 負責讀取 PDF 文字內容，並利用正規表達式 (Regex) 將其解析為六大結構化欄位。亦可單獨執行以重新解析本地檔案。
* `build_dashboard.py`: 讀取 `diseases.json` 資料，生成最終的 `index.html` 網頁。
* `diseases.json`: 儲存所有疾病結構化資料的 JSON 檔。
* `index.html`: 最終生成的靜態網頁儀表板。
* `pdfs/`: 存放下載的 PDF 原始檔。

## 如何使用

1. **安裝依賴套件**:

    ```bash
    pip install -r requirements.txt
    ```

    *(主要依賴: `requests`, `beautifulsoup4`, `pdfplumber`, `pandas`)*

2. **執行完整爬蟲與解析** (需連網):

    ```bash
    python scraper.py
    ```

    這會更新 `diseases.json`、`diseases.csv` 並下載新的 PDF。

3. **僅重新解析本地 PDF** (無需連網):

    ```bash
    python data_parser.py
    ```

    若您修改了解析邏輯，可執行此指令快速更新資料。

4. **生成儀表板**:

    ```bash
    python build_dashboard.py
    ```

    執行後請直接用瀏覽器打開 `index.html`。

## 技術說明

* **PDF 處理**: 使用 `pdfplumber` 進行高精準度的文字提取，並針對特殊 Unicode 字元與重複字元進行正規化處理。
* **資料解析**: 使用針對中文公文格式優化的 Regex 模式，精準識別「一、臨床條件」、「二、檢驗條件」等段落。
* **前端設計**: 生成單一 HTML 檔案，內嵌 CSS/JS，無需後端伺服器即可運作。使用 Inter 與 Noto Sans TC 字體提供優良的閱讀體驗。

---
*Created by Antigravity*
