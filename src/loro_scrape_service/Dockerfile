FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

COPY src/core ./core
COPY src/loro_scrape_service ./loro_scrape_service

WORKDIR /app/loro_scrape_service

RUN uv sync --no-editable

CMD ["uv", "run", "main.py"]