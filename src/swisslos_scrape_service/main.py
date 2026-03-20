import requests
from datetime import datetime
from pathlib import Path
import time
import logging
from rich import print

log_path = Path(__file__).parent / 'scrapers.log'
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s:%(name)s:%(levelname)s:%(message)s"
)
logger = logging.getLogger(Path(__file__).name)

sport = 'football'

def get_sports_bets() -> list[dict]:
    lotterie_football_url = 'https://jeux.loro.ch/api/sport/sports/FOOT/events'
    headers = {'accept-language': 'de-CH'}

    response = requests.get(lotterie_football_url, headers=headers)
    if response.status_code != 200:
        logger.critical(f'request failed with status {response.status_code}')
        return []

    event_paths = response.json()['eventPaths']
    events = []
    for event_path in event_paths:
        events += event_path['events']

    sports_bets = []
    for event_json in events:
        if event_json['eType'] == 'R':
            continue

        match_datetime = datetime.fromisoformat(event_json['startDateTime'])
        match_name = event_json['description']
        odds = {outcome['opponent']: outcome['price'] for outcome in event_json['markets'][0]['outcomes']}

        sports_bets.append({
            "match_datetime": match_datetime.isoformat(),
            "match_name": match_name,
            "odds": odds,
            "sport": sport,
        })

    return sports_bets


if __name__ == '__main__':
    try:
        t0 = time.perf_counter()
        sports_bets = get_sports_bets()
        t1 = time.perf_counter()
        print(sports_bets[:2])
        logger.info(f'scraped {len(sports_bets)} sports bets in {t1-t0:.2f}s')
    except Exception as e:
        print(e)
        logger.exception('scrape error')