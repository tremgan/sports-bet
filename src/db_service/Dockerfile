FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

COPY src/core ./core
COPY src/db_service ./db_service

WORKDIR /app/db_service

RUN uv sync --no-editable

EXPOSE 8000


# Run the FastAPI application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
