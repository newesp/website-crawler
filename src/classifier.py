from enum import Enum
from urllib.parse import urlparse, urljoin
import re
from bs4 import BeautifulSoup
from src.normalizer import normalize_url, is_same_host

class PageType(str, Enum):
    ARTICLE = "article"
    INDEX = "index"

class BaseClassifier:
    def classify(self, url: str) -> PageType:
        raise NotImplementedError
        
    def extract_candidate_links(self, html: str, base_url: str) -> list[str]:
        raise NotImplementedError

class BlogspotClassifier(BaseClassifier):
    # Blogspot articles follow /YYYY/MM/slug.html
    BLOGSPOT_ARTICLE_PATTERN = re.compile(r'^/\d{4}/\d{2}/[^/]+\.html$', re.IGNORECASE)

    def classify(self, url: str) -> PageType:
        normalized = normalize_url(url)
        parsed = urlparse(normalized)
        path = parsed.path
        
        if self.BLOGSPOT_ARTICLE_PATTERN.match(path):
            return PageType.ARTICLE
        return PageType.INDEX

    def extract_candidate_links(self, html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        discovered = set()
        
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if not href or href.startswith("javascript:") or href.startswith("mailto:") or href.startswith("tel:"):
                continue
            
            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)
            normalized = normalize_url(absolute_url)
            
            if not normalized:
                continue
                
            # Filter to same host
            if is_same_host(base_url, normalized):
                discovered.add(normalized)
                
        return sorted(list(discovered))
