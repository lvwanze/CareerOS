"""TC-ALG：算法输入输出测试。

当前跑在 reference/algorithm.py（按 problem.md 技术路线实现的参考版本）。
接入赵帝臣的正式算法后，把顶部 import 换掉即可；若签名不同导致失败，
说明算法调用接口与契约不一致，需要双方确认——这正是测试要暴露的问题。
"""

import pytest
from factories import base_profile
from reference.algorithm import classify_gap, match_profile


def _result(profile):
    return match_profile(profile)


@pytest.mark.algorithm
def test_TC_ALG_01_top5_and_descending_order():
    """Top-5 数量正确且按匹配分降序。"""
    recs = _result(base_profile())["recommendations"]
    assert len(recs) == 5
    scores = [r["match_score"] for r in recs]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.algorithm
def test_TC_ALG_02_score_range():
    """match_score 是 0～1 的相对指标（契约：不代表就业概率）。"""
    recs = _result(base_profile())["recommendations"]
    assert all(0 <= r["match_score"] <= 1 for r in recs)


@pytest.mark.algorithm
def test_TC_ALG_03_skill_lists_are_disjoint():
    """已具备 / 待加强 / 待验证三类技能互不重叠。"""
    for rec in _result(base_profile())["recommendations"]:
        matched = set(rec["matched_skills"])
        improve = set(rec["skills_to_improve"])
        verify = set(rec["skills_to_verify"])
        assert not (matched & improve)
        assert not (matched & verify)
        assert not (improve & verify)


@pytest.mark.parametrize(
    "current,required,evidence,expected_gap,expected_status",
    [
        (3, 3, "verified", 0, "mastered"),
        (1, 3, "self", 2, "needs_improvement"),
        (3, 2, "self", 0, "needs_verification"),
        (0, 2, None, 2, "needs_improvement"),
    ],
)
@pytest.mark.algorithm
def test_TC_ALG_04_gap_classification(
    current, required, evidence, expected_gap, expected_status
):
    """技能等级差值与三档状态的计算规则。"""
    gap, status = classify_gap(current, required, evidence)
    assert (gap, status) == (expected_gap, expected_status)


@pytest.mark.algorithm
def test_TC_ALG_05_development_paths_align_with_recommendations():
    """每条推荐都有对应发展路径，节点状态合法。"""
    data = _result(base_profile())
    rec_ids = {r["occupation_id"] for r in data["recommendations"]}
    paths = data["development_paths"]
    assert {p["occupation_id"] for p in paths} == rec_ids
    allowed = {
        "not_started", "learning", "needs_improvement", "needs_verification", "completed"
    }
    for path in paths:
        assert path["path_id"]
        for node in path["nodes"]:
            assert node["status"] in allowed
            assert node["node_id"] and node["skill_id"] and node["name"]


@pytest.mark.algorithm
def test_TC_ALG_06_deterministic_output():
    """相同输入应得到相同输出（排序稳定，便于复现实验）。"""
    profile = base_profile()
    assert _result(profile) == _result(profile)


@pytest.mark.algorithm
def test_TC_ALG_07_empty_skills_returns_zero_scores():
    """空技能画像不应崩溃，得分为 0 且仍是 5 条。"""
    profile = base_profile()
    profile["skills"] = []
    recs = _result(profile)["recommendations"]
    assert len(recs) == 5
    assert all(r["match_score"] == 0 for r in recs)
