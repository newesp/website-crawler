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
