import aiosqlite
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Set

class Database:
    def __init__(self, db_path: str = "crawler.db"):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS crawl_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                root_url TEXT NOT NULL,
                output_format TEXT NOT NULL,
                status TEXT NOT NULL, -- 'running', 'paused', 'cancelled', 'completed', 'failed'
                output_dir TEXT NOT NULL,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)
            await db.execute("""
            CREATE TABLE IF NOT EXISTS crawled_urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                page_type TEXT NOT NULL, -- 'article', 'index'
                status TEXT NOT NULL,    -- 'pending', 'crawled', 'failed', 'skipped'
                title TEXT,
                file_path TEXT,
                error_message TEXT,
                crawled_at TEXT,
                FOREIGN KEY (job_id) REFERENCES crawl_jobs(id)
            )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_crawled_urls_job_id ON crawled_urls(job_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_crawled_urls_url ON crawled_urls(url)")
            await db.commit()

    async def create_job(self, root_url: str, output_format: str, output_dir: str) -> int:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
            INSERT INTO crawl_jobs (root_url, output_format, status, output_dir, created_at, updated_at)
            VALUES (?, ?, 'running', ?, ?, ?)
            """, (root_url, output_format, output_dir, now, now))
            await db.commit()
            return cursor.lastrowid

    async def update_job_status(self, job_id: int, status: str, error_message: Optional[str] = None):
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
            UPDATE crawl_jobs
            SET status = ?, error_message = ?, updated_at = ?
            WHERE id = ?
            """, (status, error_message, now, job_id))
            await db.commit()

    async def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM crawl_jobs WHERE id = ?", (job_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def get_latest_job(self) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM crawl_jobs ORDER BY id DESC LIMIT 1")
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def add_crawled_url(self, job_id: int, url: str, page_type: str, status: str,
                              title: Optional[str] = None, file_path: Optional[str] = None,
                              error_message: Optional[str] = None):
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
            INSERT INTO crawled_urls (job_id, url, page_type, status, title, file_path, error_message, crawled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (job_id, url, page_type, status, title, file_path, error_message, now))
            await db.commit()

    async def get_crawled_urls(self, job_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM crawled_urls WHERE job_id = ? ORDER BY id ASC", (job_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_crawled_articles(self, job_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
            SELECT * FROM crawled_urls
            WHERE job_id = ? AND page_type = 'article' AND status = 'crawled'
            ORDER BY id ASC
            """, (job_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_job_stats(self, job_id: int) -> Dict[str, int]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM crawled_urls WHERE job_id = ?", (job_id,))
            total_discovered = (await cursor.fetchone())[0]

            cursor = await db.execute("""
            SELECT COUNT(*) FROM crawled_urls
            WHERE job_id = ? AND page_type = 'article' AND status = 'crawled'
            """, (job_id,))
            crawled_articles = (await cursor.fetchone())[0]

            cursor = await db.execute("""
            SELECT COUNT(*) FROM crawled_urls
            WHERE job_id = ? AND status = 'failed'
            """, (job_id,))
            failed = (await cursor.fetchone())[0]

            return {
                "discovered": total_discovered,
                "crawled_articles": crawled_articles,
                "failed": failed
            }

    async def get_successfully_crawled_urls_for_host(self, root_url: str) -> Set[str]:
        """
        Returns all article URLs successfully crawled for this root_url across all jobs (for resume/incremental).
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
            SELECT DISTINCT c.url FROM crawled_urls c
            JOIN crawl_jobs j ON c.job_id = j.id
            WHERE j.root_url = ? AND c.status = 'crawled'
            """, (root_url,))
            rows = await cursor.fetchall()
            return {row[0] for row in rows}
