import pytest
from src.classifier import BlogspotClassifier, PageType

def test_blogspot_classifier_article_pages():
    classifier = BlogspotClassifier()
    assert classifier.classify("https://creationsjourneytolife.blogspot.com/2019/04/day-574-using-shame-as-motivation.html") == PageType.ARTICLE
    assert classifier.classify("https://creationsjourneytolife.blogspot.com/2017/06/day-573-practical-living-explained.html") == PageType.ARTICLE
    assert classifier.classify("https://creationsjourneytolife.blogspot.com/2016/02/day-572-road-ahead.html") == PageType.ARTICLE

def test_blogspot_classifier_index_pages():
    classifier = BlogspotClassifier()
    assert classifier.classify("https://creationsjourneytolife.blogspot.com/") == PageType.INDEX
    assert classifier.classify("https://creationsjourneytolife.blogspot.com/search/label/Living") == PageType.INDEX
    assert classifier.classify("https://creationsjourneytolife.blogspot.com/2019_04_01_archive.html") == PageType.INDEX
    assert classifier.classify("https://creationsjourneytolife.blogspot.com/search?updated-max=2019-04-10T00:00:00") == PageType.INDEX
    assert classifier.classify("https://creationsjourneytolife.blogspot.com/feeds/posts/default") == PageType.INDEX

def test_extract_links_from_html():
    classifier = BlogspotClassifier()
    base_url = "https://creationsjourneytolife.blogspot.com"
    html = """
    <html>
        <body>
            <a href="/2019/04/day-574.html">Day 574</a>
            <a href="https://creationsjourneytolife.blogspot.com/2017/06/day-573.html?m=1#comments">Day 573</a>
            <a href="https://external-site.com/about">External</a>
            <a href="javascript:void(0)">No link</a>
            <a href="/search/label/Philosophy">Label</a>
        </body>
    </html>
    """
    links = classifier.extract_candidate_links(html, base_url)
    assert "https://creationsjourneytolife.blogspot.com/2019/04/day-574.html" in links
    assert "https://creationsjourneytolife.blogspot.com/2017/06/day-573.html" in links
    assert "https://creationsjourneytolife.blogspot.com/search/label/Philosophy" in links
    assert "https://external-site.com/about" not in links
