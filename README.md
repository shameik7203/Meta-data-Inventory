# HTTP Metadata Inventory Service

A production-grade REST API that collects and stores HTTP metadata (headers, cookies, raw page source) for any URL. Built with FastAPI, Motor (async MongoDB), and Docker Compose.

---

## Quick Start

```bash
cp .env.example .env
docker-compose up --build
```

- API: `http://localhost:8000`
- Interactive docs (Swagger): `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Running Tests

Integration tests require a running MongoDB instance. Spin up only the DB container first:

```bash
# Start MongoDB only
docker-compose up mongo -d

# Install dependencies locally (use a virtualenv)
pip install -r requirements.txt

# Run all tests
pytest

# Verbose output
pytest -v

# Unit tests only — fully mocked, no MongoDB required
pytest tests/unit/

# Integration tests only
pytest tests/integration/
```

---

## Endpoints

### `POST /metadata`

Fetch and store metadata for a URL immediately (synchronous).

**Request**
```http
POST /metadata
Content-Type: application/json

{
  "url": "https://example.com"
}
```

**Response `201 Created`**
```json
{
  "url": "https://example.com",
  "headers": {
    "content-type": "text/html; charset=UTF-8",
    "server": "nginx"
  },
  "cookies": {},
  "page_source": "<!DOCTYPE html>...",
  "collected_at": "2024-01-15T10:30:00.123456"
}
```

| Status | Meaning |
|--------|---------|
| `201`  | Created — metadata stored and returned |
| `409`  | Conflict — URL already exists in the database |
| `422`  | Unprocessable Entity — invalid URL format |
| `502`  | Bad Gateway — failed to reach the target URL |

---

### `GET /metadata?url=https://example.com`

Retrieve stored metadata. Triggers background collection if not yet stored.

**Request**
```http
GET /metadata?url=https://example.com
```

**Response `200 OK`** — record exists:
```json
{
  "url": "https://example.com",
  "headers": { ... },
  "cookies": {},
  "page_source": "...",
  "collected_at": "2024-01-15T10:30:00.123456"
}
```

**Response `202 Accepted`** — not yet stored, queued for collection:
```json
{
  "message": "URL has been queued for metadata collection. Retry shortly.",
  "url": "https://example.com"
}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `DB_NAME` | `metadata_db` | Database name |
| `COLLECTION_NAME` | `metadata` | Collection name |
| `FETCH_TIMEOUT_SECONDS` | `10` | HTTP request timeout in seconds |
| `FETCH_MAX_REDIRECTS` | `5` | Maximum redirects to follow |
| `APP_HOST` | `0.0.0.0` | Uvicorn bind address |
| `APP_PORT` | `8000` | Uvicorn bind port |
| `LOG_LEVEL` | `info` | Uvicorn log level (`debug`, `info`, `warning`, `error`) |

---

## Project Structure

```
metadata-service/
├── app/
│   ├── main.py                  # App factory + lifespan (DB connect/disconnect)
│   ├── api/
│   │   └── routes/
│   │       └── metadata.py      # HTTP layer only — no business logic
│   ├── services/
│   │   ├── fetcher.py           # httpx-based URL fetching, raises FetchError
│   │   └── metadata_service.py  # All DB read/write logic
│   ├── db/
│   │   └── mongo.py             # Motor client lifecycle + collection accessor
│   ├── models/
│   │   └── metadata.py          # Pydantic v2 request/response/document models
│   ├── core/
│   │   └── config.py            # pydantic-settings config (all env vars)
│   └── workers/
│       └── collector.py         # Background task entry point
├── tests/
│   ├── conftest.py              # Shared fixtures (test DB, AsyncClient)
│   ├── unit/                    # Fully mocked — no external dependencies
│   └── integration/             # Real FastAPI + real MongoDB
├── docker-compose.yml
├── Dockerfile
├── pytest.ini
├── requirements.txt
└── .env.example
```

**Key design decisions:**

- `services/` is the only layer that touches MongoDB. Routes and workers delegate to it, so swapping the DB requires changes in one place.
- `fetcher.py` is isolated from storage — the HTTP client can be replaced (e.g. with playwright for JS rendering) without touching `metadata_service.py`.
- `workers/` is a thin shim over `services/`. Moving to Celery or ARQ later means replacing only this directory.
- Background collection uses FastAPI's `BackgroundTasks` — same event loop, no extra process or queue required.
- A unique MongoDB index on `url` enforces exactly-once storage at the database level, not just application level.
