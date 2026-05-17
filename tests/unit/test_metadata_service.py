"""Unit tests for metadata_service — MongoDB and fetcher are mocked."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from pymongo.errors import DuplicateKeyError

from app.services.metadata_service import DuplicateURLError, get_metadata, store_metadata

FAKE_FETCH_RESULT = {
    "headers": {"content-type": "text/html"},
    "cookies": {},
    "page_source": "<html>test</html>",
}


@pytest.mark.asyncio
async def test_store_metadata_success():
    """store_metadata returns a MetadataResponse on success."""
    mock_collection = AsyncMock()
    mock_collection.insert_one = AsyncMock()

    with patch("app.services.metadata_service.fetch_url_metadata", return_value=FAKE_FETCH_RESULT), \
         patch("app.services.metadata_service.get_collection", return_value=mock_collection):
        result = await store_metadata("https://example.com")

    # Pydantic v2 normalizes URLs — trailing slash is expected
    assert result.url == "https://example.com/"
    assert result.headers == {"content-type": "text/html"}
    assert result.page_source == "<html>test</html>"


@pytest.mark.asyncio
async def test_store_metadata_duplicate_raises():
    """Duplicate URL insertion raises DuplicateURLError."""
    mock_collection = AsyncMock()
    mock_collection.insert_one = AsyncMock(side_effect=DuplicateKeyError("dup key"))

    with patch("app.services.metadata_service.fetch_url_metadata", return_value=FAKE_FETCH_RESULT), \
         patch("app.services.metadata_service.get_collection", return_value=mock_collection):
        with pytest.raises(DuplicateURLError):
            await store_metadata("https://example.com")


@pytest.mark.asyncio
async def test_get_metadata_returns_record_when_found():
    """get_metadata returns MetadataResponse when document exists."""
    doc = {
        "url": "https://example.com",
        "headers": {},
        "cookies": {},
        "page_source": "<html/>",
        "collected_at": datetime.now(timezone.utc),
    }
    mock_collection = AsyncMock()
    mock_collection.find_one = AsyncMock(return_value=doc)

    with patch("app.services.metadata_service.get_collection", return_value=mock_collection):
        result = await get_metadata("https://example.com")

    assert result is not None
    assert result.url == "https://example.com"


@pytest.mark.asyncio
async def test_get_metadata_returns_none_when_missing():
    """get_metadata returns None when no document exists."""
    mock_collection = AsyncMock()
    mock_collection.find_one = AsyncMock(return_value=None)

    with patch("app.services.metadata_service.get_collection", return_value=mock_collection):
        result = await get_metadata("https://missing.example.com")

    assert result is None
