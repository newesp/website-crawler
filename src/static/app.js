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
    const jobEvents = ["job_started", "status_change", "job_completed", "job_failed"];
    if (data.status && jobEvents.includes(data.event)) {
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

    // YouTube Download Progress
    if (data.event === "youtube_download_progress") {
        handleYoutubeDownloadProgress(data);
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
    const completionBanner = document.getElementById("completionBanner");
    const completionText = document.getElementById("completionText");

    // Hide completion banner by default
    completionBanner.style.display = "none";

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

        // Show completion banner for terminal states
        if (status === "completed") {
            completionBanner.style.display = "flex";
            completionBanner.className = "completion-banner";
            completionText.textContent = "✔ 爬取完成！所有文章已儲存至本機資料夾";
        } else if (status === "cancelled") {
            completionBanner.style.display = "flex";
            completionBanner.className = "completion-banner cancelled";
            completionText.textContent = "⚠ 爬取已取消，已抓取的文章仍保留在本機";
        } else if (status === "failed") {
            completionBanner.style.display = "flex";
            completionBanner.className = "completion-banner failed";
            completionText.textContent = "✖ 爬取失敗，請檢查網址或網路連線後重試";
        } else if (status === "interrupted") {
            completionBanner.style.display = "flex";
            completionBanner.className = "completion-banner cancelled";
            completionText.textContent = "⚠ 上次爬取因程式重啟而中斷，重新輸入同一網址可繼續抓取";
        }
    }
}

function getStatusText(status) {
    switch (status) {
        case "running": return "爬取進行中";
        case "paused": return "已暫停";
        case "completed": return "爬取完成";
        case "cancelled": return "已取消";
        case "failed": return "失敗";
        case "interrupted": return "已中斷";
        default: return "閒置中";
    }
}

