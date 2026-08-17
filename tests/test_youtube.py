import os
import pytest
from unittest.mock import MagicMock, patch
from datetime import date
from src.youtube import YouTubeExtractor, normalize_youtube_channel_url

def test_normalize_youtube_channel_url():
    assert normalize_youtube_channel_url("https://www.youtube.com/@testchannel") == "https://www.youtube.com/@testchannel"
    assert normalize_youtube_channel_url("http://youtube.com/@testchannel/videos") == "https://www.youtube.com/@testchannel"
    assert normalize_youtube_channel_url("youtube.com/@testchannel") == "https://www.youtube.com/@testchannel"
    assert normalize_youtube_channel_url("@testchannel") == "https://www.youtube.com/@testchannel"
    assert normalize_youtube_channel_url("https://www.youtube.com/channel/UC12345") == "https://www.youtube.com/channel/UC12345"

@patch("src.youtube.yt_dlp.YoutubeDL")
def test_extract_videos_no_date_filter(mock_ydl_class, tmp_path):
    mock_ydl = MagicMock()
    mock_ydl_class.return_value.__enter__.return_value = mock_ydl
    
    mock_ydl.extract_info.return_value = {
        "title": "Test Channel",
        "entries": [
            {"id": "vid1", "url": "https://www.youtube.com/watch?v=vid1", "title": "Video 1", "upload_date": "20260801"},
            {"id": "vid2", "url": "https://www.youtube.com/watch?v=vid2", "title": "Video 2", "upload_date": "20260805"},
            {"id": "vid3", "url": "https://www.youtube.com/watch?v=vid3", "title": "Video 3", "upload_date": "20260810"},
        ]
    }
    
    extractor = YouTubeExtractor(output_dir=str(tmp_path))
    result = extractor.extract(
        channel_url="https://www.youtube.com/@testchannel",
        start_date=None,
        end_date=None,
        export_format="csv"
    )
    
    assert len(result["video_urls"]) == 3
    assert result["video_urls"] == [
        "https://www.youtube.com/watch?v=vid1",
        "https://www.youtube.com/watch?v=vid2",
        "https://www.youtube.com/watch?v=vid3",
    ]
    assert os.path.exists(result["export_path"])
    with open(result["export_path"], "r", encoding="utf-8") as f:
        content = f.read()
    assert "https://www.youtube.com/watch?v=vid1" in content
    assert "https://www.youtube.com/watch?v=vid2" in content
    assert "https://www.youtube.com/watch?v=vid3" in content

@patch("src.youtube.yt_dlp.YoutubeDL")
def test_extract_videos_with_start_date(mock_ydl_class, tmp_path):
    mock_ydl = MagicMock()
    mock_ydl_class.return_value.__enter__.return_value = mock_ydl
    
    mock_ydl.extract_info.return_value = {
        "title": "Test Channel",
        "entries": [
            {"id": "vid1", "url": "https://www.youtube.com/watch?v=vid1", "title": "Video 1", "upload_date": "20260801"},
            {"id": "vid2", "url": "https://www.youtube.com/watch?v=vid2", "title": "Video 2", "upload_date": "20260805"},
            {"id": "vid3", "url": "https://www.youtube.com/watch?v=vid3", "title": "Video 3", "upload_date": "20260810"},
        ]
    }
    
    extractor = YouTubeExtractor(output_dir=str(tmp_path))
    result = extractor.extract(
        channel_url="https://www.youtube.com/@testchannel",
        start_date="2026-08-05",
        end_date=None,
        export_format="txt"
    )
    
    assert len(result["video_urls"]) == 2
    assert result["video_urls"] == [
        "https://www.youtube.com/watch?v=vid2",
        "https://www.youtube.com/watch?v=vid3",
    ]

