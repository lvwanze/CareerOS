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
	)
	return results