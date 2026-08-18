import os
import shutil
import pytest
from src.extractor import ExtractedArticle
from src.exporter import ArticleExporter

@pytest.fixture
def temp_output_dir(tmp_path):
    out_dir = str(tmp_path / "output")
    yield out_dir
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir, ignore_errors=True)

def test_export_article_markdown(temp_output_dir):
    exporter = ArticleExporter(base_output_dir=temp_output_dir)
    article = ExtractedArticle(
        title="Day 574: Using Shame as Motivation",
        body_html="<p>Paragraph text.</p>",
        url="https://creationsjourneytolife.blogspot.com/2019/04/day-574-using-shame-as-motivation.html"
    )
    
    file_path = exporter.save_article(article, "md")
    
    assert os.path.exists(file_path)
    assert file_path.endswith("day-574-using-shame-as-motivation.md")
    assert "creationsjourneytolife.blogspot.com" in file_path
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "# Day 574: Using Shame as Motivation" in content
        assert "Paragraph text." in content

def test_export_article_html(temp_output_dir):
    exporter = ArticleExporter(base_output_dir=temp_output_dir)
    article = ExtractedArticle(
        title="Day 574",
        body_html="<p>Paragraph text.</p>",
        url="https://creationsjourneytolife.blogspot.com/2019/04/day-574.html"
    )
    
    file_path = exporter.save_article(article, "html")
    
    assert os.path.exists(file_path)
    assert file_path.endswith("day-574.html")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "<!DOCTYPE html>" in content
        assert "<h1>Day 574</h1>" in content
