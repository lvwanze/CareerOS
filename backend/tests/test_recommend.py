from fastapi.testclient import TestClient

from packages.service.main import app
from packages.training.inference import generate_recommendations


client = TestClient(app)


def test_recommendation_endpoint_rejects_empty_skills_with_422():
    response = client.post("/api/v1/recommendations", json={"profile": {"skills": []}})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == 422
    assert body["data"]["errors"][0]["field"] == "profile.skills"


def test_inference_returns_empty_for_empty_profile():
    """「空进空出」的原语义下移到算法层，回归价值不丢。"""
    assert generate_recommendations({}, []) == []


def test_legacy_mock_recommendation_route_is_removed():
    response = client.post("/v1/recommend")

    assert response.status_code == 404


def test_recommendations_use_knowledge_base_and_return_top_five():
    response = client.post("/api/v1/recommendations", json={
        "profile": {
            "user_id": "test-user",
            "skills": [{"skill_id": "SKILL-ONET-2.A.1.a", "self_level": 2}],
        },
    })

    assert response.status_code == 200
    data = response.json()["data"]
    recommendations = data["recommendations"]
    assert 1 <= len(recommendations) <= 5
    assert data["user_id"] == "test-user"
    assert all(
        gaps == sorted(gaps, key=lambda gap: gap["importance"], reverse=True)
        for gaps in (recommendation["skill_gaps"] for recommendation in recommendations)
    )
    paths_by_occupation = {path["occupation_id"]: path for path in data["development_paths"]}
    assert set(paths_by_occupation) == {
        recommendation["occupation_id"] for recommendation in recommendations
    }
    for recommendation in recommendations:
        path = paths_by_occupation[recommendation["occupation_id"]]
        assert [node["skill_id"] for node in path["nodes"]] == [
            gap["skill_id"] for gap in recommendation["skill_gaps"] if gap["gap"] > 0
        ]
        assert [node["priority"] for node in path["nodes"]] == list(
            range(1, len(path["nodes"]) + 1)
        )


def test_skills_endpoint_excludes_unused_skills():
    response = client.get("/api/v1/skills")

    assert response.status_code == 200
    skills = response.json()["data"]
    skill_ids = {skill["skill_id"] for skill in skills}
    assert all(skill["used_in_kb"] for skill in skills)
    assert "SKILL-ONET-2.B.3.c" not in skill_ids
    assert "SKILL-ONET-2.B.3.d" not in skill_ids


def test_training_inference_caps_results_and_sorts_skill_gaps():
    occupations = [
        {
            "occupation_id": f"occupation-{index}",
            "occupation_name": f"Occupation {index}",
            "skills": [
                {"skill_id": "lower", "skill_name": "Lower", "importance": 3.0, "required_level": 2},
                {"skill_id": "higher", "skill_name": "Higher", "importance": 4.0, "required_level": 2},
            ],
        }
        for index in range(7)
    ]
    recommendations = generate_recommendations({"lower": 1}, occupations)

    assert len(recommendations) == 5
    assert [gap.importance for gap in recommendations[0].skill_gaps] == [4.0, 3.0]