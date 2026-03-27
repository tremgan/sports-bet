# Swiss Sports Bet Markets

> **Disclaimer:** This project is built for **educational and portfolio purposes only**. It is not intended for commercial use, real-money betting, or any activity that violates the terms of service of the data sources referenced. The scraping code is provided as a technical demonstration of web scraping, data engineering, and microservice architecture patterns.

A Python microservice application that scrapes real-time football (soccer) betting odds from multiple Swiss bookmakers, matches events across sources using fuzzy string matching, and surfaces cross-bookmaker odds comparisons through a Streamlit dashboard.

## Project Status

The scraping pipeline, data storage, cross-bookmaker matching, and dashboard are functional. Scrapers run on a configurable interval (`SCRAPE_FREQUENCY_HOURS`). The arbitrage detection engine is not yet implemented.

## Architecture

Four independent services communicate over HTTP, plus a shared data model library:

```
+-----------------+   +----------------------+
|  Loro Scraper   |   |  Swisslos Scraper    |
|  (REST API)     |   |  (Playwright/WS)     |
+--------+--------+   +----------+-----------+
         |                       |
         |   POST /bookmaker_    |
         |   matches/ & odds/    |
         v                       v
      +-----------------------------+
      |       DB Service            |
      |  (FastAPI + SQLModel)       |
      |                             |
      |  : stores bookmaker odds    |
      |  : fuzzy-matches events     |
      |    across bookmakers        |
      |  : serves paired odds       |
      +--------------+--------------+
                     |
                     | GET /matches/with_odds/
                     v
              +-------------+
              |  Dashboard   |
              | (Streamlit)  |
              +-------------+
```

### Services

**core** : Shared Python package containing SQLModel data models (Match, BookmakerMatch, SportsBettingOdds) used by all services. Installed as an editable dependency via uv.

**loro_scrape_service** : Scrapes football betting odds from the Loterie Romande (Loro) public REST API. Parses 1X2 match odds and posts them to the DB service.

**swisslos_scrape_service** : Scrapes football betting odds from Swisslos by launching a headless Chromium browser via Playwright, intercepting WebSocket frames, and decompressing the binary (zlib-deflate) payloads to extract event and odds data.

**db_service** : FastAPI backend that stores all scraped data in a SQL database (SQLite for dev, PostgreSQL for production). Includes a match-making engine (match_maker.py) that uses time-window filtering and fuzzy string matching (rapidfuzz token_sort_ratio) to reconcile the same football match across different bookmakers. Exposes endpoints for writing odds, triggering matching, and reading paired cross-bookmaker odds.

**dashboard** : Streamlit app that displays matched events with odds from multiple bookmakers side by side.

## Data Model

```
Match (canonical event)
|-- match_label          "FC Basel vs FC Zurich"
|-- match_datetime       2026-03-25 18:00 UTC
|-- team1, team2
|
+-- BookmakerMatch (one per bookmaker per match)
    |-- bookmaker        "Loro" / "Swisslos"
    |-- match_label      (may differ slightly between bookmakers)
    |-- match_datetime
    |-- matching_attempts
    |
    +-- SportsBettingOdds (one per scrape run)
        |-- team1_odds
        |-- draw_odds
        |-- team2_odds
        +-- timestamp
```

## Cross-Bookmaker Matching

Loro and Swisslos name teams differently and may report slightly different kick-off times, so a direct join is not possible. The match_maker module handles this by:

1. Querying all BookmakerMatch rows not yet linked to a canonical Match (with fewer than 3 matching attempts).
2. For each, searching for existing Match records within a configurable time window (default: +/- 1 hour).
3. Attempting an exact match on label + datetime first.
4. Falling back to fuzzy matching using rapidfuzz.fuzz.token_sort_ratio with a configurable threshold (default: 75).
5. If no match is found, creating a new canonical Match from the bookmaker data.

Both scrapers trigger the matching process automatically after posting data via POST /run_matching/.

## Tech Stack

- Python 3.13 with type hints throughout
- FastAPI + Uvicorn for the API layer
- SQLModel (SQLAlchemy + Pydantic) for ORM and validation
- Playwright for headless browser automation and WebSocket interception
- rapidfuzz for fuzzy string matching across bookmakers
- Streamlit for the dashboard
- uv for dependency management
- Docker + Docker Compose for containerization and orchestration
- GitHub Actions for CI/CD

## Project Structure

