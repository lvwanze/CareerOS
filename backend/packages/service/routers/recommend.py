import csv
from pathlib import Path

from fastapi import APIRouter
from packages.core.schemas import (
ApiResponse,
RecommendResponse,
RecommendResponseData,
CareerRecommendation,
SkillGap,
SkillOption,
)

router = APIRouter(prefix="/api/v1", tags=["recommend"])
DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _load_used_skills() -> list[SkillOption]:
	with (DATA_DIR / "processed" / "occupation_skills.csv").open(encoding="utf-8", newline="") as file:
		used_skill_ids = {row["skill_id"] for row in csv.DictReader(file)}

	with (DATA_DIR / "processed" / "skills.csv").open(encoding="utf-8", newline="") as file:
		return [
			SkillOption(
				skill_id=row["skill_id"],
				name=row["name"],
				category=row["category"],
				used_in_kb=True,
			)
			for row in csv.DictReader(file)
			if row["skill_id"] in used_skill_ids
		]


@router.get("/skills", response_model=ApiResponse)
async def list_skills():
	return ApiResponse(code=200, message="success", data=_load_used_skills())

@router.post("/recommend", response_model=ApiResponse)
async def recommend(user_profile: dict):
	# TODO: 调用算法模块获取推荐结果
	# 示例数据（临时mock）
	mock_data = RecommendResponseData(
		user_id="test_user",
		model_version="v1.0",
		recommendations=[
			CareerRecommendation(
				occupation_id="OCC-ONET-15-1252.00",
				occupation_name="Software Developers",
				match_score=0.751,
				skill_gaps=[
					SkillGap(
						skill_id="SKILL-ONET-2.A.1.a",
						skill_name="Reading Comprehension",
						gap=1,
						importance=3.5,
						status="needs_improvement",
						current_level=1,
						required_level=2,
					)
				],
				recommendation_reasons=["技能匹配度高"],
				matched_skills=[],
				skills_to_improve=["SKILL-ONET-2.A.1.a"],
				skills_to_verify=[],
			)
		],
	)
	return ApiResponse(
		code=200,
		message="success",
		data=mock_data,
	)