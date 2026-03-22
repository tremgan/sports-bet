# Swiss Sports Betting Arbitrage Finder

A Python microservice application that scrapes real-time football (soccer) betting odds from multiple Swiss bookmakers, matches events across sources using fuzzy string matching, and surfaces cross-bookmaker odds comparisons through a Streamlit dashboard.

Built to detect arbitrage opportunities — situations where the combined odds across bookmakers guarantee a profit regardless of outcome.

## Architecture

The application is split into four independent services that communicate over HTTP, plus a shared data model library:

```
┌─────────────────┐   ┌──────────────────────┐
│  Loro Scraper   │   │  Swisslos Scraper     │
│  (REST API)     │   │  (Playwright/WS)      │
└────────┬────────┘   └──────────┬────────────┘
         │                       │
         │   POST /bookmaker_    │
         │   matches/ & odds/    │
         ▼                       ▼
      ┌─────────────────────────────┐
      │       DB Service            │
      │  (FastAPI + SQLModel)       │
      │                             │
      │  - stores bookmaker odds    │
      │  - fuzzy-matches events     │
      │    across bookmakers        │
      │  - serves paired odds       │
      └──────────────┬──────────────┘
                     │
                     │ GET /matches/with_odds/
                     ▼
              ┌─────────────┐
              │  Dashboard   │
              │ (Streamlit)  │
              └─────────────┘
```

**core** — Shared Python package containing SQLModel data models (`Match`, `BookmakerMatch`, `SportsBettingOdds`) used by all services. Installed as an editable dependency via `uv`.

**loro_scrape_service** — Scrapes football betting odds from the Loterie Romande (Loro) public REST API. Parses 1X2 match odds and posts them to the DB service.

**swisslos_scrape_service** — Scrapes football betting odds from Swisslos by launching a headless Chromium browser via Playwright, intercepting WebSocket frames, and decompressing the binary (zlib-deflate) payloads to extract event and odds data.

**db_service** — FastAPI backend that stores all scraped data in a SQL database (SQLite for dev, PostgreSQL for production). Includes a match-making engine (`match_maker.py`) that uses time-window filtering and fuzzy string matching (rapidfuzz `token_sort_ratio`) to reconcile the same football match across different bookmakers. Exposes endpoints for writing odds, triggering matching, and reading paired cross-bookmaker odds.

**dashboard** — Streamlit app that displays matched events with odds from multiple bookmakers side by side.

## Data Model

```
Match (canonical event)
├── match_label          "FC Basel vs FC Zürich"
├── match_datetime       2026-03-25 18:00 UTC
├── team1, team2
│
└── BookmakerMatch (one per bookmaker per match)
    ├── bookmaker        "Loro" / "Swisslos"
    ├── match_label      (may differ slightly between bookmakers)
    ├── match_datetime
    ├── matching_attempts
    │
    └── SportsBettingOdds (one per scrape run)
        ├── team1_odds
        ├── draw_odds
        ├── team2_odds
        └── timestamp
```

## Cross-Bookmaker Matching

Since Loro and Swisslos name teams differently and may report slightly different kick-off times, a direct join isn't possible. The `match_maker` module handles this by:

1. Querying all `BookmakerMatch` rows not yet linked to a canonical `Match` (with fewer than 3 matching attempts).
2. For each, searching for existing `Match` records within a configurable time window (default: ±1 hour).
3. Attempting an exact match on label + datetime first.
4. Falling back to fuzzy matching using `rapidfuzz.fuzz.token_sort_ratio` with a configurable threshold (default: 75).
5. If no match is found, creating a new canonical `Match` from the bookmaker data.

Both scrapers trigger the matching process automatically after posting data via `POST /run_matching/`.

## Tech Stack

- **Python 3.13** with type hints throughout
- **FastAPI** + **Uvicorn** for the API layer
- **SQLModel** (SQLAlchemy + Pydantic) for ORM and validation
- **Playwright** for headless browser automation and WebSocket interception
- **rapidfuzz** for fuzzy string matching across bookmakers
- **Streamlit** for the dashboard
- **uv** for dependency management
- **Docker** for containerization

## Setup

Each service has its own `pyproject.toml` and is managed with [uv](https://docs.astral.sh/uv/). The `core` package is referenced as a local editable dependency.

### Prerequisites

- Python 3.13+
- uv (`pip install uv`)
- Chromium (installed automatically by Playwright for the Swisslos scraper)

### Running Locally

**1. Start the DB service:**

```bash
cd db_service
cp .env.example .env  # set SQLMODEL_DB_URL (e.g. sqlite:///test.db)
uv sync
uv run uvicorn api:app --reload
```

**2. Run the scrapers:**

```bash
# Loro (quick, REST-based)
cd loro_scrape_service
uv sync
uv run main.py

# Swisslos (launches headless browser, takes ~15s)
cd swisslos_scrape_service
uv sync
uv run playwright install chromium --with-deps
uv run main.py
```

**3. Launch the dashboard:**

```bash
cd dashboard
uv sync
uv run streamlit run main.py
```

### Running with Docker

Each service has a Dockerfile. Build from the project root:

```bash
docker build -f db_service/Dockerfile -t arb-db-service .
docker build -f loro_scrape_service/Dockerfile -t arb-loro-scraper .
docker build -f swisslos_scrape_service/Dockerfile -t arb-swisslos-scraper .
docker build -f dashboard/Dockerfile -t arb-dashboard .
```

## Roadmap

- **Arbitrage detection engine** — Calculate `1/odds_home_A + 1/odds_draw_B + 1/odds_away_C` across all bookmaker permutations to identify guaranteed-profit opportunities.
- **Real-time alerts** — Notify via Telegram/webhook when an arbitrage opportunity is detected.
- **Scheduled scraping** — Run scrapers on a loop or cron interval instead of one-shot execution.
- **Additional bookmakers** — Extend coverage beyond Loro and Swisslos.
- **Historical odds tracking** — Visualize odds movement over time in the dashboard.
