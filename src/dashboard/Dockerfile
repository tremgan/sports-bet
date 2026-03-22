FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

COPY src/core ./core
COPY src/dashboard ./dashboard

WORKDIR /app/dashboard

RUN uv sync --no-editable

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "main.py", "--server.address=0.0.0.0"]