// Update counters
function updateStats(stats) {
    if (stats.discovered !== undefined) {
        updateDiscoveredCount(stats.discovered);
    }
    if (stats.crawled_articles !== undefined) {
        const skippedCount = stats.skipped || 0;
        const totalProcessed = stats.crawled_articles + skippedCount;
        statCrawled.textContent = totalProcessed;
        articleCount.textContent = stats.crawled_articles;
        
        const statSkipped = document.getElementById("statSkipped");
        if (statSkipped) statSkipped.textContent = skippedCount;
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
    const statSkipped = document.getElementById("statSkipped");
    if (statSkipped) statSkipped.textContent = "0";
    document.getElementById("completionBanner").style.display = "none";
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

// Tool Mode Switching (Website Crawler vs YouTube Extractor)
function switchToolMode(mode) {
    const toolCrawlerBtn = document.getElementById("toolCrawlerBtn");
    const toolYoutubeBtn = document.getElementById("toolYoutubeBtn");
    const crawlerView = document.getElementById("crawlerView");
    const youtubeView = document.getElementById("youtubeView");

    if (mode === "crawler") {
        toolCrawlerBtn.classList.add("active");
        toolYoutubeBtn.classList.remove("active");
        crawlerView.style.display = "grid";
        youtubeView.style.display = "none";
    } else {
        toolYoutubeBtn.classList.add("active");
        toolCrawlerBtn.classList.remove("active");
        youtubeView.style.display = "grid";
        crawlerView.style.display = "none";
        updateYtInputMode();
    }
}

// YouTube Video Extractor & Downloader Logic
const ytForm = document.getElementById("ytForm");
const ytChannelUrl = document.getElementById("ytChannelUrl");
const ytStartDate = document.getElementById("ytStartDate");
const ytEndDate = document.getElementById("ytEndDate");
const ytExportFormat = document.getElementById("ytExportFormat");
const ytQuality = document.getElementById("ytQuality");
const ytStartBtn = document.getElementById("ytStartBtn");
const ytStartDownloadBtn = document.getElementById("ytStartDownloadBtn");
const ytDateFilterGroup = document.getElementById("ytDateFilterGroup");
const ytExportFormatGroup = document.getElementById("ytExportFormatGroup");
const ytUrlHelper = document.getElementById("ytUrlHelper");

const ytStatusBadge = document.getElementById("ytStatusBadge");
const ytOutputBox = document.getElementById("ytOutputBox");
const ytExportSummaryText = document.getElementById("ytExportSummaryText");
const ytExportFilenameText = document.getElementById("ytExportFilenameText");
const ytDownloadLink = document.getElementById("ytDownloadLink");
const ytVideoCount = document.getElementById("ytVideoCount");
const ytVideoList = document.getElementById("ytVideoList");
const ytEmptyState = document.getElementById("ytEmptyState");
const ytCopyAllBtn = document.getElementById("ytCopyAllBtn");

let currentYoutubeVideos = [];
const activeDownloads = new Map(); // videoId -> { item, btn, url, filePath }

function isSingleVideoUrl(url) {
    if (!url) return false;
    url = url.trim();
    return /(?:youtube\.com\/watch|youtu\.be\/|youtube\.com\/shorts\/|youtube\.com\/live\/)/i.test(url);
}

function extractVideoId(url) {
    if (!url) return null;
    try {
        if (url.includes("youtu.be/")) {
            const parts = url.split("youtu.be/")[1].split(/[?#&]/)[0];
            if (parts) return parts;
        }
        if (url.includes("/shorts/")) {
            const parts = url.split("/shorts/")[1].split(/[?#&]/)[0];
            if (parts) return parts;
        }
        if (url.includes("/live/")) {
            const parts = url.split("/live/")[1].split(/[?#&]/)[0];
            if (parts) return parts;
        }
        const match = url.match(/[?&]v=([a-zA-Z0-9_-]+)/);
        if (match) return match[1];
        const match2 = url.match(/(?:watch\?v=|youtu\.be\/|shorts\/|live\/)([a-zA-Z0-9_-]{11})/i);
        return match2 ? match2[1] : null;
    } catch (e) {
        return null;
    }
}

function updateYtInputMode() {
    if (!ytChannelUrl) return;
    const url = ytChannelUrl.value.trim();
    const isSingle = isSingleVideoUrl(url);

    if (ytDateFilterGroup) {
        ytDateFilterGroup.style.display = isSingle ? "none" : "block";
    }
    if (ytExportFormatGroup) {
        ytExportFormatGroup.style.display = isSingle ? "none" : "block";
    }
    if (ytStartBtn) {
        ytStartBtn.style.display = isSingle ? "none" : "inline-flex";
    }
    if (ytStartDownloadBtn) {
        ytStartDownloadBtn.style.display = isSingle ? "inline-flex" : "none";
    }
    if (ytUrlHelper) {
        ytUrlHelper.textContent = isSingle 
            ? "✔ 偵測到單一影片網址：已切換為直接下載模式" 
            : "支援頻道 (@name, /channel/...) 或單一影片 (watch?v=..., youtu.be/..., shorts/...)";
        ytUrlHelper.style.color = isSingle ? "#10b981" : "";
    }
}

if (ytChannelUrl) {
    ytChannelUrl.addEventListener("input", updateYtInputMode);
    ytChannelUrl.addEventListener("change", updateYtInputMode);
    ytChannelUrl.addEventListener("keyup", updateYtInputMode);
    ytChannelUrl.addEventListener("focus", updateYtInputMode);
    ytChannelUrl.addEventListener("blur", updateYtInputMode);
    ytChannelUrl.addEventListener("paste", () => setTimeout(updateYtInputMode, 20));
}

// WebSocket Download Progress Handler
function handleYoutubeDownloadProgress(data) {
    const vidId = data.video_id;
    const downloadEntry = activeDownloads.get(vidId);
    let btn = downloadEntry ? downloadEntry.btn : null;

    if (!btn) {
        const itemEl = document.querySelector(`[data-video-id="${vidId}"]`);
        if (itemEl) {
            btn = itemEl.querySelector(".btn-dl-video");
        }
    }

    if (!btn) return;

    if (data.status === "downloading") {
        btn.className = "btn-dl-video downloading";
        btn.disabled = true;
        const speedText = data.speed ? ` (${data.speed})` : '';
        btn.innerHTML = `<span class="dl-spin">⏳</span> ${data.percent}%${speedText}`;
    } else if (data.status === "finished") {
        btn.className = "btn-dl-video completed";
        btn.disabled = false;
        btn.innerHTML = `✔ 已下載`;
        if (data.file_path) {
            if (downloadEntry) downloadEntry.filePath = data.file_path;
            btn.title = `點擊複製路徑: ${data.file_path}`;
            btn.onclick = () => {
                navigator.clipboard.writeText(data.file_path).then(() => {
                    alert("已複製本機檔案路徑：\n" + data.file_path);
                });
            };
        }
    } else if (data.status === "error") {
        btn.className = "btn-dl-video failed";
        btn.disabled = false;
        btn.innerHTML = `✖ 失敗 (重試)`;
    }
}

// Download Single Video Core Routine
async function downloadSingleVideo(url, quality, itemElement) {
    const vidId = extractVideoId(url) || url;
    const btn = itemElement ? itemElement.querySelector(".btn-dl-video") : null;

    if (btn) {
        btn.className = "btn-dl-video downloading";
        btn.disabled = true;
        btn.innerHTML = `<span class="dl-spin">⏳</span> 下載準備中...`;
    }

    activeDownloads.set(vidId, { item: itemElement, btn: btn, url: url, filePath: null });

    try {
        const res = await fetch("/api/youtube/download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url, quality })
        });

        const data = await res.json();
        if (!res.ok || data.status !== "success") {
            throw new Error(data.detail || data.error || "下載失敗");
        }

        if (btn) {
            btn.className = "btn-dl-video completed";
            btn.disabled = false;
            btn.innerHTML = `✔ 已下載`;
            const finalPath = data.file_path || "";
            btn.title = `點擊複製路徑: ${finalPath}`;
            btn.onclick = () => {
                if (finalPath) {
                    navigator.clipboard.writeText(finalPath).then(() => {
                        alert("已複製本機檔案路徑：\n" + finalPath);
                    });
                }
            };
        }

        // Update item title if available
        if (itemElement && data.title) {
            const titleEl = itemElement.querySelector(".yt-video-title");
            if (titleEl && titleEl.textContent.startsWith("單一影片下載")) {
                titleEl.textContent = data.title;
            }
        }
    } catch (err) {
        console.error("Video download error:", err);
        if (btn) {
            btn.className = "btn-dl-video failed";
            btn.disabled = false;
            btn.innerHTML = `✖ 失敗 (重試)`;
            btn.onclick = () => downloadSingleVideo(url, quality, itemElement);
        }
        alert(`影片下載失敗：${err.message}`);
    }
}

function renderVideoItem(video, idx) {
    const li = document.createElement("li");
    li.className = "yt-video-item";
    const vidId = extractVideoId(video.url) || video.id || `vid_${idx}`;
    li.setAttribute("data-video-id", vidId);

    const displayTitle = video.title ? video.title : `影片 #${idx + 1}`;

    li.innerHTML = `
        <div class="yt-video-info">
            <span class="yt-video-title">${displayTitle}</span>
            <a href="${video.url}" target="_blank" rel="noopener noreferrer" class="yt-video-url">
                ${video.url}
                <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
            </a>
        </div>
        <div class="yt-video-actions">
            <button type="button" class="btn-dl-video" title="下載此影片">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                下載影片
            </button>
        </div>
    `;

    const dlBtn = li.querySelector(".btn-dl-video");
    dlBtn.onclick = () => {
        const quality = ytQuality ? ytQuality.value : "1080p";
        downloadSingleVideo(video.url, quality, li);
    };

    return li;
}

// Single Video Start Download Handler
if (ytStartDownloadBtn) {
    ytStartDownloadBtn.onclick = async () => {
        const url = ytChannelUrl.value.trim();
        if (!url) return;
        const quality = ytQuality ? ytQuality.value : "1080p";

        ytEmptyState.style.display = "none";
        ytVideoList.style.display = "block";

        const videoId = extractVideoId(url) || "video";
        let existingLi = document.querySelector(`[data-video-id="${videoId}"]`);
        if (!existingLi) {
            existingLi = renderVideoItem({
                url: url,
                title: `單一影片下載 (${url})`,
                id: videoId
            }, ytVideoList.children.length);
            ytVideoList.prepend(existingLi);
            ytVideoCount.textContent = ytVideoList.children.length;
        }

        downloadSingleVideo(url, quality, existingLi);
    };
}

if (ytForm) {
    ytForm.onsubmit = async (e) => {
        e.preventDefault();
        const channelUrl = ytChannelUrl.value.trim();
        if (!channelUrl) return;

        // If in single video mode, redirect to single download
        if (isSingleVideoUrl(channelUrl)) {
            if (ytStartDownloadBtn) ytStartDownloadBtn.click();
            return;
        }

        const startDate = ytStartDate.value || null;
        const endDate = ytEndDate.value || null;
        const exportFormat = ytExportFormat.value || "csv";

        // Update UI to loading state
        ytStartBtn.disabled = true;
        ytStartBtn.innerHTML = `<span class="pulse-dot" style="display:inline-block; margin-right:6px;"></span> 正在分析頻道與抓取影片...`;
        ytStatusBadge.textContent = "擷取中...";
        ytStatusBadge.className = "badge badge-running";

        try {
            const res = await fetch("/api/youtube/extract", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    channel_url: channelUrl,
                    start_date: startDate,
                    end_date: endDate,
                    export_format: exportFormat
                })
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || "擷取失敗");
            }

            const data = await res.json();
            currentYoutubeVideos = data.video_urls || [];
            const videosData = data.videos || [];

            // Update stats and download box
            ytVideoCount.textContent = data.total_count || 0;
            ytExportSummaryText.textContent = `共擷取 ${data.total_count || 0} 部影片`;
            ytExportFilenameText.textContent = data.export_filename;
            ytDownloadLink.href = `/api/youtube/download/${data.export_filename}`;
            ytDownloadLink.setAttribute("download", data.export_filename);
            ytOutputBox.style.display = "flex";

            // Render list
            ytVideoList.innerHTML = "";
            if (videosData.length > 0) {
                ytEmptyState.style.display = "none";
                ytVideoList.style.display = "block";
                ytCopyAllBtn.style.display = "inline-flex";

                videosData.forEach((video, idx) => {
                    const li = renderVideoItem(video, idx);
                    ytVideoList.appendChild(li);
                });
            } else {
                ytEmptyState.style.display = "flex";
                ytEmptyState.innerHTML = `
                    <div class="empty-icon">🔍</div>
                    <p>未找到符合條件的影片</p>
                    <small>請確認日期範圍或頻道網址是否正確</small>
                `;
                ytVideoList.style.display = "none";
                ytCopyAllBtn.style.display = "none";
            }

            ytStatusBadge.textContent = "擷取完成";
            ytStatusBadge.className = "badge badge-completed";
        } catch (err) {
            console.error("YouTube extract error:", err);
            alert("YouTube 影片擷取失敗：" + err.message);
            ytStatusBadge.textContent = "擷取失敗";
            ytStatusBadge.className = "badge badge-failed";
        } finally {
            ytStartBtn.disabled = false;
            ytStartBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                開始擷取影片連結
            `;
        }
    };
}

if (ytCopyAllBtn) {
    ytCopyAllBtn.onclick = () => {
        if (currentYoutubeVideos.length === 0) return;
        const text = currentYoutubeVideos.join("\n");
        navigator.clipboard.writeText(text).then(() => {
            alert(`已複製 ${currentYoutubeVideos.length} 個影片連結到剪貼簿！`);
        });
    };
}

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
    if (typeof updateYtInputMode === "function") {
        updateYtInputMode();
    }
};

