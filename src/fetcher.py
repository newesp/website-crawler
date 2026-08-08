import httpx
from typing import Optional

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 WebsiteCrawler/1.0"

class HttpFetcher:
    def __init__(self, user_agent: str = DEFAULT_USER_AGENT, timeout: float = 15.0):
        self.user_agent = user_agent
        self.timeout = timeout
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8,zh;q=0.7",
        }

    async def fetch(self, url: str, client: Optional[httpx.AsyncClient] = None) -> str:
        """
        Fetches page HTML using lightweight async httpx client.
        """
        if client:
            resp = await client.get(url, headers=self.headers, follow_redirects=True)
            resp.raise_for_status()
            return resp.text
            
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as local_client:
            resp = await local_client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.text

    async def fetch_with_playwright(self, url: str) -> str:
        """
        Fallback renderer using Playwright for JavaScript-heavy dynamic pages.
        Only initialized on demand.
        """
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page(user_agent=self.user_agent)
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                # Wait a small moment for scripts to render
                await page.wait_for_timeout(1000)
                content = await page.content()
                return content
            finally:
                await browser.close()
