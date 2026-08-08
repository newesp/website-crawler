import os
from urllib.parse import urlparse
from src.extractor import ExtractedArticle
from src.normalizer import extract_slug_from_url

class ArticleExporter:
    def __init__(self, base_output_dir: str = "./output"):
        self.base_output_dir = os.path.abspath(base_output_dir)

    def get_host_output_dir(self, url: str) -> str:
        parsed = urlparse(url)
        hostname = parsed.netloc.lower() or "unknown_host"
        # Sanitize folder name
        safe_hostname = "".join(c for c in hostname if c.isalnum() or c in ".-_")
        target_dir = os.path.join(self.base_output_dir, safe_hostname)
        os.makedirs(target_dir, exist_ok=True)
        return target_dir

    def save_article(self, article: ExtractedArticle, output_format: str) -> str:
        """
        Saves article to disk under base_output_dir/hostname/slug.ext.
        Returns the absolute file path.
        """
        host_dir = self.get_host_output_dir(article.url)
        slug = extract_slug_from_url(article.url)
        
        fmt = output_format.lower().strip(".")
        if fmt not in ["md", "html"]:
            fmt = "md"
            
        filename = f"{slug}.{fmt}"
        file_path = os.path.join(host_dir, filename)
        
        if fmt == "md":
            content = article.to_markdown()
        else:
            content = article.to_clean_html()
            
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return file_path
