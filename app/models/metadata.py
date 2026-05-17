"""
Pydantic v2 models for API request/response payloads and the internal DB document shape.

Separating the DB document model (MetadataDocument) from the API response model
(MetadataResponse) gives us freedom to evolve the storage schema without breaking
the public contract.
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, Field


def normalize_url(url: str | AnyHttpUrl) -> str:
    """
    Canonicalize a URL string the same way Pydantic v2 does for AnyHttpUrl fields.

    Pydantic v2 normalizes 'https://example.com' → 'https://example.com/' (trailing slash).
    Any code path that stores or queries a URL must pass through this function so the
    key is always in the same form, preventing POST/GET lookup mismatches.
    """
    return str(AnyHttpUrl(str(url)))


class MetadataRequest(BaseModel):
    """Payload for POST /metadata."""

    url: AnyHttpUrl = Field(..., description="Fully-qualified HTTP/HTTPS URL to collect metadata from.")


class MetadataResponse(BaseModel):
    """
    Full metadata record returned to the client.

    headers and cookies are free-form dicts because their keys are determined
    by the remote server, not by us.
    """

    url: str
    headers: dict[str, Any]
    cookies: dict[str, Any]
    page_source: str
    collected_at: datetime

    model_config = {"populate_by_name": True}


class QueuedResponse(BaseModel):
    """Returned when a URL is accepted for background collection (202)."""

    message: str
    url: str


class MetadataDocument(BaseModel):
    """
    Internal shape of a document stored in MongoDB.

    Not exposed directly via the API — converted to MetadataResponse before returning.
    """

    url: str
    headers: dict[str, Any]
    cookies: dict[str, Any]
    page_source: str
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
