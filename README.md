
# sports-bet

A modular monorepo for scraping, storing, and analyzing football betting odds across multiple Swiss bookmakers. The long-term goal is arbitrage detection — identifying combinations of bets across bookmakers that guarantee a profit regardless of match outcome.

---

## Architecture

```
sports-bet/
├── src/
│   ├── core/                      # Shared data models (SQLModel)
│   ├── db_service/                # FastAPI REST API + SQLite database
│   ├── loro_scrape_service/       # Scraper for Loterie Romande (REST API)
│   ├── swisslos_scrape_service/   # Scraper for Swisslos (WebSocket)
│   └── dashboard/                 # Streamlit dashboard
└── tests/
```

Each service is an independent `uv` project with its own `.venv`, `pyproject.toml`, and `uv.lock`. Services communicate over HTTP — scrapers post data to `db_service`, the dashboard reads from it.

---

## Services

### `core`

Shared SQLModel data models imported by all other services. Contains three tables:

**`Match`** — a canonical real-world football match, deduped across bookmakers.

| field | type | notes |
|---|---|---|
| `id` | int PK | |
| `match_label` | str | e.g. `"Real Madrid vs Atletico Madrid"` |
| `match_datetime` | datetime | UTC, naive |
| `team1` | str | |
| `team2` | str | |

Unique constraint on `(match_label, match_datetime)`.

**`BookmakerMatch`** — one bookmaker's listing of a match. Multiple bookmakers may list the same real-world game with slightly different names and times.

| field | type | notes |
|---|---|---|
| `id` | int PK | |
| `match_id` | int FK | → `Match.id`, nullable until matched |
| `bookmaker` | str | e.g. `"Swisslos"`, `"Loro"` |
| `match_label` | str | as listed by the bookmaker |
| `match_datetime` | datetime | UTC, naive |
| `team1` | str | |
| `team2` | str | |
| `matching_attempts` | int | number of matching job runs attempted |

Unique constraint on `(bookmaker, match_label, match_datetime)`.

**`SportsBettingOdds`** — a timestamped snapshot of odds for a bookmaker match. A new row is inserted every scrape, preserving historical odds.

| field | type | notes |
|---|---|---|
| `id` | int PK | |
| `bookmaker_match_id` | int FK | → `BookmakerMatch.id` |
| `timestamp` | datetime | UTC, set at insert time |
| `team1_odds` | float | home win |
| `draw_odds` | float | nullable (not all markets have draws) |
| `team2_odds` | float | away win |

---

### `db_service`

FastAPI service that owns the SQLite database. All other services read/write through this API. Runs uvicorn on port `8000`.

**Endpoints:**

```
GET  /                              health check
POST /bookmaker_matches/            create or return existing bookmaker match
GET  /bookmaker_matches/            list all bookmaker matches
GET  /bookmaker_matches/paired/     list matches grouped by real-world match (count > 1)
POST /sports_betting_odds/          insert new odds snapshot
GET  /sports_betting_odds/          list all odds
```

**Matching job** (`matching.py`) — runs on a background scheduler (APScheduler, every 30 minutes). For each unmatched `BookmakerMatch` (where `match_id IS NULL` and `matching_attempts < 3`):

1. Query `Match` rows within a ±1 hour datetime window.
2. Try exact label match first.
3. Fall back to fuzzy matching via `rapidfuzz.fuzz.token_sort_ratio` with a threshold of 75.
4. If a match is found, link via `match_id`. If not, create a new `Match` row.
5. Increment `matching_attempts` regardless of outcome.

**Running:**
```bash
cd src/db_service
uv run uvicorn api:app --reload
```

**Interactive docs:** http://127.0.0.1:8000/docs

---

### `loro_scrape_service`

Scraper for [Loterie Romande](https://jeux.loro.ch) football odds via a clean JSON REST API. No browser required.

**How it works:** sends a single GET request to the Loro API, parses the JSON response, normalizes datetimes to UTC, and POSTs `BookmakerMatch` + `SportsBettingOdds` to `db_service`.

**Running:**
```bash
cd src/loro_scrape_service
uv run main.py
```

**Dependencies:** `requests`, `rich`, `core` (editable)

---

### `swisslos_scrape_service`

Scraper for [Swisslos](https://www.swisslos.ch/de/sporttip/sportwetten/fussball) football odds. The site uses a compressed binary WebSocket protocol (`permessage-deflate` + raw DEFLATE, zlib `wbits=-15`) to stream odds in real time.

**How it works:**
1. Launches a headless Chromium browser via Playwright.
2. Intercepts incoming WebSocket frames and decompresses them (raw DEFLATE).
3. Parses the JSON payload — a flat list of typed entities (`Event`, `Competitor`, `Market`, `Selection`).
4. Builds a lookup index of competitors, markets, and selections.
5. For each `Event`, finds the 1X2 market (`asw:markettype:1`) and extracts home/draw/away odds.
6. POSTs results to `db_service`.

**Selection type mapping:**

| type | meaning |
|---|---|
| `asw:selectiontype:1` | home win |
| `asw:selectiontype:2` | draw |
| `asw:selectiontype:3` | away win |

**Running:**
```bash
cd src/swisslos_scrape_service
uv run main.py
```

**Dependencies:** `playwright`, `requests-html`, `pandas`, `rich`, `core` (editable)

**First-time setup:**
```bash
uv run playwright install chromium
```

---

### `dashboard`

Streamlit dashboard for monitoring scraped odds. Reads from `db_service` via HTTP.

**Running:**
```bash
cd src/dashboard
uv run streamlit run main.py
```

**Dependencies:** `streamlit`, `pandas`, `requests`

---

## Data flow

```
loro_scrape_service  ──┐
                       ├──► POST /bookmaker_matches/  ──► db_service (SQLite)
swisslos_scrape_service ┘         + /sports_betting_odds/        │
                                                                  │
                                              APScheduler (30min) │
                                              matching job        │
                                              links BookmakerMatch│
                                              → Match             │
                                                                  │
dashboard  ◄──────────────────── GET /bookmaker_matches/paired/ ──┘
```

---

## Setup

Each service has its own isolated environment. From the repo root:

```bash
# db_service
cd src/db_service && uv sync

# loro scraper
cd src/loro_scrape_service && uv sync
uv add --editable "../core"

# swisslos scraper
cd src/swisslos_scrape_service && uv sync
uv add --editable "../core"
uv run playwright install chromium

# dashboard
cd src/dashboard && uv sync
```

Each service reads its config from a `.env` file:

```dotenv
# db_service/.env
SQLMODEL_DB_URL="sqlite:///../../test.db"

# loro_scrape_service/.env and swisslos_scrape_service/.env
DB_SERVICE_URL="http://127.0.0.1:8000"
```

---

## Arbitrage logic (planned)

For each paired `Match` (linked to 2+ `BookmakerMatch` rows), the arbitrage service will:

1. Fetch the latest `SportsBettingOdds` per bookmaker.
2. For each outcome (home/draw/away), take the best available odd across all bookmakers.
3. Compute the arbitrage margin: `1/odd1 + 1/oddX + 1/odd2`.
4. If margin < 1, a risk-free profit exists. Compute optimal stake allocation.

---

## Tech stack

| component | library |
|---|---|
| API | FastAPI + uvicorn |
| ORM / models | SQLModel + SQLAlchemy |
| Database | SQLite |
| Validation | Pydantic v2 |
| Browser automation | Playwright |
| Fuzzy matching | rapidfuzz |
| Scheduling | APScheduler |
| Dashboard | Streamlit |
| Package management | uv |
| Logging | Python stdlib logging + Rich |