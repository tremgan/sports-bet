from playwright.sync_api import Playwright, sync_playwright
from datetime import datetime
from pathlib import Path
import logging
import json
import zlib
import time

from core.models import BookmakerMatchCreate, SportsBettingOddsCreate

log_path = Path(__file__).parent / 'scrapers.log'
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s:%(name)s:%(levelname)s:%(message)s"
)
logger = logging.getLogger(Path(__file__).name)

BOOKMAKER = 'swisslos'
SELECTION_TYPE_MAP = {
    'asw:selectiontype:1': 'home',
    'asw:selectiontype:2': 'draw',
    'asw:selectiontype:3': 'away',
}


def decode_binary_payload(payload: bytes) -> dict | None:
    try:
        decompressed = zlib.decompress(payload, wbits=-15)
        return json.loads(decompressed.decode('utf-8'))
    except Exception as e:
        logger.warning(f'failed to decode payload: {e}')
        return None


def collect_messages() -> list[dict]:
    messages = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        def on_websocket(ws):
            logger.info(f'websocket opened: {ws.url}')

            def on_frame(payload: bytes):
                message = decode_binary_payload(payload)
                if message:
                    messages.append(message)

            ws.on('framereceived', on_frame)
            ws.on('close', lambda _: logger.info('websocket closed'))

        page.on('websocket', on_websocket)
        page.goto('https://www.swisslos.ch/de/sporttip/sportwetten/fussball')
        time.sleep(10)
        page.close()
        browser.close()

    logger.info(f'collected {len(messages)} websocket messages')
    return messages


def parse_messages(messages: list[dict]) -> tuple[list[BookmakerMatchCreate], list[SportsBettingOddsCreate]]:
    competitors = {}
    selections = {}
    markets = {}
    events = []

    for msg in messages:
        payload = msg.get('payload', [])
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                continue

        for item in payload:
            if not isinstance(item, dict):
                continue
            body = item.get('body', {})
            if not isinstance(body, dict):
                continue
            entities = body.get('snapshotUpdate', {}).get('snapshotUpdateItems', [])
            for e in entities:
                if not isinstance(e, dict):
                    continue
                t = e.get('type')
                entity = e.get('entity', {})
                urn = entity.get('urn')

                if t == 'Competitor':
                    competitors[urn] = entity.get('name')
                elif t == 'Selection':
                    selections[urn] = {
                        'type': entity.get('type'),
                        'odds': entity.get('odds'),
                    }
                elif t == 'Market':
                    markets[urn] = {
                        'type': entity.get('type'),
                        'selections': entity.get('selections', []),
                    }
                elif t == 'Event':
                    events.append(entity)

    logger.info(f'{len(competitors)=} {len(selections)=} {len(markets)=} {len(events)=}')

    matches = []
    odds_list = []

    for event in events:
        competitors_refs = event.get('eventCompetitors', [])
        if len(competitors_refs) != 2:
            continue

        team1 = competitors.get(competitors_refs[0]['competitor'])
        team2 = competitors.get(competitors_refs[1]['competitor'])
        if not team1 or not team2:
            continue

        match_label = f'{team1} vs {team2}'
        match_datetime = datetime.fromisoformat(event['startTime'].replace('Z', '+00:00'))
        event_id = int(event['urn'].split(':')[-1])
        betradar_match_id = event.get('properties', {}).get('BetradarStatisticsId')

        market_1x2 = None
        for market_urn in event.get('markets', []):
            market = markets.get(market_urn)
            if market and market['type'] == 'asw:markettype:1':
                market_1x2 = market
                break

        if not market_1x2:
            continue

        odds_by_type = {}
        for sel_urn in market_1x2['selections']:
            sel = selections.get(sel_urn)
            if sel:
                role = SELECTION_TYPE_MAP.get(sel['type'])
                if role:
                    odds_by_type[role] = sel['odds']

        if 'home' not in odds_by_type or 'away' not in odds_by_type:
            continue

        matches.append(BookmakerMatchCreate(
            bookmaker=BOOKMAKER,
            bookmaker_event_id=event_id,
            betradar_match_id=betradar_match_id,
            match_label=match_label,
            match_datetime=match_datetime,
            team1=team1,
            team2=team2,
        ))

        odds_list.append(SportsBettingOddsCreate(
            bookmaker=BOOKMAKER,
            bookmaker_event_id=event_id,
            team1_odds=odds_by_type['home'],
            team2_odds=odds_by_type['away'],
            draw_odds=odds_by_type.get('draw'),
        ))

    return matches, odds_list


if __name__ == '__main__':
    import requests
    from config import DB_SERVICE_URL

    try:
        t0 = time.perf_counter()
        messages = collect_messages()
        matches, odds_list = parse_messages(messages)
        t1 = time.perf_counter()

        logger.info(f'scraped {len(matches)} matches in {t1-t0:.2f}s')

        for match, odds in zip(matches, odds_list):
            match_response = requests.post(
                f'{DB_SERVICE_URL}/bookmaker_matches/',
                json=match.model_dump(mode='json')
            )
            if match_response.status_code != 200:
                logger.error(f'failed to post match: {match_response.text}')
                continue
            match_id = match_response.json().get('id')
            odds.bookmaker_match_id = match_id
            odds_response = requests.post(
                f'{DB_SERVICE_URL}/sports_betting_odds/',
                json=odds.model_dump(mode='json')
            )
            if odds_response.status_code != 200:
                logger.error(f'failed to post odds: {odds_response.text}')

        logger.info(f'posted {len(matches)} matches and odds to db_service')

    except Exception as e:
        logger.exception('scrape error')
        raise