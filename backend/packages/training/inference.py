# -*- coding: utf-8 -*-
"""推理层：把算法输出转换成 API 契约模型。

分层职责（配合组长确定的「方案二：matcher 与 inference 并存」）
------------------------------------------------------------------
  matcher.py    纯算法实现。只依赖 pandas / numpy，不 import FastAPI，
                返回普通 dict，方便单独测试和离线评估。
  inference.py  适配层（本文件）。import matcher 和 core.schemas，
                负责把 dict 转成 Pydantic 模型，是 service 层唯一的调用入口。
  routers/      只做 HTTP 校验、异常映射和响应包装，不碰算法细节。

为什么不让路由直接调 matcher：
  matcher 返回的是 dict，字段名和类型都不会被校验。前端拿到 gap 是 int
  还是 float、match_score 超没超过 1，全靠约定。经过 Pydantic 这一层，
  契约错在服务端就暴露，不会漏到前端变成运行时崩溃。

对外入口
--------
generate_recommendations(profile, top_k=5, diversity_theta=0.90)
    返回 list[CareerRecommendation]，已通过模型校验。

build_response_data(profile, user_id=None, top_k=5)
    返回 RecommendResponseData，即响应体 data 字段的完整结构。

输入格式
--------
profile = {
    "user_id": "u_001",                       # 可选，缺失时由调用方补
    "skills": [
        {"skill_id": "SKILL-ONET-2.B.3.e",
         "self_level": 4,                     # 必填，整数 0~4
         "evidence_level": "project"},        # 可选，缺省按 none 处理
    ],
}
"""
from __future__ import annotations

import logging

from packages.core.schemas import (
	CareerRecommendation,
	RecommendResponseData,
	SkillGap,
)
from packages.training.matcher import MODEL_VERSION, recommend

logger = logging.getLogger(__name__)

__all__ = ["generate_recommendations", "build_response_data", "MODEL_VERSION"]


def _to_skill_gap(raw: dict) -> SkillGap:
	"""matcher 的差距明细 dict -> SkillGap 模型。

	注意：schemas.SkillGap 里没有 skill_name 字段，matcher 多返回的这个键
	只给前端展示用，在这里被静默丢弃。如果以后契约要加，改 schemas，
	不要在这里塞进 extra 字段绕过校验。
	"""
	return SkillGap(
		skill_id=raw["skill_id"],
		gap=raw["gap"],
		status=raw["status"],
		current_level=raw["current_level"],
		required_level=raw["required_level"],
	)


def _to_recommendation(raw: dict) -> CareerRecommendation:
	"""matcher 的单条推荐 dict -> CareerRecommendation 模型。"""
	return CareerRecommendation(
		occupation_id=raw["occupation_id"],
		occupation_name=raw["occupation_name"],
		match_score=raw["match_score"],
		skill_gaps=[_to_skill_gap(g) for g in raw["skill_gaps"]],
		recommendation_reasons=raw["recommendation_reasons"],
		matched_skills=raw["matched_skills"],
		skills_to_improve=raw["skills_to_improve"],
		skills_to_verify=raw["skills_to_verify"],
	)


def generate_recommendations(
	profile: dict,
	top_k: int = 5,
	diversity_theta: float = 0.90,
) -> list[CareerRecommendation]:
	"""跑匹配算法并转换成契约模型。

	返回条数在 [0, top_k] 之间，**不保证等于 top_k**。
	调用方和前端都要按「最多 top_k 条」处理，不能写死。
	"""
	raw_results = recommend(profile, top_k=top_k, diversity_theta=diversity_theta)
	return [_to_recommendation(item) for item in raw_results]


def build_response_data(
	profile: dict,
	user_id: str | None = None,
	top_k: int = 5,
	diversity_theta: float = 0.90,
) -> RecommendResponseData:
	"""组装响应体的 data 部分。

	user_id 优先取显式传入的值（通常来自鉴权上下文），
	其次回退到画像里的 user_id，都没有就空串——不在这里抛错，
	因为 user_id 的合法性属于路由层的校验职责。
	"""
	resolved_user_id = user_id or profile.get("user_id") or ""
	if not resolved_user_id:
		logger.warning("build_response_data 未拿到 user_id，响应里将为空串")

	return RecommendResponseData(
		user_id=resolved_user_id,
		model_version=MODEL_VERSION,
		recommendations=generate_recommendations(
			profile, top_k=top_k, diversity_theta=diversity_theta
		),
	)