```
sports-bet/
|-- docker-compose.yaml
|-- .github/
|   +-- workflows/
|       +-- hostinger_deploy.yaml   # GitHub Actions deploy workflow
|-- .env                        # Postgres credentials (do not commit)
|-- .gitignore
|-- src/
|   |-- core/
|   |   |-- core/
|   |   |   |-- __init__.py
|   |   |   |-- models.py      # Shared SQLModel data models
|   |   |   +-- arbitrage.py   # Arbitrage detection (not yet implemented)
|   |   +-- pyproject.toml
|   |-- db_service/
|   |   |-- api.py              # FastAPI endpoints
|   |   |-- match_maker.py      # Cross-bookmaker fuzzy matching logic
|   |   |-- config.py           # DB engine setup from env
|   |   |-- logger.py           # Logging config (file + rich console)
|   |   |-- Dockerfile
|   |   +-- pyproject.toml
|   |-- loro_scrape_service/
|   |   |-- main.py             # Loro REST API scraper
|   |   |-- config.py
|   |   |-- Dockerfile
|   |   +-- pyproject.toml
|   |-- swisslos_scrape_service/
|   |   |-- main.py             # Swisslos Playwright/WS scraper
|   |   |-- config.py
|   |   |-- Dockerfile
|   |   +-- pyproject.toml
|   +-- dashboard/
|       |-- main.py             # Streamlit dashboard
|       |-- config.py
|       |-- Dockerfile
|       +-- pyproject.toml
+-- tests/                      # (empty)
```

## Setup

Each service has its own pyproject.toml and is managed with uv (https://docs.astral.sh/uv/). The core package is referenced as a local editable dependency.

### Prerequisites

- Python 3.13+
- uv (pip install uv)
- Chromium (installed automatically by Playwright for the Swisslos scraper)

### Environment Variables

Create a .env file in the project root with:

```
POSTGRES_USER=sportsbet
POSTGRES_PASSWORD=<your-password>
POSTGRES_DB=sportsbet
```

Each scraper service and the dashboard expect a DB_SERVICE_URL variable (defaults to http://127.0.0.1:8000 for local development).

The db_service expects a SQLMODEL_DB_URL variable pointing to the database (e.g. sqlite:///test.db for local dev, or a PostgreSQL connection string for production).

### Running Locally

1. Start the DB service:

```bash
cd src/db_service
cp .env.example .env   # set SQLMODEL_DB_URL (e.g. sqlite:///test.db)
uv sync
uv run uvicorn api:app --reload
```

2. Run the scrapers:

```bash
# Loro (quick, REST-based)
cd src/loro_scrape_service
uv sync
uv run main.py

# Swisslos (launches headless browser, takes ~15s)
cd src/swisslos_scrape_service
uv sync
uv run playwright install chromium --with-deps
uv run main.py
```

3. Launch the dashboard:

```bash
cd src/dashboard
uv sync
uv run streamlit run main.py
```

### Running with Docker Compose

From the project root:

```bash
docker compose up --build
```

This starts PostgreSQL, the DB service (port 8000), both scrapers, and the dashboard (port 8501).

To build individual images:

```bash
docker build -f src/db_service/Dockerfile -t arb-db-service .
docker build -f src/loro_scrape_service/Dockerfile -t arb-loro-scraper .
docker build -f src/swisslos_scrape_service/Dockerfile -t arb-swisslos-scraper .
docker build -f src/dashboard/Dockerfile -t arb-dashboard .
```

## CI/CD

Deployments are automated via GitHub Actions. Pushing to `main` (or triggering the workflow manually) SSHs into the VPS, pulls the latest code, and rebuilds all containers in detached mode.

The workflow requires three repository secrets:

| Secret | Description |
|---|---|
| `VPS_HOST` | Public IP or hostname of the VPS |
| `VPS_USER` | SSH username (e.g. `root` or a deploy user) |
| `VPS_SSH_KEY` | Private SSH key with access to the VPS |

To add these, go to **Settings → Secrets and variables → Actions** in your GitHub repository.

The deploy step runs:

```bash
cd ~/projects/sports-bet
git pull origin main
docker compose up -d --build
```

The project is expected to be cloned at `~/projects/sports-bet` on the VPS before the first deploy.

## API Endpoints

The db_service exposes the following:

- GET / : health check
- POST /bookmaker_matches/ : create or retrieve a bookmaker match (upsert on unique constraint)
- GET /bookmaker_matches/ : list all bookmaker matches
- POST /sports_betting_odds/ : create a single odds record
- POST /sports_betting_odds/bulk/ : create multiple odds records at once
- GET /sports_betting_odds/ : list all odds records
- POST /run_matching/ : trigger the cross-bookmaker matching process
- GET /matches/with_odds/ : get canonical matches that have odds from multiple bookmakers

## Roadmap

- Arbitrage detection engine : calculate 1/odds_home_A + 1/odds_draw_B + 1/odds_away_C across all bookmaker permutations to identify guaranteed-profit opportunities
- Real-time alerts : notify via Telegram or webhook when an arbitrage opportunity is detected
- Additional bookmakers : extend coverage beyond Loro and Swisslos
- Historical odds tracking : visualize odds movement over time in the dashboard
- Test suite : add unit and integration tests for the matching logic, scrapers, and API
