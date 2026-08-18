import pytest
import asyncio
import httpx
from src.database import Database
from src.exporter import ArticleExporter
from src.crawler import CrawlEngine, CrawlStatus

@pytest.fixture
async def setup_engine(tmp_path):
    db_file = str(tmp_path / "test_crawler.db")
    db = Database(db_file)
    await db.init_db()
    
    out_dir = str(tmp_path / "output")
    exporter = ArticleExporter(base_output_dir=out_dir)
    
    engine = CrawlEngine(db=db, exporter=exporter, politeness_delay_range=(0.0, 0.0))
    return engine, db, out_dir

@pytest.mark.asyncio
async def test_crawler_full_cycle(setup_engine):
    engine, db, out_dir = setup_engine
    
    root_url = "https://creationsjourneytolife.blogspot.com"
    
    index_html = """
    <html><body>
        <h1>Blog Homepage</h1>
        <a href="/2019/04/day-574-using-shame.html">Day 574</a>
        <a href="/search/label/Living">Living Label</a>
    </body></html>
    """
    
    article_html = """
    <html><body>
        <h1 class="post-title">Day 574: Using Shame</h1>
        <div class="post-body"><p>Article text here.</p></div>
    </body></html>
    """
    
    async def mock_handler(request):
        url = str(request.url)
        if "day-574" in url:
            return httpx.Response(200, text=article_html)
        else:
            return httpx.Response(200, text=index_html)
            
    transport = httpx.MockTransport(mock_handler)
    
    progress_updates = []
    def on_progress(event):
        progress_updates.append(event)
        
    engine.on_progress = on_progress
    
    job_id = await engine.start_crawl(
        root_url=root_url,
        output_format="md",
        mock_transport=transport,
        max_pages=10
    )
    
    job = await db.get_job(job_id)
    if job["status"] != CrawlStatus.COMPLETED:
        print("JOB FAILED:", job)
    assert job["status"] == CrawlStatus.COMPLETED
    
    stats = await db.get_job_stats(job_id)
    assert stats["crawled_articles"] >= 1
    
    articles = await db.get_crawled_articles(job_id)
    assert len(articles) >= 1
    assert articles[0]["title"] == "Day 574: Using Shame"
    assert articles[0]["file_path"].endswith("day-574-using-shame.md")

@pytest.mark.asyncio
async def test_crawler_priority_queue(setup_engine):
    engine, db, out_dir = setup_engine
    root_url = "https://creationsjourneytolife.blogspot.com"
    
    # Root homepage returns both an index link and an article link
    root_html = """
    <html><body>
        <a href="/search/label/Philosophy">Index Label</a>
        <a href="/2019/04/day-574-using-shame.html">Article 574</a>
    </body></html>
    """
    
    crawled_order = []
    
    async def mock_handler(request):
        url = str(request.url)
        crawled_order.append(url)
        if "day-574" in url:
            return httpx.Response(200, text="<html><body><h1 class='post-title'>574</h1><div class='post-body'>Body</div></body></html>")
        elif "Philosophy" in url:
            return httpx.Response(200, text="<html><body><a href='/2018/01/old-article.html'>Old Article</a></body></html>")
        else:
            return httpx.Response(200, text=root_html)
            
    transport = httpx.MockTransport(mock_handler)
    
    await engine.start_crawl(root_url=root_url, output_format="md", mock_transport=transport, max_pages=3)
    
    # Expected order: Root URL -> Article 574 (High priority) -> Index Philosophy (Low priority)
    assert len(crawled_order) >= 2
    assert "day-574" in crawled_order[1] # Article prioritized over Index Philosophy!

@pytest.mark.asyncio
async def test_crawler_pause_and_cancel(setup_engine):
    engine, db, out_dir = setup_engine
    root_url = "https://creationsjourneytolife.blogspot.com"
    
    counter = 0
    async def mock_handler(request):
        nonlocal counter
        counter += 1
        await asyncio.sleep(0.05)
        # Generate many links so crawler stays busy
        links = "".join([f"<a href='/2019/01/item-{counter}-{i}.html'>Link</a>" for i in range(10)])
        return httpx.Response(200, text=f"<html><body>{links}</body></html>")
        
    transport = httpx.MockTransport(mock_handler)
    
    crawl_task = asyncio.create_task(
        engine.start_crawl(root_url=root_url, output_format="md", mock_transport=transport)
    )
    
    # Wait until it is running
    while engine.status != CrawlStatus.RUNNING:
        await asyncio.sleep(0.01)
        
    await engine.pause()
    assert engine.status == CrawlStatus.PAUSED
    
    await engine.resume()
    assert engine.status == CrawlStatus.RUNNING
    
    await engine.cancel()
    assert engine.status == CrawlStatus.CANCELLED
    
    await crawl_task

