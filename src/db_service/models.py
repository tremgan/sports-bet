
from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Scrape():
    pass


class Match(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    match_id: str
    match_time: datetime
    team1: str
    team2: str


class SportsBettingOdds(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bookmaker: str
    team1_odds: float
    team2_odds: float

    match: Optional[Match] = Relationship(back_populates="odds")

