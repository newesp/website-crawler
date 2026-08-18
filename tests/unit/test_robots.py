import pytest
from src.robots import RobotsChecker

@pytest.mark.asyncio
async def test_robots_allowed():
    robots_txt = """
    User-agent: *
    Disallow: /search
    Allow: /
    """
    checker = RobotsChecker()
    is_allowed, reason = checker.check_text(robots_txt, "https://creationsjourneytolife.blogspot.com/2019/04/day-574.html")
    assert is_allowed is True
    assert reason is None

@pytest.mark.asyncio
async def test_robots_disallowed():
    robots_txt = """
    User-agent: *
    Disallow: /
    """
    checker = RobotsChecker()
    is_allowed, reason = checker.check_text(robots_txt, "https://example.com/2019/04/day-574.html")
    assert is_allowed is False
    assert "Disallow: /" in reason

@pytest.mark.asyncio
async def test_robots_disallowed_subpath():
    robots_txt = """
    User-agent: *
    Disallow: /private/
    """
    checker = RobotsChecker()
    is_allowed, reason = checker.check_text(robots_txt, "https://example.com/private/secret.html")
    assert is_allowed is False
    assert "Disallow: /private/" in reason
    
    is_allowed_pub, _ = checker.check_text(robots_txt, "https://example.com/public/open.html")
    assert is_allowed_pub is True

from unittest.mock import patch, AsyncMock
import httpx

@pytest.mark.asyncio
async def test_robots_check_url_200():
    checker = RobotsChecker()
    mock_resp = httpx.Response(200, text="User-agent: *\nDisallow: /admin")
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        allowed, reason = await checker.check_url("https://example.com/admin/settings")
        assert allowed is False
        assert "Disallow: /admin" in reason
        
        allowed_home, reason_home = await checker.check_url("https://example.com/home")
        assert allowed_home is True

@pytest.mark.asyncio
async def test_robots_check_url_403():
    checker = RobotsChecker()
    mock_resp = httpx.Response(403)
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        allowed, reason = await checker.check_url("https://example.com/page")
        assert allowed is False
        assert "HTTP 403" in reason

@pytest.mark.asyncio
async def test_robots_check_url_network_error():
    checker = RobotsChecker()
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Network unreachable")
        allowed, reason = await checker.check_url("https://example.com/page")
        assert allowed is True
        assert reason is None

