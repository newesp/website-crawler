import os
import re
import csv
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import yt_dlp

def normalize_youtube_channel_url(url: str) -> str:
    """
    Normalizes input string/URL to standard channel URL format:
    e.g. @channel -> https://www.youtube.com/@channel
    http://youtube.com/@channel/videos -> https://www.youtube.com/@channel
    """
    url = url.strip()
    if not url:
        return ""
    
    # If handle without domain: @handle
    if url.startswith("@"):
        return f"https://www.youtube.com/{url}"
    
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    # Normalize protocol and www domain
    url = re.sub(r"^https?://(?:www\.)?youtube\.com", "https://www.youtube.com", url, flags=re.IGNORECASE)

    # Handle @handle patterns
    handle_match = re.search(r"(https://www\.youtube\.com/@[\w\.\-]+)", url, re.IGNORECASE)
    if handle_match:
        return handle_match.group(1)
    
    # Handle /channel/UC... or /c/...
    channel_match = re.search(r"(https://www\.youtube\.com/(?:channel|c)/[\w\.\-]+)", url, re.IGNORECASE)
    if channel_match:
        return channel_match.group(1)

    return url

def is_single_video_url(url: str) -> bool:
    """
    Determines if the URL is a single YouTube video (e.g., watch?v=..., youtu.be/..., shorts/..., live/...).
    """
    if not url:
        return False
    url = url.strip()
    patterns = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)",
        r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]+)",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]+)",
        r"(?:https?://)?(?:www\.)?youtube\.com/live/([a-zA-Z0-9_-]+)",
    ]
    for pattern in patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False

def extract_video_id(url: str) -> Optional[str]:
    """
    Extracts the YouTube 11-character video ID from supported URL patterns.
    """
    if not url:
        return None
    url = url.strip()
    patterns = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)",
        r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]+)",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]+)",
        r"(?:https?://)?(?:www\.)?youtube\.com/live/([a-zA-Z0-9_-]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, url, re.IGNORECASE)
        if m:
            return m.group(1)
    return None

