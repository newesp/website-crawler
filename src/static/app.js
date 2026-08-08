// State management
let currentJobId = null;
let currentStatus = "idle";
let ws = null;
let reconnectTimer = null;

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

const outputFolderBox = document.getElementById("outputFolderBox");
const folderPathText = document.getElementById("folderPathText");
const copyFolderBtn = document.getElementById("copyFolderBtn");

const statDiscovered = document.getElementById("statDiscovered");
const statCrawled = document.getElementById("statCrawled");
const statFailed = document.getElementById("statFailed");
const articleCount = document.getElementById("articleCount");
const articlesList = document.getElementById("articlesList");
const emptyState = document.getElementById("emptyState");

const robotsModal = document.getElementById("robotsModal");
const robotsReasonText = document.getElementById("robotsReasonText");
const modalCancelBtn = document.getElementById("modalCancelBtn");
const modalProceedBtn = document.getElementById("modalProceedBtn");

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

    if (data.event === "article_crawled") {
        addArticleToList(data.title, data.url, data.file_path);
    }
}

// Update status badges and button states
function updateJobStatus(status) {
    currentStatus = status;
    jobStatusBadge.textContent = getStatusText(status);
    jobStatusBadge.className = `badge ${status}`;

    // Update button states
    if (status === "running") {
        startBtn.style.display = "none";
        pauseBtn.style.display = "inline-flex";
        resumeBtn.style.display = "none";
        cancelBtn.style.display = "inline-flex";
        rootUrlInput.disabled = true;
        outputFormatSelect.disabled = true;
    } else if (status === "paused") {
        startBtn.style.display = "none";
        pauseBtn.style.display = "none";
        resumeBtn.style.display = "inline-flex";
        cancelBtn.style.display = "inline-flex";
    } else {
        // Idle, Completed, Cancelled, Failed
        startBtn.style.display = "inline-flex";
        pauseBtn.style.display = "none";
        resumeBtn.style.display = "none";
        cancelBtn.style.display = "none";
        rootUrlInput.disabled = false;
        outputFormatSelect.disabled = false;
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
    if (stats.discovered !== undefined) statDiscovered.textContent = stats.discovered;
    if (stats.crawled_articles !== undefined) {
        statCrawled.textContent = stats.crawled_articles;
        articleCount.textContent = stats.crawled_articles;
    }
    if (stats.failed !== undefined) statFailed.textContent = stats.failed;
}

// Append new article to stream
function addArticleToList(title, url, filePath) {
    emptyState.style.display = "none";

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

    info.appendChild(titleEl);
    info.appendChild(urlEl);

    const badge = document.createElement("span");
    badge.className = "article-badge";
    badge.textContent = "已存檔";

    li.appendChild(info);
    li.appendChild(badge);

    articlesList.prepend(li);
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
            // Show modal
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
                if (data.articles && data.articles.length > 0) {
                    articlesList.innerHTML = "";
                    data.articles.forEach(a => addArticleToList(a.title, a.url, a.file_path));
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
