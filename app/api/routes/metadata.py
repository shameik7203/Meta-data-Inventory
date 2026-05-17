"""
FastAPI router for /metadata endpoints.

Routes are intentionally thin — they validate input, call service functions,
and map results to HTTP status codes. No business logic lives here.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.models.metadata import MetadataRequest, MetadataResponse, QueuedResponse
from app.services.fetcher import FetchError
from app.services.metadata_service import DuplicateURLError, get_metadata, store_metadata
from app.workers.collector import collect_metadata_task

router = APIRouter(prefix="/metadata", tags=["Metadata"])


@router.post(
    "",
    response_model=MetadataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Collect and store URL metadata",
    description=(
        "Fetches HTTP headers, cookies, and raw page source from the provided URL "
        "and persists the result to MongoDB. Returns the stored record on success. "
        "Returns 409 if the URL has already been collected, 422 for invalid URLs, "
        "and 502 if the target URL cannot be reached."
    ),
    responses={
        409: {"description": "Metadata for this URL already exists."},
        502: {"description": "Failed to fetch the target URL."},
    },
)
async def post_metadata(body: MetadataRequest) -> MetadataResponse:
    """Fetch metadata for a URL and store it; returns the created record."""
    url = str(body.url)
    try:
        return await store_metadata(url)
    except DuplicateURLError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except FetchError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.get(
    "",
    summary="Retrieve stored URL metadata",
    description=(
        "Returns the stored metadata for the given URL if it exists (200). "
        "If no record is found, enqueues a background collection job and returns "
        "202 Accepted — the data will be available on a subsequent request."
    ),
    responses={
        200: {"model": MetadataResponse, "description": "Metadata found and returned."},
        202: {"model": QueuedResponse, "description": "Not found; queued for collection."},
    },
)
async def get_metadata_endpoint(
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="The URL to look up."),
):
    """Return stored metadata or trigger background collection and return 202."""
    record = await get_metadata(url)
    if record is not None:
        return record

    # Kick off collection without blocking the response. FastAPI's BackgroundTasks
    # runs the coroutine on the same event loop after the response is sent.
    background_tasks.add_task(collect_metadata_task, url)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=QueuedResponse(
            message="URL has been queued for metadata collection. Retry shortly.",
            url=url,
        ).model_dump(),
    )
