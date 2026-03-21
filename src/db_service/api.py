from fastapi import FastAPI, Depends
from core.models import BookmakerMatch, BookmakerMatchCreate ,SportsBettingOdds
from sqlmodel import SQLModel, Session, select
from config import engine
import logging

from logger import logger
from core.models import SportsBettingOddsCreate

SQLModel.metadata.create_all(engine)


def get_session():
    logger.info("Opening DB session")
    with Session(engine) as session:
        yield session
    logger.info("Closed DB session")

app = FastAPI()

logger.info("Starting db_service FastAPI app")


@app.get("/")
def root():
    logger.info("root endpoint called")
    return {"message": "All good!"}


@app.post("/bookmaker_matches/")
def create_match(match: BookmakerMatchCreate, session: Session = Depends(get_session)):
    logger.info(f"create_match called with payload: {match}")
    match_obj = BookmakerMatch.model_validate(match)
    session.add(match_obj)
    session.commit()
    session.refresh(match_obj)
    logger.info(f"Created match: {match_obj}")
    return match_obj


@app.get("/bookmaker_matches/")
def read_matches(session: Session = Depends(get_session)):
    logger.info("read_matches called")
    matches = session.exec(select(BookmakerMatch)).all()
    logger.info(f"read_matches returning {len(matches)} records: {matches}")
    return matches


@app.post("/sports_betting_odds/")
def create_sports_betting_odds(odds: SportsBettingOddsCreate, session: Session = Depends(get_session)):
    logger.info(f"create_sports_betting_odds called with payload: {odds}")
    odds_obj = SportsBettingOdds.model_validate(odds)
    session.add(odds_obj)
    session.commit()
    session.refresh(odds_obj)
    logger.info(f"Created sports betting odds: {odds_obj}")
    return odds_obj


@app.post("/sports_betting_odds/bulk/")
def create_sports_betting_odds_bulk(odds_list: list[SportsBettingOddsCreate], session: Session = Depends(get_session)):
    odds_objs = [SportsBettingOdds.model_validate(o) for o in odds_list]
    session.add_all(odds_objs)
    session.commit()
    return {"created": len(odds_objs)}

@app.get("/sports_betting_odds/")
def read_sports_betting_odds(session: Session = Depends(get_session)):
    logger.info("read_sports_betting_odds called")
    odds = session.exec(select(SportsBettingOdds)).all()
    logger.info(f"read_sports_betting_odds returning {len(odds)} records: {odds}")
    return odds