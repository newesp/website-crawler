import urllib.robotparser
from urllib.parse import urlparse, urljoin
import httpx
from typing import Tuple, Optional

class RobotsChecker:
    def __init__(self, user_agent: str = "*"):
        self.user_agent = user_agent

    async def check_url(self, target_url: str) -> Tuple[bool, Optional[str]]:
        """
        Fetches robots.txt from target host and checks if target_url is allowed.
        Returns (is_allowed, restriction_reason).
        """
        parsed = urlparse(target_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                resp = await client.get(robots_url)
                if resp.status_code == 200:
                    return self.check_text(resp.text, target_url)
                elif resp.status_code in (401, 403):
                    return False, f"robots.txt returned HTTP {resp.status_code} (access forbidden)"
                else:
                    # 404 or other status usually means no restrictions
                    return True, None
        except Exception as e:
            # Network issue getting robots.txt, assume allowable but notify
            return True, None

    def check_text(self, robots_txt: str, target_url: str) -> Tuple[bool, Optional[str]]:
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(robots_txt.splitlines())
        
        allowed = rp.can_fetch(self.user_agent, target_url)
        if not allowed:
            # Find matching disallow line for informative message
            reason = "Target URL is restricted by robots.txt rules (Disallow)"
            for line in robots_txt.splitlines():
                clean = line.strip()
                if clean.lower().startswith("disallow:"):
                    reason = f"Restricted by: {clean}"
                    break
            return False, reason
            
        return True, None
