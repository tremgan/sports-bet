
from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import UniqueConstraint



class BookmakerMatchBase(SQLModel):
    bookmaker: str
    bookmaker_event_id: int # this is the unique id from the bookmaker, we can use it to link matches and odds together
    match_label: str
    match_datetime: datetime
    team1: str
    team2: str

class BookmakerMatch(BookmakerMatchBase, table=True):
    __table_args__ = (UniqueConstraint("bookmaker_event_id", "bookmaker"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    sports_betting_odds: list["SportsBettingOdds"] = Relationship(back_populates="bookmaker_match")

class BookmakerMatchCreate(BookmakerMatchBase):
    pass


class SportsBettingOddsBase(SQLModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    bookmaker: str
    bookmaker_event_id: int # kind of functions as a foreign key to Match.bookmaker_event_id, but since it's not an int we can't use actual foreign key constraints in the DB, we'll have to enforce this at the application level
    team1_odds: float
    draw_odds: Optional[float] = None
    team2_odds: float


class SportsBettingOdds(SportsBettingOddsBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bookmaker_match_id: Optional[int] = Field(default=None, foreign_key="bookmakermatch.id")
    bookmaker_match: Optional[BookmakerMatch] = Relationship(back_populates="sports_betting_odds")

class SportsBettingOddsCreate(SportsBettingOddsBase):
    pass