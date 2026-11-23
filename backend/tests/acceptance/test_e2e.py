"""TC-E2E：从用户填报到推荐结果 + 发展路径的端到端链路。

链路：填报 -> 画像校验 -> 职业推荐 -> 技能差距 -> 发展路径 -> 统一响应
对应报告骨架样例 5-1：一条完整链路的真实输入与关键输出。
"""

import pytest

from factories import base_profile, payload
from reference.schemas import DevelopmentPath, Recommendation, UserProfile


def _to_dict(obj):
    return obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()


@pytest.mark.e2e
def test_TC_E2E_01_full_chain(client, recommend_path):
    """一条完整链路：请求画像 -> 返回 Top-5 推荐 -> 每条推荐有发展路径。"""
    profile = base_profile()
    UserProfile(**profile)

    response = client.post(recommend_path, json=payload(profile))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == 200

    data = body["data"]
    recommendations = data["recommendations"]
    development_paths = data["development_paths"]

    assert len(recommendations) == 5
    assert len(development_paths) == 5

    for rec in recommendations:
        Recommendation(**rec)

    path_by_occupation = {p["occupation_id"]: p for p in development_paths}
    for rec in recommendations:
        occ_id = rec["occupation_id"]
        assert occ_id in path_by_occupation
        DevelopmentPath(**path_by_occupation[occ_id])


@pytest.mark.e2e
def test_TC_E2E_02_develop_path_covers_improvement_skills(client, recommend_path):
    """待加强技能应在发展路径里出现，否则推荐与路径脱节。"""
    data = client.post(recommend_path, json=payload()).json()["data"]
    for rec in data["recommendations"]:
        path = next(
            p for p in data["development_paths"]
            if p["occupation_id"] == rec["occupation_id"]
        )
        node_skills = {node["skill_id"] for node in path["nodes"]}
        assert set(rec["skills_to_improve"]) <= node_skills
