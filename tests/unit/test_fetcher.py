"""Unit tests for the HTTP fetcher — all network calls are mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.fetcher import FetchError, fetch_url_metadata


@pytest.mark.asyncio
async def test_fetch_success():
    """Happy path: valid URL returns headers, cookies, and page source."""
    mock_response = MagicMock()
    mock_response.headers = {"content-type": "text/html"}
    mock_response.cookies = {}
    mock_response.text = "<html>hello</html>"
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.services.fetcher.httpx.AsyncClient", return_value=mock_client):
        result = await fetch_url_metadata("https://example.com")

    assert result["headers"] == {"content-type": "text/html"}
    assert result["page_source"] == "<html>hello</html>"
    assert result["cookies"] == {}


@pytest.mark.asyncio
async def test_fetch_timeout_raises_fetch_error():
    """Timeouts are wrapped in FetchError so callers get one exception type."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

    with patch("app.services.fetcher.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(FetchError, match="timed out"):
            await fetch_url_metadata("https://slow.example.com")


@pytest.mark.asyncio
async def test_fetch_http_error_raises_fetch_error():
    """Non-2xx responses are raised as FetchError."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=mock_response)
    )

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.services.fetcher.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(FetchError):
            await fetch_url_metadata("https://notfound.example.com")


@pytest.mark.asyncio
async def test_fetch_connection_error_raises_fetch_error():
    """Network-level errors are wrapped in FetchError."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=httpx.RequestError("connection refused"))

    with patch("app.services.fetcher.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(FetchError, match="connection refused"):
            await fetch_url_metadata("https://unreachable.example.com")
