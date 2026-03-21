FROM ghcr.io/astral-sh/uv:latest

WORKDIR /app

# Copy core and db_service
COPY src/core ./src/core
COPY src/db_service ./src/db_service

WORKDIR /app/src/db_service

# Sync dependencies
RUN uv sync --no-editable

# Expose FastAPI port
EXPOSE 8000

# Run the FastAPI application
CMD ["uv", "run", "python", "main.py"]
