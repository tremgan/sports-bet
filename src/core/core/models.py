from datetime import datetime, timezone
from typing import Optional
import pandas as pd


from pydantic import model_validator, validator
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


class MatchBase(SQLModel):
    """Represents a Match with odds from multiple bookmakers,
    allowing simplified comparisons for identifying arbitrage opportunities."""


    match_label: str
    match_datetime: datetime
    team1: str
    team2: str

    def __repr__(self):
        return f"<Match(id={self.id}, label='{self.match_label}', datetime='{self.match_datetime}')>"

    @property
    def bookmaker_matches(self) -> list["BookmakerMatch"]:
        return self.match.bookmaker_matches

    def _latest_odds(self, bm: "BookmakerMatch") -> Optional["SportsBettingOdds"]:
        if not bm.sports_betting_odds:
            return None
        return max(bm.sports_betting_odds, key=lambda o: o.timestamp)

    @property
    def odds_df(self) -> pd.DataFrame:
        rows = {}
        for bm in self.bookmaker_matches:
            odds = self._latest_odds(bm)
            if odds:
                row = {"team1": odds.team1_odds, "team2": odds.team2_odds}
                if odds.draw_odds is not None:
                    row["draw"] = odds.draw_odds
                rows[bm.bookmaker] = row
        return pd.DataFrame(rows).T

    @property
    def max_odds(self) -> pd.Series:
        return self.odds_df.max(axis=0)

    @property
    def argmax_odds(self) -> pd.Series:
        return self.odds_df.idxmax(axis=0)

    @property
    def implied_probability_df(self) -> pd.DataFrame:
        return self.odds_df ** -1

    @property
    def min_implied_probabilities(self) -> pd.Series:
        return self.implied_probability_df.min(axis=0)

    @property
    def argmin_implied_probabilities(self) -> pd.Series:
        return self.implied_probability_df.idxmin(axis=0)

    @property
    def implied_minimal_total_probability(self) -> float:
        return float(self.min_implied_probabilities.sum())

    @property
    def has_arbitrage(self) -> bool:
        return self.implied_minimal_total_probability < 1.0

    @property
    def stakes(self) -> pd.DataFrame:
        df = pd.concat(
            (
                self.argmin_implied_probabilities,
                self.min_implied_probabilities / self.implied_minimal_total_probability,
            ),
            axis=1,
        ).T
        df.index = ["company", "stake"]
        return df

    @property
    def payout(self) -> float:
        return float(
            (
                (self.min_implied_probabilities / self.implied_minimal_total_probability)
                * self.max_odds
            ).iloc[0]
        )

    @property
    def profit(self) -> float:
        return self.payout - 1

    def summary(self) -> dict:
        return {
            "match": self.match.match_label,
            "match_datetime": self.match.match_datetime,
            "has_arbitrage": self.has_arbitrage,
            "implied_total_probability": self.implied_minimal_total_probability,
            "profit": self.profit if self.has_arbitrage else None,
            "odds": self.odds_df.to_dict("index"),
            "stakes": self.stakes.to_dict() if self.has_arbitrage else None,
        }




class Match(MatchBase, table=True):
    __table_args__ = (UniqueConstraint("match_label", "match_datetime"),)
    id: Optional[int] = Field(default=None, primary_key=True)

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
    matching_attempts: int = Field(default=0, index=True)

    sports_betting_odds: list["SportsBettingOdds"] = Relationship(
        back_populates="bookmaker_match"
    )

    match_id: Optional[int] = Field(default=None, foreign_key="match.id")
    match: Optional["Match"] = Relationship(back_populates="bookmaker_matches")


class BookmakerMatchCreate(BookmakerMatchBase):
    pass


class SportsBettingOddsBase(SQLModel):
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
    team1_odds: float
    draw_odds: Optional[float] = None
    team2_odds: float

    @model_validator(mode="after")
    def implied_probability_sanity_check(self) -> "SportsBettingOddsBase":
        implied = 1 / self.team1_odds + 1 / self.team2_odds
        if self.draw_odds:
            implied += 1 / self.draw_odds
        if implied < 1.0:
            raise ValueError(f"implied probability {implied:.3f} is below 1.0: odds look invalid")
        return self

class SportsBettingOdds(SportsBettingOddsBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    bookmaker_match_id: Optional[int] = Field(
        default=None, foreign_key="bookmakermatch.id"
    )
    bookmaker_match: Optional[BookmakerMatch] = Relationship(
        back_populates="sports_betting_odds"
    )


class SportsBettingOddsCreate(SportsBettingOddsBase):
    bookmaker_match_id: Optional[int] = None
