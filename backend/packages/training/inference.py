from typing import List, Dict, Any
from packages.core.schemas import CareerRecommendation, SkillGap

def generate_recommendations(
	user_skills: Dict[str, int],
	occupation_requirements: List[Dict[str, Any]]
) -> List[CareerRecommendation]:
	"""
	返回符合 data_contract.md §3.5 的推荐结果列表
	"""
	results: List[CareerRecommendation] = []
	# TODO: 实现匹配算法
	# 示例输出结构（必须包含所有字段）
	results.append(
		CareerRecommendation(
			occupation_id="15-1134.00",
			occupation_name="Web Developer",
			match_score=0.751,
			skill_gaps=[
				SkillGap(
					skill_id="SK001",
					gap=1.5,
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
	)
	return results