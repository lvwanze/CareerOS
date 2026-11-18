from fastapi import APIRouter, HTTPException
from packages.core.schemas import (
ApiResponse,
RecommendResponse,
RecommendResponseData,
CareerRecommendation,
SkillGap,
)

router = APIRouter(prefix="/api/v1", tags=["recommend"])

@router.post("/recommend", response_model=ApiResponse)
async def recommend(user_profile: dict):
	# TODO: 调用算法模块获取推荐结果
	# 示例数据（临时mock）
	mock_data = RecommendResponseData(
		user_id="test_user",
		model_version="v1.0",
		recommendations=[
			CareerRecommendation(
				occupation_id="15-1134.00",
				occupation_name="Web Developer",
				match_score=0.751,
				skill_gaps=[
					SkillGap(
						skill_id="SK001",
						gap=2,
						status="needs_improvement",
						current_level=2,
						required_level=4,
					)
				],
				recommendation_reasons=["技能匹配度高"],
				matched_skills=["SK002", "SK003"],
				skills_to_improve=["SK001"],
				skills_to_verify=["SK004"],
			)
		],
	)
	return ApiResponse(
		code=200,
		message="success",
		data=mock_data,
	)