import requests
from datetime import datetime, timezone
from pathlib import Path
import time
import logging

from config import DB_SERVICE_URL
from core.models import BookmakerMatchCreate, SportsBettingOddsCreate

log_path = Path(__file__).parent / "scrapers.log"
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s:%(name)s:%(levelname)s:%(message)s",
)
logger = logging.getLogger(Path(__file__).name)

BOOKMAKER = "Loro"


def get_sports_bets() -> tuple[
    list[BookmakerMatchCreate], list[SportsBettingOddsCreate]
]:
    lotterie_football_url = "https://jeux.loro.ch/api/sport/sports/FOOT/events"
    headers = {"accept-language": "de-CH"}

    response = requests.get(lotterie_football_url, headers=headers)
    if response.status_code != 200:
        logger.critical(f"request failed with status {response.status_code}")
        return [], []

    event_paths = response.json()["eventPaths"]
    events = []
    for event_path in event_paths:
        events += event_path["events"]

    matches = []
    sports_bets = []

    for event_json in events:
        if event_json["eType"] == "R":
            continue

        match_datetime = datetime.fromisoformat(event_json["startDateTime"])
        match_datetime = match_datetime.astimezone(timezone.utc).replace(tzinfo=None)

        team1, team2 = event_json["description"].split(" vs ")
        outcomes = {
            outcome["opponent"]: float(outcome["price"])
            for outcome in event_json["markets"][0]["outcomes"]
        }

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

    return matches, sports_bets


if __name__ == "__main__":
    try:
        t0 = time.perf_counter()
        matches, sports_bets = get_sports_bets()
        t1 = time.perf_counter()
        logger.info(f"scraped {len(matches)} matches in {t1 - t0:.2f}s")

        for match, odds in zip(matches, sports_bets):
            match_response = requests.post(
                f"{DB_SERVICE_URL}/bookmaker_matches/",
                json=match.model_dump(mode="json"),
            )
            if match_response.status_code != 200:
                logger.error(f"failed to post match: {match_response.text}")
                continue
            bookmaker_match_id = match_response.json().get("id")

            odds.bookmaker_match_id = bookmaker_match_id
            odds_response = requests.post(
                f"{DB_SERVICE_URL}/sports_betting_odds/",
                json=odds.model_dump(mode="json"),
            )
            if odds_response.status_code != 200:
                logger.error(f"failed to post odds: {odds_response.text}")

        logger.info(f"posted {len(matches)} matches and odds to db_service")

        requests.post(f"{DB_SERVICE_URL}/run_matching/")

    except Exception:
        logger.exception("scrape error")
        raise