@patch("src.youtube.yt_dlp.YoutubeDL")
def test_extract_videos_with_end_date(mock_ydl_class, tmp_path):
    mock_ydl = MagicMock()
    mock_ydl_class.return_value.__enter__.return_value = mock_ydl
    
    mock_ydl.extract_info.return_value = {
        "title": "Test Channel",
        "entries": [
            {"id": "vid1", "url": "https://www.youtube.com/watch?v=vid1", "title": "Video 1", "upload_date": "20260801"},
            {"id": "vid2", "url": "https://www.youtube.com/watch?v=vid2", "title": "Video 2", "upload_date": "20260805"},
            {"id": "vid3", "url": "https://www.youtube.com/watch?v=vid3", "title": "Video 3", "upload_date": "20260810"},
        ]
    }
    
    extractor = YouTubeExtractor(output_dir=str(tmp_path))
    result = extractor.extract(
        channel_url="https://www.youtube.com/@testchannel",
        start_date=None,
        end_date="2026-08-05",
        export_format="csv"
    )
    
    assert len(result["video_urls"]) == 2
    assert result["video_urls"] == [
        "https://www.youtube.com/watch?v=vid1",
        "https://www.youtube.com/watch?v=vid2",
    ]

@patch("src.youtube.yt_dlp.YoutubeDL")
def test_extract_videos_with_date_range(mock_ydl_class, tmp_path):
    mock_ydl = MagicMock()
    mock_ydl_class.return_value.__enter__.return_value = mock_ydl
    
    mock_ydl.extract_info.return_value = {
        "title": "Test Channel",
        "entries": [
            {"id": "vid1", "url": "https://www.youtube.com/watch?v=vid1", "title": "Video 1", "upload_date": "20260801"},
            {"id": "vid2", "url": "https://www.youtube.com/watch?v=vid2", "title": "Video 2", "upload_date": "20260805"},
            {"id": "vid3", "url": "https://www.youtube.com/watch?v=vid3", "title": "Video 3", "upload_date": "20260810"},
        ]
    }
    
    extractor = YouTubeExtractor(output_dir=str(tmp_path))
    result = extractor.extract(
        channel_url="https://www.youtube.com/@testchannel",
        start_date="2026-08-02",
        end_date="2026-08-08",
        export_format="csv"
    )
    
    assert len(result["video_urls"]) == 1
    assert result["video_urls"] == [
        "https://www.youtube.com/watch?v=vid2",
    ]

def test_is_single_video_url():
    from src.youtube import is_single_video_url, extract_video_id
    assert is_single_video_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert is_single_video_url("http://youtube.com/watch?v=dQw4w9WgXcQ&t=10s") is True
    assert is_single_video_url("https://youtu.be/dQw4w9WgXcQ") is True
    assert is_single_video_url("https://www.youtube.com/shorts/dQw4w9WgXcQ") is True
    assert is_single_video_url("https://www.youtube.com/live/dQw4w9WgXcQ") is True
    
    # Negative cases (channels)
    assert is_single_video_url("https://www.youtube.com/@channel") is False
    assert is_single_video_url("https://www.youtube.com/channel/UC12345") is False
    assert is_single_video_url("@channel") is False
    assert is_single_video_url("") is False

    # Extract ID
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

@patch("src.youtube.yt_dlp.YoutubeDL")
def test_download_video_1080p(mock_ydl_class, tmp_path):
    mock_ydl = MagicMock()
    mock_ydl_class.return_value.__enter__.return_value = mock_ydl
    mock_ydl.extract_info.return_value = {
        "id": "vid123",
        "title": "Sample Video Title",
        "ext": "mp4",
    }
    
    progress_updates = []
    def on_progress(p):
        progress_updates.append(p)

    extractor = YouTubeExtractor(output_dir=str(tmp_path))
    res = extractor.download_video(
        url="https://www.youtube.com/watch?v=vid123",
        quality="1080p",
        progress_callback=on_progress
    )

    assert res["status"] == "success"
    assert res["video_id"] == "vid123"
    assert res["title"] == "Sample Video Title"
    assert "youtube_videos" in res["file_path"]
    assert mock_ydl.download.called

@patch("src.youtube.yt_dlp.YoutubeDL")
def test_download_video_mp3(mock_ydl_class, tmp_path):
    mock_ydl = MagicMock()
    mock_ydl_class.return_value.__enter__.return_value = mock_ydl
    mock_ydl.extract_info.return_value = {
        "id": "vid456",
        "title": "Audio Track",
        "ext": "mp3",
    }

    extractor = YouTubeExtractor(output_dir=str(tmp_path))
    res = extractor.download_video(
        url="https://www.youtube.com/watch?v=vid456",
        quality="mp3"
    )

    assert res["status"] == "success"
    assert res["video_id"] == "vid456"
    assert mock_ydl.download.called

