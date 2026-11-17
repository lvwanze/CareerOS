#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : recommendations.py
# @Path       : packages/service/routers/recommendations.py
# @Project    : CareerOS
# @Author     : 代旭
# @Date       : 2026-11-18 00:05:00
# @Version    : v1.0.0
# @Description: 职业推荐接口（结构定稿，结果仍为占位）
# @ChangeLog:
#   2026-11-18 00:05:00 | 代旭 | v1.0.0 | 初始化创建
"""职业推荐接口。

接口结构按 docs/api_spec.md §3.1 与 docs/data_contract.md §3.5 定稿，
返回内容仍是占位数据：匹配引擎未接入（decisions.md ADR-002）。
请求体下一版换成 Pydantic 请求模型，做 0~4 级范围校验。
"""

from fastapi import APIRouter

from packages.service.config import TOP_K
from packages.service.response import new_request_id, ok

router = APIRouter(tags=["recommendations"])


def _build_placeholder_recommendation(profile: dict) -> dict:
    """用请求里已填的技能拼一条占位推荐，只为验证链路通。

    Args:
        profile: 请求体里的用户画像字典。

    Returns:
        结构符合 data_contract.md §3.5 的推荐结果字典。
    """
    skills = profile.get("skills") or []
    matched_skills = [item.get("skill_id") for item in skills if item.get("self_level", 0) >= 3]
    skills_to_improve = [
        item.get("skill_id") for item in skills if 0 < item.get("self_level", 0) < 3
    ]
    skills_to_verify = [item.get("skill_id") for item in skills if item.get("self_level", 0) == 0]

    return {
        "occupation_id": "OCC-ONET-15-1252.00",
        "occupation_name": "软件开发工程师",
        "match_score": 0.5,
        "matched_skills": matched_skills,
        "skills_to_improve": skills_to_improve,
        "skills_to_verify": skills_to_verify,
        "recommendation_reasons": [
            "占位结果：匹配引擎尚未接入，本条仅用于验证接口结构",
            f"本次共收到 {len(skills)} 项技能填报",
        ],
        "skill_gaps": [
            {
                "skill_id": "SKILL-ONET-2.B.3.e",
                "current_level": 3,
                "required_level": 3,
                "gap": 0,
                "status": "mastered",
            }
        ],
    }


def _build_placeholder_path(occupation_id: str) -> dict:
    """占位发展路径，结构对齐 data_contract.md §3.7。"""
    return {
        "path_id": f"path_{occupation_id}",
        "occupation_id": occupation_id,
        "nodes": [
            {
                "node_id": f"node_{occupation_id}_1",
                "skill_id": "SKILL-ONET-2.B.3.e",
                "name": "Programming",
                "status": "not_started",
                "priority": 1,
                "description": "占位节点：发展路径规则尚未接入",
            }
        ],
    }


@router.post("/recommendations", summary="提交用户画像，返回职业推荐与发展路径")
def create_recommendations(payload: dict) -> dict:
    """接收 {"profile": {...}}，返回 Top-K 推荐与基础发展路径。"""
    request_id = new_request_id()
    profile = payload.get("profile") or {}
    recommendation = _build_placeholder_recommendation(profile)

    data = {
        "recommendations": [recommendation][:TOP_K],
        "development_paths": [_build_placeholder_path(recommendation["occupation_id"])],
    }
    return ok(data, request_id)
