from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_echoes_message():
    response = client.post("/chat", json={"message": "什么是 Python？"})

    assert response.status_code == 200
    assert response.json() == {"reply": "你问的是：什么是 Python？"}


def test_chat_requires_message():
    response = client.post("/chat", json={})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "message"]
