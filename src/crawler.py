import asyncio
import random
from collections import deque
from enum import Enum
from typing import Optional, Callable, Set, Dict, Any, Tuple
import httpx

from src.database import Database
from src.normalizer import normalize_url, is_same_host
from src.classifier import BlogspotClassifier, PageType
from src.extractor import BlogspotExtractor
from src.exporter import ArticleExporter
from src.fetcher import HttpFetcher

class CrawlStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

class CrawlEngine:
    def __init__(
        self,
        db: Database,
        exporter: Optional[ArticleExporter] = None,
        fetcher: Optional[HttpFetcher] = None,
        classifier: Optional[BlogspotClassifier] = None,
        extractor: Optional[BlogspotExtractor] = None,
        politeness_delay_range: Tuple[float, float] = (1.0, 2.0)
    ):
        self.db = db
        self.exporter = exporter or ArticleExporter()
        self.fetcher = fetcher or HttpFetcher()
        self.classifier = classifier or BlogspotClassifier()
        self.extractor = extractor or BlogspotExtractor()
        self.politeness_delay_range = politeness_delay_range
        
        self.status = CrawlStatus.IDLE
        self.current_job_id: Optional[int] = None
        self.current_root_url: Optional[str] = None
        self.active_url: Optional[str] = None
        
        # Async control primitives
        self._pause_event = asyncio.Event()
        self._pause_event.set() # Unpaused by default
        self._cancel_requested = False
        
        # Progress callback hook
        self.on_progress: Optional[Callable[[Dict[str, Any]], None]] = None

    def _emit_progress(self, event_type: str, data: Dict[str, Any]):
        if self.on_progress:
            payload = {
                "event": event_type,
                "job_id": self.current_job_id,
                "status": self.status.value,
                **data
            }
            try:
                self.on_progress(payload)
            except Exception:
                pass

    async def pause(self):
        if self.status == CrawlStatus.RUNNING:
            self._pause_event.clear()
            self.status = CrawlStatus.PAUSED
            if self.current_job_id:
                await self.db.update_job_status(self.current_job_id, CrawlStatus.PAUSED.value)
            self._emit_progress("status_change", {"status": CrawlStatus.PAUSED.value})

    async def resume(self):
        if self.status == CrawlStatus.PAUSED:
            self._pause_event.set()
            self.status = CrawlStatus.RUNNING
            if self.current_job_id:
                await self.db.update_job_status(self.current_job_id, CrawlStatus.RUNNING.value)
            self._emit_progress("status_change", {"status": CrawlStatus.RUNNING.value})

    async def cancel(self):
        self._cancel_requested = True
        self._pause_event.set() # Unblock if paused so loop can terminate
        self.status = CrawlStatus.CANCELLED
        if self.current_job_id:
            await self.db.update_job_status(self.current_job_id, CrawlStatus.CANCELLED.value)
        self._emit_progress("status_change", {"status": CrawlStatus.CANCELLED.value})

    async def start_crawl(
        self,
        root_url: str,
        output_format: str = "md",
        mock_transport: Optional[httpx.BaseTransport] = None,
        max_pages: Optional[int] = None
    ) -> int:
        """
        Main crawling loop with Candidate Priority Queue (Articles prioritized over Index pages).
        """
        normalized_root = normalize_url(root_url)
        self.current_root_url = normalized_root
        self._cancel_requested = False
        self._pause_event.set()
        self.status = CrawlStatus.RUNNING
        
        # Determine output folder
        output_dir = self.exporter.get_host_output_dir(normalized_root)
        
        # Create job record in SQLite
        job_id = await self.db.create_job(
            root_url=normalized_root,
            output_format=output_format,
            output_dir=output_dir
        )
        self.current_job_id = job_id
        
        # Query previously successful articles for incremental skipping
        previously_crawled_urls = await self.db.get_successfully_crawled_urls_for_host(normalized_root)
        
        self._emit_progress("job_started", {
            "root_url": normalized_root,
            "output_format": output_format,
            "output_dir": output_dir,
            "previously_crawled_count": len(previously_crawled_urls)
        })
        
        # Candidate Priority Queues
        # Articles get highest priority so we extract articles as soon as they are discovered
        article_queue: deque[str] = deque()
        index_queue: deque[str] = deque()
        
        root_type = self.classifier.classify(normalized_root)
        if root_type == PageType.ARTICLE:
            article_queue.append(normalized_root)
        else:
            index_queue.append(normalized_root)

        seen_in_this_run: Set[str] = {normalized_root}
        
        self._emit_progress("url_discovered", {
            "url": normalized_root,
            "page_type": root_type.value,
            "status": "pending"
        })
        
        client_kwargs = {"timeout": 15.0}
        if mock_transport:
            client_kwargs["transport"] = mock_transport

        pages_crawled_count = 0
        
        try:
            async with httpx.AsyncClient(**client_kwargs) as client:
                while (article_queue or index_queue) and not self._cancel_requested:
                    # Handle pause state
                    await self._pause_event.wait()
                    if self._cancel_requested:
                        break

                    # Priority scheduling: Pop article first, then index
                    if article_queue:
                        current_url = article_queue.popleft()
                        page_type = PageType.ARTICLE
                    else:
                        current_url = index_queue.popleft()
                        page_type = PageType.INDEX

                    self.active_url = current_url
                    self._emit_progress("url_active", {
                        "url": current_url,
                        "page_type": page_type.value
                    })

                    # Check if already successfully saved in past runs
                    if page_type == PageType.ARTICLE and current_url in previously_crawled_urls:
                        await self.db.add_crawled_url(
                            job_id=job_id,
                            url=current_url,
                            page_type=page_type.value,
                            status="skipped",
                            title="[Previously Crawled]"
                        )
                        self._emit_progress("url_status_change", {
                            "url": current_url,
                            "status": "skipped",
                            "page_type": page_type.value
                        })
                        # Still fetch candidate links so we can reach older/deeper unvisited articles
                        try:
                            html = await self.fetcher.fetch(current_url, client=client)
                            new_links = self.classifier.extract_candidate_links(html, current_url)
                            for link in new_links:
                                if link not in seen_in_this_run and is_same_host(normalized_root, link):
                                    seen_in_this_run.add(link)
                                    l_type = self.classifier.classify(link)
                                    if l_type == PageType.ARTICLE:
                                        article_queue.append(link)
                                    else:
                                        index_queue.append(link)
                                    self._emit_progress("url_discovered", {
                                        "url": link,
                                        "page_type": l_type.value,
                                        "status": "pending"
                                    })
                        except Exception:
                            pass
                        continue

                    # Politeness delay between requests
                    if self.politeness_delay_range[1] > 0:
                        delay = random.uniform(*self.politeness_delay_range)
                        await asyncio.sleep(delay)

                    # Fetch page HTML
                    html = ""
                    try:
                        html = await self.fetcher.fetch(current_url, client=client)
                    except Exception as e:
                        await self.db.add_crawled_url(
                            job_id=job_id,
                            url=current_url,
                            page_type=page_type.value,
                            status="failed",
                            error_message=str(e)
                        )
                        self._emit_progress("url_status_change", {
                            "url": current_url,
                            "status": "failed",
                            "error": str(e)
                        })
                        self._emit_progress("url_failed", {
                            "url": current_url,
                            "error": str(e),
                            "stats": await self.db.get_job_stats(job_id)
                        })
                        continue

                    # Discover outgoing links from this page
                    new_links = self.classifier.extract_candidate_links(html, current_url)
                    for link in new_links:
                        if link not in seen_in_this_run and is_same_host(normalized_root, link):
                            seen_in_this_run.add(link)
                            l_type = self.classifier.classify(link)
                            if l_type == PageType.ARTICLE:
                                article_queue.append(link)
                            else:
                                index_queue.append(link)
                            self._emit_progress("url_discovered", {
                                "url": link,
                                "page_type": l_type.value,
                                "status": "pending"
                            })

                    # If this is an Article page, extract and save content
                    if page_type == PageType.ARTICLE:
                        article = self.extractor.extract(html, current_url)
                        
                        # Fallback to Playwright if empty body returned from httpx
                        if (not article or not article.body_html.strip()) and not mock_transport:
                            try:
                                pw_html = await self.fetcher.fetch_with_playwright(current_url)
                                article = self.extractor.extract(pw_html, current_url)
                            except Exception:
                                pass

                        if article and article.body_html.strip():
                            # Save article to file
                            saved_path = self.exporter.save_article(article, output_format)
                            await self.db.add_crawled_url(
                                job_id=job_id,
                                url=current_url,
                                page_type=page_type.value,
                                status="crawled",
                                title=article.title,
                                file_path=saved_path
                            )
                            previously_crawled_urls.add(current_url)
                            pages_crawled_count += 1
                            
                            self._emit_progress("url_status_change", {
                                "url": current_url,
                                "status": "crawled",
                                "title": article.title,
                                "file_path": saved_path
                            })
                            self._emit_progress("article_crawled", {
                                "url": current_url,
                                "title": article.title,
                                "file_path": saved_path,
                                "stats": await self.db.get_job_stats(job_id)
                            })
                        else:
                            await self.db.add_crawled_url(
                                job_id=job_id,
                                url=current_url,
                                page_type=page_type.value,
                                status="failed",
                                error_message="Empty article content extracted"
                            )
                            self._emit_progress("url_status_change", {
                                "url": current_url,
                                "status": "failed",
                                "error": "Empty content"
                            })
                            self._emit_progress("url_failed", {
                                "url": current_url,
                                "error": "Empty article content",
                                "stats": await self.db.get_job_stats(job_id)
                            })
                    else:
                        # Index page recorded
                        await self.db.add_crawled_url(
                            job_id=job_id,
                            url=current_url,
                            page_type=page_type.value,
                            status="crawled"
                        )
                        self._emit_progress("url_status_change", {
                            "url": current_url,
                            "status": "crawled",
                            "page_type": page_type.value
                        })
                        self._emit_progress("index_crawled", {
                            "url": current_url,
                            "stats": await self.db.get_job_stats(job_id)
                        })

                    if max_pages and pages_crawled_count >= max_pages:
                        break

            # Finalize status
            self.active_url = None
            if self._cancel_requested:
                self.status = CrawlStatus.CANCELLED
                await self.db.update_job_status(job_id, CrawlStatus.CANCELLED.value)
            else:
                self.status = CrawlStatus.COMPLETED
                await self.db.update_job_status(job_id, CrawlStatus.COMPLETED.value)
                
            self._emit_progress("job_completed", {
                "status": self.status.value,
                "output_dir": output_dir,
                "stats": await self.db.get_job_stats(job_id)
            })

        except Exception as e:
            self.active_url = None
            self.status = CrawlStatus.FAILED
            await self.db.update_job_status(job_id, CrawlStatus.FAILED.value, error_message=str(e))
            self._emit_progress("job_failed", {
                "error": str(e),
                "stats": await self.db.get_job_stats(job_id)
            })
            
        return job_id
