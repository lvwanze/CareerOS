# -*- coding: utf-8 -*-
"""推理层：把 matcher 的算法输出转换成 API 契约模型。

分层职责
--------
  matcher.py    纯算法实现。只依赖 pandas / numpy，不 import FastAPI。
                权重、达成度、三档判定、相似职业去重都在这里。
  inference.py  适配层（本文件）。接收 service 层组装好的
                occupation_requirements，转成 matcher 的索引结构算分，
                再把 dict 结果转成 Pydantic 模型。
  routers/      HTTP 校验、异常映射、响应包装，不碰算法细节。

为什么算法不让路由直接调：
  matcher 返回的是 dict，字段名和类型都不会被校验。前端拿到 gap 是 int
  还是 float、match_score 超没超过 1，全靠约定。经过 Pydantic 这一层，
  契约错在服务端就暴露，不会漏到前端变成运行时崩溃。

为什么要有「数据注入」这条路：
  路由已经把三张表组装成 occupation_requirements（还附带中英文名），
  算法再自己读一遍 CSV 就重复了，而且两份数据可能不同步。
  所以 matcher 提供了 build_index / recommend_from_index，
  这里用它构建索引，保证在线服务和离线评估跑的是同一套权重和判定。

对外入口
--------
generate_recommendations(user_skills, occupation_requirements, limit=5)
    返回 list[CareerRecommendation]，已通过模型校验。

参数
----
user_skills : dict[str, int | dict]
    {skill_id: 等级} 或 {skill_id: {"level": 3, "evidence": "project"}}。
    只给 int 时按「自述证据（self）」处理——用户确实自己填了等级，
    但不是所有场景都需要区分证据强度；需要时传 dict 即可，无需改接口。

occupation_requirements : list[dict]
    [{"occupation_id", "occupation_name", "occupation_name_zh",
      "skills": [{"skill_id", "skill_name", "skill_name_zh",
                  "importance", "required_level"}]}]
"""
from __future__ import annotations

import logging

import pandas as pd

from packages.core.schemas import (
	CareerRecommendation,
	SkillGap,
)
from packages.training.matcher import (
	MODEL_VERSION,
	build_index,
	recommend_from_index,
)

logger = logging.getLogger(__name__)

__all__ = ["generate_recommendations", "MODEL_VERSION"]

# 用户只填等级、没填证据时的默认值。
# 用 "self" 而不是 "none"：用户主动自评本身就是一种证据，
# 若用 "none" 会把所有技能都判成「待验证」，界面上满屏待验证。
DEFAULT_EVIDENCE = "self"


def _iter_skill_items(user_skills: dict):
	"""把两种入参格式统一成 (skill_id, level, evidence) 三元组。"""
	for skill_id, value in user_skills.items():
		if isinstance(value, dict):
			level = value.get("level", value.get("self_level", 0))
			evidence = value.get("evidence", value.get("evidence_level"))
		else:
			level = value
			evidence = None
		yield skill_id, level, evidence or DEFAULT_EVIDENCE


def _prepare(occupation_requirements: list[dict]):
	"""把路由组装的数据转成 matcher 的索引，同时留下展示用的查表。

	返回 (index, occ_name_zh, skill_name_zh, importance)
	"""
	rows = []
	occ_names: dict[str, str] = {}
	occ_name_zh: dict[str, str | None] = {}
	skill_names: dict[str, str] = {}
	skill_name_zh: dict[str, str | None] = {}
	importance: dict[tuple[str, str], float | None] = {}

	for occupation in occupation_requirements:
		occupation_id = occupation["occupation_id"]
		occ_names[occupation_id] = occupation.get("occupation_name") or occupation_id
		occ_name_zh[occupation_id] = occupation.get("occupation_name_zh")

		for skill in occupation.get("skills") or []:
			skill_id = skill["skill_id"]
			skill_names.setdefault(skill_id, skill.get("skill_name") or skill_id)
			skill_name_zh.setdefault(skill_id, skill.get("skill_name_zh"))
			importance[(occupation_id, skill_id)] = skill.get("importance")
			rows.append(
				{
					"occupation_id": occupation_id,
					"skill_id": skill_id,
					"importance": skill.get("importance", 0.0),
					"required_level": skill.get("required_level", 0),
				}
			)

	index = build_index(pd.DataFrame(rows), occ_names, skill_names)
	return index, occ_name_zh, skill_name_zh, importance


