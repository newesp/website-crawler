import pytest
from src.extractor import BlogspotExtractor, ExtractedArticle

def test_extract_blogspot_article_content():
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Day 574: Using Shame as Motivation - Journey to Life</title></head>
    <body>
        <div class="header"><h1>Header Navigation</h1></div>
        <div class="post">
            <h1 class="post-title entry-title">Day 574: Using Shame as Motivation</h1>
            <div class="post-body entry-content" id="post-body-12345">
                <p>This is the first paragraph about shame and motivation.</p>
                <div class="separator"><a href="#"><img src="https://blogger.googleusercontent.com/img/a.jpg" alt="pic"/></a></div>
                <p>This is the second paragraph.</p>
                <div class="post-share-buttons">Share this</div>
            </div>
            <div id="comments">Comments section here</div>
        </div>
    </body>
    </html>
    """
    extractor = BlogspotExtractor()
    article = extractor.extract(html, "https://creationsjourneytolife.blogspot.com/2019/04/day-574-using-shame-as-motivation.html")
    
    assert article is not None
    assert article.title == "Day 574: Using Shame as Motivation"
    assert "This is the first paragraph about shame and motivation." in article.body_html
    assert "This is the second paragraph." in article.body_html
    # Image must be stripped
    assert "<img" not in article.body_html
    # Comments & share buttons must be excluded
    assert "Comments section here" not in article.body_html
    assert "Share this" not in article.body_html

def test_extract_markdown_conversion():
    html = """
    <html>
    <body>
        <h1 class="post-title">Test Title</h1>
        <div class="post-body">
            <p>Hello <strong>world</strong>!</p>
            <ul><li>Item 1</li><li>Item 2</li></ul>
            <img src="test.jpg" />
        </div>
    </body>
    </html>
    """
    extractor = BlogspotExtractor()
    article = extractor.extract(html, "https://example.com/2020/01/test.html")
    md = article.to_markdown()
    
    assert "# Test Title" in md
    assert "Hello **world**!" in md
    assert "Item 1" in md
    assert "test.jpg" not in md

def test_extract_clean_html_conversion():
    html = """
    <html>
    <body>
        <h1 class="post-title">Test Clean HTML</h1>
        <div class="post-body">
            <p>Clean paragraph.</p>
            <img src="test.jpg" />
        </div>
    </body>
    </html>
    """
    extractor = BlogspotExtractor()
    article = extractor.extract(html, "https://example.com/2020/01/test.html")
    clean_html = article.to_clean_html()
    
    assert "<!DOCTYPE html>" in clean_html
    assert "<title>Test Clean HTML</title>" in clean_html
    assert "<h1>Test Clean HTML</h1>" in clean_html
    assert "<p>Clean paragraph.</p>" in clean_html
    assert "test.jpg" not in clean_html

def test_extract_empty_when_not_article():
    html = "<html><body><div>Just a random empty page</div></body></html>"
    extractor = BlogspotExtractor()
    article = extractor.extract(html, "https://example.com/not-article")
    assert article is None or article.body_html.strip() == ""
