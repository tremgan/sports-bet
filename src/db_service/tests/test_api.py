import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool
from main import app, get_session
from core.models import BookmakerMatch, SportsBettingOdds

DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.drop_all(engine) # avoid leaking state between tests
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_test_session():
        yield session

    app.dependency_overrides[get_session] = get_test_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ── root ──────────────────────────────────────────────────────────────────────

def test_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "All good!"}


# ── bookmaker matches ─────────────────────────────────────────────────────────

MATCH_DATA = {
    "bookmaker": "TestBookmaker",
    "match_label": "Team A vs Team B",
    "match_datetime": "2024-01-01T12:00:00",
}


def test_create_bookmaker_match(client: TestClient, session: Session):
    response = client.post("/bookmaker_matches/", json=MATCH_DATA)
    assert response.status_code == 200
    data = response.json()
    assert data["bookmaker"] == MATCH_DATA["bookmaker"]
    assert data["match_label"] == MATCH_DATA["match_label"]

    db_match = session.exec(
        select(BookmakerMatch).where(BookmakerMatch.id == data["id"])
    ).first()
    assert db_match is not None
    assert db_match.bookmaker == MATCH_DATA["bookmaker"]


def test_create_bookmaker_match_duplicate_returns_existing(client: TestClient):
    response1 = client.post("/bookmaker_matches/", json=MATCH_DATA)
    response2 = client.post("/bookmaker_matches/", json=MATCH_DATA)
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json()["id"] == response2.json()["id"]


def test_read_bookmaker_matches_empty(client: TestClient):
    response = client.get("/bookmaker_matches/")
    assert response.status_code == 200
    assert response.json() == []


def test_read_bookmaker_matches(client: TestClient):
    client.post("/bookmaker_matches/", json=MATCH_DATA)
    response = client.get("/bookmaker_matches/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["bookmaker"] == MATCH_DATA["bookmaker"]


# ── sports betting odds ───────────────────────────────────────────────────────

def test_create_odds(client: TestClient, session: Session):
    match_response = client.post("/bookmaker_matches/", json=MATCH_DATA)
    match_id = match_response.json()["id"]

    odds_data = {
        "bookmaker_match_id": match_id,
        "team1_odds": 1.85,
        "draw_odds": 3.20,
        "team2_odds": 4.50,
    }
    response = client.post("/sports_betting_odds/", json=odds_data)
    assert response.status_code == 200
    data = response.json()
    assert data["team1_odds"] == odds_data["team1_odds"]
    assert data["draw_odds"] == odds_data["draw_odds"]
    assert data["team2_odds"] == odds_data["team2_odds"]

    db_odds = session.exec(
        select(SportsBettingOdds).where(SportsBettingOdds.id == data["id"])
    ).first()
    assert db_odds is not None
    assert db_odds.team1_odds == odds_data["team1_odds"]


def test_create_odds_bulk(client: TestClient, session: Session):
    match_response = client.post("/bookmaker_matches/", json=MATCH_DATA)
    match_id = match_response.json()["id"]

    odds_list = [
        {"bookmaker_match_id": match_id, "team1_odds": 1.85, "draw_odds": 3.20, "team2_odds": 4.50},
        {"bookmaker_match_id": match_id, "team1_odds": 1.90, "draw_odds": 3.10, "team2_odds": 4.20},
    ]
    response = client.post("/sports_betting_odds/bulk/", json=odds_list)
    assert response.status_code == 200
    assert response.json() == {"created": 2}

    db_odds = session.exec(
        select(SportsBettingOdds).where(SportsBettingOdds.bookmaker_match_id == match_id)
    ).all()
    assert len(db_odds) == 2


def test_read_odds_empty(client: TestClient):
    response = client.get("/sports_betting_odds/")
    assert response.status_code == 200
    assert response.json() == []


def test_read_odds(client: TestClient):
    match_response = client.post("/bookmaker_matches/", json=MATCH_DATA)
    match_id = match_response.json()["id"]
    odds_data = {
        "bookmaker_match_id": match_id,
        "team1_odds": 1.85,
        "draw_odds": 3.20,
        "team2_odds": 4.50,
    }
    client.post("/sports_betting_odds/", json=odds_data)
    response = client.get("/sports_betting_odds/")
    assert response.status_code == 200
    assert len(response.json()) == 1