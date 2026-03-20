
from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Scrape():
    pass


class MatchBase(SQLModel):
    match_id: str
    match_time: datetime
    team1: str
    team2: str

class Match(MatchBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sports_betting_odds: list["SportsBettingOdds"] = Relationship(back_populates="match")

class MatchCreate(MatchBase):
    pass

class SportsBettingOdds(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bookmaker: str
    team1_odds: float
    team2_odds: float

    match_id: Optional[int] = Field(default=None, foreign_key="match.id")
    match: Optional[Match] = Relationship(back_populates="sports_betting_odds")

