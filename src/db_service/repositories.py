from datetime import timedelta

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from core.models import (
    BookmakerMatch,
    BookmakerMatchCreate,
    SportsBettingOdds,
    SportsBettingOddsCreate,
    Match,
)


class BettingRepository:
    MAX_ODDS_AGE_HOURS = 1

    def __init__(self, session: Session):
        self.session = session

    def create_bookmaker_match(self, match: BookmakerMatchCreate) -> BookmakerMatch:
        try:
            match_obj = BookmakerMatch.model_validate(match)
            self.session.add(match_obj)
            self.session.commit()
            self.session.refresh(match_obj)
            return match_obj
        except IntegrityError:
            self.session.rollback()
            return self.session.exec(
                select(BookmakerMatch).where(
                    BookmakerMatch.bookmaker == match.bookmaker,
                    BookmakerMatch.match_label == match.match_label,
                    BookmakerMatch.match_datetime == match.match_datetime,
                )
            ).first()

    def get_bookmaker_matches(self) -> list[BookmakerMatch]:
        return self.session.exec(select(BookmakerMatch)).all()

    def create_odds(self, odds: SportsBettingOddsCreate) -> SportsBettingOdds:
        odds_obj = SportsBettingOdds.model_validate(odds)
        self.session.add(odds_obj)
        self.session.commit()
        self.session.refresh(odds_obj)
        return odds_obj

    def create_odds_bulk(self, odds_list: list[SportsBettingOddsCreate]) -> int:
        odds_objs = [SportsBettingOdds.model_validate(o) for o in odds_list]
        self.session.add_all(odds_objs)
        self.session.commit()
        return len(odds_objs)

    def get_odds(self) -> list[SportsBettingOdds]:
        return self.session.exec(select(SportsBettingOdds)).all()

    def get_matches_with_odds(self) -> list[dict]:

        matches = self.session.exec(select(Match)).all()
        result = []
        for match in matches:
            bookmaker_data = {}

            bookmaker_matches = self.session.exec(
                select(BookmakerMatch).where(BookmakerMatch.match_id == match.id)
            ).all()

            for bm in bookmaker_matches:
                latest_odds = self.session.exec(
                    select(SportsBettingOdds)
                    .where(SportsBettingOdds.bookmaker_match_id == bm.id)
                    .order_by(SportsBettingOdds.timestamp.desc())
                ).first()
                if latest_odds:
                    bookmaker_data[bm.bookmaker] = {
                        "team1_odds": latest_odds.team1_odds,
                        "draw_odds": latest_odds.draw_odds,
                        "team2_odds": latest_odds.team2_odds,
                        "timestamp": latest_odds.timestamp,
                    }

            if not len(bookmaker_data) > 1:
                continue

            max_timestamp = max(v["timestamp"] for v in bookmaker_data.values())
            min_timestamp = min(v["timestamp"] for v in bookmaker_data.values())
            if not max_timestamp - min_timestamp <= timedelta(
                hours=BettingRepository.MAX_ODDS_AGE_HOURS
            ):
                continue

            result.append({"match": match, "bookmaker_odds": bookmaker_data})

        return result
