#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : recommendations.py
# @Path       : packages/service/routers/recommendations.py
# @Project    : CareerOS
# @Author     : 代旭
# @Date       : 2026-11-18 15:40:00
# @Version    : v1.1.0
# @Description: 职业推荐接口：请求校验、三档差距判定、发展路径组织
# @ChangeLog:
#   2026-11-18 15:40:00 | 代旭 | v1.1.0 | 接 Pydantic 请求模型，三档判定改证据优先
#   2026-11-18 00:05:00 | 代旭 | v1.0.0 | 初始化创建
"""职业推荐接口。

接口结构见 docs/api_spec.md §3.1，字段见 docs/data_contract.md §3.5 / §3.6。
当前匹配引擎仍是占位实现（decisions.md ADR-002，算法 11-20 交付），
但请求校验、三档判定、发展路径组织已按最终口径写死，接算法时只换打分来源。

三档判定顺序由赵帝臣 11-18 定稿，四条顺序不可调换：
    1. self_level == 0              -> needs_improvement
    2. evidence_level == "none"     -> needs_verification
    3. self_level >= required_level -> mastered
    4. 其余                          -> needs_improvement
"""

from fastapi import APIRouter

from packages.service.config import TOP_K
from packages.service.response import new_request_id, ok
from packages.service.schemas.request import RecommendRequest, UserProfile

router = APIRouter(tags=["recommendations"])

# 占位职业：用赵帝臣 D1 里得分最高的职业，12 项要求技能取自 O*NET 15-1252.00
STUB_OCCUPATION = {
    "occupation_id": "OCC-ONET-15-1252.00",
    "occupation_name": "软件开发工程师",
    "required_skills": {
        "SKILL-ONET-2.B.3.e": (3, 4.5),
        "SKILL-ONET-2.B.3.b": (3, 4.0),
        "SKILL-ONET-2.B.4.g": (3, 4.0),
        "SKILL-ONET-2.B.4.h": (3, 4.0),
        "SKILL-ONET-2.B.2.i": (3, 4.0),
        "SKILL-ONET-2.B.3.a": (3, 4.0),
        "SKILL-ONET-2.A.1.e": (3, 3.5),
        "SKILL-ONET-2.A.1.a": (2, 3.5),
        "SKILL-ONET-2.A.2.a": (2, 3.0),
        "SKILL-ONET-2.A.2.b": (2, 3.0),
        "SKILL-ONET-2.B.4.e": (2, 3.0),
        "SKILL-ONET-2.B.5.a": (2, 3.0),
    },
}

# 技能中文名：高帅龙这版表不加 name_zh 列，后端兜底映射（M1 的 B4 已确认）
SKILL_NAME_ZH = {
    "SKILL-ONET-2.B.3.e": "编程",
    "SKILL-ONET-2.B.3.b": "系统分析",
    "SKILL-ONET-2.B.4.g": "系统评估",
    "SKILL-ONET-2.B.4.h": "系统设计",
    "SKILL-ONET-2.B.2.i": "故障排查",
    "SKILL-ONET-2.B.3.a": "批判性思维",
    "SKILL-ONET-2.A.1.e": "阅读理解",
    "SKILL-ONET-2.A.1.a": "主动倾听",
    "SKILL-ONET-2.A.2.a": "写作",
    "SKILL-ONET-2.A.2.b": "表达",
    "SKILL-ONET-2.B.4.e": "复杂问题解决",
    "SKILL-ONET-2.B.5.a": "判断与决策",
}


def judge_status(self_level: int, evidence_level: str, required_level: int) -> str:
    """按证据优先的四条顺序判定三档状态。

    Args:
        self_level: 用户自评等级，0~4。
        evidence_level: 能力证据状态，已由请求模型归一化。
        required_level: 职业要求等级，0~4。

    Returns:
        needs_improvement / needs_verification / mastered 之一。
    """
    if self_level == 0:
        return "needs_improvement"
    if evidence_level in ("", "none", None):
        return "needs_verification"
    if self_level >= required_level:
        return "mastered"
    return "needs_improvement"


