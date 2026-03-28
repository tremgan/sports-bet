import os
from pydantic import ValidationError
from playwright.sync_api import sync_playwright
from datetime import datetime, timezone
from pathlib import Path
import logging
from rich.logging import RichHandler
import json
import zlib
import time
import requests
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

BOOKMAKER = "Swisslos"
SELECTION_TYPE_MAP = {
    "asw:selectiontype:1": "home",
    "asw:selectiontype:2": "draw",
    "asw:selectiontype:3": "away",
}


def decode_binary_payload(payload: bytes) -> dict | None:
    try:
        decompressed = zlib.decompress(payload, wbits=-15)
        return json.loads(decompressed.decode("utf-8"))
    except Exception as e:
        logger.warning(f"failed to decode payload: {e}")
        return None


def collect_messages() -> list[dict]:
    messages = []
    logger.info("launching headless browser...")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        def on_websocket(ws):
            logger.info(f"websocket opened: {ws.url}")

            def on_frame(payload: bytes):
                message = decode_binary_payload(payload)
                if message:
                    messages.append(message)

            ws.on("framereceived", on_frame)
            ws.on("close", lambda _: logger.info("websocket closed"))

        page.on("websocket", on_websocket)
        logger.info("navigating to Swisslos football page...")
        page.goto(
            "https://www.swisslos.ch/de/sporttip/sportwetten/fussball",
            timeout=180_000,
            wait_until="domcontentloaded",
        )
        logger.info("page loaded, collecting websocket frames for 60s...")
        time.sleep(60)
        page.close()
        browser.close()

    logger.info(f"collected {len(messages)} websocket messages")
    return messages


def parse_messages(
    messages: list[dict],
) -> tuple[list[BookmakerMatchCreate], list[SportsBettingOddsCreate]]:
    competitors = {}
    selections = {}
    markets = {}
    events = []

    for msg in messages:
        payload = msg.get("payload", [])
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                continue

        for item in payload:
            if not isinstance(item, dict):
                continue
            body = item.get("body", {})
            if not isinstance(body, dict):
                continue
            entities = body.get("snapshotUpdate", {}).get("snapshotUpdateItems", [])
            for e in entities:
                if not isinstance(e, dict):
                    continue
                t = e.get("type")
                entity = e.get("entity", {})
                urn = entity.get("urn")

                if t == "Competitor":
                    competitors[urn] = entity.get("name")
                elif t == "Selection":
                    selections[urn] = {
                        "type": entity.get("type"),
                        "odds": entity.get("odds"),
                    }
                elif t == "Market":
                    markets[urn] = {
                        "type": entity.get("type"),
                        "selections": entity.get("selections", []),
                    }
                elif t == "Event":
                    events.append(entity)

    logger.info(
        f"{len(competitors)=} {len(selections)=} {len(markets)=} {len(events)=}"
    )

    matches = []
    odds_list = []
    skipped = 0

    for event in events:
        competitors_refs = event.get("eventCompetitors", [])
        if len(competitors_refs) != 2:
            skipped += 1
            continue

        team1 = competitors.get(competitors_refs[0]["competitor"])
        team2 = competitors.get(competitors_refs[1]["competitor"])
        if not team1 or not team2:
            logger.warning(f"missing competitor name for event {event.get('urn')!r}")
            skipped += 1
            continue

        match_label = f"{team1} vs {team2}"
        match_datetime = datetime.fromisoformat(
            event["startTime"].replace("Z", "+00:00")
        )
        match_datetime = match_datetime.astimezone(timezone.utc).replace(tzinfo=None)

        market_1x2 = None
        for market_urn in event.get("markets", []):
            market = markets.get(market_urn)
            if market and market["type"] == "asw:markettype:1":
                market_1x2 = market
                break

        if not market_1x2:
            logger.warning(f"no 1X2 market found for {match_label!r}")
            skipped += 1
            continue

        odds_by_type = {}
        for sel_urn in market_1x2["selections"]:
            sel = selections.get(sel_urn)
            if sel:
                role = SELECTION_TYPE_MAP.get(sel["type"])
                if role:
                    odds_by_type[role] = sel["odds"]

        if "home" not in odds_by_type or "away" not in odds_by_type:
            logger.warning(f"incomplete odds for {match_label!r}: {odds_by_type}")
            skipped += 1
            continue

     

        try:
            matches.append(
                BookmakerMatchCreate(
                    bookmaker=BOOKMAKER,
                    match_label=match_label,
                    match_datetime=match_datetime,
                )
            )
            odds_list.append(
                SportsBettingOddsCreate(
                    team1_odds=odds_by_type["home"],
                    team2_odds=odds_by_type["away"],
                    draw_odds=odds_by_type.get("draw"),
                )
            )
        except ValidationError as e:
            logger.warning(f"invalid odds for {match_label!r}, skipping: {e}")
            matches.pop()  # remove the match we just appended
            skipped += 1
            continue

    logger.info(f"parsed {len(matches)} matches, skipped {skipped}")
    return matches, odds_list


def main():
    logger.info("=== Swisslos scrape run starting ===")
    try:
        t0 = time.perf_counter()
        messages = collect_messages()
        matches, odds_list = parse_messages(messages)
        t1 = time.perf_counter()
        logger.info(f"scraped {len(matches)} matches in {t1 - t0:.2f}s")

        posted, failed = 0, 0
        for match, odds in zip(matches, odds_list):
            match_response = requests.post(
                f"{DB_SERVICE_URL}/bookmaker_matches/",
                json=match.model_dump(mode="json"),
            )
            if match_response.status_code != 200:
                logger.error(f"failed to post match {match.match_label!r}: {match_response.text}")
                failed += 1
                continue

            odds.bookmaker_match_id = match_response.json().get("id")
            odds_response = requests.post(
                f"{DB_SERVICE_URL}/sports_betting_odds/",
                json=odds.model_dump(mode="json"),
            )
            if odds_response.status_code != 200:
                logger.error(f"failed to post odds for {match.match_label!r}: {odds_response.text}")
                failed += 1
            else:
                posted += 1

        logger.info(f"posted {posted} matches, {failed} failures")

        logger.info("triggering match-making...")
        requests.post(f"{DB_SERVICE_URL}/run_matching/")
        logger.info("match-making triggered")

    except Exception:
        logger.exception("unhandled scrape error")

    logger.info("=== Swisslos scrape run complete ===")


if __name__ == "__main__":
    SCRAPE_FREQUENCY_HOURS = int(os.getenv("SCRAPE_FREQUENCY_HOURS", 3))
    logger.info(f"starting Swisslos scraper, frequency: {SCRAPE_FREQUENCY_HOURS}h")

    while True:
        main()
        logger.info(f"sleeping {SCRAPE_FREQUENCY_HOURS}h until next run")
        time.sleep(SCRAPE_FREQUENCY_HOURS * 60 * 60)