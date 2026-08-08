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

**Fallback Rendering**:
When a lightweight HTTP request (httpx) returns empty content, the system retries using a headless browser to handle JavaScript-rendered pages.
_Avoid_: Dynamic rendering, JS rendering

**Politeness Delay**:
A 1–2 second pause between consecutive HTTP requests to avoid overwhelming the target server.
_Avoid_: Rate limit, throttle, backoff