def build_skill_gaps(profile: UserProfile) -> list[dict]:
    """把用户填报的技能与职业要求逐项比对，产出差距明细。

    Args:
        profile: 已通过校验的用户画像。

    Returns:
        按职业要求的重要程度降序排列的差距明细列表。
    """
    filled = {item.skill_id: item for item in profile.skills}
    ordered = sorted(
        STUB_OCCUPATION["required_skills"].items(),
        key=lambda pair: (-pair[1][1], pair[0]),
    )

    gaps: list[dict] = []
    for skill_id, (required_level, importance) in ordered:
        filled_item = filled.get(skill_id)
        self_level = filled_item.self_level if filled_item else 0
        evidence_level = filled_item.evidence_level if filled_item else "none"
        gaps.append(
            {
                "skill_id": skill_id,
                "skill_name": SKILL_NAME_ZH.get(skill_id, skill_id),
                "current_level": self_level,
                "required_level": required_level,
                "gap": max(0, required_level - self_level),
                "status": judge_status(self_level, evidence_level, required_level),
                "importance": importance,
            }
        )
    return gaps


def score_recommendation(skill_gaps: list[dict]) -> float:
    """按重要程度加权的达成度，得到 0~1 的匹配分数。

    分母取职业要求的权重总和（不是技能个数），这样满分可达、分布能拉开；
    权重按 (importance - 1) / 4 归一化，与算法的口径一致。

    Args:
        skill_gaps: 差距明细列表。

    Returns:
        保留 3 位小数的匹配分数。
    """
    weight_total = 0.0
    weighted_hit = 0.0
    for item in skill_gaps:
        weight = (item["importance"] - 1) / 4
        required = item["required_level"]
        achieve = min(item["current_level"] / required, 1.0) if required else 1.0
        weight_total += weight
        weighted_hit += weight * achieve
    if weight_total == 0:
        return 0.0
    return round(weighted_hit / weight_total, 3)


def build_development_path(occupation_id: str, skill_gaps: list[dict]) -> dict:
    """按差距大小与重要程度排出学习节点，结构对齐 data_contract.md §3.7。

    第一阶段没有技能前置关系数据（赵帝臣 11-18 确认），
    所以 priority 只用「gap 降序 + importance 降序」两级键。

    Args:
        occupation_id: 目标职业 ID。
        skill_gaps: 差距明细列表。

    Returns:
        一条发展路径字典。
    """
    pending = [item for item in skill_gaps if item["status"] != "mastered"]
    pending.sort(key=lambda item: (-item["gap"], -item["importance"], item["skill_id"]))

    nodes: list[dict] = []
    for order, item in enumerate(pending, start=1):
        nodes.append(
            {
                "node_id": f"node_{occupation_id}_{order}",
                "skill_id": item["skill_id"],
                "name": item["skill_name"],
                "status": "not_started",
                "priority": order,
                "description": (
                    f"当前 {item['current_level']} 级，目标 {item['required_level']} 级，"
                    f"需补齐 {item['gap']} 级；建议先完成 2 个小练习再自评一次"
                ),
            }
        )
    return {"path_id": f"path_{occupation_id}", "occupation_id": occupation_id, "nodes": nodes}


def build_reasons(skill_gaps: list[dict], match_score: float) -> list[str]:
    """生成推荐依据，数字全部来自计算结果。"""
    mastered = sum(1 for item in skill_gaps if item["status"] == "mastered")
    total = len(skill_gaps)
    return [
        f"加权匹配度 {match_score:.3f}，满分代表高重要度技能全部达标",
        f"职业要求 {total} 项技能，其中 {mastered} 项已具备",
        "占位结果：匹配引擎尚未接入，分数按加权达成度估算",
    ]


@router.post("/recommendations", summary="提交用户画像，返回职业推荐与发展路径")
def create_recommendations(payload: RecommendRequest) -> dict:
    """接收用户画像，返回 Top-K 推荐与基础发展路径。"""
    request_id = new_request_id()
    profile = payload.profile

    skill_gaps = build_skill_gaps(profile)
    match_score = score_recommendation(skill_gaps)

    recommendation = {
        "occupation_id": STUB_OCCUPATION["occupation_id"],
        "occupation_name": STUB_OCCUPATION["occupation_name"],
        "match_score": match_score,
        "matched_skills": [item["skill_id"] for item in skill_gaps if item["status"] == "mastered"],
        "skills_to_improve": [
            item["skill_id"] for item in skill_gaps if item["status"] == "needs_improvement"
        ],
        "skills_to_verify": [
            item["skill_id"] for item in skill_gaps if item["status"] == "needs_verification"
        ],
        "recommendation_reasons": build_reasons(skill_gaps, match_score),
        "skill_gaps": skill_gaps,
    }

    data = {
        "recommendations": [recommendation][:TOP_K],
        "development_paths": [build_development_path(recommendation["occupation_id"], skill_gaps)],
    }
    return ok(data, request_id)
