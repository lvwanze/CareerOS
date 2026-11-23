"""接口契约测试（代旭 · 验收单第 2 行「接口保障」）

只补 main 上还没有的覆盖，避免和已有用例重复：
  tests/test_health.py            → /health、/ready 存活探针
  tests/test_recommend.py         → 推荐算法、self_level 校验、未知 skill_id
  tests/test_response_envelope.py → 404/405/422/500 的信封格式

本文件专盯验收单那三条：
  ① 核心接口 200
  ② 技能列表字段完整、无空值遗漏
  ③ 树结构合法、可正常解析

只断言接口返回，不碰算法内部，所以调权重、改排序时不会误报。
"""

from fastapi.testclient import TestClient

from packages.service.main import app

client = TestClient(app)


def _first_skill_id() -> str:
    return client.get("/api/v1/skills").json()["data"][0]["skill_id"]


def test_skills_fields_complete():
    """验收第②条：技能列表字段完整、无空值遗漏。

    填报页的技能选项全来自这个接口，任何一个字段空着前端就会出空白项。
    """
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


def test_request_id_uses_spec_prefix():
    """request_id 格式与 docs/api_spec.md 的 req_xxx 对齐。

    改 schemas.py 之前这里是裸 UUID，和文档对不上。
    """
    body = client.get("/api/v1/skills").json()
    request_id = body["request_id"]
    assert request_id.startswith("req_"), f"request_id 前缀不对: {request_id}"
    assert len(request_id) == 12, f"request_id 长度不对（应为 req_ + 8 位）: {request_id}"


def test_recommendations_fields_and_score_range():
    """验收第①条：推荐接口 200 且关键字段齐全、匹配度在有效区间。"""
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
    assert body["data"]["user_id"] == "tester@careeros.com"

    recommendations = body["data"]["recommendations"]
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


def test_tree_shape():
    """验收第③条：树结构合法、可正常解析。

    注意：当前 /v1/tree/{id} 返回写死的节点，本用例只能证明"结构可解析"，
    证明不了"按 occupation_id 返回不同树"——那需要后端先把数据接上。
    """
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
