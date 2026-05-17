"""
HTTP fetching logic — entirely decoupled from storage or routing.

httpx is used instead of requests because Motor requires an async event loop,
and mixing sync I/O with async code on the same thread causes subtle deadlocks.
"""

import httpx

from app.core.config import settings


class FetchError(Exception):
    """Raised when the remote URL cannot be fetched for any recoverable reason."""


async def fetch_url_metadata(url: str) -> dict:
    """
    Perform a single HTTP GET and return headers, cookies, and raw page source.

    Follows redirects up to fetch_max_redirects. Does not execute JavaScript —
    returns the raw server response body only.

    Raises FetchError for timeouts, connection errors, or non-2xx responses so
    callers get a single exception type to handle rather than httpx internals.
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            max_redirects=settings.fetch_max_redirects,
            timeout=settings.fetch_timeout_seconds,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        return {
            "headers": dict(response.headers),
            # httpx exposes cookies as a Cookies object; convert to plain dict for storage.
            "cookies": dict(response.cookies),
            "page_source": response.text,
        }

    except httpx.TimeoutException as exc:
        raise FetchError(f"Request timed out after {settings.fetch_timeout_seconds}s: {url}") from exc
    except httpx.TooManyRedirects as exc:
        raise FetchError(f"Too many redirects for URL: {url}") from exc
    except httpx.HTTPStatusError as exc:
        raise FetchError(f"HTTP {exc.response.status_code} from {url}") from exc
    except httpx.RequestError as exc:
        raise FetchError(f"Connection error for {url}: {exc}") from exc
