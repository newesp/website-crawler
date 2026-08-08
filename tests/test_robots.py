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
