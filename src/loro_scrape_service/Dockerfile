FROM ghcr.io/astral-sh/uv:latest

WORKDIR /app

# Copy core and loro_scrape_service
COPY src/core ./src/core
COPY src/loro_scrape_service ./src/loro_scrape_service

WORKDIR /app/src/loro_scrape_service

# Sync dependencies
RUN uv sync --no-editable

# Run the scraping service
CMD ["uv", "run", "python", "main.py"]
