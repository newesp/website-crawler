# Website Crawler

Website Crawler 是一個功能強大且具備現代化操作介面的非同步網頁爬蟲與文章萃取引擎。目前針對通用型文章萃取以及 Blogspot 平台有特別的最佳化設計。

## 🌟 核心特色 (Features)

- **現代化互動介面**：提供精美的 Web Dashboard，可即時監控爬蟲進度、已發現連結與已抓取文章列表。
- **動態渲染與智慧降級**：預設使用輕量的 `httpx` / `BeautifulSoup` 進行高速請求，遇到空內容或動態渲染的頁面會自動無縫切換到 Headless Browser (`Playwright`) 進行渲染與抓取。
- **文章優先佇列機制**：自動識別文章頁面（Article）與目錄頁面（Index），並優先將資源用於抓取文章正文，提高爬取效率。
- **支援斷點續爬 (Resume/Incremental)**：使用 SQLite 記錄每個 Job 與爬取歷史，中斷後重新啟動同一個網址，會自動跳過已抓取的文章繼續爬取。
- **多格式輸出**：可選擇將文章保存為：
  - `Markdown (.md)`：乾淨的標題與正文（自動過濾不必要的側邊欄與選單）。
  - `HTML (.html)`：獨立且乾淨的 HTML 頁面結構。
- **尊重 Robots 協議**：爬取前自動讀取並解析目標網站的 `robots.txt`，並在遇到限制時於 UI 發出提醒，讓使用者決定是否繼續。
- **非同步與併發**：基於 `asyncio` 和 `FastAPI`，確保高效的非阻塞 I/O 處理。

## 🚀 系統架構 (Architecture)

整個專案由幾個核心模組組成：

- **App (`src/app.py`)**：FastAPI 應用程式，提供 RESTful APIs、WebSocket 即時推播以及靜態檔案路由。
- **Crawler Engine (`src/crawler.py`)**：核心排程引擎，負責管理優先佇列（Priority Queue）、爬取邏輯、延遲控制以及進度事件的發送。
- **Extractor (`src/extractor.py`)**：文章萃取器，利用 BeautifulSoup 解析與淨化 HTML，並透過 markdownify 將 HTML 轉換為乾淨的 Markdown 格式。
- **Fetcher (`src/fetcher.py`)**：負責 HTTP 請求的封裝，實作了輕量請求與 Playwright 動態渲染的雙重回退機制。
- **Classifier (`src/classifier.py`)**：負責分析 URL 模式以及頁面內容，判斷是文章正文頁面還是目錄頁面。
- **Database (`src/database.py`)**：封裝 SQLite 邏輯，記錄 Job 狀態、爬取歷史與相關統計數據。
- **Frontend UI (`src/static/`)**：基於 Vanilla JS 與原生 CSS 的現代化響應式單頁應用（SPA），透過 WebSocket 接收狀態。

## 🛠️ 安裝與執行 (Getting Started)

### 1. 安裝環境與依賴

請確保已安裝 Python 3.10+ 環境，然後安裝必要的套件：

```bash
pip install fastapi uvicorn httpx beautifulsoup4 playwright aiosqlite markdownify
```

如果您是第一次使用 Playwright，請安裝瀏覽器執行檔：

```bash
playwright install chromium
```

### 2. 啟動服務器

直接執行專案根目錄下的 `run.py` 啟動 FastAPI 服務：

```bash
python run.py
```
> 預設服務將會運行在：`http://127.0.0.1:8000`

### 3. 使用介面
打開瀏覽器進入 `http://127.0.0.1:8000` 即可看到控制台介面。
1. 輸入目標網址（例如：`https://creationsjourneytolife.blogspot.com`）。
2. 選擇你要儲存的格式 (`.md` 或 `.html`)。
3. 點擊 **開始爬取**。
4. 爬蟲進行時，您可以隨時點擊 **暫停** / **繼續** 或 **取消**。所有成功抓取的檔案將會自動歸檔於本地的 `output/{domain}/` 資料夾中。

## 🧪 測試 (Testing)

專案包含了高覆蓋率的 `pytest` 測試集，測試指令：

```bash
pytest tests -v
```

## 📝 開發規劃

- [x] 核心 Crawler 與 Queue 機制
- [x] Playwright 與 httpx 雙軌機制
- [x] Markdown 內容淨化與儲存
- [x] 暫停/繼續與斷點續爬功能
- [x] 現代化 UI 介面
- [x] Robots.txt 支援
- [ ] 支援針對自定義網域撰寫自定義萃取規則（Extraction Rules）
- [ ] 更多非 Blogspot 平台的泛用相容性調整
