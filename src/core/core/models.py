
from datetime import datetime, timezone
from typing import Optional


from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


class MatchBase(SQLModel):
    match_label: str
    match_datetime: datetime
    team1: str
    team2: str
    
class Match(MatchBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    matching_attempts: int = Field(default=0, index=True)

    
    bookmaker_matches: list["BookmakerMatch"] = Relationship(back_populates="match")

class MatchCreate(MatchBase):
    pass


class BookmakerMatchBase(SQLModel):
    bookmaker: str
    match_label: str
    match_datetime: datetime

class BookmakerMatch(BookmakerMatchBase, table=True):
    __table_args__ = (UniqueConstraint("bookmaker", "match_label", "match_datetime"),)
  
    id: Optional[int] = Field(default=None, primary_key=True)
    
    sports_betting_odds: list["SportsBettingOdds"] = Relationship(back_populates="bookmaker_match")

    match_id: Optional[int] = Field(default=None, foreign_key="match.id")
    match: Optional["Match"] = Relationship(back_populates="bookmaker_matches")

class BookmakerMatchCreate(BookmakerMatchBase):
    pass




class SportsBettingOddsBase(SQLModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    team1_odds: float
    draw_odds: Optional[float] = None
    team2_odds: float


class SportsBettingOdds(SportsBettingOddsBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    bookmaker_match_id: Optional[int] = Field(default=None, foreign_key="bookmakermatch.id")
    bookmaker_match: Optional[BookmakerMatch] = Relationship(back_populates="sports_betting_odds")

class SportsBettingOddsCreate(SportsBettingOddsBase):
    bookmaker_match_id: Optional[int] = None

