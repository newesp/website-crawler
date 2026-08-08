from dataclasses import dataclass
from typing import Optional
from bs4 import BeautifulSoup
import markdownify

@dataclass
class ExtractedArticle:
    title: str
    body_html: str
    url: str

    def to_markdown(self) -> str:
        """
        Converts the extracted article into clean Markdown format with H1 title.
        """
        # Convert body_html to markdown
        md_body = markdownify.markdownify(self.body_html, heading_style="ATX", strip=['img', 'script', 'style'])
        # Strip excessive newlines
        lines = [line.rstrip() for line in md_body.splitlines()]
        cleaned_body = "\n".join(lines).strip()
        
        md = f"# {self.title}\n\n{cleaned_body}\n"
        return md

    def to_clean_html(self) -> str:
        """
        Converts the extracted article into a clean standalone HTML document.
        """
        return (
            "<!DOCTYPE html>\n"
            "<html lang=\"en\">\n"
            "<head>\n"
            "    <meta charset=\"UTF-8\">\n"
            f"    <title>{self.title}</title>\n"
            "</head>\n"
            "<body>\n"
            f"    <h1>{self.title}</h1>\n"
            f"    <article>\n{self.body_html}\n    </article>\n"
            "</body>\n"
            "</html>\n"
        )

class BaseExtractor:
    def extract(self, html: str, url: str) -> Optional[ExtractedArticle]:
        raise NotImplementedError

class BlogspotExtractor(BaseExtractor):
    def extract(self, html: str, url: str) -> Optional[ExtractedArticle]:
        if not html:
            return None
            
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. Extract title
        title = ""
        title_elem = soup.select_one(".post-title, h1.post-title, .entry-title")
        if title_elem:
            title = title_elem.get_text(strip=True)
        elif soup.title:
            raw_title = soup.title.get_text(strip=True)
            # Remove blog title suffix if separated by ' - ' or ' | '
            if " - " in raw_title:
                title = raw_title.split(" - ")[0].strip()
            elif " | " in raw_title:
                title = raw_title.split(" | ")[0].strip()
            else:
                title = raw_title
                
        # 2. Extract body
        body_elem = soup.select_one(".post-body, .entry-content, article .post-body, #post-body")
        if not body_elem:
            return None
            
        # Clean up unwanted elements inside the body element
        for unwanted in body_elem.select("img, picture, svg, script, style, iframe, noscript, .post-share-buttons, .reaction-buttons, .feed-links, #comments, .comments"):
            unwanted.decompose()
            
        # Clean separator wrappers if they are now empty
        for sep in body_elem.select(".separator"):
            if not sep.get_text(strip=True):
                sep.decompose()
                
        body_html = body_elem.decode_contents().strip()
        if not body_html:
            return None
            
        return ExtractedArticle(
            title=title or "Untitled",
            body_html=body_html,
            url=url
        )
