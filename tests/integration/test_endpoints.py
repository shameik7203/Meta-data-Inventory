"""
Integration tests — real FastAPI app, real Motor, real test MongoDB instance.

These tests require a running MongoDB (provided by docker-compose or a local instance).
The MONGO_URI env var controls the connection target; CI should set it to a
dedicated test container.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.fetcher import FetchError

VALID_FETCH = {
    "headers": {"content-type": "text/html"},
    "cookies": {"session": "abc"},
    "page_source": "<html>integration test</html>",
}


@pytest.mark.asyncio
async def test_post_metadata_valid_url(async_client):
    """POST with a valid URL returns 201 with the stored record."""
    with patch("app.services.metadata_service.fetch_url_metadata", return_value=VALID_FETCH):
        response = await async_client.post("/metadata", json={"url": "https://example.com"})

    assert response.status_code == 201
    data = response.json()
    assert data["url"] == "https://example.com"
    assert "headers" in data
    assert "collected_at" in data


@pytest.mark.asyncio
async def test_post_metadata_invalid_url(async_client):
    """POST with a non-URL string returns 422 Unprocessable Entity."""
    response = await async_client.post("/metadata", json={"url": "not-a-url"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_metadata_duplicate(async_client):
    """Second POST for the same URL returns 409 Conflict."""
    with patch("app.services.metadata_service.fetch_url_metadata", return_value=VALID_FETCH):
        await async_client.post("/metadata", json={"url": "https://dup.example.com"})
        response = await async_client.post("/metadata", json={"url": "https://dup.example.com"})

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_metadata_when_record_exists(async_client):
    """GET returns 200 with the full record when data is already stored."""
    with patch("app.services.metadata_service.fetch_url_metadata", return_value=VALID_FETCH):
        await async_client.post("/metadata", json={"url": "https://get.example.com"})

    response = await async_client.get("/metadata", params={"url": "https://get.example.com"})
    assert response.status_code == 200
    assert response.json()["url"] == "https://get.example.com"


@pytest.mark.asyncio
async def test_get_metadata_when_missing_returns_202(async_client):
    """GET for an unknown URL returns 202 and triggers background collection."""
    with patch("app.workers.collector.upsert_metadata_background", new_callable=AsyncMock):
        response = await async_client.get("/metadata", params={"url": "https://new.example.com"})

    assert response.status_code == 202
    assert "queued" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_post_metadata_fetch_timeout(async_client):
    """POST that times out returns 502 Bad Gateway."""
    with patch(
        "app.services.metadata_service.fetch_url_metadata",
        side_effect=FetchError("Request timed out"),
    ):
        response = await async_client.post("/metadata", json={"url": "https://timeout.example.com"})

    assert response.status_code == 502


@pytest.mark.asyncio
async def test_db_connection_failure(async_client):
    """Service raises RuntimeError when DB client is not initialised."""
    from app.db import mongo as mongo_module

    original = mongo_module._client
    mongo_module._client = None

    try:
        with patch("app.services.metadata_service.fetch_url_metadata", return_value=VALID_FETCH):
            response = await async_client.post("/metadata", json={"url": "https://dbfail.example.com"})
        # RuntimeError from get_collection() propagates as an unhandled 500
        assert response.status_code == 500
    finally:
        mongo_module._client = original
