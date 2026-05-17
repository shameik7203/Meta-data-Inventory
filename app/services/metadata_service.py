"""
Core business logic for metadata storage and retrieval.

This module is the single authoritative place for all interactions between the
HTTP layer and MongoDB. Routes and workers call these functions; they do not
touch Motor directly.
"""

from datetime import datetime

from pymongo.errors import DuplicateKeyError

from app.db.mongo import get_collection
from app.models.metadata import MetadataDocument, MetadataResponse
from app.services.fetcher import FetchError, fetch_url_metadata


class DuplicateURLError(Exception):
    """Raised when a POST attempts to store a URL that already exists."""


async def store_metadata(url: str) -> MetadataResponse:
    """
    Fetch and persist metadata for the given URL. Returns the stored record.

    Raises:
        FetchError: if the remote URL cannot be retrieved.
        DuplicateURLError: if the URL already exists in the database.
    """
    raw = await fetch_url_metadata(url)
    doc = MetadataDocument(
        url=url,
        headers=raw["headers"],
        cookies=raw["cookies"],
        page_source=raw["page_source"],
        collected_at=datetime.utcnow(),
    )

    collection = get_collection()
    try:
        await collection.insert_one(doc.model_dump())
    except DuplicateKeyError:
        # The unique index on `url` prevents double storage. Surface this so the
        # route layer can return a meaningful 409 instead of a 500.
        raise DuplicateURLError(f"Metadata for '{url}' already exists.")

    return MetadataResponse(**doc.model_dump())


async def get_metadata(url: str) -> MetadataResponse | None:
    """
    Look up a stored metadata record by exact URL.

    Returns None when no record exists, letting the route layer decide whether
    to return 404 or 202 depending on context.
    """
    collection = get_collection()
    doc = await collection.find_one({"url": url}, {"_id": 0})
    if doc is None:
        return None
    return MetadataResponse(**doc)


async def upsert_metadata_background(url: str) -> None:
    """
    Fetch and store metadata, silently ignoring duplicates.

    Used by the background worker: if two rapid GETs race, only one insertion
    wins; the other is a no-op rather than an error.
    """
    try:
        raw = await fetch_url_metadata(url)
    except FetchError:
        # Background failures are silent — we can't surface them to the caller
        # because the 202 has already been sent. A real system would push this
        # to a dead-letter queue or increment a metric here.
        return

    doc = MetadataDocument(
        url=url,
        headers=raw["headers"],
        cookies=raw["cookies"],
        page_source=raw["page_source"],
        collected_at=datetime.utcnow(),
    )

    collection = get_collection()
    try:
        await collection.insert_one(doc.model_dump())
    except DuplicateKeyError:
        pass  # Another request already stored it — nothing to do.
