import os
import asyncio
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

from src.database import Database
from src.robots import RobotsChecker
from src.exporter import ArticleExporter
from src.crawler import CrawlEngine, CrawlStatus
from src.youtube import YouTubeExtractor

class StartCrawlRequest(BaseModel):
    root_url: str
    output_format: str = "md"
    ignore_robots: bool = False

class CheckRobotsRequest(BaseModel):
    url: str

class YouTubeExtractRequest(BaseModel):
    channel_url: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    export_format: str = "csv"

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

def create_app(db_path: str = "crawler.db", output_dir: str = "./output") -> FastAPI:
    db = Database(db_path=db_path)
    exporter = ArticleExporter(base_output_dir=output_dir)
    robots_checker = RobotsChecker()
    ws_manager = ConnectionManager()
    yt_extractor = YouTubeExtractor(output_dir=output_dir)
    
    # Single active engine instance
    engine = CrawlEngine(db=db, exporter=exporter)
    crawl_task: Optional[asyncio.Task] = None

    def on_crawler_progress(event_data: dict):
        # Broadcast via WebSocket in running event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(ws_manager.broadcast(event_data))
        except Exception:
            pass

    engine.on_progress = on_crawler_progress

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await db.init_db()
        yield

    app = FastAPI(title="Website Crawler", lifespan=lifespan)

    # Static files directory
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(static_dir, exist_ok=True)

    @app.get("/", response_class=HTMLResponse)
    async def serve_index():
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return HTMLResponse("<h1>Website Crawler Dashboard</h1>")

    @app.post("/api/check-robots")
    async def check_robots(req: CheckRobotsRequest):
        allowed, reason = await robots_checker.check_url(req.url)
        return {
            "allowed": allowed,
            "reason": reason
        }

    @app.post("/api/crawl/start")
    async def start_crawl(req: StartCrawlRequest):
        nonlocal crawl_task
        
        if engine.status == CrawlStatus.RUNNING:
            raise HTTPException(status_code=400, detail="A crawl job is already in progress.")

        # Check robots if not explicitly ignored
        if not req.ignore_robots:
            allowed, reason = await robots_checker.check_url(req.root_url)
            if not allowed:
                return {
                    "status": "robots_warning",
                    "reason": reason,
                    "message": "Target website robots.txt disallows crawling. User confirmation required."
                }

        fmt = req.output_format.lower()
        if fmt not in ["md", "html"]:
            fmt = "md"

        # Launch crawling in background task
        async def run_job():
            try:
                await engine.start_crawl(root_url=req.root_url, output_format=fmt)
            except Exception as e:
                print(f"Crawl job error: {e}")

        crawl_task = asyncio.create_task(run_job())
        
        # Short yield to allow job record creation
        await asyncio.sleep(0.05)
        
        return {
            "status": "running",
            "job_id": engine.current_job_id,
            "root_url": req.root_url,
            "output_format": fmt,
            "output_dir": exporter.get_host_output_dir(req.root_url)
        }

    @app.post("/api/crawl/pause")
    async def pause_crawl():
        await engine.pause()
        return {"status": engine.status.value}

    @app.post("/api/crawl/resume")
    async def resume_crawl():
        await engine.resume()
        return {"status": engine.status.value}

    @app.post("/api/crawl/cancel")
    async def cancel_crawl():
        await engine.cancel()
        return {"status": engine.status.value}

    @app.get("/api/crawl/status")
    async def get_current_status():
        latest_job = await db.get_latest_job()
        if not latest_job:
            return {
                "status": "idle",
                "job": None,
                "articles": [],
                "urls": [],
                "stats": {"discovered": 0, "crawled_articles": 0, "failed": 0},
                "active_url": None
            }
            
        stats = await db.get_job_stats(latest_job["id"])
        articles = await db.get_crawled_articles(latest_job["id"])
        urls = await db.get_crawled_urls(latest_job["id"])
        
        return {
            "status": engine.status.value if engine.current_job_id == latest_job["id"] else latest_job["status"],
            "job": latest_job,
            "stats": stats,
            "articles": articles,
            "urls": urls,
            "active_url": engine.active_url
        }

    @app.get("/api/jobs/{job_id}")
    async def get_job_details(job_id: int):
        job = await db.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        stats = await db.get_job_stats(job_id)
        articles = await db.get_crawled_articles(job_id)
        urls = await db.get_crawled_urls(job_id)
        return {
            "job": job,
            "stats": stats,
            "articles": articles,
            "urls": urls
        }

    @app.post("/api/youtube/extract")
    async def extract_youtube(req: YouTubeExtractRequest):
        try:
            # Run extraction in thread pool since yt-dlp is synchronous/blocking
            result = await asyncio.to_thread(
                yt_extractor.extract,
                channel_url=req.channel_url,
                start_date=req.start_date,
                end_date=req.end_date,
                export_format=req.export_format
            )
            return {
                "status": "success",
                **result
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/youtube/download/{filename}")
    async def download_youtube_export(filename: str):
        file_path = os.path.join(output_dir, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(file_path, filename=filename)

    @app.websocket("/ws/progress")
    async def websocket_progress(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            # Send initial current status immediately on connect
            latest_job = await db.get_latest_job()
            if latest_job:
                stats = await db.get_job_stats(latest_job["id"])
                articles = await db.get_crawled_articles(latest_job["id"])
                urls = await db.get_crawled_urls(latest_job["id"])
                await websocket.send_json({
                    "event": "initial_state",
                    "job_id": latest_job["id"],
                    "status": engine.status.value if engine.current_job_id == latest_job["id"] else latest_job["status"],
                    "output_dir": latest_job["output_dir"],
                    "stats": stats,
                    "articles": articles,
                    "urls": urls,
                    "active_url": engine.active_url
                })
            while True:
                # Keep connection alive
                await websocket.receive_text()
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)
        except Exception:
            ws_manager.disconnect(websocket)

    # Mount static assets
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    return app

# Default app instance for uvicorn
app = create_app()
