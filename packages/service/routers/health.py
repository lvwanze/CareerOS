#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : health.py
# @Path       : packages/service/routers/health.py
# @Project    : CareerOS
# @Author     : 代旭
# @Date       : 2026-11-18 15:55:00
# @Version    : v1.1.0
# @Description: 存活探针 /health 与就绪探针 /ready（ready 真跑一条样例）
# @ChangeLog:
#   2026-11-18 15:55:00 | 代旭 | v1.1.0 | ready 改为真跑推荐链路最小闭环
#   2026-11-18 00:05:00 | 代旭 | v1.0.0 | 初始化创建
"""存活探针与就绪探针。

两个探针职责不同，不能合并：
- /health 只判进程活着，依赖挂了也返 200，否则会被反复重启；
- /ready 判能不能干活，依赖不可用时返 503，让流量别打进来。

/ready 不能只判"对象非空"，要真跑一次样例输入（讲师红线 37），
所以这里构造一份最小画像，走一遍「差距判定」的真实代码路径。
"""

import logging

from fastapi import APIRouter, HTTPException

from packages.service.config import ENGINE_TAG
from packages.service.routers.recommendations import build_skill_gaps
from packages.service.schemas.request import LearningStage, Preferences, UserProfile, UserSkill

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


def build_probe_profile() -> UserProfile:
    """构造一份最小可用画像，用于就绪探针真跑一次链路。

    Returns:
        只填一项技能的用户画像，字段与其他接口完全同构。
    """
    return UserProfile(
        user_id="health_probe",
        learning_stage=LearningStage(),
        preferences=Preferences(),
        skills=[UserSkill(skill_id="SKILL-ONET-2.B.3.e", self_level=2, evidence_level="none")],
    )


def is_knowledge_base_ready() -> bool:
    """真跑一条样例，确认推荐链路可用。

    Returns:
        链路返回了非空差距明细时视为就绪；任何异常都视为未就绪。
    """
    try:
        gaps = build_skill_gaps(build_probe_profile())
        return len(gaps) > 0
    except Exception:
        logger.exception("就绪探针执行失败，知识库或匹配链路不可用")
        return False


@router.get("/health", summary="存活探针：进程是否活着")
def health_check() -> dict:
    """只返回进程存活，不检查依赖。"""
    return {"status": "ok"}


@router.get("/ready", summary="就绪探针：能否对外提供服务")
def readiness_check() -> dict:
    """依赖不可用时返回 503，避免把请求打给一个不能干活的进程。"""
    if not is_knowledge_base_ready():
        raise HTTPException(status_code=503, detail="知识库或匹配引擎未就绪")
    return {"status": "ready", "engine": ENGINE_TAG}
