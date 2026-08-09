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

class YouTubeExtractor:
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir

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

                # Get video URL
                v_url = entry.get("url")
                if not v_url and entry.get("id"):
                    v_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                
                if not v_url:
                    continue

                # Ensure canonical video link
                if not v_url.startswith("http"):
                    v_url = f"https://www.youtube.com/watch?v={v_url}"

                # Date filtering (upload_date is YYYYMMDD, release_timestamp is epoch)
                video_date = None
                upload_date_str = entry.get("upload_date")
                release_timestamp = entry.get("release_timestamp") or entry.get("timestamp")

                if release_timestamp:
                    try:
                        # Local date approximation from timestamp
                        video_date = datetime.fromtimestamp(release_timestamp)
                    except Exception:
                        pass
                elif upload_date_str and len(upload_date_str) == 8:
                    try:
                        video_date = datetime.strptime(upload_date_str, "%Y%m%d")
                    except Exception:
                        pass

                if video_date:
                    v_date_only = video_date.date()
                    if dt_start and v_date_only < dt_start.date():
                        continue
                    if dt_end and v_date_only > dt_end.date():
                        continue
                else:
                    # If date is completely unknown and date filters are set, we include it by default or keep it
                    pass

                matched_videos.append({
                    "url": v_url,
                    "title": entry.get("title", ""),
                    "date": video_date.strftime("%Y-%m-%d") if video_date else ""
                })

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
            "export_path": export_path,
            "export_filename": filename,
            "format": export_fmt
        }
