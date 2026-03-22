FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

COPY src/core ./core
COPY src/swisslos_scrape_service ./swisslos_scrape_service

WORKDIR /app/swisslos_scrape_service

RUN uv sync --no-editable
RUN uv run playwright install chromium --with-deps

CMD ["uv", "run", "main.py"]