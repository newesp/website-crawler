import pytest
import os
from src.database import Database

@pytest.fixture
async def db(tmp_path):
    db_file = str(tmp_path / "test_crawler.db")
    database = Database(db_file)
    await database.init_db()
    yield database

@pytest.mark.asyncio
async def test_create_and_get_job(db):
    job_id = await db.create_job("https://creationsjourneytolife.blogspot.com", "md", "./output/creationsjourneytolife.blogspot.com")
    assert job_id > 0
    
    job = await db.get_job(job_id)
    assert job is not None
    assert job["root_url"] == "https://creationsjourneytolife.blogspot.com"
    assert job["output_format"] == "md"
    assert job["status"] == "running"

@pytest.mark.asyncio
async def test_update_job_status(db):
    job_id = await db.create_job("https://creationsjourneytolife.blogspot.com", "html", "./output")
    await db.update_job_status(job_id, "paused")
    
    job = await db.get_job(job_id)
    assert job["status"] == "paused"

@pytest.mark.asyncio
async def test_add_and_query_crawled_urls(db):
    job_id = await db.create_job("https://creationsjourneytolife.blogspot.com", "md", "./output")
    
    await db.add_crawled_url(job_id, "https://creationsjourneytolife.blogspot.com/2019/04/day-574.html", "article", "crawled", title="Day 574", file_path="./output/day-574.md")
    await db.add_crawled_url(job_id, "https://creationsjourneytolife.blogspot.com/search/label/Living", "index", "crawled")
    await db.add_crawled_url(job_id, "https://creationsjourneytolife.blogspot.com/2019/04/day-575.html", "article", "failed", error_message="HTTP 404")
    
    stats = await db.get_job_stats(job_id)
    assert stats["discovered"] == 3
    assert stats["crawled_articles"] == 1
    assert stats["failed"] == 1
    
    articles = await db.get_crawled_articles(job_id)
    assert len(articles) == 1
    assert articles[0]["title"] == "Day 574"

@pytest.mark.asyncio
async def test_seen_urls_for_resume(db):
    root_url = "https://creationsjourneytolife.blogspot.com"
    job1_id = await db.create_job(root_url, "md", "./output")
    await db.add_crawled_url(job1_id, f"{root_url}/2019/04/day-574.html", "article", "crawled", title="Day 574")
    await db.add_crawled_url(job1_id, f"{root_url}/2019/04/day-575.html", "article", "failed")
    
    seen = await db.get_successfully_crawled_urls_for_host(root_url)
    assert f"{root_url}/2019/04/day-574.html" in seen
    # Failed ones shouldn't prevent retry
    assert f"{root_url}/2019/04/day-575.html" not in seen
