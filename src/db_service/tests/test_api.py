import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool
from main import app, get_session
from core.models import BookmakerMatch

DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="session")
def session_fixture():
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


def test_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "All good!"}


def test_create_bookmaker_match(client: TestClient, session: Session):
    match_data = {
        "bookmaker": "TestBookmaker",
        "match_label": "Team A vs Team B",
        "match_datetime": "2024-01-01T12:00:00",
    }
    response = client.post("/bookmaker_matches/", json=match_data)
    assert response.status_code == 200
    data = response.json()
    assert data["bookmaker"] == match_data["bookmaker"]

    db_match = session.exec(
        select(BookmakerMatch).where(BookmakerMatch.id == data["id"])
    ).first()
    assert db_match is not None
    assert db_match.bookmaker == match_data["bookmaker"]
