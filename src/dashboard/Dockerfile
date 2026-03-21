FROM ghcr.io/astral-sh/uv:latest

WORKDIR /app

# Copy core and dashboard services
COPY src/core ./src/core
COPY src/dashboard ./src/dashboard

WORKDIR /app/src/dashboard

# Sync dependencies
RUN uv sync --no-editable

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["uv", "run", "streamlit", "run", "main.py", "--server.address=0.0.0.0"]
