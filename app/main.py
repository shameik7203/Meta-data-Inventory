"""
FastAPI application factory and lifespan handler.

Lifespan (startup/shutdown) replaces the deprecated @app.on_event pattern
introduced in FastAPI 0.93. The database connection is opened once at startup
and closed cleanly on shutdown — this avoids leaving dangling Motor clients
during test teardown.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.metadata import router as metadata_router
from app.db.mongo import close_db, connect_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open DB connection before serving requests; close it on shutdown."""
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="HTTP Metadata Inventory Service",
    description=(
        "Collects and stores HTTP headers, cookies, and page source for any URL. "
        "Use POST /metadata to collect immediately, or GET /metadata to retrieve "
        "stored data (triggers background collection if not yet stored)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(metadata_router)
