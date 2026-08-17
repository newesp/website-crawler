# Website & YouTube Crawler

Website & YouTube Crawler 是一個功能強大且具備現代化操作介面的非同步網頁爬蟲與 YouTube 頻道影片連結擷取工具。

---

## 🌟 核心特色 (Features)

### 1. 🌐 網站文章爬蟲 (Website Article Crawler)
- **動態渲染與智慧降級**：預設使用輕量的 `httpx` / `BeautifulSoup` 進行高速請求，遇到空內容或動態渲染的頁面會自動切換至 Headless Browser (`Playwright`) 進行渲染與完整抓取。
- **文章優先佇列機制**：自動識別文章頁面（Article）與目錄頁面（Index），優先抓取文章正文，提高爬取效率。
- **支援斷點續爬 (Resume/Incremental)**：使用 SQLite 記錄每個 Job 與爬取歷史，中斷後重新啟動同一個網址會自動跳過已抓取的文章繼續爬取。
- **多格式輸出**：可選擇將文章保存為：
  - `Markdown (.md)`：乾淨的標題與正文（自動過濾不必要的側邊欄與選單）。
  - `HTML (.html)`：獨立且乾淨的 HTML 頁面結構。
- **尊重 Robots 協議**：爬取前自動讀取並解析目標網站的 `robots.txt`，並在遇到限制時於 UI 發出提醒，讓使用者決定是否繼續。

### 2. 🎥 YouTube 頻道影片擷取 (YouTube Video Extractor)
- **頻道網址自動正規化**：支援輸入各式頻道別名、handle、自訂網址或 `/videos` 連結，自動標準化為 `https://www.youtube.com/@ChannelName`。
- **精準日期區間過濾**：
  - 未輸入：抓取頻道所有公開影片。
  - 僅輸入開始日期：從該日期抓取至最新影片。
  - 僅輸入結束日期：從最早期影片抓取至指定結束日期。
  - 輸入起訖日期：抓取該區間內的公開影片。
- **高效二元搜尋 (Binary Search) 邊界定位**：結合快速清單抓取與二元搜尋日期探測演算法，在數百上千部影片中亦能高速精確定位日期邊界。
- **單一影片自動偵測模式**：直接貼上單一影片連結（`/watch`, `youtu.be`, `/shorts`, `/live`），表單自動切換為即時下載模式。
- **多元畫質選擇與 MP3 轉換**：支援 `1080p (最佳畫質 MP4)`、`720p (標準 MP4)` 以及 `MP3 音訊檔` 擷取與下載。
- **即時下載進度與平行下載**：清單每個項目均可獨立點擊「下載影片」，透過 WebSocket 即時反饋百分比與下載速度，並於下載完成後支援一鍵複製本機檔案路徑。
- **多種匯出與一鍵複製**：
  - 支援匯出純網址清單為 `CSV` 或 `TXT` 格式。
  - 支援一鍵複製所有擷取之影片網址到剪貼簿。

### 3. 💻 現代化 Web Dashboard
- **雙工具無縫切換**：頂部導航列可快速切換「網站爬蟲」與「YouTube 影片擷取」模式。
- **WebSocket 即時推播**：即時串流爬取進度、已發現連結狀態、即時活動 URL 與統計數據。
- **純原生現代化設計**：基於 Vanilla HTML5 / CSS3 / JavaScript，無額外龐大前端框架包袱，載入迅速且具備精美暗色風格。

---

## 🚀 系統架構 (Architecture)

整個專案由以下核心模組組成：

- **App (`src/app.py`)**：FastAPI 應用程式，提供 RESTful APIs、WebSocket 即時推播以及靜態檔案路由。
- **Crawler Engine (`src/crawler.py`)**：核心爬蟲排程引擎，負責管理優先佇列（Priority Queue）、爬取邏輯、延遲控制以及進度事件的發送。
- **YouTube Extractor (`src/youtube.py`)**：YouTube 頻道影片擷取器，基於 `yt-dlp` 與二元搜尋日期邊界演算法，支援網址正規化與 CSV/TXT 檔案匯出。
- **Extractor (`src/extractor.py`)**：文章萃取器，利用 BeautifulSoup 解析與淨化 HTML，並透過 markdownify 將 HTML 轉換為乾淨的 Markdown 格式。
- **Fetcher (`src/fetcher.py`)**：負責 HTTP 請求的封裝，實作了輕量請求與 Playwright 動態渲染的雙重回退機制。
- **Classifier (`src/classifier.py`)**：負責分析 URL 模式以及頁面內容，判斷是文章正文頁面還是目錄頁面。
- **Database (`src/database.py`)**：封裝 SQLite 邏輯，記錄 Job 狀態、爬取歷史與相關統計數據。
- **Robots Checker (`src/robots.py`)**：解析與檢查目標網站 `robots.txt` 爬取規則。
- **Frontend UI (`src/static/`)**：現代化響應式單頁應用（SPA），包含即時連線監控與雙模式操作面板。

---

## 🛠️ 安裝與執行 (Getting Started)

### 1. 安裝環境與依賴

請確保已安裝 Python 3.10+ 環境，然後安裝必要的套件：

```bash
pip install fastapi uvicorn httpx beautifulsoup4 playwright aiosqlite markdownify yt-dlp
```

如果是第一次使用 Playwright，請安裝瀏覽器執行核心：

```bash
playwright install chromium
```

### 2. 啟動服務

直接執行專案根目錄下的 `run.py` 啟動 FastAPI 服務：

```bash
python run.py
```
> 預設服務將運行在：`http://127.0.0.1:8000`

### 3. 操作使用

打開瀏覽器進入 `http://127.0.0.1:8000`：

#### 🌐 網站文章爬蟲
1. 切換至 **網站文章爬蟲** 分頁。
2. 輸入目標根網址（例如：`https://creationsjourneytolife.blogspot.com`）。
3. 選擇儲存格式 (`.md` 或 `.html`)，點擊 **開始爬取**。
4. 所有抓取成功的文章將自動歸檔於本地 `output/{domain}/` 資料夾中。

#### 🎥 YouTube 影片連結擷取
1. 切換至 **YouTube 影片擷取** 分頁。
2. 輸入 YouTube 頻道網址或 handle（例如：`https://www.youtube.com/@totality-of-life` 或 `@totality-of-life`）。
3. 自由設定 **開始日期** 與 **結束日期**（留空代表不限）。
4. 選擇匯出格式 (`CSV` 或 `TXT`)，點擊 **開始擷取影片連結**。
5. 擷取完成後可直接於網頁點擊下載純網址清單檔案，或點擊 **一鍵複製全部連結**。

---

## 🧪 測試 (Testing)

專案包含完整的 `pytest` 測試集，涵蓋 API 整合測試、爬蟲排程、分類器、YouTube 萃取與日期演算法等：

```bash
pytest tests -v
```

---

## 📝 開發里程碑 (Roadmap)

- [x] 核心非同步 Crawler 與 Priority Queue 機制
- [x] Playwright 與 httpx 雙軌自動降級機制
- [x] Markdown / HTML 內容淨化與結構化儲存
- [x] 暫停 / 繼續與 SQLite 斷點續爬功能
- [x] Robots.txt 規範檢查與警告確認
- [x] YouTube 頻道公開影片連結高速擷取
- [x] YouTube 發布日期區間過濾與二元搜尋加速
- [x] 現代化雙工具切換 Web Dashboard (WebSocket 即時更新)
- [ ] 支援針對自定義網域撰寫自定義萃取規則（Extraction Rules）
