from core.models import Match, BookmakerMatch, SportsBettingOdds
import pytest

MATCH_LABEL = "Test Match"
MATCH_DATETIME = "2024-01-01T12:00:00Z"
TEAM_1 = "Team A"
TEAM_2 = "Team B"

bookmaker_matches = [
    BookmakerMatch(
        id=1,
        bookmaker="Bookmaker A",
        match_label=MATCH_LABEL,
        match_datetime=MATCH_DATETIME,
        sports_betting_odds=[
            SportsBettingOdds(
                id=1,
                timestamp="2024-01-01T10:00:00Z",
                team1_odds=2.1,
                draw_odds=3.6,
                team2_odds=4.0,
            )
        ],
    ),
    BookmakerMatch(
        id=2,
        bookmaker="Bookmaker B",
        match_label=MATCH_LABEL,
        match_datetime=MATCH_DATETIME,
        sports_betting_odds=[
            SportsBettingOdds(
                id=2,
                timestamp="2024-01-01T11:00:00Z",
                team1_odds=1.8,
                draw_odds=3.5,
                team2_odds=5.0,
            )
        ],
    ),
]

match = Match(
    id=1,
    match_label=MATCH_LABEL,
    match_datetime=MATCH_DATETIME,
    bookmaker_matches=bookmaker_matches,
    team1=TEAM_1,
    team2=TEAM_2,
)


def test_arbitrage_opportunity_match():
    assert len(match.bookmaker_matches) == 2
    assert match.odds_df.shape == (2, 3)

    assert match.max_odds["team1"] == 2.1
    assert match.argmax_odds["team1"] == "Bookmaker A"

    assert match.implied_probability_df.shape == (2, 3)
    assert match.min_implied_probabilities["team1"] == pytest.approx(1 / 2.1)
    assert match.argmin_implied_probabilities["team1"] == "Bookmaker A"

    assert match.min_implied_probabilities["team2"] == pytest.approx(1 / 5.0)
    assert match.argmin_implied_probabilities["team2"] == "Bookmaker B"

    assert match.implied_minimal_total_probability == pytest.approx(
        1 / 2.1 + 1 / 3.6 + 1 / 5.0
    )
    assert match.implied_minimal_total_probability < 1.0
    assert match.has_arbitrage
