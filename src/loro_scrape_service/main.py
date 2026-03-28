import os
from pydantic import ValidationError
import requests
from datetime import datetime, timezone
from pathlib import Path
import time
import logging
from rich.logging import RichHandler

from config import DB_SERVICE_URL
from core.models import BookmakerMatchCreate, SportsBettingOddsCreate

log_path = Path(__file__).parent / "scrapers.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(name)s:%(levelname)s:%(message)s",
    handlers=[
        logging.FileHandler(log_path),
        RichHandler(rich_tracebacks=True, show_path=False),
    ],
)
logger = logging.getLogger(Path(__file__).name)

BOOKMAKER = "Loro"


def get_sports_bets() -> tuple[
    list[BookmakerMatchCreate], list[SportsBettingOddsCreate]
]:
    url = "https://jeux.loro.ch/api/sport/sports/FOOT/events"
    headers = {"accept-language": "de-CH"}

    logger.info("fetching Loro football events...")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        logger.critical(f"request failed: HTTP {response.status_code}")
        return [], []

    event_paths = response.json()["eventPaths"]
    events = []
    for event_path in event_paths:
        events += event_path["events"]

    logger.info(f"found {len(events)} raw events")

    matches = []
    sports_bets = []
    skipped = 0

    for event_json in events:
        if event_json["eType"] == "R":
            skipped += 1
            continue

        match_datetime = datetime.fromisoformat(event_json["startDateTime"])
        match_datetime = match_datetime.astimezone(timezone.utc).replace(tzinfo=None)

        try:
            team1, team2 = event_json["description"].split(" vs ")
        except ValueError:
            logger.warning(f"could not parse teams from: {event_json['description']!r}")
            skipped += 1
            continue

        try:
            outcomes = {
                outcome["opponent"]: float(outcome["price"])
                for outcome in event_json["markets"][0]["outcomes"]
            }
        except (KeyError, IndexError, ValueError) as e:
            logger.warning(
                f"could not parse outcomes for {event_json['description']!r}: {e}"
            )
            skipped += 1
            continue

        try:
            matches.append(
                BookmakerMatchCreate(
                    bookmaker=BOOKMAKER,
                    match_label=event_json["description"],
                    match_datetime=match_datetime,
                )
            )
            sports_bets.append(
                SportsBettingOddsCreate(
                    team1_odds=outcomes[team1],
                    team2_odds=outcomes[team2],
                    draw_odds=outcomes.get("X"),
                )
            )
        except ValidationError as e:
            logger.warning(
                f"invalid odds for {event_json['description']!r}, skipping: {e}"
            )
            if matches and matches[-1].match_label == event_json["description"]:
                matches.pop()
            skipped += 1
            continue

    logger.info(f"parsed {len(matches)} matches, skipped {skipped}")
    return matches, sports_bets


def main():
    logger.info("=== Loro scrape run starting ===")
    try:
        t0 = time.perf_counter()
        matches, sports_bets = get_sports_bets()
        t1 = time.perf_counter()
        logger.info(f"scraped {len(matches)} matches in {t1 - t0:.2f}s")

        posted, failed = 0, 0
        for match, odds in zip(matches, sports_bets):
            match_response = requests.post(
                f"{DB_SERVICE_URL}/bookmaker_matches/",
                json=match.model_dump(mode="json"),
            )
            if match_response.status_code != 200:
                logger.error(
                    f"failed to post match {match.match_label!r}: {match_response.text}"
                )
                failed += 1
                continue

            odds.bookmaker_match_id = match_response.json().get("id")
            odds_response = requests.post(
                f"{DB_SERVICE_URL}/sports_betting_odds/",
                json=odds.model_dump(mode="json"),
            )
            if odds_response.status_code != 200:
                logger.error(
                    f"failed to post odds for {match.match_label!r}: {odds_response.text}"
                )
                failed += 1
            else:
                posted += 1

        logger.info(f"posted {posted} matches, {failed} failures")

        logger.info("triggering match-making...")
        requests.post(f"{DB_SERVICE_URL}/run_matching/")
        logger.info("match-making triggered")

    except Exception:
        logger.exception("unhandled scrape error")

    logger.info("=== Loro scrape run complete ===")


if __name__ == "__main__":
    SCRAPE_FREQUENCY_HOURS = int(os.getenv("SCRAPE_FREQUENCY_HOURS", 3))
    logger.info(f"starting Loro scraper, frequency: {SCRAPE_FREQUENCY_HOURS}h")

    while True:
        main()
        logger.info(f"sleeping {SCRAPE_FREQUENCY_HOURS}h until next run")
        time.sleep(SCRAPE_FREQUENCY_HOURS * 60 * 60)
