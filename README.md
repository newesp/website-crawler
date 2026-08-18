# Website & YouTube Crawler

[![Tests & Quality Checks](https://github.com/newesp/website-crawler/actions/workflows/tests.yml/badge.svg)](https://github.com/newesp/website-crawler/actions/workflows/tests.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Coverage Quality Gate](https://img.shields.io/badge/coverage-%E2%89%A575%25-brightgreen.svg)](#-測試與品質保證-testing--quality-gate)

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

請確保已安裝 Python 3.10+（推薦 3.12+），並透過 `requirements.txt` 安裝相依套件：

```bash
pip install -r requirements.txt
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

## 🧪 測試與品質保證 (Testing & Quality Gate)

本專案實作自動化單元測試與整合測試，並於 GitHub Actions CI 每次 Push 與 Pull Request 自動驗證程式品質與測試覆蓋率。

### 測試策略 (Testing Strategy)

- **單元測試 (Unit Tests - `tests/unit/`)**：
  - URL 正規化 (`test_normalizer.py`)
  - 網頁類型與連結分類 (`test_classifier.py`)
  - HTML 內文與 Markdown 萃取轉換 (`test_extractor.py`)
  - HTTP 請求封裝與錯誤處置 (`test_fetcher.py`)
  - Robots.txt 語法與規則檢查 (`test_robots.py`)
  - 檔案匯出與路徑生成 (`test_exporter.py`)
- **整合測試 (Integration Tests - `tests/integration/`)**：
  - 爬蟲核心生命週期與優先佇列排程 (`test_crawler.py`)
  - 斷點續爬 (Resume / Incremental Crawling) 機制驗證 (`test_crawler.py`)
  - 網路 Timeout / 錯誤恢復與異常 HTML 容錯處理 (`test_crawler.py`)
  - SQLite 持久化與任務狀態更新 (`test_database.py`)
  - FastAPI RESTful API 與 WebSocket 推播 (`test_api.py`)
  - YouTube 影片萃取、二元搜尋與下載流程 (`test_youtube.py`)
- **隔離外部相依 (Deterministic & Offline-friendly)**：
  - 一般 CI 測試全數 Mock 外部網路請求（`httpx.MockTransport` / `unittest.mock`），杜絕因外網不穩定或網站結構變動導致的 Flaky Tests。

### 執行本機測試

```bash
# 執行全部測試
pytest -v

# 僅執行單元測試
pytest -m unit -v

# 僅執行整合測試
pytest -m integration -v
```

### 執行測試覆蓋率檢查 (Coverage Check)

```bash
pytest --cov=src --cov-report=term-missing --cov-fail-under=75
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
- [x] GitHub Actions CI 自動化測試與覆蓋率 Quality Gate
- [ ] 支援針對自定義網域撰寫自定義萃取規則（Extraction Rules）
