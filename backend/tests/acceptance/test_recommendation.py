"""TC-REC：职业推荐与技能差距测试。

对应报告骨架 5.5 的典型画像合理性检查，全部使用高帅龙 M1 交付包里的
真实职业 ID / 技能 ID。判定口径写在各用例里，方便答辩时说明"谁判的、依据什么"。

注意：这些断言针对的是 reference 参考算法 + 真实知识库的组合；
赵帝臣的正式算法接入后需复测，若排序变化属预期，应更新这里的判定口径。
"""

from factories import (
    OCC_BI_ANALYSTS,
    OCC_COMPUTER_PROGRAMMERS,
    OCC_DATA_SCIENTISTS,
    OCC_SOFTWARE_DEVELOPERS,
    OCC_STATISTICIANS,
    OCC_WEB_DESIGNERS,
    SKILL_ACTIVE_LEARNING,
    SKILL_COMPLEX_PROBLEM_SOLVING,
    SKILL_CRITICAL_THINKING,
    SKILL_LISTENING,
    SKILL_MATHEMATICS,
    SKILL_PROGRAMMING,
    SKILL_READING,
    SKILL_SYSTEMS_ANALYSIS,
    SKILL_WRITING,
    base_profile,
    profile_with_skills,
)
from reference.algorithm import match_profile


def _rank(profile):
    """返回 {occupation_id: 排名}，Top-5 之外的职业记为 6。"""
    recs = match_profile(profile)["recommendations"]
    return {item["occupation_id"]: i for i, item in enumerate(recs, start=1)}


def rank_of(rank, occupation_id):
    """Top-5 未包含时返回 6（排名最末，便于比较）。"""
    return rank.get(occupation_id, 6)


def test_TC_REC_01_profile_a_zero_base_liberal_arts():
    """画像 A：零基础文科生，写作/阅读为主，不应推荐软件开发。"""
    profile = profile_with_skills([
        (SKILL_WRITING, 2, "self"),
        (SKILL_READING, 1, "self"),
        (SKILL_LISTENING, 1, "self"),
    ])
    rank = _rank(profile)
    assert rank_of(rank, OCC_WEB_DESIGNERS) < rank_of(rank, OCC_SOFTWARE_DEVELOPERS)
    assert rank_of(rank, OCC_BI_ANALYSTS) < rank_of(rank, OCC_SOFTWARE_DEVELOPERS)


def test_TC_REC_02_profile_b_student_with_coding_basics():
    """画像 B：有编程基础学生，编程类职业应进入前二。"""
    profile = profile_with_skills([
        (SKILL_PROGRAMMING, 3, "verified"),
        (SKILL_MATHEMATICS, 2, "self"),
        (SKILL_SYSTEMS_ANALYSIS, 1, "self"),
    ])
    rank = _rank(profile)
    assert min(
        rank_of(rank, OCC_COMPUTER_PROGRAMMERS),
        rank_of(rank, OCC_DATA_SCIENTISTS),
    ) <= 2


def test_TC_REC_03_profile_e_highly_matched():
    """画像 E：与目标职业高度匹配，数据科学家应排第一。"""
    profile = profile_with_skills([
        (SKILL_PROGRAMMING, 4, "verified"),
        (SKILL_MATHEMATICS, 3, "verified"),
        (SKILL_CRITICAL_THINKING, 3, "project"),
        (SKILL_COMPLEX_PROBLEM_SOLVING, 3, "verified"),
        (SKILL_ACTIVE_LEARNING, 2, "self"),
    ])
    rank = _rank(profile)
    assert rank_of(rank, OCC_DATA_SCIENTISTS) == 1
    assert rank_of(rank, OCC_STATISTICIANS) <= 3


def test_TC_REC_04_recommendation_reasons_not_empty():
    """可解释性：每条推荐必须有非空的推荐依据。"""
    recs = match_profile(base_profile())["recommendations"]
    for rec in recs:
        assert rec["recommendation_reasons"]
        assert all(isinstance(reason, str) and reason for reason in rec["recommendation_reasons"])


def test_TC_REC_05_gap_status_matches_verify_list():
    """待验证技能与差距分级口径一致（已具备但未验证 → skills_to_verify）。"""
    profile = profile_with_skills([
        (SKILL_PROGRAMMING, 4, "self"),
        (SKILL_MATHEMATICS, 1, "self"),
    ])
    data = match_profile(profile)
    for path in data["development_paths"]:
        verify_nodes = [
            n for n in path["nodes"] if n["status"] == "needs_verification"
        ]
        rec = next(
            r for r in data["recommendations"]
            if r["occupation_id"] == path["occupation_id"]
        )
        assert {n["skill_id"] for n in verify_nodes} <= set(rec["skills_to_verify"])
