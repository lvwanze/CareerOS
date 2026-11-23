"""接口契约测试（代旭 · 接口保障验收项）

覆盖验收单第 2 行要求的三个接口：
  POST /api/v1/recommendations
  GET  /api/v1/skills
  GET  /v1/tree/{occupation_id}
外加两条容易回归的约束：request_id 格式、422 也要带统一信封。

这些断言只依赖接口返回，不碰算法内部实现，所以赵帝臣改算法权重时不会误报。
"""

from fastapi.testclient import TestClient

from packages.service.main import app

client = TestClient(app)


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_skills_fields_complete():
    """技能列表是填报页的数据源，字段缺一个前端就要白屏。"""
    response = client.get("/api/v1/skills")
    assert response.status_code == 200

    body = response.json()
    assert body["code"] == 200
    skills = body["data"]
    assert isinstance(skills, list)
    assert len(skills) > 0

    required_fields = ["skill_id", "name", "name_zh", "category", "used_in_kb"]
    for skill in skills:
        for field in required_fields:
            assert field in skill, f"技能 {skill.get('skill_id')} 缺字段 {field}"
            assert skill[field] not in (None, ""), f"技能 {skill.get('skill_id')} 的 {field} 是空值"

    ids = [skill["skill_id"] for skill in skills]
    assert len(ids) == len(set(ids)), "skill_id 有重复"


def test_skills_request_id_format():
    """和 docs/api_spec.md 对齐：req_ 加 8 位十六进制。"""
    body = client.get("/api/v1/skills").json()
    request_id = body["request_id"]
    assert request_id.startswith("req_"), f"request_id 前缀不对: {request_id}"
    assert len(request_id) == 12, f"request_id 长度不对: {request_id}"


def _first_skill_id() -> str:
    return client.get("/api/v1/skills").json()["data"][0]["skill_id"]


def test_recommendations_shape():
    payload = {
        "profile": {
            "user_id": "tester@careeros.com",
            "learning_stage": {
                "education_level": "本科",
                "major": "软件工程",
                "current_stage": "大三",
            },
            "preferences": {},
            "skills": [{"skill_id": _first_skill_id(), "self_level": 1}],
            "constraints": {},
            "career_goals": {},
        }
    }
    response = client.post("/api/v1/recommendations", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["user_id"] == "tester@careeros.com"

    recommendations = data["recommendations"]
    assert isinstance(recommendations, list)
    assert len(recommendations) > 0

    for item in recommendations:
        for field in [
            "occupation_id",
            "occupation_name",
            "match_score",
            "skill_gaps",
            "recommendation_reasons",
            "matched_skills",
            "skills_to_improve",
            "skills_to_verify",
        ]:
            assert field in item, f"推荐缺字段 {field}"

        assert 0 <= item["match_score"] <= 1, f"match_score 越界: {item['match_score']}"

        for gap in item["skill_gaps"]:
            for field in ["skill_id", "gap", "status", "current_level", "required_level"]:
                assert field in gap, f"技能缺口缺字段 {field}"
            assert gap["status"] in ("mastered", "needs_improvement", "needs_verification")
            assert 0 <= gap["current_level"] <= 4
            assert 0 <= gap["required_level"] <= 4


def test_recommendations_flat_body_returns_empty():
    """组长给的扁平请求体不会报错，但会返回空列表——
    这条测试是把「口径不一致时会静默失败」这个坑钉死，不是认可这种写法。"""
    response = client.post(
        "/api/v1/recommendations",
        json={"user_skills": ["skill_01"], "target_occupation": "occ_eng"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["recommendations"] == []


def test_tree_shape():
    response = client.get("/v1/tree/occ_eng")
    assert response.status_code == 200

    body = response.json()
    assert body["code"] == 200
    nodes = body["data"]["nodes"]
    assert isinstance(nodes, list)
    assert len(nodes) > 0

    for node in nodes:
        for field in ["node_id", "skill_id", "skill_name", "description", "status"]:
            assert field in node, f"树节点缺字段 {field}"
        assert node["status"] in ("not_started", "in_progress", "mastered")

    node_ids = [node["node_id"] for node in nodes]
    assert len(node_ids) == len(set(node_ids)), "node_id 有重复"


def test_validation_error_has_envelope():
    """FastAPI 默认 422 返回 {"detail": [...]}，前端没法按统一信封解析。"""
    response = client.post(
        "/api/v1/recommendations",
        content=b"not-a-json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422

    body = response.json()
    assert body["code"] == 422
    assert "message" in body
    assert body["request_id"].startswith("req_")
