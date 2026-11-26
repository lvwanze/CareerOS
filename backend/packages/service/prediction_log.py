#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : prediction_log.py
# @Path       : backend/packages/service/prediction_log.py
# @Project    : CareerOS
# @Author     : 2428324206代旭
# @Date       : 2026-11-26 16:10:00
# @Version    : v1.0.0
"""预测记录：每次推荐成功后追加一行 JSONL（清单「加分项二：预测记录与回流」）。

为什么值得做：
    服务是无状态的，"这次推荐用了哪版模型、什么样的画像、返回了什么"过一小时就查不到。
    预测记录把一次请求固化成一行，同一行里的 request_id 与响应体、响应头、日志是同一个，
    于是"线上发生了什么"第一次可以被事后复现。这也是漂移监控（加分项三）的数据来源。

为什么写失败绝不能影响响应：
    记录是旁路（清单原文"旁路"）。磁盘满、权限错、路径被占，都只应该打一条 warning，
    让调用方照常拿到推荐结果——把观测能力做成故障源，是这类功能最常见的翻车方式。
    所有异常都在 record_prediction 内部吞掉，调用点不需要 try。

为什么路径从 knowledge.DATA_DIR 推：
    架构测试锁定"数据目录推算点不得新增"（现状 4 处）。这里不写 parents[N]，
    改成复用 knowledge 已算好的 DATA_DIR，再取它的上一级目录——既满足约束，
    也符合"数据入口收敛到一处"的方向。

文件位置与生命周期：
    backend/predictions.jsonl，已在 .gitignore 第 18 行预留（不提交，属运行时产物）。
    演示与验收时删掉重来即可，不影响任何冻结数据。
"""
import json
import logging
from datetime import datetime

from packages.core.request_context import current_request_id

from packages.service import knowledge

logger = logging.getLogger(__name__)

# knowledge.DATA_DIR 是 backend/data，上一级是 backend，日志落在 backend/predictions.jsonl
PREDICTIONS_PATH = knowledge.DATA_DIR.parent / "predictions.jsonl"

# 画像里可能出现的"每周投入时长"字段名（前端传参口径不统一时逐个试）
_WEEKLY_HOUR_KEYS = ("weekly_hours", "hours_per_week", "weekly_hours_invested")


def _profile_digest(profile) -> dict:
    """画像摘要：技能数、每周时长、逐条自评等级。

    只记能解释推荐结果的最小集合，不记 user_id 等可识别信息——
    预测记录是运行日志，不是用户档案。
    """
    skills = getattr(profile, "skills", None) or []
    digest = {
        "skill_count": len(skills),
        "skills": {item.skill_id: item.self_level for item in skills},
    }
    extra = getattr(profile, "model_extra", None) or {}
    for key in _WEEKLY_HOUR_KEYS:
        if key in extra and extra[key] is not None:
            digest["weekly_hours"] = extra[key]
            break
    return digest


def _contributions(top_recommendation) -> list[dict]:
    """第一条推荐的逐项贡献：importance × gap，取前 5 条。

    与 matcher 的打分口径一致：差距越大、该技能越重要，对排序的影响越大。
    这里只做记录，不参与打分，避免"记录逻辑反过来影响结果"。
    """
    gaps = getattr(top_recommendation, "skill_gaps", None) or []
    scored = []
    for gap in gaps:
        if gap.gap <= 0:
            continue
        importance = gap.importance if gap.importance is not None else 0.0
        scored.append(
            {
                "skill_id": gap.skill_id,
                "gap": gap.gap,
                "importance": round(float(importance), 4),
                "weight": round(float(importance) * gap.gap, 4),
            }
        )
    scored.sort(key=lambda item: item["weight"], reverse=True)
    return scored[:5]


def build_record(profile, recommendations, model_version: str) -> dict:
    """组装一行记录。字段对齐清单要求：id、时间、模型版本、画像摘要、返回与贡献。

    model_version 由调用方传入而不是这里 import training 的常量：
    架构测试禁止 service 新增对 training 的依赖（ADR-009 只放行 recommend.py 的推理入口），
    记录模块没必要为了一个字符串去踩这条线。
    """
    return {
        "request_id": current_request_id(),
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "model_version": model_version,
        "profile": _profile_digest(profile),
        "returns": [
            {
                "occupation_id": item.occupation_id,
                "match_score": round(float(item.match_score), 4),
            }
            for item in recommendations
        ],
        "contributions": _contributions(recommendations[0]) if recommendations else [],
    }


def record_prediction(profile, recommendations, model_version: str) -> None:
    """追加一行预测记录。任何失败都只在日志里留痕，不抛给调用方。"""
    try:
        record = build_record(profile, recommendations, model_version)
        PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with PREDICTIONS_PATH.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    except (OSError, TypeError, ValueError) as exc:
        # 旁路失败：warning 即可，绝不把 500 抛给前端
        logger.warning("预测记录写入失败（不影响本次响应）：%s", exc)
