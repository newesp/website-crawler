import pytest
import httpx
from src.fetcher import HttpFetcher

@pytest.mark.asyncio
async def test_http_fetcher_success():
    fetcher = HttpFetcher()
    async def mock_handler(request):
        return httpx.Response(200, text="<html><body><h1>Test</h1></body></html>")
        
    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        html = await fetcher.fetch("https://example.com/test", client=client)
        assert "<h1>Test</h1>" in html

@pytest.mark.asyncio
async def test_http_fetcher_404():
    fetcher = HttpFetcher()
    async def mock_handler(request):
        return httpx.Response(404, text="Not Found")
        
    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await fetcher.fetch("https://example.com/not-found", client=client)
