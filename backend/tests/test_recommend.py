from fastapi.testclient import TestClient

from packages.service.main import app
from packages.training.inference import generate_recommendations


client = TestClient(app)


def test_recommendation_endpoint_returns_empty_list_without_skills():
    response = client.post("/api/v1/recommendations", json={"profile": {"skills": []}})

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["recommendations"] == []
    assert body["data"]["development_paths"] == []


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
        assert recommendation["occupation_name_zh"]
        assert all(gap["skill_name_zh"] for gap in recommendation["skill_gaps"])
        path = paths_by_occupation[recommendation["occupation_id"]]
        assert all(node["name"] for node in path["nodes"])
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


def test_skills_endpoint_returns_chinese_names_from_reference_mapping():
    response = client.get("/api/v1/skills")

    assert response.status_code == 200
    skills_by_id = {skill["skill_id"]: skill for skill in response.json()["data"]}
    assert skills_by_id["SKILL-ONET-2.B.3.e"]["name"] == "Programming"
    assert skills_by_id["SKILL-ONET-2.B.3.e"]["name_zh"] == "编程"


def test_training_inference_caps_results_and_sorts_skill_gaps():
    # 每个职业额外挂一个独有技能，保证两两 Jaccard 只有 2/4，
    # 不会因为职业技能集合雷同被相似度去重剔除。
    occupations = [
        {
            "occupation_id": f"occupation-{index}",
            "occupation_name": f"Occupation {index}",
            "skills": [
                {"skill_id": "lower", "skill_name": "Lower", "importance": 3.0, "required_level": 2},
                {"skill_id": "higher", "skill_name": "Higher", "importance": 4.0, "required_level": 2},
                {
                    "skill_id": f"unique-{index}",
                    "skill_name": f"Unique {index}",
                    "importance": 2.0,
                    "required_level": 1,
                },
            ],
        }
        for index in range(7)
    ]
    recommendations = generate_recommendations({"lower": 1}, occupations)

    assert len(recommendations) == 5
    assert [gap.importance for gap in recommendations[0].skill_gaps] == [4.0, 3.0, 2.0]


def test_training_inference_deduplicates_identical_occupations():
    """职业技能集合完全相同（Jaccard=1.0）时只保留一个。

    不加去重的话，Top-5 会变成同一个职业的五张卡片。
    """
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
    recommendations = generate_recommendations({"lower": 2, "higher": 2}, occupations)

    assert len(recommendations) == 1


# ---------------------------------------------------------------------------
# 画像入参边界（契约 §2.2：self_level 为 int，取值 0～4）
# ---------------------------------------------------------------------------
def _post_skill(skill: dict) -> object:
    return client.post("/api/v1/recommendations", json={"profile": {"skills": [skill]}})


def test_recommendation_rejects_self_level_above_max():
    """self_level=5 必须 422。

    旧实现在路由层按 0<=level<=4 过滤，越界条目被静默丢弃、
    接口仍返回 200，调用方无从察觉该技能没有参与计算。
    """
    response = _post_skill({"skill_id": "SKILL-ONET-2.A.1.a", "self_level": 5})

    assert response.status_code == 422


def test_recommendation_rejects_negative_self_level():
    response = _post_skill({"skill_id": "SKILL-ONET-2.A.1.a", "self_level": -1})

    assert response.status_code == 422


def test_recommendation_accepts_boundary_self_levels():
    """0 与 4 是契约闭区间端点，必须放行。"""
    for level in (0, 4):
        response = _post_skill({"skill_id": "SKILL-ONET-2.A.1.a", "self_level": level})

        assert response.status_code == 200, f"self_level={level} 应被接受"


def test_missing_self_level_defaults_to_zero():
    """字段缺失沿用"没填 = 0 级"的既有约定，结果需与显式传 0 完全一致。"""
    missing = _post_skill({"skill_id": "SKILL-ONET-2.A.1.a"})
    explicit = _post_skill({"skill_id": "SKILL-ONET-2.A.1.a", "self_level": 0})

    assert missing.status_code == 200
    assert explicit.status_code == 200
    assert missing.json()["data"] == explicit.json()["data"]


def test_profile_extra_fields_are_tolerated():
    """画像里多传字段（学历、偏好等）不应导致 422。"""
    response = client.post("/api/v1/recommendations", json={
        "profile": {
            "user_id": "u-extra",
            "education_level": "本科",
            "preferences": {"interest_areas": ["数据"]},
            "skills": [{"skill_id": "SKILL-ONET-2.A.1.a", "self_level": 2, "note": "自学"}],
        },
    })

    assert response.status_code == 200
    assert response.json()["data"]["user_id"] == "u-extra"