class YouTubeExtractor:
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir
        self._date_cache = {}

    def _get_video_date(self, url: str, entry: Optional[dict] = None) -> Optional[datetime.date]:
        if entry:
            release_timestamp = entry.get("release_timestamp") or entry.get("timestamp")
            if release_timestamp:
                try:
                    return datetime.fromtimestamp(release_timestamp).date()
                except Exception:
                    pass
            upload_date_str = entry.get("upload_date")
            if upload_date_str and len(upload_date_str) == 8:
                try:
                    return datetime.strptime(upload_date_str, "%Y%m%d").date()
                except Exception:
                    pass

        if url in self._date_cache:
            return self._date_cache[url]

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False, process=False)
                if info:
                    date_str = info.get("upload_date")
                    if date_str and len(date_str) == 8:
                        d = datetime.strptime(date_str, "%Y%m%d").date()
                        self._date_cache[url] = d
                        return d
        except Exception:
            pass
        self._date_cache[url] = None
        return None

    def _find_date_index(self, entries: List[dict], target_date: datetime.date, find_start: bool) -> int:
        if not entries:
            return 0
        
        low = 0
        high = len(entries) - 1
        best_idx = 0 if find_start else len(entries) - 1
        
        while low <= high:
            mid = (low + high) // 2
            entry = entries[mid]
            url = entry.get("url")
            if not url and entry.get("id"):
                url = f"https://www.youtube.com/watch?v={entry['id']}"
            if not url:
                low += 1
                continue
                
            if not url.startswith("http"):
                url = f"https://www.youtube.com/watch?v={url}"

            d = self._get_video_date(url, entry)
            if not d:
                # If we really can't get date, try next
                low += 1
                continue
                
            if find_start:
                if d >= target_date:
                    best_idx = mid
                    low = mid + 1
                else:
                    high = mid - 1
            else:
                if d <= target_date:
                    best_idx = mid
                    high = mid - 1
                else:
                    low = mid + 1
                    
        return best_idx

    def extract(
        self,
        channel_url: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        export_format: str = "csv"
    ) -> Dict[str, Any]:
        """
        Extracts public video URLs from a YouTube channel with optional date filtering (YYYY-MM-DD).
        """
        canonical_url = normalize_youtube_channel_url(channel_url)
        # Ensure we target the /videos tab for completeness
        target_url = canonical_url if canonical_url.endswith("/videos") else f"{canonical_url.rstrip('/')}/videos"

        # Parse filter dates
        dt_start = None
        if start_date:
            try:
                # Start date 00:00:00
                dt_start = datetime.strptime(start_date.strip(), "%Y-%m-%d")
            except ValueError:
                pass

        dt_end = None
        if end_date:
            try:
                # End date 23:59:59
                dt_end = datetime.strptime(end_date.strip(), "%Y-%m-%d")
            except ValueError:
                pass

        ydl_opts = {
            "extract_flat": True,
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "ignoreerrors": True,
        }

        matched_videos = []

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            if not info:
                # fallback to canonical url without /videos if failed
                info = ydl.extract_info(canonical_url, download=False)
            
            entries = info.get("entries", []) if info else []
            channel_title = info.get("title", "youtube_channel") if info else "youtube_channel"

            for entry in entries:
                if not entry:
                    continue
                v_url = entry.get("url")
                if not v_url and entry.get("id"):
                    v_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                if not v_url:
                    continue
                if not v_url.startswith("http"):
                    v_url = f"https://www.youtube.com/watch?v={v_url}"
                matched_videos.append(entry)

            # Date filtering with binary search + buffer
            if dt_start or dt_end:
                start_idx = 0
                end_idx = len(matched_videos) - 1
                buffer_size = 10

                if dt_start:
                    end_idx = self._find_date_index(matched_videos, dt_start.date(), find_start=True)
                    end_idx = min(len(matched_videos) - 1, end_idx + buffer_size)

                if dt_end:
                    start_idx = self._find_date_index(matched_videos, dt_end.date(), find_start=False)
                    start_idx = max(0, start_idx - buffer_size)

                candidate_entries = matched_videos[start_idx:end_idx + 1]
                
                final_videos = []
                for entry in candidate_entries:
                    v_url = entry.get("url")
                    if not v_url and entry.get("id"):
                        v_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                    if not v_url.startswith("http"):
                        v_url = f"https://www.youtube.com/watch?v={v_url}"
                        
                    d = self._get_video_date(v_url, entry)
                    if d:
                        if dt_start and d < dt_start.date():
                            continue
                        if dt_end and d > dt_end.date():
                            continue
                    
                    final_videos.append({
                        "url": v_url,
                        "title": entry.get("title", ""),
                        "date": d.strftime("%Y-%m-%d") if d else ""
                    })
                matched_videos = final_videos
            else:
                # Map to format if no filters
                final_videos = []
                for entry in matched_videos:
                    v_url = entry.get("url")
                    if not v_url and entry.get("id"):
                        v_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                    if not v_url.startswith("http"):
                        v_url = f"https://www.youtube.com/watch?v={v_url}"
                    final_videos.append({
                        "url": v_url,
                        "title": entry.get("title", ""),
                        "date": ""
                    })
                matched_videos = final_videos

        # Generate export file
        os.makedirs(self.output_dir, exist_ok=True)
        # Safe filename
        safe_title = re.sub(r'[\\/*?:"<>| ]+', "_", channel_title)[:50]
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        export_fmt = export_format.lower() if export_format else "csv"
        if export_fmt not in ["csv", "txt"]:
            export_fmt = "csv"

        filename = f"youtube_{safe_title}_{timestamp_str}.{export_fmt}"
        export_path = os.path.join(self.output_dir, filename)

        video_urls = [v["url"] for v in matched_videos]

        if export_fmt == "csv":
            with open(export_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["URL"])
                for u in video_urls:
                    writer.writerow([u])
        else:
            with open(export_path, "w", encoding="utf-8") as f:
                for u in video_urls:
                    f.write(f"{u}\n")

        return {
            "channel_url": canonical_url,
            "channel_title": channel_title,
            "total_count": len(video_urls),
            "video_urls": video_urls,
            "videos": matched_videos,
            "export_path": export_path,
            "export_filename": filename,
            "format": export_fmt
        }

    def download_video(
        self,
        url: str,
        quality: str = "1080p",
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Downloads a single YouTube video or audio file to output/youtube_videos/.
        Quality options:
          - '1080p': Best MP4 up to 1080p
          - '720p': Best MP4 up to 720p
          - 'mp3': Best audio converted to MP3
        """
        vid_dir = os.path.join(self.output_dir, "youtube_videos")
        os.makedirs(vid_dir, exist_ok=True)

        vid_id = extract_video_id(url) or "video"

        def _hook(d):
            if not progress_callback:
                return
            try:
                status = d.get("status")
                percent = 0.0
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                if total and total > 0:
                    percent = round((downloaded / total) * 100, 1)
                elif status == "finished":
                    percent = 100.0

                speed_bytes = d.get("speed")
                speed_str = f"{round(speed_bytes / (1024 * 1024), 1)} MB/s" if speed_bytes else ""
                eta = d.get("eta")
                eta_str = f"{eta}s" if eta else ""

                progress_callback({
                    "video_id": vid_id,
                    "status": status,
                    "percent": percent,
                    "speed": speed_str,
                    "eta": eta_str,
                    "filename": os.path.basename(d.get("filename", "")),
                })
            except Exception:
                pass

        outtmpl = os.path.join(vid_dir, "%(title).100s_%(id)s.%(ext)s")

        quality_clean = (quality or "1080p").lower()
        if quality_clean == "mp3":
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [_hook],
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }
        elif quality_clean == "720p":
            ydl_opts = {
                "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
                "outtmpl": outtmpl,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [_hook],
            }
        else: # 1080p / default
            ydl_opts = {
                "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
                "outtmpl": outtmpl,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [_hook],
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise ValueError("Could not extract video info")

            actual_id = info.get("id", vid_id)
            actual_title = info.get("title", "youtube_video")
            safe_title = re.sub(r'[\\/*?:"<>| ]+', "_", actual_title)[:100]

            # Execute download
            ydl.download([url])

            ext = "mp3" if quality_clean == "mp3" else info.get("ext", "mp4")
            filename = f"{safe_title}_{actual_id}.{ext}"
            file_path = os.path.join(vid_dir, filename)

            # Check if file exists under actual prepared filename
            if not os.path.exists(file_path):
                # Search in vid_dir for actual_id matching file
                for f in os.listdir(vid_dir):
                    if actual_id in f:
                        filename = f
                        file_path = os.path.join(vid_dir, f)
                        break

            return {
                "status": "success",
                "video_id": actual_id,
                "title": actual_title,
                "file_path": file_path,
                "filename": filename,
                "quality": quality_clean
            }