def _reasons_from_gaps(gaps: list[dict], skill_name_zh: dict, limit: int = 4) -> list[str]:
	"""用中文技能名生成推荐依据。

	规则与 matcher._build_reasons 一致（先说 2 条已达标的，再补缺口 ≥2 的），
	区别只在于这里能拿到中文名。matcher 不碰中文，展示层的拼装放在适配层。
	"""

	def label(skill_id: str) -> str:
		return skill_name_zh.get(skill_id) or skill_id

	reasons: list[str] = []
	for gap in gaps:
		if gap["status"] == "mastered" and len(reasons) < 2:
			reasons.append(f"{label(gap['skill_id'])} 已达标")
	for gap in gaps:
		if gap["status"] == "needs_improvement" and gap["gap"] >= 2 and len(reasons) < limit:
			reasons.append(f"{label(gap['skill_id'])} 还差 {gap['gap']} 级")
	return reasons


def _to_model(raw: dict, occ_name_zh: dict, skill_name_zh: dict, importance: dict) -> CareerRecommendation:
	"""matcher 的单条推荐 dict -> CareerRecommendation 模型。"""
	occupation_id = raw["occupation_id"]

	# matcher 内部按权重（importance_norm × idf）排序，那是为了算分和挑推荐依据。
	# 对外展示要求「重要的技能排前面」，所以这里按原始 importance 重排一次。
	gaps = sorted(
		raw["skill_gaps"],
		key=lambda gap: importance.get((occupation_id, gap["skill_id"])) or 0.0,
		reverse=True,
	)

	return CareerRecommendation(
		occupation_id=occupation_id,
		occupation_name=raw["occupation_name"],
		occupation_name_zh=occ_name_zh.get(occupation_id),
		match_score=raw["match_score"],
		skill_gaps=[
			SkillGap(
				skill_id=gap["skill_id"],
				skill_name=gap.get("skill_name"),
				skill_name_zh=skill_name_zh.get(gap["skill_id"]),
				gap=gap["gap"],
				importance=importance.get((occupation_id, gap["skill_id"])),
				status=gap["status"],
				current_level=gap["current_level"],
				required_level=gap["required_level"],
			)
			for gap in gaps
		],
		recommendation_reasons=_reasons_from_gaps(gaps, skill_name_zh),
		matched_skills=raw["matched_skills"],
		skills_to_improve=raw["skills_to_improve"],
		skills_to_verify=raw["skills_to_verify"],
	)


def generate_recommendations(
	user_skills: dict,
	occupation_requirements: list[dict],
	limit: int = 5,
) -> list[CareerRecommendation]:
	"""跑匹配算法并转换成契约模型。

	返回条数在 [0, limit] 之间，**不保证等于 limit**：
	相似职业被去重后可选数量会变少，调用方不能写死 5。
	"""
	if not user_skills or not occupation_requirements:
		return []

	index, occ_name_zh, skill_name_zh, importance = _prepare(occupation_requirements)

	profile = {
		"skills": [
			{
				"skill_id": skill_id,
				"self_level": level,
				"evidence_level": evidence,
			}
			for skill_id, level, evidence in _iter_skill_items(user_skills)
		]
	}

	raw_results = recommend_from_index(index, profile, top_k=limit)
	if not raw_results:
		logger.info("本轮未产生推荐：输入 %d 项技能", len(user_skills))
		return []

	return [_to_model(item, occ_name_zh, skill_name_zh, importance) for item in raw_results]
