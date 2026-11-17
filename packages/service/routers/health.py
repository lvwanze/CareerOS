#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : health.py
# @Path       : packages/service/routers/health.py
# @Project    : CareerOS
# @Author     : 代旭
# @Date       : 2026-11-18 00:05:00
# @Version    : v1.0.0
# @Description: 存活探针 /health 与就绪探针 /ready
# @ChangeLog:
#   2026-11-18 00:05:00 | 代旭 | v1.0.0 | 初始化创建
"""存活探针与就绪探针。

两个探针职责不同，不能合并：
- /health 只判进程活着，依赖挂了也返 200，否则会被反复重启；
- /ready 判能不能干活，依赖不可用时返 503，让流量别打进来。
"""

from fastapi import APIRouter, HTTPException

from packages.service.config import ENGINE_TAG

router = APIRouter(tags=["health"])


def is_knowledge_base_ready() -> bool:
    """判断职业技能知识库与匹配引擎是否可用。

    当前阶段引擎是占位实现（见 decisions.md ADR-002），恒为 True；
    接入真实知识库后改为读 data/processed 的加载状态。
    """
    return True


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
