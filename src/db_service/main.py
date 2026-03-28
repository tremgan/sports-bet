from fastapi import FastAPI, Depends
from sqlmodel import SQLModel, Session, select
from config import engine
from core.models import BookmakerMatchCreate, SportsBettingOddsCreate, SportsBettingOdds
from repositories import BettingRepository
import match_maker

SQLModel.metadata.create_all(engine)

app = FastAPI()


def get_session():
    with Session(engine) as session:
        yield session


def get_repo(session: Session = Depends(get_session)) -> BettingRepository:
    return BettingRepository(session)


@app.get("/")
def root():
    return {"message": "All good!"}


@app.post("/bookmaker_matches/")
def create_bookmaker_match(
    match: BookmakerMatchCreate, repo: BettingRepository = Depends(get_repo)
):
    return repo.create_bookmaker_match(match)


@app.get("/bookmaker_matches/")
def read_matches(repo: BettingRepository = Depends(get_repo)):
    return repo.get_bookmaker_matches()


@app.post("/sports_betting_odds/")
def create_sports_betting_odds(
    odds: SportsBettingOddsCreate, repo: BettingRepository = Depends(get_repo)
):
    return repo.create_odds(odds)


@app.post("/sports_betting_odds/bulk/")
def create_sports_betting_odds_bulk(
    odds_list: list[SportsBettingOddsCreate],
    repo: BettingRepository = Depends(get_repo),
):
    return {"created": repo.create_odds_bulk(odds_list)}


@app.get("/sports_betting_odds/")
def read_sports_betting_odds(repo: BettingRepository = Depends(get_repo)):
    return repo.get_odds()


@app.post("/run_matching/")
def trigger_matching(repo: BettingRepository = Depends(get_repo)):
    match_maker.run(repo.session)
    return {"status": "matching complete"}


@app.get("/matches/with_odds/")
def read_matches_with_odds(repo: BettingRepository = Depends(get_repo)):
    return repo.get_matches_with_odds()


