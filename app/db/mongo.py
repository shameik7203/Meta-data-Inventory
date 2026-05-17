"""
MongoDB connection lifecycle and collection accessor.

Motor's AsyncIOMotorClient is created once at startup and closed at shutdown
via FastAPI's lifespan context manager. A module-level reference is stored so
routes and services can call get_collection() without passing a client around.

Index creation is idempotent — safe to call on every startup.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo import ASCENDING, IndexModel

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


async def connect_db() -> None:
    """Open the Motor client and ensure required indexes exist."""
    global _client
    _client = AsyncIOMotorClient(settings.mongo_uri)
    collection = _client[settings.db_name][settings.collection_name]
    # Unique index on url ensures exactly-once storage and O(1) lookup.
    await collection.create_indexes(
        [IndexModel([("url", ASCENDING)], unique=True, name="url_unique")]
    )


async def close_db() -> None:
    """Close the Motor client gracefully on app shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_collection() -> AsyncIOMotorCollection:
    """Return the metadata collection. Raises if called before connect_db()."""
    if _client is None:
        raise RuntimeError("Database client is not initialised. Call connect_db() first.")
    return _client[settings.db_name][settings.collection_name]
