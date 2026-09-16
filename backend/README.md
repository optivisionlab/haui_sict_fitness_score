## Haui Sport Fitness Score API

The backend implements the MongoDB/PyMongo and Pydantic v2 contract in `api.md`.
Legacy class, exam, result, Redis, and PostgreSQL-era routes have been removed.

### Run locally

```bash
uv sync
uv run uvicorn app.main:app --reload --port 2305
```

The versioned API is available at `http://localhost:2305/api/v1`.
Set `MONGODB_URI`, `MONGODB_DB`, and `SECRET_KEY` in `.env` before starting the service.
