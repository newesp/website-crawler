# Website Crawler

A web application that crawls a target website, discovers and extracts article pages, and saves them locally in user-selected formats.

## Language

**Crawl Job**:
A single crawl session targeting one root URL. Only one job can be active at a time.
_Avoid_: Task, run, session

**Root URL**:
The starting URL provided by the user. Defines the host boundary for the crawl.
_Avoid_: Seed URL, start URL, base URL

**Host Boundary**:
The constraint that only URLs sharing the same hostname as the root URL are eligible for crawling.
_Avoid_: Domain boundary, scope

**Discovery**:
The process of following links on crawled pages to find new candidate URLs within the host boundary.
_Avoid_: Spidering, link extraction

**Candidate URL**:
A URL found during discovery that has not yet been classified or crawled.
_Avoid_: Found URL, pending URL

**Candidate Priority Queue**:
A priority queue where candidate URLs are scheduled such that Article Pages are dequeued and extracted before Index Pages.
_Avoid_: Task list, URL stack

**Active URL**:
The specific URL currently being fetched and processed by the crawler, highlighted in real-time in the UI.
_Avoid_: Current link, working item

**Article Page**:
A page containing a single blog post or article with a title and body content. Distinguished from index pages by URL pattern (for Blogspot: `/<year>/<month>/<slug>.html`).
_Avoid_: Post page, content page

**Index Page**:
A page used only for discovery (e.g., homepage, archive pages, tag/label pages). Its content is never saved.
_Avoid_: Navigation page, listing page, taxonomy page

**URL Normalization**:
The process of stripping query parameters (e.g., `?m=1`), fragments (e.g., `#comments`), and trailing slashes to produce a canonical URL for deduplication.
_Avoid_: URL cleaning, URL canonicalization

**Content Extraction**:
The process of isolating the article title and main body text from a full HTML page, discarding navigation, sidebars, ads, comments, and images.
_Avoid_: Parsing, scraping

**Output Format**:
The file format chosen by the user for saved articles: Markdown (`md`) or HTML (`html`).
_Avoid_: Save format, export format

**Slug**:
The URL path segment used as the filename for a saved article (e.g., `day-574-using-shame-as-motivation`).
_Avoid_: Filename, identifier

**Crawl State**:
The persistent record (in SQLite) of which URLs have been crawled, failed, or remain pending for a given root URL. Enables resume and incremental updates.
_Avoid_: Progress, checkpoint

**Tabbed Stream View**:
The dashboard presentation splitting real-time progress into two dedicated tabs: Crawled Articles and Discovered Links.
_Avoid_: Multi-panel view, split screen

**Fallback Rendering**:
When a lightweight HTTP request (httpx) returns empty content, the system retries using a headless browser to handle JavaScript-rendered pages.
_Avoid_: Dynamic rendering, JS rendering

**Politeness Delay**:
A 1–2 second pause between consecutive HTTP requests to avoid overwhelming the target server.
_Avoid_: Rate limit, throttle, backoff

**YouTube Channel URL**:
The canonical Root URL for the YouTube video crawler. All input formats (e.g., `/channel/UC...`, `/c/...`) are normalized to `https://www.youtube.com/@ChannelName`.
_Avoid_: User URL, custom URL

**Video Link**:
A discovered YouTube video URL belonging to the channel. Treated as a "Discovered Link" in the UI rather than an "Article Page" because its content is not extracted.
_Avoid_: Video page, YouTube article

**Video List Export**:
The final output of the YouTube crawler, which is a plain text or CSV file containing only the video URLs, without any extracted body content.
_Avoid_: Extracted videos, scraped content

**Publish Date Filter**:
A date range filter evaluated against the video's public publish date, converted and compared in the user's local timezone.
_Avoid_: Upload date, stream date

**Video Download Job**:
An asynchronous task triggered to download a single YouTube video or audio file to the local storage directory.
_Avoid_: Stream rip, scraping task

**Media Format Option**:
The user-selected target format and quality resolution for downloading a video (e.g., 1080p, 720p, or MP3 Audio Only).
_Avoid_: Codec profile, stream type

**Video Storage Directory**:
The local destination folder (`output/youtube_videos/`) where downloaded video and audio files are archived.
_Avoid_: Cache folder, temp dir

**Single Video Input Mode**:
The dynamic UI state triggered when the user enters a specific video URL instead of a channel URL, replacing extraction controls with immediate download actions.
_Avoid_: Video URL mode, single link view

