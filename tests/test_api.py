import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(provider="offline", db_path=str(tmp_path / "test.db")))
    with TestClient(app) as c:
        yield c


def test_health_and_tones(client):
    assert client.get("/api/health").json()["provider"] == "offline"
    assert {t["id"] for t in client.get("/api/tones").json()} == {"formal", "family"}


def test_refine_saves_history_and_stats(client):
    r = client.post("/api/refine", json={"text": "i dont know", "tone": "formal", "context": "email to HR"})
    assert r.status_code == 200
    body = r.json()
    assert body["refined"] == "I do not know."
    assert body["id"] is not None and body["diff"]

    history = client.get("/api/history").json()
    assert len(history) == 1 and history[0]["context"] == "email to HR"

    stats = client.get("/api/stats").json()
    assert stats["total"] == 1 and stats["by_type"]["tone"] >= 1

    assert client.delete(f"/api/history/{body['id']}").status_code == 200
    assert client.get("/api/history").json() == []
    assert client.delete(f"/api/history/{body['id']}").status_code == 404


def test_refine_without_saving(client):
    r = client.post("/api/refine", json={"text": "hello", "tone": "family", "save": False})
    assert r.status_code == 200 and r.json()["id"] is None
    assert client.get("/api/history").json() == []


def test_validation_errors(client):
    assert client.post("/api/refine", json={"text": "hi", "tone": "angry"}).status_code == 422
    assert client.post("/api/refine", json={"text": "   ", "tone": "formal"}).status_code == 422


def test_ollama_down_gives_friendly_error(tmp_path):
    settings = Settings(provider="ollama", ollama_url="http://127.0.0.1:9", db_path=str(tmp_path / "t.db"))
    with TestClient(create_app(settings)) as c:
        r = c.post("/api/refine", json={"text": "hello", "tone": "formal"})
    assert r.status_code == 502 and "Ollama is not running" in r.json()["detail"]


def test_web_page_is_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "SecondLang" in r.text
