"""
Background collection worker.

Intentionally thin — it delegates all logic to metadata_service.
The separation from the route module makes it easy to later move this work to
Celery, ARQ, or any task queue without touching routing code.
"""

from app.services.metadata_service import upsert_metadata_background


async def collect_metadata_task(url: str) -> None:
    """
    Entry point invoked by FastAPI's BackgroundTasks scheduler.

    Runs after the 202 response has been sent; the event loop handles it as a
    regular coroutine — no threads, no subprocesses.
    """
    await upsert_metadata_background(url)
