from fastapi import FastAPI
from models import Match, SportsBettingOdds
from sqlmodel import SQLModel, Session
from config import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQLModel.metadata.create_all(engine)
    

def get_session():
    with Session(engine) as session:
        yield session

app  = FastAPI()


@app.get("/")
def root():
    return {"message": "All good!"}


@app.post("/matches/")
def create_match(match: Match, session: Session = next(get_session())):
    session.add(match)
    session.commit()
    session.refresh(match)
    return match