@pytest.mark.asyncio
async def test_crawler_resume_incremental_crawl(setup_engine):
    engine, db, out_dir = setup_engine
    root_url = "https://creationsjourneytolife.blogspot.com"
    
    # 3 Articles
    html_root = """
    <html><body>
        <a href="/2019/01/article-1.html">Article 1</a>
        <a href="/2019/02/article-2.html">Article 2</a>
        <a href="/2019/03/article-3.html">Article 3</a>
    </body></html>
    """
    
    def make_article_html(num):
        return f"<html><body><h1 class='post-title'>Article {num}</h1><div class='post-body'><p>Content {num}</p></div></body></html>"
        
    requested_urls = []
    async def mock_handler_run1(request):
        url = str(request.url)
        requested_urls.append(url)
        if "article-1" in url:
            return httpx.Response(200, text=make_article_html(1))
        elif "article-2" in url:
            return httpx.Response(200, text=make_article_html(2))
        elif "article-3" in url:
            return httpx.Response(200, text=make_article_html(3))
        return httpx.Response(200, text=html_root)
        
    # First crawl job: limit max_pages to 2 articles
    transport1 = httpx.MockTransport(mock_handler_run1)
    job1_id = await engine.start_crawl(
        root_url=root_url,
        output_format="md",
        mock_transport=transport1,
        max_pages=2
    )
    
    job1_stats = await db.get_job_stats(job1_id)
    assert job1_stats["crawled_articles"] == 2
    
    # Second crawl job: resume on same root_url without page limit
    requested_urls_run2 = []
    async def mock_handler_run2(request):
        url = str(request.url)
        requested_urls_run2.append(url)
        if "article-3" in url:
            return httpx.Response(200, text=make_article_html(3))
        elif "article-1" in url:
            return httpx.Response(200, text=make_article_html(1))
        elif "article-2" in url:
            return httpx.Response(200, text=make_article_html(2))
        return httpx.Response(200, text=html_root)
        
    transport2 = httpx.MockTransport(mock_handler_run2)
    job2_id = await engine.start_crawl(
        root_url=root_url,
        output_format="md",
        mock_transport=transport2
    )
    
    job2 = await db.get_job(job2_id)
    assert job2["status"] == CrawlStatus.COMPLETED
    
    # Verify incremental behavior:
    # Article 3 was newly crawled in run 2
    job2_articles = await db.get_crawled_articles(job2_id)
    assert len(job2_articles) == 1
    assert job2_articles[0]["title"] == "Article 3"
    
    # Articles 1 and 2 were marked skipped in job2
    job2_urls = await db.get_crawled_urls(job2_id)
    skipped = [u for u in job2_urls if u["status"] == "skipped"]
    assert len(skipped) == 2

@pytest.mark.asyncio
async def test_crawler_http_timeout_and_failure(setup_engine):
    engine, db, out_dir = setup_engine
    root_url = "https://creationsjourneytolife.blogspot.com"
    
    root_html = """
    <html><body>
        <a href="/2019/01/timeout-article.html">Timeout Article</a>
        <a href="/2019/02/success-article.html">Success Article</a>
    </body></html>
    """
    
    async def mock_handler(request):
        url = str(request.url)
        if "timeout-article" in url:
            raise httpx.ReadTimeout("Connection timed out reading response")
        elif "success-article" in url:
            return httpx.Response(200, text="<html><body><h1 class='post-title'>Success</h1><div class='post-body'><p>OK</p></div></body></html>")
        return httpx.Response(200, text=root_html)
        
    transport = httpx.MockTransport(mock_handler)
    job_id = await engine.start_crawl(
        root_url=root_url,
        output_format="md",
        mock_transport=transport
    )
    
    job = await db.get_job(job_id)
    assert job["status"] == CrawlStatus.COMPLETED
    
    stats = await db.get_job_stats(job_id)
    assert stats["failed"] == 1
    assert stats["crawled_articles"] == 1
    
    urls = await db.get_crawled_urls(job_id)
    failed_items = [u for u in urls if u["status"] == "failed"]
    assert len(failed_items) == 1
    err_msg = failed_items[0]["error_message"].lower()
    assert "timed out" in err_msg or "timeout" in err_msg


@pytest.mark.asyncio
async def test_crawler_malformed_and_empty_html(setup_engine):
    engine, db, out_dir = setup_engine
    root_url = "https://creationsjourneytolife.blogspot.com"
    
    root_html = """
    <html><body>
        <a href="/2019/01/empty.html">Empty Article</a>
        <a href="/2019/02/missing-body.html">Missing Body Article</a>
        <a href="/2019/03/valid.html">Valid Article</a>
    </body></html>
    """
    
    async def mock_handler(request):
        url = str(request.url)
        if "empty" in url:
            return httpx.Response(200, text="")
        elif "missing-body" in url:
            return httpx.Response(200, text="<html><body><div>No post title or body here</div></body></html>")
        elif "valid" in url:
            return httpx.Response(200, text="<html><body><h1 class='post-title'>Valid</h1><div class='post-body'><p>Content</p></div></body></html>")
        return httpx.Response(200, text=root_html)
        
    transport = httpx.MockTransport(mock_handler)
    job_id = await engine.start_crawl(
        root_url=root_url,
        output_format="md",
        mock_transport=transport
    )
    
    job = await db.get_job(job_id)
    assert job["status"] == CrawlStatus.COMPLETED
    
    stats = await db.get_job_stats(job_id)
    assert stats["failed"] == 2
    assert stats["crawled_articles"] == 1

