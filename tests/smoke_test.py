# -*- coding: utf-8 -*-
"""matcher 冒烟测试：加载、缓存、打分、字段契约。

运行方式（在项目根目录）：
    .venv\\Scripts\\python.exe tests\\smoke_test.py

不做 pytest 依赖，直接跑，失败即抛 AssertionError。
"""
import sys
from pathlib import Path

# 允许以脚本方式直接运行，把项目根加入 sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.training.matcher import (  # noqa: E402
    MODEL_VERSION,
    _load_data,
    recommend,
)

# 高匹配画像：计算机专业背景，编程/数学 4 级且有项目证据（12 项）
PROFILE_HIGH = {
    "user_id": "user_high",
    "skills": [
        {"skill_id": "SKILL-ONET-2.B.3.e", "self_level": 4, "evidence_level": "project"},   # Programming
        {"skill_id": "SKILL-ONET-2.A.1.e", "self_level": 4, "evidence_level": "project"},   # Mathematics
        {"skill_id": "SKILL-ONET-2.A.2.a", "self_level": 3, "evidence_level": "course"},    # Critical Thinking
        {"skill_id": "SKILL-ONET-2.B.4.g", "self_level": 3, "evidence_level": "course"},    # Systems Analysis
        {"skill_id": "SKILL-ONET-2.B.4.h", "self_level": 3, "evidence_level": "course"},    # Systems Evaluation
        {"skill_id": "SKILL-ONET-2.B.2.i", "self_level": 3, "evidence_level": "project"},   # Complex Problem Solving
        {"skill_id": "SKILL-ONET-2.B.3.b", "self_level": 3, "evidence_level": "project"},   # Technology Design
        {"skill_id": "SKILL-ONET-2.B.3.a", "self_level": 2, "evidence_level": "course"},    # Operations Analysis
        {"skill_id": "SKILL-ONET-2.B.4.e", "self_level": 2, "evidence_level": "course"},    # Judgment and Decision Making
        {"skill_id": "SKILL-ONET-2.A.1.a", "self_level": 3, "evidence_level": "course"},    # Reading Comprehension
        {"skill_id": "SKILL-ONET-2.A.2.b", "self_level": 3, "evidence_level": "self"},      # Active Learning
        {"skill_id": "SKILL-ONET-2.B.5.a", "self_level": 3, "evidence_level": "self"},      # Time Management
    ],
}

# 低匹配画像：只有通用能力，其中一项自评了但没有证据（5 项）
PROFILE_LOW = {
    "user_id": "user_low",
    "skills": [
        {"skill_id": "SKILL-ONET-2.A.1.a", "self_level": 2, "evidence_level": "course"},    # Reading Comprehension
        {"skill_id": "SKILL-ONET-2.A.1.d", "self_level": 2, "evidence_level": "none"},      # Speaking
        {"skill_id": "SKILL-ONET-2.A.1.c", "self_level": 2, "evidence_level": "course"},    # Writing
        {"skill_id": "SKILL-ONET-2.A.1.b", "self_level": 2, "evidence_level": "self"},      # Active Listening
        {"skill_id": "SKILL-ONET-2.B.5.a", "self_level": 2, "evidence_level": "self"},      # Time Management
    ],
}

CONTRACT_FIELDS = {
    "occupation_id",
    "occupation_name",
    "match_score",
    "matched_skills",
    "skills_to_improve",
    "skills_to_verify",
    "recommendation_reasons",
}
GAP_FIELDS = {"skill_id", "current_level", "required_level", "gap", "status"}

# ---- D4 回归基线：固定输入 -> 期望输出，容差 ±0.01 ----
# 数据或算法变更导致分数漂移时，这里必须同步更新并说明原因。
TOLERANCE = 0.01
EXPECTED_HIGH = [
    ("OCC-ONET-15-1252.00", 0.751),   # Software Developers
    ("OCC-ONET-15-2051.00", 0.714),   # Data Scientists
    ("OCC-ONET-15-1255.00", 0.705),   # Web and Digital Interface Designers
    ("OCC-ONET-15-1243.00", 0.647),   # Database Architects
    ("OCC-ONET-15-2099.01", 0.631),   # Bioinformatics Technicians
]
EXPECTED_LOW = [
    ("OCC-ONET-15-1255.00", 0.383),   # Web and Digital Interface Designers
    ("OCC-ONET-15-2051.00", 0.334),   # Data Scientists
    ("OCC-ONET-15-1212.00", 0.312),   # Information Security Analysts
    ("OCC-ONET-15-2051.01", 0.307),   # Business Intelligence Analysts
    ("OCC-ONET-15-2099.01", 0.297),   # Bioinformatics Technicians
]


