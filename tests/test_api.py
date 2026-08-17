import pytest
from fastapi.testclient import TestClient
from src.app import create_app
from src.database import Database

@pytest.fixture
def client(tmp_path):
    db_file = str(tmp_path / "test_api.db")
    app = create_app(db_path=db_file, output_dir=str(tmp_path / "output"))
    # Run startup events
    with TestClient(app) as test_client:
        yield test_client

def test_get_root_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Website Crawler" in response.text

def test_check_robots_endpoint(client):
    response = client.post("/api/check-robots", json={"url": "https://creationsjourneytolife.blogspot.com"})
    assert response.status_code == 200
    data = response.json()
    assert "allowed" in data

def test_start_crawl_endpoint(client):
    response = client.post("/api/crawl/start", json={
        "root_url": "https://creationsjourneytolife.blogspot.com",
        "output_format": "md"
    })
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] in ["running", "completed"]

def test_pause_resume_cancel_endpoints(client):
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

from unittest.mock import patch

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


