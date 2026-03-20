from fastapi import FastAPI, Depends
from models import Match, MatchCreate ,SportsBettingOdds
from sqlmodel import SQLModel, Session, select
from config import engine
import logging

from logger import logger

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


@app.post("/matches/")
def create_match(match: MatchCreate, session: Session = Depends(get_session)):
    logger.info(f"create_match called with payload: {match}")
    match_obj = Match.model_validate(match)
    session.add(match_obj)
    session.commit()
    session.refresh(match_obj)
    logger.info(f"Created match: id={match_obj.id}, team1={match_obj.team1}, team2={match_obj.team2}, time={match_obj.match_time}")
    return match_obj


@app.get("/matches/")
def read_matches(session: Session = Depends(get_session)):
    logger.info("read_matches called")
    matches = session.exec(select(Match)).all()
    logger.info(f"read_matches returning {len(matches)} records: {matches}")
    return matches