def main():
    print("=" * 72)
    print("1. 数据加载与缓存")
    first = _load_data()
    second = _load_data()
    print(f"   occupations  : {first['occupations'].shape}")
    print(f"   skills       : {first['skills'].shape}")
    print(f"   relations    : {first['relations'].shape}")
    print(f"   缓存生效(a is b): {first is second}")
    assert first is second, "缓存未生效：两次调用返回了不同对象"
    assert len(first["occupations"]) == 28

    print("=" * 72)
    print("2. 高匹配画像 Top-5")
    high = recommend(PROFILE_HIGH, top_k=5)
    for rank, item in enumerate(high, 1):
        mastered = len(item["matched_skills"])
        improve = len(item["skills_to_improve"])
        verify = len(item["skills_to_verify"])
        print(
            f"   {rank}. {item['match_score']:.3f}  {item['occupation_name']:<42s}"
            f" 掌握{mastered:2d} 提升{improve:2d} 验证{verify:2d}"
        )

    print("=" * 72)
    print("3. 低匹配画像 Top-5")
    low = recommend(PROFILE_LOW, top_k=5)
    for rank, item in enumerate(low, 1):
        mastered = len(item["matched_skills"])
        improve = len(item["skills_to_improve"])
        verify = len(item["skills_to_verify"])
        print(
            f"   {rank}. {item['match_score']:.3f}  {item['occupation_name']:<42s}"
            f" 掌握{mastered:2d} 提升{improve:2d} 验证{verify:2d}"
        )

    print("=" * 72)
    print("4. 契约校验")
    assert len(high) == 5, f"top_k=5 但返回 {len(high)} 条"
    assert len(low) == 5
    for item in high + low:
        missing = CONTRACT_FIELDS - set(item)
        assert not missing, f"缺少契约字段：{missing}"
        assert 0.0 <= item["match_score"] <= 1.0, f"分数越界：{item['match_score']}"
        assert len(item["occupation_name"]) > 0
        for gap in item["skill_gaps"]:
            miss = GAP_FIELDS - set(gap)
            assert not miss, f"SkillGap 缺少字段：{miss}"
            assert gap["status"] in {"mastered", "needs_improvement", "needs_verification"}
            assert gap["current_level"] >= 0
            assert gap["gap"] == max(0, gap["required_level"] - gap["current_level"])
    print("   字段完整、分数在 [0,1]、status 枚举合法、gap 计算自洽  ✓")

    print("=" * 72)
    print("5. 排序与确定性")
    scores_high = [x["match_score"] for x in high]
    assert scores_high == sorted(scores_high, reverse=True), "未按分数降序"
    again = recommend(PROFILE_HIGH, top_k=5)
    assert [x["occupation_id"] for x in again] == [x["occupation_id"] for x in high], \
        "同一输入两次推荐结果不一致"
    print(f"   降序正确、两次调用完全一致  ✓")

    print("=" * 72)
    print("6. D4 回归基线（容差 ±%.2f）" % TOLERANCE)
    for label, actual, expected in (("高匹配", high, EXPECTED_HIGH), ("低匹配", low, EXPECTED_LOW)):
        for got, (exp_id, exp_score) in zip(actual, expected):
            assert got["occupation_id"] == exp_id, (
                f"{label}职业顺序变了：期望 {exp_id}，实际 {got['occupation_id']}"
            )
            delta = abs(got["match_score"] - exp_score)
            assert delta <= TOLERANCE, (
                f"{label} {exp_id} 分数漂移：期望 {exp_score}，实际 {got['match_score']}，"
                f"差 {delta:.3f} 超出容差"
            )
        print(f"   {label}：5 项职业与分数全部落在容差内  ✓")

    print("=" * 72)
    print("7. 两条边界")
    empty = recommend({"user_id": "u0", "skills": []}, top_k=5)
    print(f"   空画像：返回 {len(empty)} 条，最高分 {empty[0]['match_score']:.3f}")
    assert len(empty) == 5 and all(x["match_score"] == 0.0 for x in empty)

    one = recommend(PROFILE_HIGH, top_k=1)
    print(f"   top_k=1：返回 {len(one)} 条  -> {one[0]['occupation_name']}")
    assert len(one) == 1

    try:
        recommend({"skills": [{"skill_id": "SKILL-ONET-2.B.3.e", "self_level": 9}]})
        raise AssertionError("self_level=9 应当抛 ValueError，但没有")
    except ValueError as exc:
        print(f"   超范围等级被拦下：{exc}")

    print("=" * 72)
    print(f"全部通过  |  MODEL_VERSION = {MODEL_VERSION}")
    print(f"高匹配区间 {min(scores_high):.3f} ~ {max(scores_high):.3f}")
    low_scores = [x["match_score"] for x in low]
    print(f"低匹配区间 {min(low_scores):.3f} ~ {max(low_scores):.3f}")


if __name__ == "__main__":
    main()
