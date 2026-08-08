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
