from sqlmodel import Session, select, func
from core.models import BookmakerMatch, Match
from config import engine
from rich import print


with Session(engine) as session:
    duplicates = session.exec(
        select(BookmakerMatch.match_id, func.count(BookmakerMatch.id).label("count"))
        .where(BookmakerMatch.match_id != None)
        .group_by(BookmakerMatch.match_id)
        .having(func.count(BookmakerMatch.id) > 1)
    ).all()

    for match_id, count in duplicates:
        match = session.get(Match, match_id)
        bookmaker_matches = session.exec(
            select(BookmakerMatch).where(BookmakerMatch.match_id == match_id)
        ).all()
        print(f"\nMatch: '{match.match_label}' (id={match_id}, count={count})")
        for bm in bookmaker_matches:
            print(f"  [{bm.bookmaker}] '{bm.match_label}' @ {bm.match_datetime}")