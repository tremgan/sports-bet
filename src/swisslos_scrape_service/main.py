import requests
from datetime import datetime
from pathlib import Path
import time
import logging
from rich import print

from config import DB_SERVICE_URL

from core.models import MatchCreate, SportsBettingOddsCreate

log_path = Path(__file__).parent / 'scrapers.log'
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s:%(name)s:%(levelname)s:%(message)s"
)
logger = logging.getLogger(Path(__file__).name)


def get_sports_bets() -> tuple[list[SportsBettingOddsCreate], list[MatchCreate]]:

    lotterie_football_url = 'https://jeux.loro.ch/api/sport/sports/FOOT/events'
    headers = {'accept-language': 'de-CH'}

    response = requests.get(lotterie_football_url, headers=headers)
    if response.status_code != 200:
        logger.critical(f'request failed with status {response.status_code}')
        return [], []

    event_paths = response.json()['eventPaths']
    events = []
    for event_path in event_paths:
        events += event_path['events']


    sports_bets = []
    matches = []

    for event_json in events:
        if event_json['eType'] == 'R':
            continue

        match_datetime = datetime.fromisoformat(event_json['startDateTime'])

        team1, team2 = event_json['description'].split(' vs ')

        outcomes = {outcome['opponent']: float(outcome['price']) for outcome in event_json['markets'][0]['outcomes']}

        sports_bet = SportsBettingOddsCreate(
            bookmaker='Swisslos',
            bookmaker_event_id=event_json['id'],
            team1_odds=outcomes[team1],
            team2_odds=outcomes[team2],
            draw_odds=outcomes.get('X'),  # returns None if not present
        )
        sports_bets.append(sports_bet)

        matches.append(
            MatchCreate(
                bookmaker_event_id=event_json['id'],
                match_label=event_json['description'],
                match_datetime=match_datetime,
                team1=team1,
                team2=team2
            )
        )

    return sports_bets, matches


if __name__ == '__main__':
    try:
        t0 = time.perf_counter()
        sports_bets, matches = get_sports_bets()
        t1 = time.perf_counter()
        print(sports_bets[:50])
        logger.info(f'scraped {len(sports_bets)} sports bets in {t1-t0:.2f}s')

        for sports_bet in sports_bets:
            
            print(f'posting {sports_bet} to db_service')
            requests.post(f'{DB_SERVICE_URL}/sports_betting_odds/', json=sports_bet.model_dump(mode='json'))

        for match in matches:
            print(f'posting {match} to db_service')
            requests.post(f'{DB_SERVICE_URL}/matches/', json=match.model_dump(mode='json'))

    except Exception as e:
        print(e)
        logger.exception('scrape error')