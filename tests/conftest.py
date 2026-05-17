"""
Shared pytest fixtures for unit and integration tests.

The integration fixtures spin up a real Motor client pointed at a test database
(metadata_test_db) so tests exercise actual MongoDB behaviour — mocking Motor
would give false confidence given how much logic lives in index constraints and
the duplicate-key error path.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, IndexModel

from app.core.config import settings
from app.db import mongo as mongo_module
from app.main import app

TEST_DB_NAME = "metadata_test_db"


@pytest_asyncio.fixture
async def test_db():
    """
    Connect to a dedicated test database and drop the collection after each test.

    Using a separate database name prevents test runs from corrupting real data
    and allows parallelism without index conflicts.
    """
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[TEST_DB_NAME]
    collection = db[settings.collection_name]

    # Mirror the production index so duplicate-key behaviour is identical in tests.
    await collection.create_indexes(
        [IndexModel([("url", ASCENDING)], unique=True, name="url_unique")]
    )

    # Patch module-level client so get_collection() uses the test DB.
    original_client = mongo_module._client
    original_db_name = settings.db_name
    mongo_module._client = client
    settings.db_name = TEST_DB_NAME

    yield collection

    # Teardown: wipe test data and restore original state.
    await collection.drop()
    mongo_module._client = original_client
    settings.db_name = original_db_name
    client.close()


@pytest_asyncio.fixture
async def async_client(test_db):
    """httpx AsyncClient wired to the FastAPI app with the test DB in place."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
