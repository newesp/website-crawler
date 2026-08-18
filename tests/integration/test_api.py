import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from src.app import create_app
from src.database import Database

@pytest.fixture
def client(tmp_path):
    db_file = str(tmp_path / "test_api.db")
    app = create_app(db_path=db_file, output_dir=str(tmp_path / "output"))
    with TestClient(app) as test_client:
        yield test_client

def test_get_root_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Website Crawler" in response.text

@patch("src.robots.RobotsChecker.check_url", new_callable=AsyncMock)
def test_check_robots_endpoint(mock_check_url, client):
    mock_check_url.return_value = (True, None)
    response = client.post("/api/check-robots", json={"url": "https://creationsjourneytolife.blogspot.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is True

@patch("src.robots.RobotsChecker.check_url", new_callable=AsyncMock)
@patch("src.crawler.CrawlEngine.start_crawl", new_callable=AsyncMock)
def test_start_crawl_endpoint(mock_start_crawl, mock_check_url, client):
    mock_check_url.return_value = (True, None)
    mock_start_crawl.return_value = 1
    
    response = client.post("/api/crawl/start", json={
        "root_url": "https://creationsjourneytolife.blogspot.com",
        "output_format": "md"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["root_url"] == "https://creationsjourneytolife.blogspot.com"

@patch("src.robots.RobotsChecker.check_url", new_callable=AsyncMock)
def test_start_crawl_robots_disallowed(mock_check_url, client):
    mock_check_url.return_value = (False, "Restricted by robots.txt")
    response = client.post("/api/crawl/start", json={
        "root_url": "https://creationsjourneytolife.blogspot.com",
        "output_format": "md",
        "ignore_robots": False
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "robots_warning"
    assert "Restricted by robots.txt" in data["reason"]

@patch("src.robots.RobotsChecker.check_url", new_callable=AsyncMock)
@patch("src.crawler.CrawlEngine.start_crawl", new_callable=AsyncMock)
def test_pause_resume_cancel_endpoints(mock_start_crawl, mock_check_url, client):
    mock_check_url.return_value = (True, None)
    mock_start_crawl.return_value = 1
    
    client.post("/api/crawl/start", json={
        "root_url": "https://creationsjourneytolife.blogspot.com",
        "output_format": "html"
    })
    
    pause_res = client.post("/api/crawl/pause")
    assert pause_res.status_code == 200
    
    resume_res = client.post("/api/crawl/resume")
    assert resume_res.status_code == 200
    
    cancel_res = client.post("/api/crawl/cancel")
    assert cancel_res.status_code == 200

def test_get_status_idle(client):
    response = client.get("/api/crawl/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "idle"

def test_get_nonexistent_job(client):
    response = client.get("/api/jobs/999")
    assert response.status_code == 404

@patch("src.youtube.YouTubeExtractor.extract")
def test_youtube_extract_endpoint(mock_extract, client):
    mock_extract.return_value = {
        "channel_url": "https://www.youtube.com/@test",
        "channel_title": "Test Channel",
        "total_count": 2,
        "video_urls": ["https://www.youtube.com/watch?v=1", "https://www.youtube.com/watch?v=2"],
        "export_path": "./output/youtube_test.csv",
        "export_filename": "youtube_test.csv",
        "format": "csv"
    }

    response = client.post("/api/youtube/extract", json={
        "channel_url": "https://www.youtube.com/@test",
        "start_date": "2026-08-01",
        "end_date": "2026-08-10",
        "export_format": "csv"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_count"] == 2
    assert len(data["video_urls"]) == 2
    assert "export_filename" in data

@patch("src.youtube.YouTubeExtractor.download_video")
def test_youtube_download_endpoint(mock_download, client):
    mock_download.return_value = {
        "status": "success",
        "video_id": "vid123",
        "title": "My Sample Video",
        "file_path": "./output/youtube_videos/My_Sample_Video_vid123.mp4",
        "filename": "My_Sample_Video_vid123.mp4",
        "quality": "1080p"
    }

    response = client.post("/api/youtube/download", json={
        "url": "https://www.youtube.com/watch?v=vid123",
        "quality": "1080p"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["video_id"] == "vid123"
    assert data["title"] == "My Sample Video"
    assert "file_path" in data

@pytest.fixture
def client_and_db(tmp_path):
    db_file = str(tmp_path / "test_api.db")
    db = Database(db_path=db_file)
    app = create_app(db_path=db_file, output_dir=str(tmp_path / "output"))
    with TestClient(app) as test_client:
        yield test_client, db

@pytest.mark.asyncio
async def test_get_job_details_and_status_with_job(client_and_db):
    client, db = client_and_db
    await db.init_db()
    job_id = await db.create_job(
        root_url="https://creationsjourneytolife.blogspot.com",
        output_format="md",
        output_dir="./output/test"
    )
    await db.add_crawled_url(
        job_id=job_id,
        url="https://creationsjourneytolife.blogspot.com/2019/04/day-574.html",
        page_type="article",
        status="crawled",
        title="Day 574",
        file_path="./output/test/day-574.md"
    )
    
    # Get status
    status_res = client.get("/api/crawl/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["job"] is not None
    assert status_data["job"]["id"] == job_id
    assert status_data["stats"]["crawled_articles"] == 1
    
    # Get job details
    job_res = client.get(f"/api/jobs/{job_id}")
    assert job_res.status_code == 200
    job_data = job_res.json()
    assert job_data["job"]["id"] == job_id
    assert job_data["job"]["root_url"] == "https://creationsjourneytolife.blogspot.com"
    assert len(job_data["articles"]) == 1


def test_download_youtube_export_endpoint(tmp_path):
    import os
    out_dir = str(tmp_path / "output")
    os.makedirs(out_dir, exist_ok=True)
    test_file = os.path.join(out_dir, "export_test.csv")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("url,title\n")
        
    db_file = str(tmp_path / "test_api_export.db")
    app = create_app(db_path=db_file, output_dir=out_dir)
    with TestClient(app) as test_client:
        res = test_client.get("/api/youtube/download/export_test.csv")
        assert res.status_code == 200
        assert "url,title" in res.text
        
        res_404 = test_client.get("/api/youtube/download/nonexistent.csv")
        assert res_404.status_code == 404

def test_websocket_progress(client):
    with client.websocket_connect("/ws/progress") as websocket:
        # Initial connection works
        assert websocket is not None




