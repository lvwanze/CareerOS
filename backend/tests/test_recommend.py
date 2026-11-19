from fastapi.testclient import TestClient

from packages.service.main import app
from packages.training.inference import generate_recommendations


client = TestClient(app)


def test_recommend_returns_recommendations():
    response = client.post("/api/v1/recommend", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["recommendations"]
    recommendation = body["data"]["recommendations"][0]
    assert recommendation["occupation_id"] == "OCC-ONET-15-1252.00"
    assert recommendation["skill_gaps"][0]["gap"] == 1
    assert recommendation["skill_gaps"][0]["importance"] == 3.5


def test_main_recommend_returns_recommendations():
    response = client.post("/v1/recommend")

    assert response.status_code == 200
    assert response.json()["data"]["recommendations"]


def test_skills_endpoint_excludes_unused_skills():
    response = client.get("/api/v1/skills")

    assert response.status_code == 200
    skills = response.json()["data"]
    skill_ids = {skill["skill_id"] for skill in skills}
    assert all(skill["used_in_kb"] for skill in skills)
    assert "SKILL-ONET-2.B.3.c" not in skill_ids
    assert "SKILL-ONET-2.B.3.d" not in skill_ids


def test_training_inference_returns_current_schema_values():
    recommendation = generate_recommendations({}, [])[0]

    assert recommendation.occupation_id == "OCC-ONET-15-1252.00"
    assert recommendation.skill_gaps[0].gap == 1
    assert recommendation.skill_gaps[0].importance == 3.5