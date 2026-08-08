// State management
let currentJobId = null;
let currentStatus = "idle";
let activeTab = "articles";
let ws = null;
let reconnectTimer = null;

// Discovered links map: url -> { element, status, page_type }
const discoveredLinksMap = new Map();

// DOM Elements
const rootUrlInput = document.getElementById("rootUrl");
const outputFormatSelect = document.getElementById("outputFormat");
const crawlForm = document.getElementById("crawlForm");
const startBtn = document.getElementById("startBtn");
const pauseBtn = document.getElementById("pauseBtn");
const resumeBtn = document.getElementById("resumeBtn");
const cancelBtn = document.getElementById("cancelBtn");
const jobStatusBadge = document.getElementById("jobStatusBadge");
const connectionStatus = document.getElementById("connectionStatus");
const connectionText = document.getElementById("connectionText");

const activeTaskPill = document.getElementById("activeTaskPill");
const activeTaskUrl = document.getElementById("activeTaskUrl");

const outputFolderBox = document.getElementById("outputFolderBox");
const folderPathText = document.getElementById("folderPathText");
const copyFolderBtn = document.getElementById("copyFolderBtn");

const statDiscovered = document.getElementById("statDiscovered");
const statCrawled = document.getElementById("statCrawled");
const statFailed = document.getElementById("statFailed");
const articleCount = document.getElementById("articleCount");
const discoveredCount = document.getElementById("discoveredCount");

const tabArticlesBtn = document.getElementById("tabArticlesBtn");
const tabLinksBtn = document.getElementById("tabLinksBtn");
const articlesTabContent = document.getElementById("articlesTabContent");
const linksTabContent = document.getElementById("linksTabContent");

const articlesList = document.getElementById("articlesList");
const linksList = document.getElementById("linksList");
const articlesEmptyState = document.getElementById("articlesEmptyState");
const linksEmptyState = document.getElementById("linksEmptyState");

const robotsModal = document.getElementById("robotsModal");
const robotsReasonText = document.getElementById("robotsReasonText");
const modalCancelBtn = document.getElementById("modalCancelBtn");
const modalProceedBtn = document.getElementById("modalProceedBtn");

// Tab Switching
function switchTab(tabName) {
    activeTab = tabName;
    if (tabName === "articles") {
        tabArticlesBtn.classList.add("active");
        tabLinksBtn.classList.remove("active");
        articlesTabContent.style.display = "block";
        linksTabContent.style.display = "none";
    } else {
        tabLinksBtn.classList.add("active");
        tabArticlesBtn.classList.remove("active");
        linksTabContent.style.display = "block";
        articlesTabContent.style.display = "none";
    }
}

