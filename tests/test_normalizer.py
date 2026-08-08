import pytest
from src.normalizer import normalize_url, extract_slug_from_url, is_same_host

def test_normalize_url_strips_query_and_fragment():
    url = "https://creationsjourneytolife.blogspot.com/2019/04/day-574-using-shame-as-motivation.html?m=1#comments"
    expected = "https://creationsjourneytolife.blogspot.com/2019/04/day-574-using-shame-as-motivation.html"
    assert normalize_url(url) == expected

def test_normalize_url_strips_trailing_slash():
    url = "https://creationsjourneytolife.blogspot.com/search/label/Living/"
    expected = "https://creationsjourneytolife.blogspot.com/search/label/Living"
    assert normalize_url(url) == expected

def test_normalize_url_root_domain():
    url = "https://creationsjourneytolife.blogspot.com/"
    expected = "https://creationsjourneytolife.blogspot.com"
    assert normalize_url(url) == expected

def test_extract_slug_from_url():
    url = "https://creationsjourneytolife.blogspot.com/2019/04/day-574-using-shame-as-motivation.html"
    assert extract_slug_from_url(url) == "day-574-using-shame-as-motivation"

def test_extract_slug_fallback():
    url = "https://creationsjourneytolife.blogspot.com/p/about.html"
    assert extract_slug_from_url(url) == "about"

def test_is_same_host():
    root = "https://creationsjourneytolife.blogspot.com"
    target = "https://creationsjourneytolife.blogspot.com/2019/04/day-574.html"
    different = "https://otherblog.blogspot.com/2019/04/day-574.html"
    assert is_same_host(root, target) is True
    assert is_same_host(root, different) is False
