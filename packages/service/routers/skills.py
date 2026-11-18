#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : skills.py
# @Path       : packages/service/routers/skills.py
# @Project    : CareerOS
# @Author     : 代旭
# @Date       : 2026-11-18 16:10:00
# @Version    : v1.0.0
# @Description: 技能字典接口：给前端填报页提供可选的 skill_id
# @ChangeLog:
#   2026-11-18 16:10:00 | 代旭 | v1.0.0 | 初始化创建
"""技能字典接口。

为什么需要这个接口：data_contract.md §3.1 规定用户技能用 skill_id 填报，
不是中文名。前端如果拿不到字典，就没有办法生成合法的 skill_id，
填报页只能让用户手打 "SKILL-ONET-2.B.3.e"，实际不可用。

当前数据源是占位常量（与推荐接口共用同一套 ID），
高帅龙的三表到货后改为读 data/processed/skills.csv，接口形状不变。
"""

from fastapi import APIRouter, Query

from packages.service.response import ok
from packages.service.routers.recommendations import SKILL_NAME_ZH

router = APIRouter(tags=["skills"])

# 占位技能分类：第一阶段只有 O*NET 的技能域，先统一标为 skills
SKILL_CATEGORY = "skills"

# 英文原名：与 O*NET Element 对应，前端展示时优先用 name_zh
SKILL_NAME_EN = {
    "SKILL-ONET-2.B.3.e": "Programming",
    "SKILL-ONET-2.B.3.b": "Systems Analysis",
    "SKILL-ONET-2.B.4.g": "Systems Evaluation",
    "SKILL-ONET-2.B.4.h": "Systems Design",
    "SKILL-ONET-2.B.2.i": "Troubleshooting",
    "SKILL-ONET-2.B.3.a": "Critical Thinking",
    "SKILL-ONET-2.A.1.e": "Reading Comprehension",
    "SKILL-ONET-2.A.1.a": "Active Listening",
    "SKILL-ONET-2.A.2.a": "Writing",
    "SKILL-ONET-2.A.2.b": "Speaking",
    "SKILL-ONET-2.B.4.e": "Complex Problem Solving",
    "SKILL-ONET-2.B.5.a": "Judgment and Decision Making",
}


def build_skill_items() -> list[dict]:
    """组装技能字典条目。

    Returns:
        按 skill_id 升序排列的条目列表，每项含 id、英文名、中文名与分类。
    """
    items: list[dict] = []
    for skill_id in sorted(SKILL_NAME_ZH):
        items.append(
            {
                "skill_id": skill_id,
                "name": SKILL_NAME_EN.get(skill_id, skill_id),
                "name_zh": SKILL_NAME_ZH[skill_id],
                "category": SKILL_CATEGORY,
            }
        )
    return items


@router.get("/skills", summary="获取技能字典")
def list_skills(limit: int = Query(default=100, ge=1, le=200, description="返回条数上限")) -> dict:
    """返回可选技能列表，供前端填报页渲染下拉框。

    Args:
        limit: 返回条数上限，防止前端一次拉走整张表。

    Returns:
        统一信封，data 里含 items 与 total。
    """
    items = build_skill_items()
    data = {"items": items[:limit], "total": len(items)}
    return ok(data)
