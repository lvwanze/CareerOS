from fastapi.testclient import TestClient

from packages.service.main import app


client = TestClient(app)


def test_recommend_returns_recommendations():
    response = client.post("/api/v1/recommend", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["recommendations"]


def test_main_recommend_returns_recommendations():
    response = client.post("/v1/recommend")

    assert response.status_code == 200
    assert response.json()["data"]["recommendations"]