// Initialize WebSocket Connection
function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/progress`;
    
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        connectionStatus.style.background = "rgba(16, 185, 129, 0.1)";
        connectionStatus.style.color = "#10b981";
        connectionText.textContent = "即時連線中";
    };

    ws.onclose = () => {
        connectionStatus.style.background = "rgba(244, 63, 94, 0.1)";
        connectionStatus.style.color = "#f43f5e";
        connectionText.textContent = "連線中斷，重連中...";
        clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(initWebSocket, 2000);
    };

    ws.onerror = () => {
        ws.close();
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleCrawlerEvent(data);
        } catch (e) {
            console.error("Error parsing WS message:", e);
        }
    };
}

// Handle WebSocket event streams
function handleCrawlerEvent(data) {
    if (data.status) {
        updateJobStatus(data.status);
    }
    
    if (data.stats) {
        updateStats(data.stats);
    }

    if (data.output_dir) {
        showOutputFolder(data.output_dir);
    }

    // Active URL changes
    if (data.event === "url_active") {
        setActiveUrl(data.url);
        updateLinkStatus(data.url, "fetching");
    }

    // New link discovered
    if (data.event === "url_discovered") {
        addDiscoveredLink(data.url, data.page_type, data.status || "pending");
    }

    // URL Status Change
    if (data.event === "url_status_change") {
        updateLinkStatus(data.url, data.status);
    }

    // Article Crawled
    if (data.event === "article_crawled") {
        addArticleToList(data.title, data.url, data.file_path);
        updateLinkStatus(data.url, "crawled");
    }

    // Job finalized
    if (data.event === "job_completed" || data.event === "job_failed" || data.event === "status_change") {
        if (data.status !== "running") {
            clearActiveUrl();
        }
    }
}

// Set Active URL in Header and in Links List
function setActiveUrl(url) {
    if (url) {
        activeTaskPill.style.display = "flex";
        activeTaskUrl.textContent = url;
        activeTaskUrl.title = url;
    } else {
        clearActiveUrl();
    }
}

function clearActiveUrl() {
    activeTaskPill.style.display = "none";
    document.querySelectorAll(".link-item.active-item").forEach(el => {
        el.classList.remove("active-item");
    });
}

// Add or update Discovered Link
function addDiscoveredLink(url, pageType, status) {
    if (discoveredLinksMap.has(url)) {
        updateLinkStatus(url, status);
        return;
    }

    linksEmptyState.style.display = "none";

    const li = document.createElement("li");
    li.className = "link-item";

    const info = document.createElement("div");
    info.className = "link-info";

    const urlEl = document.createElement("a");
    urlEl.className = "link-url";
    urlEl.href = url;
    urlEl.target = "_blank";
    urlEl.rel = "noopener noreferrer";
    urlEl.textContent = url;
    urlEl.title = url;

    info.appendChild(urlEl);

    const badge = document.createElement("span");
    badge.className = `link-badge ${status}`;
    badge.textContent = getLinkStatusText(status, pageType);

    li.appendChild(info);
    li.appendChild(badge);

    linksList.prepend(li);

    discoveredLinksMap.set(url, { element: li, badge: badge, pageType: pageType });
    updateDiscoveredCount(discoveredLinksMap.size);
}

function updateDiscoveredCount(newCount) {
    const currentCount = parseInt(statDiscovered.textContent) || 0;
    const bestCount = Math.max(currentCount, newCount);
    statDiscovered.textContent = bestCount;
    discoveredCount.textContent = bestCount;
}

function updateLinkStatus(url, status) {
    const item = discoveredLinksMap.get(url);
    if (item) {
        item.badge.className = `link-badge ${status}`;
        item.badge.textContent = getLinkStatusText(status, item.pageType);
        
        if (status === "fetching") {
            item.element.classList.add("active-item");
        } else {
            item.element.classList.remove("active-item");
        }
    }
}

function getLinkStatusText(status, pageType) {
    switch (status) {
        case "fetching": return "抓取中...";
        case "crawled": return pageType === "article" ? "已存檔" : "已索引";
        case "skipped": return "已略過";
        case "failed": return "失敗";
        default: return "等待中";
    }
}

// Update status badges and button states
function updateJobStatus(status) {
    currentStatus = status;
    jobStatusBadge.textContent = getStatusText(status);
    jobStatusBadge.className = `badge ${status}`;

    const inlineControls = document.getElementById("inlineControls");

    if (status === "running") {
        startBtn.style.display = "none";
        inlineControls.style.display = "flex";
        pauseBtn.style.display = "inline-flex";
        resumeBtn.style.display = "none";
        cancelBtn.style.display = "inline-flex";
        rootUrlInput.disabled = true;
        outputFormatSelect.disabled = true;
    } else if (status === "paused") {
        startBtn.style.display = "none";
        inlineControls.style.display = "flex";
        pauseBtn.style.display = "none";
        resumeBtn.style.display = "inline-flex";
        cancelBtn.style.display = "inline-flex";
    } else {
        startBtn.style.display = "inline-flex";
        inlineControls.style.display = "none";
        rootUrlInput.disabled = false;
        outputFormatSelect.disabled = false;
        clearActiveUrl();
    }
}

function getStatusText(status) {
    switch (status) {
        case "running": return "爬取進行中";
        case "paused": return "已暫停";
        case "completed": return "爬取完成";
        case "cancelled": return "已取消";
        case "failed": return "失敗";
        default: return "閒置中";
    }
}

// Update counters
function updateStats(stats) {
    if (stats.discovered !== undefined) {
        updateDiscoveredCount(stats.discovered);
    }
    if (stats.crawled_articles !== undefined) {
        statCrawled.textContent = stats.crawled_articles;
        articleCount.textContent = stats.crawled_articles;
    }
    if (stats.failed !== undefined) statFailed.textContent = stats.failed;
}

// Append new article to stream
function addArticleToList(title, url, filePath) {
    articlesEmptyState.style.display = "none";

    const li = document.createElement("li");
    li.className = "article-item";

    const info = document.createElement("div");
    info.className = "article-info";

    const titleEl = document.createElement("div");
    titleEl.className = "article-title";
    titleEl.textContent = title;

    const urlEl = document.createElement("a");
    urlEl.className = "article-url";
    urlEl.href = url;
    urlEl.target = "_blank";
    urlEl.rel = "noopener noreferrer";
    urlEl.textContent = url;
    urlEl.title = url;

    info.appendChild(titleEl);
    info.appendChild(urlEl);

    const badge = document.createElement("span");
    badge.className = "article-badge";
    badge.textContent = "已存檔";

    li.appendChild(info);
    li.appendChild(badge);

    articlesList.prepend(li);
    articleCount.textContent = articlesList.children.length;
}

// Show output directory
function showOutputFolder(dir) {
    outputFolderBox.style.display = "flex";
    folderPathText.textContent = dir;
}

// Start crawl job
async function startCrawl(ignoreRobots = false) {
    const rootUrl = rootUrlInput.value.trim();
    const outputFormat = outputFormatSelect.value;

    if (!rootUrl) return;

    // Reset lists for a fresh job
    discoveredLinksMap.clear();
    linksList.innerHTML = "";
    articlesList.innerHTML = "";
    statDiscovered.textContent = "0";
    statCrawled.textContent = "0";
    statFailed.textContent = "0";
    discoveredCount.textContent = "0";
    articleCount.textContent = "0";

    try {
        const res = await fetch("/api/crawl/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                root_url: rootUrl,
                output_format: outputFormat,
                ignore_robots: ignoreRobots
            })
        });

        const data = await res.json();

        if (data.status === "robots_warning") {
            robotsReasonText.textContent = data.reason || "Disallow: /";
            robotsModal.style.display = "flex";
            return;
        }

        if (res.ok) {
            currentJobId = data.job_id;
            updateJobStatus("running");
            if (data.output_dir) {
                showOutputFolder(data.output_dir);
            }
        } else {
            alert(data.detail || "無法啟動爬取工作");
        }
    } catch (e) {
        console.error(e);
        alert("啟動爬取時發生錯誤");
    }
}

// Control button handlers
crawlForm.onsubmit = (e) => {
    e.preventDefault();
    startCrawl(false);
};

pauseBtn.onclick = async () => {
    await fetch("/api/crawl/pause", { method: "POST" });
    updateJobStatus("paused");
};

resumeBtn.onclick = async () => {
    await fetch("/api/crawl/resume", { method: "POST" });
    updateJobStatus("running");
};

cancelBtn.onclick = async () => {
    if (confirm("確定要取消當前的爬取工作嗎？")) {
        await fetch("/api/crawl/cancel", { method: "POST" });
        updateJobStatus("cancelled");
    }
};

// Robots modal actions
modalCancelBtn.onclick = () => {
    robotsModal.style.display = "none";
};

modalProceedBtn.onclick = () => {
    robotsModal.style.display = "none";
    startCrawl(true);
};

// 1-Click Copy folder path
copyFolderBtn.onclick = () => {
    const path = folderPathText.textContent;
    navigator.clipboard.writeText(path).then(() => {
        alert("已複製儲存目錄路徑：" + path);
    });
};

// Initial state fetch
async function loadInitialState() {
    try {
        const res = await fetch("/api/crawl/status");
        if (res.ok) {
            const data = await res.json();
            if (data.job) {
                updateJobStatus(data.status);
                updateStats(data.stats);
                showOutputFolder(data.job.output_dir);
                if (data.active_url) {
                    setActiveUrl(data.active_url);
                }
                if (data.articles && data.articles.length > 0) {
                    articlesEmptyState.style.display = "none";
                    data.articles.forEach(a => addArticleToList(a.title, a.url, a.file_path));
                }
                if (data.urls && data.urls.length > 0) {
                    linksEmptyState.style.display = "none";
                    data.urls.forEach(u => addDiscoveredLink(u.url, u.page_type, u.status));
                }
            }
        }
    } catch (e) {
        console.error("Failed to load initial status", e);
    }
}

// Boot
window.onload = () => {
    initWebSocket();
    loadInitialState();
};
