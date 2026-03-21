FROM ghcr.io/astral-sh/uv:latest

WORKDIR /app

# Copy core and swisslos_scrape_service
COPY src/core ./src/core
COPY src/swisslos_scrape_service ./src/swisslos_scrape_service

WORKDIR /app/src/swisslos_scrape_service

# Sync dependencies
RUN uv sync --no-editable

# Run the scraping service
CMD ["uv", "run", "python", "main.py"]
